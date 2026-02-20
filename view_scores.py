import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="19871019",
    database="ranking",
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# 获取完整的评分结果
cursor.execute("""
    SELECT ts_code, state, base_score, trigger_strength, pool_final_score, key_levels, reasons
    FROM dws_pool_replay_daily 
    WHERE trade_date='20260213'
    ORDER BY pool_final_score DESC
""")

results = cursor.fetchall()

print("=" * 90)
print("NVDA-CONCEPT 池评分结果 (20260213)")
print("=" * 90)
print(f"\n总共有 {len(results)} 个股票\n")

# 按状态分组
states = {}
for row in results:
    state = row['state']
    if state not in states:
        states[state] = []
    states[state].append(row)

for state in sorted(states.keys()):
    print(f"\n【{state}】({len(states[state])} 个)")
    print("-" * 90)
    print(f"{'股票代码':<12} {'基础分':<10} {'触发强度':<12} {'最终分':<10}")
    print("-" * 90)
    
    for row in sorted(states[state], key=lambda x: x['pool_final_score'] or 0, reverse=True):
        ts_code = row['ts_code']
        base = f"{row['base_score']:.4f}" if row['base_score'] else "N/A"
        trigger = f"{row['trigger_strength']:.4f}" if row['trigger_strength'] else "N/A"
        final = f"{row['pool_final_score']:.4f}" if row['pool_final_score'] else "N/A"
        print(f"{ts_code:<12} {base:<10} {trigger:<12} {final:<10}")

conn.close()
