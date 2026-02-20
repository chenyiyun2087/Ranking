import pymysql
import json

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="19871019",
    database="ranking",
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# 查询两个股票的详细信息
sql = """
    SELECT ts_code, state, base_score, trigger_strength, pool_final_score, 
           risk_flags, avoid, action
    FROM dws_pool_replay_daily 
    WHERE trade_date='20260213' AND ts_code IN ('603912.SH', '603881.SH')
    ORDER BY pool_final_score DESC
"""

cursor.execute(sql)
results = cursor.fetchall()

print("=" * 80)
print("比较 603912.SH 和 603881.SH 的差异：")
print("=" * 80)

for row in results:
    print(f"\nts_code 股票代码: {row['ts_code']}")
    print(f"  基础分: {row['base_score']}")
    print(f"  触发强度: {row['trigger_strength']}")
    print(f"  最终分: {row['pool_final_score']}")
    print(f"  状态: {row['state']}")
    print(f"  行动: {row['action']}")
    print(f"  避免标志 (avoid): {row['avoid']}")
    print(f"  风险标志 (risk_flags): {row['risk_flags']}")
    
    # 解析 risk_flags
    if row['risk_flags']:
        try:
            flags = json.loads(row['risk_flags'])
            print(f"  解析后的风险标志: {flags}")
        except:
            print(f"  风险标志解析失败")

conn.close()
