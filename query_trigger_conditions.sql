-- 高效验证触发条件的SQL查询

-- SQL 1: 收盘价 ≥ 60日高的股票
-- 使用window function更高效
SELECT COUNT(*) as count_close_gte_high60
FROM (
    SELECT ts_code
    FROM dwd_stock_daily_standard
    WHERE trade_date = '20260213'
    AND adj_close >= (
        SELECT MAX(adj_high) 
        FROM dwd_stock_daily_standard h
        WHERE h.ts_code = dwd_stock_daily_standard.ts_code
          AND h.trade_date >= DATE_FORMAT(STR_TO_DATE('20260213', '%Y%m%d') - INTERVAL 60 DAY, '%Y%m%d')
          AND h.trade_date < '20260213'
    )
) t;

-- SQL 2: 成交量比 ≥ 1.5 的股票
SELECT COUNT(DISTINCT ts_code) as count_vol_ratio_gte_1_5
FROM dwd_stock_daily_standard d1
WHERE trade_date = '20260213'
  AND vol >= 1.5 * (
      SELECT AVG(vol)
      FROM dwd_stock_daily_standard d2
      WHERE d2.ts_code = d1.ts_code
        AND d2.trade_date < '20260213'
        AND d2.trade_date >= DATE_FORMAT(STR_TO_DATE('20260213', '%Y%m%d') - INTERVAL 20 DAY, '%Y%m%d')
  );

-- SQL 3: 3日资金流 > 0 的股票
SELECT COUNT(*) as count_flow_3d_gt_0
FROM (
    SELECT ts_code
    FROM ods_moneyflow
    WHERE trade_date >= '20260211'
      AND trade_date <= '20260213'
    GROUP BY ts_code
    HAVING SUM(net_mf_amount) > 0
) t;

-- SQL 4: 显示满足各条件的样本股票

-- 满足"收盘价 ≥ 60日高"的股票示例
SELECT DISTINCT ts_code
FROM dwd_stock_daily_standard
WHERE trade_date = '20260213'
  AND adj_close >= (
      SELECT MAX(adj_high) 
      FROM dwd_stock_daily_standard h
      WHERE h.ts_code = dwd_stock_daily_standard.ts_code
        AND h.trade_date >= DATE_FORMAT(STR_TO_DATE('20260213', '%Y%m%d') - INTERVAL 60 DAY, '%Y%m%d')
        AND h.trade_date < '20260213'
  )
LIMIT 10;

-- 满足"成交量比 ≥ 1.5"的股票示例
SELECT DISTINCT ts_code
FROM dwd_stock_daily_standard d1
WHERE trade_date = '20260213'
  AND vol >= 1.5 * (
      SELECT AVG(vol)
      FROM dwd_stock_daily_standard d2
      WHERE d2.ts_code = d1.ts_code
        AND d2.trade_date < '20260213'
        AND d2.trade_date >= DATE_FORMAT(STR_TO_DATE('20260213', '%Y%m%d') - INTERVAL 20 DAY, '%Y%m%d')
  )
LIMIT 10;

-- 满足"3日资金流 > 0"的股票示例
SELECT ts_code, SUM(net_mf_amount) as total_flow
FROM ods_moneyflow
WHERE trade_date >= '20260211'
  AND trade_date <= '20260213'
GROUP BY ts_code
HAVING SUM(net_mf_amount) > 0
ORDER BY SUM(net_mf_amount) DESC
LIMIT 10;
