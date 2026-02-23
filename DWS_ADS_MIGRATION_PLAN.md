# DWS/ADS 评分系统改造方案

## 现状分析

### 当前项目使用的4维度评分（base_score）

```
base_score = 0.35×momentum + 0.30×technical + 0.25×capital + 0.10×chip
最高分：0.35×25 + 0.30×10 + 0.25×3 + 0.10×4 = 11.65 分 ❌ 问题来源
```

### 底层数据库已有的6维度评分（Claude Score）

```
total_score = 0.25×momentum + 0.20×value + 0.20×quality + 0.15×technical + 0.10×capital + 0.10×chip
最高分：0.25×25 + 0.20×20 + 0.20×20 + 0.15×15 + 0.10×10 + 0.10×10 = 17.5 分 ✓ 更科学
```

---

## 改造方案

### 方案 A：完全迁移到ADS层评分（推荐）

#### 优点：
- 充分利用已有的底层数据
- 评分体系更科学和完善
- 百分位排名确保相对公平性

#### 缺点：
- 需要修改现有的评分逻辑
- 需要理解ADS的百分位排名算法

#### 实施步骤：

**第1步：修改 store.py 中的 load_dws_scores_daily**

```python
# 当前逻辑：只加载4个维度
def load_dws_scores_daily(self, universe, trade_date):
    sql = f"""
    SELECT m.ts_code, m.momentum_score, t.technical_score, c.capital_score, ch.chip_score
    FROM dws_momentum_score m
    LEFT JOIN dws_technical_score t ON ...
    LEFT JOIN dws_capital_score c ON ...
    LEFT JOIN dws_chip_score ch ON ...
    WHERE m.ts_code IN ({ph}) AND m.trade_date=%s
    """
    return self._load_rows(sql, [*universe, trade_date])

# 改为：加载全6维度
def load_dws_scores_daily(self, universe, trade_date):
    sql = f"""
    SELECT m.ts_code, m.momentum_score, v.value_score, q.quality_score, 
           t.technical_score, c.capital_score, ch.chip_score
    FROM dws_momentum_score m
    LEFT JOIN dws_value_score v ON m.ts_code=v.ts_code AND m.trade_date=v.trade_date
    LEFT JOIN dws_quality_score q ON m.ts_code=q.ts_code AND m.trade_date=q.trade_date
    LEFT JOIN dws_technical_score t ON m.ts_code=t.ts_code AND m.trade_date=t.trade_date
    LEFT JOIN dws_capital_score c ON m.ts_code=c.ts_code AND m.trade_date=c.trade_date
    LEFT JOIN dws_chip_score ch ON m.ts_code=ch.ts_code AND m.trade_date=ch.trade_date
    WHERE m.ts_code IN ({ph}) AND m.trade_date=%s
    """
    return self._load_rows(sql, [*universe, trade_date])
```

**第2步：修改 scoring.py 中的 compute_base_score**

```python
# 当前逻辑：4维度权重
def compute_base_score(rows: list[dict], weights: dict) -> list[float]:
    result = []
    for row in rows:
        result.append(
            weights["momentum"] * float(row.get("momentum_score") or 0) +
            weights["technical"] * float(row.get("technical_score") or 0) +
            weights["capital"] * float(row.get("capital_score") or 0) +
            weights["chip"] * float(row.get("chip_score") or 0)
        )
    return result

# 改为：6维度权重
def compute_base_score(rows: list[dict], weights: dict) -> list[float]:
    result = []
    for row in rows:
        result.append(
            weights["momentum"] * float(row.get("momentum_score") or 0) +
            weights["value"] * float(row.get("value_score") or 0) +
            weights["quality"] * float(row.get("quality_score") or 0) +
            weights["technical"] * float(row.get("technical_score") or 0) +
            weights["capital"] * float(row.get("capital_score") or 0) +
            weights["chip"] * float(row.get("chip_score") or 0)
        )
    return result
```

**第3步：修改 config/default.yaml**

```yaml
# 当前配置
"scoring": {
  "base_weights": {
    "momentum": 0.35,
    "technical": 0.3,
    "capital": 0.25,
    "chip": 0.1
  },
  "trigger_bonus_weight": 0.4
}

# 改为：新配置
"scoring": {
  "base_weights": {
    "momentum": 0.25,      # 从 35% 降到 25%
    "value": 0.20,         # 新增：价值评分
    "quality": 0.20,       # 新增：质量评分
    "technical": 0.15,     # 从 30% 降到 15%
    "capital": 0.10,       # 从 25% 降到 10%
    "chip": 0.10           # 同 10%
  },
  "trigger_bonus_weight": 0.4,
  "setup_threshold": {
    "base_score": 30,      # 从 60 降到 30（因为总分更高）
    "momentum_threshold": 5
  }
}
```

**第4步：调整 state_machine.py 中的SETUP进入条件**

```python
# 当前：base_score >= 60（永远无法满足）
def next_state(row: dict, prev_state: str, weaken_vol_ratio: float) -> str:
    if row.get("close", 0) > row.get("ma60", 0) and \
       row.get("ma20_slope", 0) > 0 and \
       row.get("base_score", 0) >= 60:  # ❌ 无法满足
        return "SETUP"

# 改为：设置合理的阈值
def next_state(row: dict, prev_state: str, weaken_vol_ratio: float, cfg: dict) -> str:
    if row.get("close", 0) > row.get("ma60", 0) and \
       row.get("ma20_slope", 0) > 0 and \
       row.get("base_score", 0) >= cfg["setup_threshold"]:  # ✓ 可以满足
        return "SETUP"
```

---

### 方案 B：改进现有评分（折中方案）

如果不想大改现有逻辑，可以在当前4维度基础上做快速优化：

**快速改进（仅改 default.yaml）**

```yaml
"scoring": {
  "base_weights": {
    "momentum": 0.25,    # 从 35% 降到 25%
    "technical": 0.25,   # 从 30% 改为 25%
    "capital": 0.3,      # 从 25% 升到 30%
    "chip": 0.2          # 从 10% 升到 20%
  },
  "trigger_bonus_weight": 0.5,  # 升高触发奖励
  "setup_threshold": 15  # 改为15分（而非60）
}
```

**预期效果**：base_score 最高可达 15.75 分，会有更多股票通过SETUP检查

---

## 验证与测试

### 验证Step 1：创建价值评分样本

```sql
SELECT ts_code, trade_date, pe_score, pb_score, ps_score, value_score
FROM dws_value_score 
WHERE trade_date = '20260213'
LIMIT 5;
```

期望结果：000628.SZ 的 value_score 应该在 2-8 分之间

### 验证Step 2：创建质量评分样本

```sql
SELECT ts_code, trade_date, roe_score, margin_score, leverage_score, quality_score
FROM dws_quality_score 
WHERE trade_date = '20260213'
LIMIT 5;
```

期望结果：000628.SZ 的 quality_score 应该在 2-8 分之间

### 验证Step 3：对比新旧评分

```sql
SELECT m.ts_code,
       m.momentum_score,
       v.value_score,
       q.quality_score,
       t.technical_score,
       c.capital_score,
       ch.chip_score,
       (0.25*m.momentum_score + 0.20*v.value_score + 0.20*q.quality_score + 
        0.15*t.technical_score + 0.10*c.capital_score + 0.10*ch.chip_score) as new_score
FROM dws_momentum_score m
LEFT JOIN dws_value_score v ON m.ts_code=v.ts_code AND m.trade_date=v.trade_date
LEFT JOIN dws_quality_score q ON m.ts_code=q.ts_code AND m.trade_date=q.trade_date
LEFT JOIN dws_technical_score t ON m.ts_code=t.ts_code AND m.trade_date=t.trade_date
LEFT JOIN dws_capital_score c ON m.ts_code=c.ts_code AND m.trade_date=c.trade_date
LEFT JOIN dws_chip_score ch ON m.ts_code=ch.ts_code AND m.trade_date=ch.trade_date
WHERE m.trade_date = '20260213' 
ORDER BY new_score DESC 
LIMIT 10;
```

---

## 改造工作量评估

| 任务 | 难度 | 工作量 | 风险 |
|------|------|--------|------|
| 方案A：完全迁移 | 中 | 2-3小时 | 低（测试充分） |
| 方案B：快速改进 | 低 | 30分钟 | 极低 |

**推荐**：先用方案B快速验证，再考虑方案A的完全迁移。

---

## 关键文件位置

```
pool_replay_engine/
├── src/
│   ├── datastore/
│   │   └── store.py              # 需要修改：load_dws_scores_daily() ← 关键
│   └── signals/
│       ├── scoring.py            # 需要修改：compute_base_score() ← 关键
│       └── state_machine.py       # 需要修改：next_state() 添加cfg参数
├── config/
│   └── default.yaml              # 需要修改：weights和threshold
└── cli.py                         # 调用参数传递
```

---

## 预期效果对比

| 指标 | 方案A（完全迁移） | 方案B（快速改进） |
|------|-----------------|-----------------|
| 最高base_score | 17.5 | 15.75 |
| SETUP阈值 | 30 | 15 |
| 预期SETUP通过率 | ~5-10% | ~3-5% |
| TRIGGER通过率 | ~0.5-1% | ~0.5% |
| n_trigger（预期） | 2-4 | 1-2 |
| 实施难度 | 中等 | 很简单 |
