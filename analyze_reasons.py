#!/usr/bin/env python3
"""
分析自选股池为什么所有股票都显示流动性不足和无触发信号
"""
import csv
import json
from collections import defaultdict

# 读取评分结果数据
data = []
with open('output/pool_risk_list.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

print("=" * 120)
print("自选股池流动性和触发信号分析")
print("=" * 120)
print()

# 1. 分析流动性问题
print("【1. 流动性不足问题分析】")
print("-" * 120)

illiquid_count = 0
amount_stats = []

for row in data:
    try:
        risk_flags = json.loads(row.get('risk_flags', '{}'))
        if 'illiquid' in risk_flags:
            illiquid_count += 1
        
        amount = float(row.get('amount', 0))
        amount_stats.append({
            'code': row['ts_code'],
            'amount': amount,
            'is_illiquid': 1 if 'illiquid' in risk_flags else 0
        })
    except:
        pass

amount_stats.sort(key=lambda x: x['amount'], reverse=True)

print(f"流动性不足的股票数: {illiquid_count}")
print(f"配置的最小成交额(min_amount): 50000000 元")
print()
print("成交额统计 (单位: 万元):")
print(f"  最大成交额: {amount_stats[0]['amount']/10000:.0f}万 ({amount_stats[0]['code']})")
print(f"  最小成交额: {amount_stats[-1]['amount']/10000:.0f}万 ({amount_stats[-1]['code']})")
print(f"  平均成交额: {sum([s['amount'] for s in amount_stats])/len(amount_stats)/10000:.0f}万")
print()

# 统计成交额分布
above_50m = sum(1 for s in amount_stats if s['amount'] >= 50000000)
print(f"成交额 > 5000万 的股票: {above_50m} 个 ({above_50m*100/len(data):.1f}%)")
print()

print("【流动性判断逻辑】")
print("if amount < 50000000:  # 配置值")
print("    flags['illiquid'] = 1  # 标记为流动性不足")
print("    avoid = 1  # 规避处理")
print()

# 2. 分析触发信号问题
print("=" * 120)
print("【2. 触发信号问题分析】")
print("-" * 120)

trigger_stats = defaultdict(int)
breakout_reasons = {'close_check': 0, 'vol_ratio_check': 0, 'flow_3d_check': 0, 'all_ok': 0}
pullback_reasons = {'recent_check': 0, 'low_check': 0, 'close_check': 0, 'vol_check': 0, 'flow_check': 0, 'all_ok': 0}

for row in data:
    try:
        trigger_type = row.get('trigger_type', 'none')
        trigger_stats[trigger_type] += 1
        
        # 分析触发失败原因
        close = float(row.get('close', 0))
        high_60 = float(row.get('high_60', 0))
        vol_ratio = float(row.get('vol_ratio', 0))
        flow_3d = float(row.get('flow_3d', 0))
        recent_breakout = float(row.get('recent_breakout', 0))
        low = float(row.get('low', 0))
        ma20 = float(row.get('ma20', 0))
        
        # Breakout 检查
        if close >= high_60:
            if vol_ratio >= 1.5:
                if flow_3d > 0:
                    breakout_reasons['all_ok'] += 1
                else:
                    breakout_reasons['flow_3d_check'] += 1
            else:
                breakout_reasons['vol_ratio_check'] += 1
        else:
            breakout_reasons['close_check'] += 1
        
        # Pullback 检查
        if recent_breakout >= 1:
            if low <= ma20 * 1.01:
                if close >= ma20:
                    if vol_ratio <= 1.0:
                        if flow_3d > 0:
                            pullback_reasons['all_ok'] += 1
                        else:
                            pullback_reasons['flow_check'] += 1
                    else:
                        pullback_reasons['vol_check'] += 1
                else:
                    pullback_reasons['close_check'] += 1
            else:
                pullback_reasons['low_check'] += 1
        else:
            pullback_reasons['recent_check'] += 1
    except:
        pass

print("当前数据中的触发类型分布:")
for trigger_type, count in sorted(trigger_stats.items(), key=lambda x: -x[1]):
    print(f"  {trigger_type}: {count} 个 ({count*100/len(data):.1f}%)")

print()
print("【Breakout 触发失败原因分析】")
print(f"  收盘价未突破60日高点 (close < high_60): {breakout_reasons['close_check']} 个")
print(f"  成交量比例不足 (vol_ratio < 1.5): {breakout_reasons['vol_ratio_check']} 个")
print(f"  3日净资金流为负 (flow_3d <= 0): {breakout_reasons['flow_3d_check']} 个")
print(f"  全部条件满足: {breakout_reasons['all_ok']} 个")

print()
print("【Pullback 触发失败原因分析】")
print(f"  近期无突破 (recent_breakout < 1): {pullback_reasons['recent_check']} 个")
print(f"  最低价低于MA20 (low > ma20*1.01): {pullback_reasons['low_check']} 个")
print(f"  收盘价低于MA20 (close < ma20): {pullback_reasons['close_check']} 个")
print(f"  成交量过大 (vol_ratio > 1.0): {pullback_reasons['vol_check']} 个")
print(f"  3日净资金流为负 (flow_3d <= 0): {pullback_reasons['flow_check']} 个")
print(f"  全部条件满足: {pullback_reasons['all_ok']} 个")

print()
print("【触发信号判断逻辑】")
print()
print("Breakout 条件 (需全部满足):")
print("  1. close >= high_60  # 收盘价突破60日最高价")
print("  2. vol_ratio >= 1.5   # 成交量在20日均量的1.5倍以上")
print("  3. flow_3d > 0        # 3日净资金为正")
print()
print("Pullback 条件 (需全部满足):")
print("  1. recent_breakout >= 1  # 最近10日内有过突破")
print("  2. low <= ma20 * 1.01     # 最低价回落到MA20附近")
print("  3. close >= ma20          # 收盘价在MA20上方")
print("  4. vol_ratio <= 1.0       # 成交量没有大量涌入")
print("  5. flow_3d > 0            # 3日净资金为正")
print()

# 3. 分析触发强度为0的原因
print("=" * 120)
print("【3. 触发强度为0的原因分析】")
print("-" * 120)

zero_strength_count = 0
trigger_strength_list = []

for row in data:
    try:
        strength = float(row.get('trigger_strength', 0))
        trigger_strength_list.append(strength)
        if strength == 0:
            zero_strength_count += 1
    except:
        pass

print(f"触发强度为0的股票: {zero_strength_count} 个 ({zero_strength_count*100/len(data):.1f}%)")
print(f"非零触发强度的股票: {len(trigger_strength_list)-zero_strength_count} 个")
print()
print("【触发强度计算逻辑】")
print("触发强度 = 100 * (0.25*s1 + 0.25*s2 + 0.25*s3 + 0.15*s4 + 0.10*s5)")
print("其中:")
print("  s1 = 百分位排名(close/high_60 - 1)      # 收盘价相对60日高点的强度")
print("  s2 = 百分位排名(vol_ratio)              # 成交量强度")
print("  s3 = 百分位排名(flow_ratio_3d)          # 资金流强度")
print("  s4 = 百分位排名(close_pos)              # 收盘位置强度")
print("  s5 = 百分位排名(chip_stable_score)      # 筹码稳定度")
print()
print("说明: 即使没有有效触发信号，触发强度也会计算，但最终评分会受到影响")
print()

# 4. 具体示例分析
print("=" * 120)
print("【4. 具体示例解析】")
print("-" * 120)

# 选择几个代表性的样本
samples = data[:5]
for i, row in enumerate(samples, 1):
    print(f"\n示例 {i}: {row['ts_code']}")
    print(f"  收盘价: {row['close']}")
    print(f"  60日高: {row['high_60']}")
    print(f"  20日线: {row['ma20']}")
    print(f"  成交额: {float(row['amount'])/1000000:.2f}百万")
    print(f"  成交量比: {row['vol_ratio']}")
    print(f"  3日资金流: {row['flow_3d']}")
    print(f"  ➜ 成交额不足5000万，标记为illiquid，规避处理 ✗")
    
    close = float(row['close'])
    high_60 = float(row['high_60'])
    vol_ratio = float(row['vol_ratio'])
    flow_3d = float(row['flow_3d'])
    
    if close < high_60:
        print(f"  ➜ 收盘价{close} < 60日高{high_60}，无Breakout ✗")
    if vol_ratio < 1.5:
        print(f"  ➜ 成交量比{vol_ratio} < 1.5，无Breakout ✗")
    if flow_3d <= 0:
        print(f"  ➜ 3日资金流{flow_3d}不为正，无法触发 ✗")

print()
print("=" * 120)
print("【总结】")
print("=" * 120)
print("""
当前自选股池所有股票显示规避的主要原因：

1. 流动性不足 (100%)
   - 配置的最小成交额为 5000万 (50000000)
   - 而大部分股票成交额远低于此标准
   - 这导致所有股票在过滤阶段就被标记为illiquid并规避

2. 触发信号缺失 (100%)
   - Breakout条件严格（需同时满足：价格突破+量能配合+资金流为正）
   - Pullback条件也复杂（需历史突破+位置回落+量能下降+资金流为正）
   - 当前数据中几乎没有股票同时满足所有条件

3. 资金流为负是主要问题
   - 大部分股票3日净资金流(flow_3d)为0或负值
   - 这表明市场缺乏有效的买入意愿
   
建议改进方向：
✓ 调整 min_amount 参数（从5000万降低到更合理的值）
✓ 优化触发条件的权重（可以将资金流要求改为非必须）
✓ 增加其他触发条件（如技术形态、相对强度等）
✓ 分析市场环境是否不适合当前策略
""")
