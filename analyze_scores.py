#!/usr/bin/env python3
import csv

# 读取风险清单数据
risk_stocks = []
with open('output/pool_risk_list.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            risk_stocks.append({
                'ts_code': row['ts_code'],
                'close': float(row['close']),
                'final_score': float(row['pool_final_score']),
                'state': row['state'],
                'momentum': float(row['momentum_score']) if row.get('momentum_score') else 0,
                'technical': float(row['technical_score']) if row.get('technical_score') else 0,
                'capital': float(row['capital_score']) if row.get('capital_score') else 0
            })
        except:
            pass

# 按最终分排序
risk_stocks.sort(key=lambda x: x['final_score'], reverse=True)

print("=" * 120)
print("自选股池 2026-02-13 评分结果详情")
print("=" * 120)
print()
print(f"总处理股票数: 432")
print(f"最终分类:")
print(f"  - 作战池: 0")
print(f"  - 候选池: 0")
print(f"  - 观察池: 0")
print(f"  - 风险清单: {len(risk_stocks)}")
print()
print("=" * 120)
print("TOP 30 高分股票（按最终分排序）:")
print("=" * 120)
print(f"{'排名':<5} {'代码':<12} {'收盘价':<10} {'动量':<7} {'技术':<7} {'资金':<7} {'最终分':<10} {'状态':<8}")
print("-" * 120)

for i, stock in enumerate(risk_stocks[:30], 1):
    print(f"{i:<5} {stock['ts_code']:<12} {stock['close']:<10.2f} {stock['momentum']:<7.1f} {stock['technical']:<7.1f} {stock['capital']:<7.1f} {stock['final_score']:<10.2f} {stock['state']:<8}")

print()
print("=" * 120)
print("统计信息:")
print("=" * 120)
avg_score = sum([s['final_score'] for s in risk_stocks]) / len(risk_stocks) if risk_stocks else 0
max_score = max([s['final_score'] for s in risk_stocks]) if risk_stocks else 0
min_score = min([s['final_score'] for s in risk_stocks]) if risk_stocks else 0
above_20 = sum(1 for s in risk_stocks if s['final_score'] > 20)
above_30 = sum(1 for s in risk_stocks if s['final_score'] > 30)
above_50 = sum(1 for s in risk_stocks if s['final_score'] > 50)

print(f"平均最终分: {avg_score:.2f}")
print(f"最高最终分: {max_score:.2f}")
print(f"最低最终分: {min_score:.2f}")
print(f"评分 > 20 的股票: {above_20} 个")
print(f"评分 > 30 的股票: {above_30} 个")
print(f"评分 > 50 的股票: {above_50} 个")
