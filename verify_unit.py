import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='19871019',
    database='tushare_stock'
)

cur = conn.cursor()

# 查询000839.SZ在20260213的数据
cur.execute('''
    SELECT ts_code, trade_date, adj_open, adj_high, adj_low, adj_close, vol, amount 
    FROM dwd_stock_daily_standard 
    WHERE ts_code = '000839.SZ' AND trade_date = '20260213'
''')

result = cur.fetchone()
if result:
    ts_code, tr_date, open_p, high, low, close, vol, amount = result
    print(f'Stock: {ts_code}')
    print(f'Date: {tr_date}')
    print(f'Price: Open={open_p}, High={high}, Low={low}, Close={close}')
    print(f'Volume (vol): {vol}')
    print(f'Amount: {amount}')
    print()
    print('Unit interpretation:')
    print(f'If amount in 万元: {amount:,.2f} 万元 = {amount/10000:,.4f}亿元')
    print(f'If amount in 元: {amount:,.2f} 元 = {amount/100000000:.4f}亿元')
    print()
    print('Your finding: This stock has trading volume of 3.60亿元')
    if amount > 100000:
        print(f'Match check: {amount/10000:.4f}亿元 ≈ 3.60亿元? {abs(amount/10000 - 3.60) < 0.01} ✓ AMOUNT IS IN 万元')
    else:
        print(f'Match check: {amount/100000000:.4f}亿元 ≈ 3.60亿元? {abs(amount/100000000 - 3.60) < 0.01}')
else:
    print('No data found for 000839.SZ on 20260213')

cur.close()
conn.close()
