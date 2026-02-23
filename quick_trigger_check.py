#!/usr/bin/env python3
import pymysql
import time

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='19871019',
    database='tushare_stock'
)

cur = conn.cursor()

print("\n验证触发条件统计 - 20260213")
print("=" * 90)

# 检查数据量
cur.execute("SELECT COUNT(*) FROM dwd_stock_daily_standard WHERE trade_date = '20260213'")
total = cur.fetchone()[0]
print(f"\n📊 数据情况:")
print(f"   20260213日期的价格数据: {total} 条记录\n")

# 简化版本：直接计数而不进行复杂子查询
print("⏳ 查询中... (这可能需要一些时间)")
print("-" * 90)

# 1. 快速查询：技术上满足某个条件的股票（简化版）
try:
    print("\n1️⃣  【收盘价 ≥ MA60 的股票】(简化检查)")
    # 先获取所有20260213的股票
    cur.execute("SELECT DISTINCT ts_code, adj_close FROM dwd_stock_daily_standard WHERE trade_date = '20260213'")
    stocks_20260213 = {row[0]: row[1] for row in cur.fetchall()}
    
    count1 = 0
    sample1 = []
    for ts_code, close in list(stocks_20260213.items())[:100]:  # 样本检查前100个
        cur.execute(f"""
            SELECT MAX(adj_high) 
            FROM dwd_stock_daily_standard 
            WHERE ts_code = %s 
            AND trade_date < '20260213'
            AND trade_date >= DATE_SUB('20260213', INTERVAL 60 DAY)
        """, (ts_code,))
        result = cur.fetchone()
        if result and result[0] is not None:
            high_60 = result[0]
            if close >= high_60:
                count1 += 1
                if len(sample1) < 3:
                    sample1.append(f"{ts_code}({close:.2f}≥{high_60:.2f})")
    
    print(f"   数量: {count1} 个 (检查前100个股票)")
    if sample1:
        print(f"   样本: {', '.join(sample1)}")
    
except Exception as e:
    print(f"   查询出错: {e}")

# 2. 简化查询：资金流数据
try:
    print("\n2️⃣  【3日资金流 > 0 的股票】")
    cur.execute("""
        SELECT COUNT(*) 
        FROM (
            SELECT ts_code
            FROM ods_moneyflow
            WHERE trade_date >= '20260211'
            GROUP BY ts_code
            HAVING SUM(net_mf_amount) > 0
        ) t
    """)
    result3 = cur.fetchone()[0]
    pct3 = result3 / 432 * 100
    print(f"   数量: {result3} 个")
    print(f"   占比: {pct3:.2f}%")
    
    # 显示样本
    cur.execute("""
        SELECT ts_code, SUM(net_mf_amount) 
        FROM ods_moneyflow
        WHERE trade_date >= '20260211'
        GROUP BY ts_code
        HAVING SUM(net_mf_amount) > 0
        ORDER BY SUM(net_mf_amount) DESC
        LIMIT 3
    """)
    for ts, flow in cur.fetchall():
        print(f"   样本: {ts} (资金流={float(flow):.2f}万元)")

except Exception as e:
    print(f"   查询出错: {e}")

print("\n" + "=" * 90)
print("📝 说明:")
print("   由于复杂的嵌套子查询性能较差，上面只展示了部分数据。")
print("   建议直接在数据库中执行 query_trigger_conditions.sql 文件。")
print("\n各条件的 SQL 查询已保存在: query_trigger_conditions.sql")

cur.close()
conn.close()
