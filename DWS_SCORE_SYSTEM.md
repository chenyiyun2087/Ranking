# DWS 评分系统详解

## 概述

DWS (Data Warehouse System) 评分系统是 Ranking 项目的核心评分引擎，用于对股票进行多维度评分。

### 核心公式

```
base_score = 0.35 × momentum_score + 0.30 × technical_score + 0.25 × capital_score + 0.10 × chip_score
```

| 维度 | 权重 | 满分 | 实际最高 |
|------|------|------|---------|
| 动量 (momentum) | 35% | 25 | 25 |
| 技术 (technical) | 30% | 9 | 10 |
| 资金 (capital) | 25% | 5 | 3 |
| 筹码 (chip) | 10% | 5 | 4 |
| **合计** | **100%** | **44** | **11.65** |

---

## 四维度评分详解

### 1️⃣ 动量评分 (dws_momentum_score)

**表名**: `dws_momentum_score`  
**主键**: trade_date, ts_code  
**更新频率**: 每个交易日

#### 包含的子分数：

| 字段 | 说明 | 取值 | 来源 |
|------|------|------|------|
| **ret_5_score** | 5日收益率分数 | 0-5 | 过去5个交易日涨跌幅 |
| **ret_20_score** | 20日收益率分数 | 0-5 | 过去20个交易日涨跌幅 |
| **ret_60_score** | 60日收益率分数 | 0-5 | 过去60个交易日涨跌幅 |
| **vol_ratio_score** | 成交量比分数 | 0-10 | 当日成交量 vs 20日均量 |
| **turnover_score** | 换手率分数 | 0-10 | 当日换手率 |
| **mtm_score** | 动量分数 | 0-10 | Momentum指标值 |
| **mtmma_score** | 动量均线分数 | 0-10 | Momentum均线偏离度 |

#### 合成方式：

```python
momentum_score = sum([ret_5_score, ret_20_score, ret_60_score, 
                      vol_ratio_score, turnover_score, 
                      mtm_score, mtmma_score])
# 最高 = 5+5+5+10+10+10+10 = 55，但实际因监管上限约 25
```

#### 示例（000628.SZ，20260213）：

```
ret_5_score:     0 (5日涨跌幅差)
ret_20_score:    3 (20日涨幅较好)
ret_60_score:    5 (60日涨幅突出)
vol_ratio_score: 3 (成交量2倍20日均)
turnover_score:  4 (换手率4%)
mtm_score:       5 (Momentum正值)
mtmma_score:     3 (均线向上)
───────────────────────── 
momentum_score:  23 ✅
```

---

### 2️⃣ 技术评分 (dws_technical_score)

**表名**: `dws_technical_score`  
**主键**: trade_date, ts_code  
**说明**: 技术面评价表

#### 包含的指标分数：

| 字段 | 说明 | 取值 | 指标含义 |
|------|------|------|---------|
| **macd_score** | MACD分数 | 0-5 | MACD柱子强度 |
| **kdj_score** | KDJ分数 | 0-5 | KDJ快速线位置 |
| **rsi_score** | RSI分数 | 0-5 | RSI相对强弱指数 |
| **cci_score** | CCI分数 | 0-5 | CCI顺势指标 |
| **bias_score** | BIAS分数 | 0-5 | 乖离率指标 |

#### 合成方式：

```python
technical_score = sum([macd_score, kdj_score, rsi_score, 
                       cci_score, bias_score])
# 最高 = 5+5+5+5+5 = 25，实际最高约 10
```

#### 示例（000628.SZ，20260213）：

```
macd_score:  2 (MACD弱势)
kdj_score:   1 (KDJ低位80)
rsi_score:   2 (RSI中性)
cci_score:   1 (CCI中性)
bias_score:  1 (乖离率小)
──────────────────
technical_score: 7 ✅ (较弱)
```

**问题诊断**: 技术面评分偏低，说明当前技术形态不够强势

---

### 3️⃣ 资金评分 (dws_capital_score)

**表名**: `dws_capital_score`  
**主键**: trade_date, ts_code  
**说明**: 大资金进出评价表

#### 包含的资金指标：

| 字段 | 说明 | 取值 | 数据单位 |
|------|------|------|---------|
| **elg_net** | 超大单净额 | 实数 | 万元 (超过100万元单笔) |
| **lg_net** | 大单净额 | 实数 | 万元 (50-100万元单笔) |
| **elg_score** | 超大单评分 | 0-2 | 正/负/中性 |
| **lg_score** | 大单评分 | 0-2 | 正/负/中性 |
| **margin_score** | 融资融券评分 | 0-1 | 融资余额趋势 |

#### 合成方式：

```python
capital_score = sum([elg_score, lg_score, margin_score])
# 最高 = 2+2+1 = 5，实际最高约 3
```

#### 示例（000628.SZ，20260213）：

```
elg_net:      2500 (超大单净流入)
lg_net:       1800 (大单净流入)
elg_score:    1 (小幅正流)
lg_score:     1 (小幅正流)
margin_score: 0 (融资融券无明显变化)
────────────────────────────
capital_score: 2 ✅ (资金中性偏弱)
```

**问题诊断**: 资金评分最低，说明机构资金没有积极介入

---

### 4️⃣ 筹码评分 (dws_chip_score)

**表名**: `dws_chip_score`  
**主键**: trade_date, ts_code  
**说明**: 持股结构评价表

#### 包含的筹码指标：

| 字段 | 说明 | 取值 | 含义 |
|------|------|------|------|
| **winner_score** | 获利盘评分 | 0-5 | 浮盈投资者比例 |
| **cost_score** | 成本分布评分 | 0-5 | 持仓成本集中度 |

#### 合成方式：

```python
chip_score = sum([winner_score, cost_score])
# 最高 = 5+5 = 10，实际最高约 4-5
```

#### 示例（000628.SZ，20260213）：

```
winner_score: 3 (60% 投资者浮盈)
cost_score:   1 (成本分散)
──────────────────
chip_score:   4 ✅
```

**含义**: 大部分投资者获利，但成本分散，缺乏一致性

---

## 数据流与计算链路

### 数据来源关系

```
【原始数据层 ODS】
├─ ods_moneyflow (资金流向)
├─ dwd_stock_daily_standard (日线数据)
└─ ods_holder (持股信息)
    ↓ [聚合计算]
【数据仓库层 DWS】
├─ dws_momentum_score (动量评分)
├─ dws_technical_score (技术评分)
├─ dws_capital_score (资金评分)
└─ dws_chip_score (筹码评分)
    ↓ [加权合成]
【应用层】
    base_score = 35%×m + 30%×t + 25%×c + 10%×ch
    pool_final_score = base_score + trigger_bonus - risk_penalty
```

### 加载流程（代码中的调用）

```python
# 1. 从4个DWS表读取分数
scores = ds.load_dws_scores_daily(universe, date)
# SELECT m.ts_code, m.momentum_score, t.technical_score, 
#        c.capital_score, ch.chip_score
# FROM dws_momentum_score m
# LEFT JOIN dws_technical_score t ON ...
# LEFT JOIN dws_capital_score c ON ...
# LEFT JOIN dws_chip_score ch ON ...

# 2. 使用配置权重合成base_score
bases = compute_base_score(rows, cfg["scoring"]["base_weights"])
# base_score[i] = 0.35*m + 0.30*t + 0.25*c + 0.10*ch

# 3. 加入触发奖励和风险惩罚
final_score = base_score + trigger_bonus - risk_penalty
```

---

## 当前系统的问题分析

### 问题：base_score 太保守

| 日期 | 最高分 | 需要分 | 通过率 |
|------|--------|--------|--------|
| 20260213 | 11.65 | 60 | 0% ❌ |

**原因链**：
1. DWS 4个分数表本身设计都很保守
   - momentum_score 最高 25（能达到的很少）
   - technical_score 最高 10（技术形态要求高）
   - capital_score 最高 3（大资金门票高）
   - chip_score 最高 4（筹码集中度要求高）

2. 权重分配不均
   - 动量权 35% → 贡献最多
   - 技术权 30% → 次要
   - 资金权 25% → 第三
   - 筹码权 10% → 最少

3. 绝对阈值过高
   - SETUP 需要 base_score >= 60
   - 但整个市场最高才 11.65
   - **无法进SETUP就无法TRIGGER** ❌

---

## 配置位置

[pool_replay_engine/config/default.yaml](pool_replay_engine/config/default.yaml)

```yaml
"scoring": {
  "base_weights": {
    "momentum": 0.35,    # 动量权重
    "technical": 0.3,    # 技术权重
    "capital": 0.25,     # 资金权重
    "chip": 0.1          # 筹码权重
  },
  "trigger_bonus_weight": 0.4  # 触发奖励权重
}
```

---

## 改进建议

### 短期 (无需改数据表)

1. **降低SETUP进入阈值**
   ```yaml
   # 从 base_score >= 60 改为 >= 10
   # 这样至少能进入SETUP和TRIGGER状态
   ```

2. **重新校准权重**
   ```yaml
   # 改为更平衡的权重，如：
   "base_weights": {
     "momentum": 0.25,    # 从35%降到25%
     "technical": 0.3,
     "capital": 0.25,
     "chip": 0.2          # 从10%升到20%
   }
   ```

### 中期 (需要调整DWS表)

3. **放宽各维度的评分标准**
   - ret_score 范围改为 0-10 而非 0-5
   - vol_ratio_score 阈值降低
   - 大资金评分标准调整

4. **增加触发奖励**
   ```yaml
   "trigger_bonus_weight": 0.6  # 从0.4升到0.6
   ```

### 长期

5. **重新设计DWS分数系统**
   - 参考业界成熟的评分体系
   - 与实际交易收益率做回测对标

---

## 总结

**DWS分数系统 = 4个独立的评分表 × 加权平均**

但当前问题是**所有评分都太保守**，导致没有任何股票能达到 base_score >= 60 的SETUP入场条件。

这不是bug，而是设计上的保守策略。但这个策略对自选股池来说过于严苛，导致n_trigger永远为0。
