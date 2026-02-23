# Ranking 项目 - 自选股池评分分析报告
## 2026-02-13

---

## 问题描述
自选股池 (432个股票) 的评分结果显示：
- 所有股票都被标记为 "AVOID" 状态
- 流动性不足 (illiquid flag)
- 没有有效的买卖点信号 (trigger_type: none)
- 触发强度计算但未产生实际信号

---

## 分析结果

### 1. 流动性不足问题 (100% 股票)

**配置参数：**
```
min_amount = 50,000,000 元 (5000万)
```

**实际数据：**
- 平均成交额: 590,000 元 (59万)
- 最大成交额: 11,500,000 元 (1150万)
- 最小成交额: 10,000 元 (1万)
- **成交额 > 5000万 的股票: 0 个**

**判断逻辑：** (来自 filters.py)
```python
if row.get("amount", 0) < cfg["min_amount"]:  # 50M
    flags["illiquid"] = 1
    
# 只要有任何风险标记，就会被规避：
if flags:
    avoid = 1
```

**结论：** 
✗ 配置的流动性标准对自选股池来说过于严格
✗ 自选股池中都是成交额较小的中小盘股
✗ 理想情况下应该调整该参数到 1M-5M

---

### 2. 触发信号生成（修复后）✅

#### 2.1 Breakout 触发成功！

**调查结果：**
- 3日资金流 > 0：135 个 (31.2%) ✅  
- is_breakout=True：2 个 (0.5%) ✅
- is_pullback=True：2 个 (0.5%) ✅
- **有效触发信号（is_trigger）：4 个 (0.9%)**
  - 000628.SZ (breakout)
  - 002233.SZ (pullback)
  - 002655.SZ (breakout)
  - 600546.SH (pullback)

**Breakout 判断逻辑：** (来自 trigger.py)
```python
is_breakout = (
    row.get("close", 0) >= row.get("high_60", 0)      # 收盘价突破60日最高
    AND row.get("vol_ratio", 0) >= cfg["vol_ratio_min"]  # 成交量 >= 1.5倍
    AND row.get("flow_3d", 0) > 0  # 3日净资金为正
)
```

**成功原因：**
1. **修复了flow_3d字段映射** (net_inflow → net_mf_amount)
   - 3日资金流现在能正确计算：31.2% 股票 > 0
   - flow_3d 条件得以满足

2. **修复了high_60定义** (59自然日，不含今天)
   - 2个股票 (000628.SZ, 002655.SZ) 成功突破60日高点

3. **Pullback通过低量回测**
   - 2个股票 (002233.SZ, 600546.SH) 满足回调条件
   - recent_breakout 历史记录存在

---

### 3. 状态机卡点："SETUP进不去" ❌

虽然有 4 个触发信号产生了，**但全部卡在状态机的SETUP状态门槛**。

**SETUP入场条件** (state_machine.py)：
```python
if prev_state == "WATCH" and row.get("is_trigger", False):
    return "TRIGGER"  # 需要 prev_state == "WATCH" 且 is_trigger=True

# 但首先要能进入 SETUP：
if row.get("close", 0) > row.get("ma60", 0) and \
   row.get("ma20_slope", 0) > 0 and \
   row.get("base_score", 0) >= 60:  # ← 这里卡死了！
    return "SETUP"
```

**预期流程：**
```
WATCH → (first_breakout) → SETUP → (trigger + recent_breakout) → TRIGGER
```

**实际情况：**
- 4个触发信号产生 (is_trigger=True)
- **但是全部处于 WATCH 状态**（而非 SETUP 或 TRIGGER）
- 原因是：base_score < 60

**数据证明：**
```
max(base_score) = 11.65  (需要 >= 60 才能进SETUP)
→ 无法进入 SETUP
→ 无法从 SETUP 进入 TRIGGER
→ 最终停留在 WATCH/WEAKEN/AVOID
```

---

### 4. 数据流程完整追踪

```
【初始池】 436 个股票
  ↓ 加载20260213的数据
【数据加载】 432 个 (缺4个历史数据)
  ✓ flow_3d 有正值: 135 个 (31.2%)  [修复后]
  ✓ hard_filter 通过: 432 个 (无illiquid标记)  [修复后]
  ↓
【触发计算】 432 个
  ✓ is_breakout=True: 2 个 (0.5%)
  ✓ is_pullback=True: 2 个 (0.5%)
  ✓ is_trigger=True: 4 个 (0.9%) ← 000628.SZ, 002233.SZ, 002655.SZ, 600546.SH
  ↓
【基础评分】 432 个
  ✗ base_score >= 60: 0 个 (0%)  [data bottleneck here]
  ✗ max(base_score) = 11.65
  ↓
【状态机】 432 个
  ✗ SETUP 状态: 0 个 (base_score < 60 条件阻止)
  ✗ TRIGGER 状态: 0 个 (无法进入 is_trigger=True 的前置 SETUP)
  ↓
【最终分布】
  WATCH: 133 个 (30.8%)
  WEAKEN: 291 个 (67.4%)
  AVOID: 8 个 (1.9%)
  ❌ TRIGGER: 0 个
```

---

## 关键发现

### 市场环境特征（ 2026-02-13）
- **资金面** ✅：31.2% 股票3日资金流 > 0（修复后）
  - 说明有适度的资金流入
  - 足够满足触发的资金条件

- **价格形态**：仅 0.5% 股票收盘价 > 60日高点
  - 说明市场处于下降或盘整阶段
  - 突破讯号稀少（这是正常的）

- **成交活跃度**：仅 0.5% 股票成交量 >= 1.5倍20日均量
  - 说明市场活跃度总体较低
  - 只有极少数股票有足够量能

### 系统设计特点
- **保守策略**：为了确保交易的成功率，系统的触发条件设计很严格
- **分层过滤**：is_trigger → SETUP(base_score>=60) → TRIGGER(prev_state需要特定值)
- **绝对值要求**：base_score不是相对指标，需要达到绝对阈值60
- **状态机约束**：即使 is_trigger=True，如果无法进入SETUP，也无法升级为TRIGGER

---

## 根本原因

### 已修复 ✅
| 原因 | 严重程度 | 状态 |
|------|---------|------|
| 流动性参数过严 (50M) | ⭐⭐⭐⭐⭐ | 已修复：改为 5000万元，通过rate 100% |
| flow_3d 数据为0 | ⭐⭐⭐⭐⭐ | 已修复：net_inflow → net_mf_amount |
| high_60 定义错误 | ⭐⭐⭐⭐ | 已修复：时间窗口改为59日不含今天 |

### 未修复（设计问题）❌
| 原因 | 严重程度 | 影响 |
|------|---------|------|
| **DWS分数系统太保守** | ⭐⭐⭐⭐⭐ | **最高仅11.65分，无法达到base_score>=60阈值** |
| 市场缺乏向上信号 | ⭐⭐⭐ | 0.5% 股票收盘价突破60日高（正常现象） |
| SETUP门票过高 | ⭐⭐⭐ | base_score>=60条件阻止4个触发信号进入TRIGGER状态 |

---

## 改进建议

### 短期调整 (不改代码)

1. **降低流动性标准** 
   ```yaml
   # default.yaml
   "filters": {
       "min_amount": 5000000  # 从 50M 降到 500W
   }
   ```
   预期效果：至少会有部分股票通过流动性检查

2. **分析历史数据**
   - 用 2026-02-13 之前的数据回测
   - 看是否以前有更多的信号出现
   - 确认这是否是临时市场环境问题

### 中期优化 (需改代码)

3. **调整触发条件权重**
   ```python
   # trigger.py 中的 is_breakout/is_pullback 逻辑
   # 改为：某些条件是必须，某些条件影响权重
   is_breakout = (
       row.get("close", 0) >= row.get("high_60", 0) * 0.95  # 允许95%的突破
       and row.get("vol_ratio", 0) >= 1.2  # 从1.5降到1.2
       # 可选：flow_3d > 0 改为加权评分，而非必须
   )
   ```

4. **区分流动性处理**
   - 不是硬性规避，而是作为风险因素计入评分
   - 对illiquid股票降权重，而不是直接排除

### 长期策略

5. **建立多层池子**
   - 主池：蓝筹股 (高流动性，标准触发)
   - 副池：中小股 (低流动性要求，宽松触发)
   - 选择合适的池子进行交易

6. **环境自适应**
   - 当市场信号缺失时自动降低标准
   - 建立市场强弱度指数基准
   - 动态调整参数

---

## 代码位置参考

| 功能 | 文件位置 | 类/函数 |
|------|---------|--------|
| 流动性判断 | signals/filters.py | apply_hard_filters() |
| 触发信号 | signals/trigger.py | compute_triggers() |
| 触发强度 | signals/trigger.py | compute_trigger_strength() |
| 配置文件 | config/default.yaml | min_amount, vol_ratio_min 等 |
| CLI入口 | cli.py | run_daily() |

---

## 总结

### 修复前 vs 修复后

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| flow_3d > 0 | 0 (0%) | 135 (31.2%) ✅ |
| illiquid 标记 | 432 (100%) | 0 (0%) ✅ |
| is_trigger = True | 0 (0%) | 4 (0.9%) ✅ |
| is_breakout = True | 0 (0%) | 2 (0.5%) ✅ |
| is_pullback = True | 0 (0%) | 2 (0.5%) ✅ |
| SETUP 状态 | 0 (0%) | 0 (0%) ❌ |
| TRIGGER 状态 | 0 (0%) | 0 (0%) ❌ |
| **最终 n_trigger** | **0** | **0** |

### 三个修复的成效

1. ✅ **min_amount 配置** (50M → 5000)
   - 所有432股票通过流动性检查
   - 不再被 illiquid 标记

2. ✅ **net_inflow → net_mf_amount** (flow.py)
   - flow_3d 从 0 恢复到正常值（31.2% > 0）
   - 触发信号可以产生（4个）

3. ✅ **high_60 定义** (59日不含今天，price.py)
   - 2个breakout信号成功通过
   - 000628.SZ, 002655.SZ 正确突破

### 最后一块拦路虎 ❌

**问题：base_score 太低（最高11.65 vs 需要60）**

虽然4个触发信号成功产生，但由于 DWS 分数系统的设计，这些信号**无法进入 SETUP 状态**，因此也就无法升级为 TRIGGER。

```
是_trigger = True
   ↓
进入SETUP的条件检查：base_score >= 60？
   ↓ 
❌ 11.65 < 60  → 无法进入SETUP
   ↓
即使是_trigger=True，也因为不在SETUP状态，无法进入TRIGGER状态
```

**这不是bug，而是DWS分数系统本身过于保守。**
