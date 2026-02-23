# Unit Mismatch Analysis & Fix - Summary Report

## Root Cause Discovered ✓

### The Problem
The database `amount` field is in **万元** (10,000 yuan) units, but the configuration `min_amount=50,000,000` was being compared directly without unit conversion.

**Example:**
- Stock 000839.SZ: amount = 359702.39 万元 = **35.97亿元** (3.597 billion yuan)
- Configuration checking: `if amount < 50,000,000万元` → effectively `< 50,000亿元` (impossible!)
- Result: **All 432 stocks marked illiquid** (wrongly)

### The Fix Applied ✓
Changed configuration from:
```json
"min_amount": 50000000  // Comparing 万元 values against 5000亿 threshold
```

To:
```json
"min_amount": 5000  // Now comparing 万元 values against 5000万 threshold (5M yuan)
```

---

## Results After Fix

### Before Fix (Previous Run)
- **All 432 stocks**: Status = AVOID, illiquid flag = 1
- **Trigger signals**: 0 (because illiquid stocks skip trigger analysis)
- **Output**: 432 rejected stocks, 0 recommended stocks

### After Fix (Current Run)
- **Total processed**: 432 stocks
- **In WATCH state** (safe): 419 stocks (97%)
- **In WEAKEN state** (warning): 5 stocks (1.2%)
- **In AVOID state** (rejected): 8 stocks (1.9%)

**Status Distribution:**
```
WATCH:   419 stocks (default state for safe, no-signal stocks)
WEAKEN:    5 stocks (potential downturn, recommend reduction)
AVOID:     8 stocks (specific flags like ST, one-price, or severe risk)
TRIGGER:   0 stocks (no strong breakout signals in market)
SETUP:     0 stocks (no good setup conditions found)
HOLD:      0 stocks (no active positions to maintain)
```

---

## Top Risk Stocks (WEAKEN/AVOID States)

These 13 stocks require attention:

| Rank | Stock | State | Reason | Score |
|------|-------|-------|--------|-------|
| 1 | 000791.SZ | WEAKEN | Weak momentum, high volatility | 23.21 |
| 2 | 601975.SH | WEAKEN | Below MA20, volume ratio issue | 23.72 |
| 3 | 300833.SZ | WEAKEN | Price falling, momentum weak | 25.95 |
| 4 | 600177.SH | WEAKEN | Below MA20 support | 28.01 |
| 5 | 688660.SH | WEAKEN | Price below MA60, downtrend | 30.46 |
| 6 | 000839.SZ | AVOID | **one_price flag** (all trading at 3.39) | 0.00 |
| 7 | 002306.SZ | AVOID | **ST stock** (special treatment) | 22.59 |
| 8 | 300343.SZ | AVOID | **ST stock** | 22.70 |
| 9 | 300506.SZ | AVOID | **ST stock** | 24.73 |
| 10 | 300020.SZ | AVOID | **ST stock** | 26.96 |
| 11 | 300175.SZ | AVOID | **ST stock** | 30.41 |
| 12 | 000821.SZ | AVOID | **ST stock** | 34.81 |
| 13 | 300198.SZ | AVOID | **ST stock** | 36.20 |

**Note:** Most AVOID are from ST (Special Treatment) stocks with special regulations.

---

## Impact Assessment

### What Changed
1. **Liquidity filter now works correctly**: Stocks with amount ≥ 5000万 yuan pass the filter
2. **Invalid rejections removed**: 419 stocks now properly evaluated instead of all being rejected
3. **Market reality reflected**: Only 8 stocks are truly problematic (ST stocks or trading anomalies)
4. **Analysis validity restored**: The 13 WEAKEN/AVOID stocks are legitimate warnings, not false positives

### What Remains Unchanged
- **Market conditions**: No strong breakout signals (trigger_type = "none" for all)
- **Capital flow**: Weak money inflow (flow_3d ≈ 0) indicates cautious market
- **No TRIGGER/SETUP**: Market environment not favorable for active trading signals
- **WATCH stocks are healthy**: 419 stocks are in safe default state, waiting for better conditions

---

## Verification Data

**Database Confirmation:**
```
Sample 20260213 Trading Data (万元 amounts):
  000001.SZ: 607501.38万元 = 60.75亿元 ✓ (passes min 5000万)
  000002.SZ: 1108675.80万元 = 110.87亿元 ✓ (passes min 5000万)
  000004.SZ: 219725.29万元 = 21.97亿元 ✓ (passes min 5000万)
  000839.SZ: 359702.39万元 = 35.97亿元 ✓ (passes min 5000万)
```

All sample stocks now correctly pass the liquidity check!

---

## Configuration Recommendation

**Current (Fixed):**
```json
"filters": {"new_stock_days": 60, "min_amount": 5000, "avoid_one_price": true}
```

**Consider Alternative Values Based on Risk Tolerance:**
- `min_amount": 5000` (5000万 = 50M yuan) - Current setting, filters out very small stocks
- `min_amount": 10000` (10000万 = 100M yuan) - More conservative, focuses on larger caps
- `min_amount": 2000` (2000万 = 20M yuan) - More inclusive, includes SME stocks

**For Production Use:**
Recommend validating these thresholds against your trading liquidity requirements and the specific market you're analyzing.

---

## Conclusion

✅ **Root cause identified and fixed**: Unit mismatch in min_amount configuration
✅ **Pipeline restoration**: 432 stocks now properly evaluated  
✅ **Result validity**: 13 risk stocks identified are legitimate concerns, not false positives
✅ **System health**: 419 stocks in healthy WATCH state pending better market conditions

The system is now **working as designed**. The market environment on 2026-02-13 simply shows no strong trading signals for the analyzed pool.
