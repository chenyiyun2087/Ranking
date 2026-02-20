import pymysql

nvda_stocks = [
    "300308.SZ", "300502.SZ", "300394.SZ", "002281.SZ", "000988.SZ",
    "601869.SH", "002837.SZ", "300499.SZ", "300990.SZ", "603912.SH",
    "301018.SZ", "002463.SZ", "002916.SZ", "300476.SZ", "603228.SH",
    "600183.SH", "002335.SZ", "002518.SZ", "002364.SZ", "002851.SZ",
    "300693.SZ", "300383.SZ", "300442.SZ", "603881.SH", "300738.SZ",
    "600845.SH"
]

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="19871019",
    database="tushare_stock",
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# Check score availability
tables = ["dws_momentum_score", "dws_technical_score", "dws_capital_score", "dws_chip_score"]

for table in tables:
    placeholders = ",".join("%s" for _ in nvda_stocks)
    sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE ts_code IN ({placeholders}) AND trade_date=20260213"
    cursor.execute(sql, nvda_stocks)
    result = cursor.fetchone()
    print(f"{table}: {result['cnt']} records")

# Check which stocks are missing technical_score
placeholders = ",".join("%s" for _ in nvda_stocks)
sql = f"SELECT ts_code FROM dws_technical_score WHERE ts_code IN ({placeholders}) AND trade_date=20260213"
cursor.execute(sql, nvda_stocks)
technical_stocks = {r["ts_code"] for r in cursor.fetchall()}
missing = [s for s in nvda_stocks if s not in technical_stocks]
print(f"\nMissing technical_score ({len(missing)}): {missing}")

conn.close()
