-- SQL验证查询脚本
-- 用于检查自选股池(432只，日期20260213)中满足各项条件的股票数量

-- 首先，获取自选股池的所有股票代码
-- (这些数据在评分过程中已经计算过，我们查询源数据表来验证)

USE tushare_stock;

-- 1. 查询满足"收盘价 ≥ 60日高"的股票
-- 需要计算每只股票的60日最高价
SELECT COUNT(*) as count_close_gte_high60,
       GROUP_CONCAT(DISTINCT CONCAT(ts_code) ORDER BY ts_code LIMIT 20) as sample_stocks
FROM (
    SELECT 
        t1.ts_code,
        t1.adj_close as close,
        MAX(t2.adj_high) as high_60
    FROM dwd_stock_daily_standard t1
    INNER JOIN dwd_stock_daily_standard t2 
        ON t1.ts_code = t2.ts_code 
        AND t2.trade_date BETWEEN 
            DATE_FORMAT(STR_TO_DATE(t1.trade_date, '%Y%m%d') - INTERVAL 60 DAY, '%Y%m%d')
            AND t1.trade_date
    WHERE t1.trade_date = '20260213'
    GROUP BY t1.ts_code, t1.adj_close
) subq
WHERE close >= high_60;

-- 2. 查询满足"成交量比 ≥ 1.5"的股票
-- vol_ratio = 当日成交量 / 20日平均成交量
SELECT COUNT(*) as count_vol_ratio_gte_1_5,
       GROUP_CONCAT(ts_code ORDER BY ts_code LIMIT 20) as sample_stocks
FROM (
    SELECT 
        t1.ts_code,
        t1.vol as today_vol,
        AVG(t2.vol) as ma20_vol,
        t1.vol / NULLIF(AVG(t2.vol), 0) as vol_ratio
    FROM dwd_stock_daily_standard t1
    INNER JOIN dwd_stock_daily_standard t2 
        ON t1.ts_code = t2.ts_code 
        AND t2.trade_date BETWEEN 
            DATE_FORMAT(STR_TO_DATE(t1.trade_date, '%Y%m%d') - INTERVAL 20 DAY, '%Y%m%d')
            AND t1.trade_date
    WHERE t1.trade_date = '20260213'
    GROUP BY t1.ts_code, t1.vol
) subq
WHERE vol_ratio >= 1.5;

-- 3. 查询满足"3日资金流 > 0"的股票
-- 需要计算3日内的净资金流（若有moneyflow数据）
SELECT COUNT(*) as count_flow_3d_gt_0,
       GROUP_CONCAT(ts_code ORDER BY ts_code LIMIT 20) as sample_stocks
FROM (
    SELECT 
        ts_code,
        SUM(net_mf_amount) as flow_3d
    FROM ods_moneyflow
    WHERE trade_date BETWEEN '20260211' AND '20260213'
    GROUP BY ts_code
    HAVING flow_3d > 0
) subq;

-- 4. 同时满足所有三个条件的股票
SELECT COUNT(*) as count_all_three_conditions
FROM (
    SELECT DISTINCT t1.ts_code
    FROM dwd_stock_daily_standard t1
    INNER JOIN dwd_stock_daily_standard t2 
        ON t1.ts_code = t2.ts_code 
        AND t2.trade_date BETWEEN 
            DATE_FORMAT(STR_TO_DATE(t1.trade_date, '%Y%m%d') - INTERVAL 60 DAY, '%Y%m%d')
            AND t1.trade_date
    LEFT JOIN (
        SELECT 
            ts_code,
            (vol / NULLIF(AVG(vol), 0)) as vol_ratio
        FROM dwd_stock_daily_standard
        WHERE trade_date < '20260213'
        GROUP BY ts_code
    ) vol_subq ON t1.ts_code = vol_subq.ts_code
    LEFT JOIN (
        SELECT 
            ts_code,
            SUM(net_mf_amount) as flow_3d
        FROM ods_moneyflow
        WHERE trade_date BETWEEN '20260211' AND '20260213'
        GROUP BY ts_code
    ) flow_subq ON t1.ts_code = flow_subq.ts_code
    WHERE t1.trade_date = '20260213'
      AND t1.adj_close >= MAX(t2.adj_high)
      AND vol_subq.vol_ratio >= 1.5
      AND flow_subq.flow_3d > 0
) subq;

-- 5. 详细查看20260213的样本数据
SELECT 
    ts_code,
    trade_date,
    adj_close,
    vol,
    amount
FROM dwd_stock_daily_standard
WHERE trade_date = '20260213'
LIMIT 10;

-- 6. 查看资金流数据是否存在
SELECT COUNT(*) as mf_record_count
FROM ods_moneyflow
WHERE trade_date = '20260213';
