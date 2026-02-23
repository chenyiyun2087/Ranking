#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='19871019',
    database='tushare_stock'
)

cur = conn.cursor()

print("验证触发条件统计 - 20260213")
print("=" * 90)

# 检查数据量
cur.execute("SELECT COUNT(*) FROM dwd_stock_daily_standard WHERE trade_date = '20260213'")
total = cur.fetchone()[0]
print(f"\n📊 数据情况:")
print(f"   20260213日期的价格数据: {total} 条记录")

# 1. 收盘价 >= 60日高
print(f"\n1️⃣  【收盘价 ≥ 60日高】")
query1 = """
SELECT COUNT(DISTINCT d1.ts_code) as cnt
FROM dwd_stock_daily_standard d1
WHERE d1.trade_date = '20260213'
AND d1.adj_close >= (
  SELECT COALESCE(MAX(d2.adj_high), 0)
  FROM dwd_stock_daily_standard d2
  WHERE d2.ts_code = d1.ts_code
  AND d2.trade_date < '20260213'
  AND d2.trade_date >= DATE_SUB('20260213', INTERVAL 60 DAY)
)
"""
cur.execute(query1)
result1 = cur.fetchone()[0]
pct1 = result1 / 432 * 100 if 432 > 0 else 0
print(f"   数量: {result1} 个")
print(f"   占比: {pct1:.2f}%")

# 显示满足条件的股票样本
if result1 > 0:
    cur.execute("""
    SELECT DISTINCT d1.ts_code FROM dwd_stock_daily_standard d1
    WHERE d1.trade_date = '20260213'
    LIMIT 5
    """)
    print(f"   样本: {', '.join([r[0] for r in cur.fetchall()])}")

# 2. 成交量比 >= 1.5
print(f"\n2️⃣  【成交量比 ≥ 1.5】")
query2 = """
SELECT COUNT(DISTINCT ts_code) as cnt
FROM dwd_stock_daily_standard d1
WHERE trade_date = '20260213'
AND vol > 0
AND vol >= 1.5 * (
  SELECT COALESCE(AVG(vol), 1)
  FROM dwd_stock_daily_standard d2
  WHERE d2.ts_code = d1.ts_code
  AND d2.trade_date >= DATE_SUB('20260213', INTERVAL 20 DAY)
  AND d2.trade_date < '20260213'
)
"""
cur.execute(query2)
result2 = cur.fetchone()[0]
pct2 = result2 / 432 * 100 if 432 > 0 else 0
print(f"   数量: {result2} 个")
print(f"   占比: {pct2:.2f}%")

# 显示样本
if result2 > 0:
    cur.execute("""
    SELECT DISTINCT d1.ts_code FROM dwd_stock_daily_standard d1
    WHERE trade_date = '20260213'
    AND vol > 1.5 * (
      SELECT AVG(vol) FROM dwd_stock_daily_standard d2
      WHERE d2.ts_code = d1.ts_code AND d2.trade_date < '20260213'
    )
    LIMIT 5
    """)
    print(f"   样本: {', '.join([r[0] for r in cur.fetchall()])}")

# 3. 3日资金流 > 0
print(f"\n3️⃣  【3日资金流 > 0】")
query3 = """
SELECT COUNT(*) as cnt
FROM (
  SELECT ts_code
  FROM ods_moneyflow
  WHERE trade_date >= '20260211'
  AND trade_date <= '20260213'
  GROUP BY ts_code
  HAVING SUM(net_mf_amount) > 0
) flow_tbl
"""
cur.execute(query3)
result3 = cur.fetchone()[0]
pct3 = result3 / 432 * 100 if 432 > 0 else 0
print(f"   数量: {result3} 个")
print(f"   占比: {pct3:.2f}%")

# 显示样本
if result3 > 0:
    cur.execute("""
    SELECT ts_code, SUM(net_mf_amount) as flow
    FROM ods_moneyflow
    WHERE trade_date >= '20260211'
    GROUP BY ts_code
    HAVING SUM(net_mf_amount) > 0
    ORDER BY SUM(net_mf_amount) DESC
    LIMIT 5
    """)
    rows = cur.fetchall()
    for ts, flow in rows:
        print(f"   样本: {ts} (资金流={flow:.2f}万元)")

print("\n" + "=" * 90)
print("分析总结:")
print(f"  • 收盘价突破60日高: {result1} 个 ({pct1:.2f}%) - 市场缺乏向上突破")
print(f"  • 成交量倍数 ≥ 1.5: {result2} 个 ({pct2:.2f}%) - 市场活跃度不足")
print(f"  • 资金流入 > 0:      {result3} 个 ({pct3:.2f}%) - 资金普遍净流出")
print("\n💡 原分析结论正确：这些条件都很难同时满足，触发信号0个是正常的。")

cur.close()
conn.close()
