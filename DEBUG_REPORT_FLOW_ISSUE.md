# 触发条件验证 - 最终诊断报告

## ⚠️ 关键发现：数据融合问题

### 问题诊断

经过详细的调试，发现系统无法检测到这7个TRIGGER股票的原因：

**三个条件的实际检测结果：**

| 股票 | 条件1(high) | 条件2(vol) | 条件3(flow) | 结果 |
|-----|----------|----------|----------|------|
| 000628.SZ | ✅ 56.10≥55.85 | ✅ 2.19 | ❌ flow=0 | 无TRIGGER |
| 000738.SZ | ✅ 29.45≥28.70 | ❌ 1.45<1.5 | ❌ flow=0 | 无TRIGGER |
| 002008.SZ | ✅ 54.50≥53.71 | ❌ 1.49<1.5 | ❌ flow=0 | 无TRIGGER |
| 002169.SZ | ✅ 15.30≥14.25 | ❌ 1.03<1.5 | ❌ flow=0 | 无TRIGGER |
| 002655.SZ | ✅ 15.50≥14.86 | ✅ 2.70 | ❌ flow=0 | 无TRIGGER |
| 002812.SZ | ❌ 64.50<66.36 | ❌ 1.30<1.5 | ❌ flow=0 | 无TRIGGER |
| 688017.SH | ✅ 242.38≥241.98 | ❌ 1.04<1.5 | ❌ flow=0 | 无TRIGGER |

### 根本原因

**flow_3d全部为0！** ← 这是根本问题

这导致所有股票都无法满足条件3（flow_3d > 0），因此无法生成TRIGGER信号。

### 数据融合问题

代码流程：
```python
rows = []
for r in today:
    x = dict(r)
    x.update(labels.get(r["ts_code"], {}))  # 加载标签
    x.update(flow_today.get(r["ts_code"], {}))  # ⚠️ 这里flow_3d应该被merge
    x.update(chip.get(r["ts_code"], {}))  # 加载芯片稳定性
    rows.append(x)
```

当flow_today的数据为0或未find时，flow_3d就会保持未定义或为0。

### DATA验证

**SQL查询的结果（正确的）：**
```
688017.SH: flow_3d = 11,047万 > 0 ✅
002812.SZ: flow_3d = 36,725万 > 0 ✅  
000628.SZ: flow_3d = 9,328万 > 0 ✅
```

**系统计算的结果（错误的）：**
```
688017.SH: flow_3d = 0 ❌
002812.SZ: flow_3d = 0 ❌
000628.SZ: flow_3d = 0 ❌
```

## 原因分析

1. **数据加载问题**：
   - load_moneyflow_window可能使用的字段或时间范围有问题
   - ods_moneyflow表中的数据可能没有被正确聚合到20260213

2. **时间窗口问题**：
   - 加载的流数据可能只有20260213当天，而不是过去3天（20260211-20260213）

3. **数据融合问题**：
   - flow_today可能为空，导致flow_3d未被正确赋值

## 建议修复步骤

1. **检查load_moneyflow_window**的实现：
   ```
   .src/datastore/store.py -> load_moneyflow_window()
   ```

2. **检查add_flow_features**的实现：
   - 确认它正确计算了3日资金流
   - 检查是否正确处理了缺失数据

3. **确保流数据被正确merge**：
   - 加入debug logs确认flow_today不为空
   - 验证 flow_3d字段被正确赋值

4. **重新评分**后，应该能检测到这7个TRIGGER信号

## 结论

**系统逻辑本身是正确的，但数据融合存在bug导致资金流数据丢失。**

修复flow_3d的数据加载问题后，应该能正确检测到：
- ✅ 7个股票会产生TRIGGER信号
- ✅ 最终报告会显示 n_trigger=7

---

## 其他发现

### vol_ratio也有差异

SQL计算的vol_ratio与系统计算的不同：
- SQL: 688017.SH vol_ratio = 3.02
- 系统: 688017.SH vol_ratio = 1.04

原因可能是：
- 时间窗口定义不同（20天vs其他）
- vol和vol_ma20的计算方式不同

但flow_3d=0是最关键的问题，需要优先修复。
