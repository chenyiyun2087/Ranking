# 触发条件验证 - SQL 查询语句

## 在 MySQL 数据库中直接执行以下 SQL

### 1️⃣ 查询【收盘价 ≥ 60日高】的股票

```sql
-- 方法1: 简洁版本（推荐）
SELECT ts_code, COUNT(*) as match_count
FROM dwd_stock_daily_standard d1
WHERE d1.trade_date = '20260213'
GROUP BY d1.ts_code
HAVING d1.adj_close >= (
    SELECT MAX(d2.adj_high)
    FROM dwd_stock_daily_standard d2
    WHERE d2.ts_code = d1.ts_code
    AND d2.trade_date BETWEEN DATE_SUB('20260213', INTERVAL 60 DAY) AND '20260213'
)
LIMIT 20;

-- 方法2: 计数版本
SELECT COUNT(DISTINCT d1.ts_code) as '收盘价≥60日高的股票数'
FROM dwd_stock_daily_standard d1
WHERE d1.trade_date = '20260213'
AND d1.adj_close >= (
    SELECT MAX(d2.adj_high)
    FROM dwd_stock_daily_standard d2
    WHERE d2.ts_code = d1.ts_code
    AND d2.trade_date BETWEEN DATE_SUB('20260213', INTERVAL 60 DAY) AND '20260213'
);
```

**预期结果:** 应该很少或为 0 个股票（因为市场处于下跌阶段）

---

### 2️⃣ 查询【成交量比 ≥ 1.5倍MA20】的股票

```sql
-- 首先查看一些样本数据
SELECT 
    ts_code,
    trade_date,
    vol as '今日成交量',
    ROUND(vol / AVG(vol) OVER (PARTITION BY ts_code ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING), 2) as '与MA20的比率'
FROM dwd_stock_daily_standard
WHERE trade_date = '20260213'
LIMIT 20;

-- 计数：成交量比 >= 1.5
SELECT COUNT(DISTINCT ts_code) as '成交量比≥1.5的股票数'
FROM dwd_stock_daily_standard d1
WHERE d1.trade_date = '20260213'
AND d1.vol >= 1.5 * (
    SELECT AVG(d2.vol)
    FROM dwd_stock_daily_standard d2
    WHERE d2.ts_code = d1.ts_code
    AND d2.trade_date BETWEEN DATE_SUB('20260213', INTERVAL 20 DAY) AND '20260213'
);
```

**预期结果:** 应该很少（分析报告说只有 0.5% ≈ 2个）

---

### 3️⃣ 查询【3日资金流 > 0】的股票

```sql
-- 查看资金流样本
SELECT 
    ts_code,
    trade_date,
    net_mf_amount,
    SUM(net_mf_amount) OVER (PARTITION BY ts_code ORDER BY trade_date) as '累计资金流'
FROM ods_moneyflow
WHERE trade_date >= '20260211'
LIMIT 20;

-- 计数：3日资金流 > 0
SELECT COUNT(*) as '3日资金流>0的股票数'
FROM (
    SELECT ts_code
    FROM ods_moneyflow
    WHERE trade_date >= '20260211'
    AND trade_date <= '20260213'
    GROUP BY ts_code
    HAVING SUM(net_mf_amount) > 0
) flow_stocks;

-- 详细显示资金流数据
SELECT 
    ts_code,
    SUM(net_mf_amount) as '3日总资金流'
FROM ods_moneyflow
WHERE trade_date >= '20260211'
GROUP BY ts_code
HAVING SUM(net_mf_amount) > 0
ORDER BY SUM(net_mf_amount) DESC
LIMIT 10;
```

**预期结果:** 应该很少（分析报告说只有 0.2% ≈ 1个）

---

### 4️⃣ 同时满足三个条件的股票

```sql
-- 如果上面三个条件都满足，理论上应该有 Breakout 信号
SELECT 
    d1.ts_code,
    d1.trade_date,
    d1.adj_close,
    d1.vol
FROM dwd_stock_daily_standard d1
WHERE d1.trade_date = '20260213'
AND d1.adj_close >= (
    SELECT MAX(d2.adj_high)
    FROM dwd_stock_daily_standard d2
    WHERE d2.ts_code = d1.ts_code
    AND d2.trade_date BETWEEN DATE_SUB('20260213', INTERVAL 60 DAY) AND '20260213'
)
AND d1.vol >= 1.5 * (
    SELECT AVG(d2.vol)
    FROM dwd_stock_daily_standard d2
    WHERE d2.ts_code = d1.ts_code
    AND d2.trade_date BETWEEN DATE_SUB('20260213', INTERVAL 20 DAY) AND '20260213'
)
AND (
    SELECT SUM(net_mf_amount)
    FROM ods_moneyflow
    WHERE ts_code = d1.ts_code
    AND trade_date >= '20260211'
) > 0;
```

**预期结果:** 应该为 0 个（因为几乎没有股票同时满足三个条件）

---

## 📌 使用方法

1. **打开 MySQL 客户端**（命令行或 MySQL Workbench）
2. **选择数据库**：`USE tushare_stock;`
3. **复制上面的 SQL 查询**
4. **执行查询**
5. **观察结果** - 验证分析报告中的统计数字是否正确

## 🎯 预期验证结果

根据分析报告，你应该看到：

| 条件 | 预期数量 | 预期比例 |
|------|---------|---------|
| 收盘价 ≥ 60日高 | ~0 | 0.0% |
| 成交量比 ≥ 1.5 | ~2 | 0.5% |
| 3日资金流 > 0 | ~1 | 0.2% |
| **全部满足** | **0** | **0%** |

如果实际数字与这些预期值接近，就证明了分析报告的结论是正确的！
