# Ranking - 交易池复盘识别引擎

本项目实现了一个**收盘后交易池复盘识别系统**，围绕 ODS/DWD/DWS 数据分层，输出“作战池/候选池/观察池/风险清单/池子健康度”。

> 当前实现是一个可迭代的工程骨架：已具备完整 pipeline、核心规则和测试，可在此基础上继续补齐环境因子、字段映射细节与策略细化。

---

## 1. 项目目标

输入：
- `trade_date`
- `pool_id`（DB 成分池）或 `pool_file`（文件池）

输出：
- 明细表：`dws_pool_replay_daily`
- 健康度表：`dws_pool_health_daily`
- 文件：
  - `output/pool_battle_pool.csv`
  - `output/pool_candidate_pool.csv`
  - `output/pool_hold_watch.csv`
  - `output/pool_risk_list.csv`
  - `output/report_pool_{pool_id}_{trade_date}.md`

---

## 2. 项目组织架构

```text
pool_replay_engine/
  config/
    default.yaml                 # 运行参数（当前内容为 JSON 格式）
  cli.py                         # CLI 入口，串联整条 pipeline
  src/
    datastore/
      store.py                   # SQLite 数据读取与结果写入
      pool.py                    # pool_file 读取
      calendar.py                # 前一交易日工具函数
      adapters.py                # 标签标准化
    features/
      price.py                   # 价格特征（MA/High/ATR/量比/收益等）
      flow.py                    # 资金流特征（1/3/5日、比率）
      chip.py                    # 筹码特征透传
      env.py                     # 环境占位模块
    signals/
      filters.py                 # 硬过滤 + risk_flags
      trigger.py                 # breakout/pullback 触发与触发强度
      scoring.py                 # base_score + risk_penalty
      state_machine.py           # 状态机与 action
    outputs/
      writer.py                  # CSV 列表输出 + 健康度统计
      report_md.py               # Markdown 报告生成
tests/
  test_trigger.py                # 触发器测试
  test_state_machine.py          # 状态流转测试
  test_filters.py                # 过滤规则测试
  test_scoring.py                # 排序与打分测试
```

---

## 3. 业务逻辑（按 pipeline）

### Step 0：确定股票池 Universe

在 `cli.py` 中按以下优先逻辑读取：
1. 传入 `--pool-id`：调用 `DataStore.get_pool_members(pool_id, date)`
2. 传入 `--pool-file`：读取 CSV 的 `ts_code`

### Step 1：加载窗口数据

- 价格：`dwd_stock_daily_standard`（窗口）
- 标签：`dwd_stock_label_daily`（当日）
- 资金：`ods_moneyflow`（窗口）
- 筹码：`dwd_chip_stability`（当日）
- 评分：`dws_momentum_score/dws_technical_score/dws_capital_score/dws_chip_score`（当日）

### Step 2：硬过滤（Hard Filters）

`signals/filters.py` 生成 `risk_flags` 与 `avoid`：
- `is_st == 1`
- `list_days < new_stock_days`
- `vol <= 0` 或 `amount <= 0`
- `high == low`（一字板风险）
- `amount < min_amount`（流动性不足）

只要命中任一条，`avoid=1`，最终状态会强制为 `AVOID`。

### Step 3：特征构建

#### 价格特征（`features/price.py`）
- `ma20`, `ma60`
- `high_60`（breakout lookback）
- `vol_ma20`, `vol_ratio`
- `close_pos`
- `atr_pct`（当前简化实现）
- `ma20_slope`
- `ret_10`
- `recent_breakout`

#### 资金特征（`features/flow.py`）
- `flow_1d`
- `flow_3d`
- `flow_5d`
- `flow_ratio`
- `flow_ratio_3d`

#### 筹码特征（`features/chip.py`）
- 当前为透传（后续可扩展清洗/标准化）。

### Step 4：触发器识别（`signals/trigger.py`）

#### A. breakout
满足：
- `close >= high_60`
- `vol_ratio >= vol_ratio_min`
- `flow_3d > 0`

#### B. pullback
满足：
- `recent_breakout >= 1`
- `low <= ma20 * (1 + pullback_tol)`
- `close >= ma20`
- `vol_ratio <= pullback_vol_ratio_max`
- `flow_3d > 0`

输出：
- `is_breakout`
- `is_pullback`
- `is_trigger`
- `trigger_type`

### Step 5：触发强度（trigger_strength）

将以下因子做分位排名后加权：
- `close/high_60 - 1`
- `vol_ratio`
- `flow_ratio_3d`
- `close_pos`
- `chip_stable_score`

加权后映射到 0~100。

### Step 6：基础分（base_score）

`signals/scoring.py`：
- `base_score = 0.35*momentum + 0.30*technical + 0.25*capital + 0.10*chip`

### Step 7：风险扣分（risk_penalty）

当前扣分项：
- `atr_pct > atr_pct_max`
- `cost_dev > high_cost_dev`
- `vol_ratio > 2 and close_pos < 0.4`
- `risk_flags` 含 `one_price`

### Step 8：最终分（pool_final_score）

在 `cli.py` 中计算：

```text
pool_final_score = clip(base_score + trigger_bonus_weight * trigger_strength - risk_penalty, 0, 100)
```

### Step 9：状态机（`signals/state_machine.py`）

状态：
- `WATCH / SETUP / TRIGGER / HOLD / WEAKEN / DROP / AVOID`

流转核心：
- 硬风险直接 `AVOID`
- `SETUP + is_trigger -> TRIGGER`
- `TRIGGER` 延续 -> `HOLD`
- 转弱条件 -> `WEAKEN`
- `WEAKEN` 且跌破中期条件 -> `DROP`
- 其余按趋势条件进入 `SETUP` 或回到 `WATCH`

动作映射：
- `TRIGGER -> BUY_READY`
- `HOLD + pullback -> ADD`
- `HOLD -> HOLD`
- `WEAKEN -> REDUCE`
- `DROP -> SELL`
- `AVOID -> AVOID`
- 其他 -> `WATCH`

### Step 10：结果输出

1. 写库：
   - `dws_pool_replay_daily`
   - `dws_pool_health_daily`
2. 写文件：
   - battle/candidate/hold/risk 四类 CSV
   - Markdown 报告

---

## 4. 配置说明

配置文件路径：`pool_replay_engine/config/default.yaml`

> 注意：文件后缀为 `.yaml`，但当前内容是 JSON 结构；`cli.py` 使用 `json.load()` 读取。

主要配置区块：
- `db`: 数据库连接
- `pool`: 各列表 TopK
- `window`: 回看窗口
- `filters`: 硬过滤阈值
- `trigger`: 触发参数
- `risk`: 风险阈值
- `scoring`: 评分权重

---

## 5. 运行方式

```bash
python -m pool_replay_engine.cli run-daily --date 20260220 --pool-id 3
python -m pool_replay_engine.cli run-daily --date 20260220 --pool-file ./pool.csv
```

---

## 6. 测试

```bash
pytest -q
```

覆盖点：
- breakout/pullback 触发
- 状态机流转
- 硬过滤 AVOID
- 触发加分导致排序提升

---

## 7. 当前实现边界与后续建议

### 已实现
- 完整可运行流程
- 可落库/可出报表
- 基本单元测试

### 待增强
- `env.py` 增加指数/行业风险开关
- 配置读取统一为 YAML（或统一改名 `.json`）
- `store.py` 增加更严格字段容错与批量写优化
- pullback “曾经突破”的定义可改成更严格窗口事件
- 报告内容可增加 reasons 的可读化解释
---

## 8. 权重配置指南

### 配置位置

权重配置在 `pool_replay_engine/config/default.yaml` 中的 `scoring` 块：

```json
"scoring": {
  "base_weights": {
    "momentum": 0.25,      // 动量 (25%)
    "value": 0.20,         // 估值 (20%)
    "quality": 0.20,       // 质量 (20%)
    "technical": 0.15,     // 技术 (15%)
    "capital": 0.10,       // 资金 (10%)
    "chip": 0.10           // 筹码 (10%)
  },
  "trigger_bonus_weight": 0.4,          // TRIGGER时的奖励权重 (40%)
  "setup_base_score_threshold": 10      // SETUP入选阈值
}
```

### 权重说明

**各维度含义**：
- `momentum`: 动量维度（DWS中的 `dws_momentum_score`）
- `value`: 估值维度（DWS中的 `dws_value_score`，PE/PB/PS）
- `quality`: 质量维度（DWS中的 `dws_quality_score`，ROE/利润率）
- `technical`: 技术维度（DWS中的 `dws_technical_score`，MACD/KDJ等）
- `capital`: 资金维度（DWS中的 `dws_capital_score`，大单资金）
- `chip`: 筹码维度（DWS中的 `dws_chip_score`，持仓集中度）

**权重总和建议不超过 1.0**（代表100%）。虽然技术上可超过1，但通常不推荐：
- 权重 > 1：会导致某个因子过度强调，可能引致评分过度波动
- 权重 < 1：评分会被压低，影响评分区分度
- 最佳实践：总和 = 1.0，通过调整各因子比例来改变策略偏向

### 实际应用公式

```text
base_score = momentum_score × 0.25 
           + value_score × 0.20 
           + quality_score × 0.20 
           + technical_score × 0.15 
           + capital_score × 0.10 
           + chip_score × 0.10

pool_final_score = clip(base_score + trigger_bonus_weight × trigger_strength - risk_penalty, 0, 100)
```

---

## 9. 执行评分流程与输出

### 执行命令

配置完权重后，执行：

```bash
# 自选股池评分
python -m pool_replay_engine.cli run-daily --date 20260213 --pool-file pool.csv

# 指定数据库池评分
python -m pool_replay_engine.cli run-daily --date 20260213 --pool-id <pool_id>

# 指定其他日期和配置
python -m pool_replay_engine.cli run-daily --date YYYYMMDD --pool-file <pool_file> --config <config_path>
```

### 输出文件

执行后自动在 `output/` 目录生成以下文件：

```
output/
├── report_pool_-1_20260213.md       # 📋 评分摘要 (n_trigger, n_setup等)
├── pool_risk_list.csv              # 📊 完整清单 (所有股票评分明细)
├── pool_battle_pool.csv            # ⚡ TRIGGER池 (可直接交易)
├── pool_candidate_pool.csv         # 📈 SETUP池 (等待触发)
└── pool_hold_watch.csv             # 持仓观察 (HOLD状态)
```

### 快速查看结果

**查看评分摘要**：
```bash
cat output/report_pool_-1_20260213.md
```

输出示例：
```
# Pool Replay Report pool=-1 date=20260213

## 池子健康度摘要
- n_trigger=1 n_setup=3 n_hold=0 n_weaken=115 n_drop=0 n_avoid=0
- up_ratio=35.92%
```

**查看完整列表前20行**：
```bash
head -20 output/pool_risk_list.csv
```

**查看TRIGGER股票**：
```bash
grep "TRIGGER" output/pool_risk_list.csv
```

### 数据库持久化

评分结果同时写入两个表（自动持久化）：

**1. `dws_pool_replay_daily`** - 每日评分明细
```bash
mysql -h localhost -u root -p<password> ranking -e \
  "SELECT ts_code, state, base_score, pool_final_score 
   FROM dws_pool_replay_daily 
   WHERE trade_date='20260213' AND pool_id=-1 AND state='TRIGGER';"
```

**2. `dws_pool_health_daily`** - 池子健康度汇总
```bash
mysql -h localhost -u root -p<password> ranking -e \
  "SELECT * FROM dws_pool_health_daily 
   WHERE trade_date='20260213' AND pool_id=-1;"
```

### 修改权重后的重新评分

1. 编辑 `pool_replay_engine/config/default.yaml` 中的权重
2. 重新执行评分命令
3. 新的 `output/` 文件会覆盖旧文件
4. 数据库表记录保留历史（按 pool_id 和 trade_date 区分）

---

## 10. Web 管理平台（新增）

新增了一个 Flask Web 平台，提供三个核心模块：

- 任务调度：创建/启停/删除评分定时任务，支持立即执行和执行历史查看
- 股票池更新：在线维护 `pool*.csv`（增删代码、CSV 上传替换）
- 评分展示：展示 `output/` 中 battle/candidate/hold/risk 明细与最新健康度

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动平台

```bash
python run_web.py
```

默认访问地址：

```text
http://127.0.0.1:8050
```

### 代码位置

- `run_web.py`: Web 启动入口
- `ranking_web/app.py`: 路由与页面控制
- `ranking_web/scheduler.py`: 内置轻量定时任务与持久化
- `ranking_web/services.py`: 评分执行、CSV 读写、数据汇总服务
- `ranking_web/templates/`: 页面模板
- `ranking_web/static/`: 样式与前端交互
- `web_data/scheduler_state.json`: 调度任务与执行历史持久化文件
