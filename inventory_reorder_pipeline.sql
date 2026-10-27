-- =====================================================================
-- SUPPLY CHAIN REORDER POINT (ROP) & SAFETY STOCK PIPELINE
-- Author: Puneet Goswami
-- Description: Analyzes SKU daily consumption variance and supplier lead times
--              to determine dynamic reorder triggers and stockout exposure.
-- =====================================================================

WITH daily_sku_consumption AS (
    SELECT 
        sku_id,
        warehouse_id,
        consumption_date,
        units_depleted,
        -- Rolling 30-day demand metrics
        AVG(units_depleted) OVER (
            PARTITION BY sku_id, warehouse_id 
            ORDER BY consumption_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_avg_daily_demand,
        STDDEV(units_depleted) OVER (
            PARTITION BY sku_id, warehouse_id 
            ORDER BY consumption_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_std_daily_demand
    FROM logistics_dw.warehouse_inventory_logs
    WHERE consumption_date >= CURRENT_DATE - INTERVAL '90 DAYS'
),

latest_demand_snapshot AS (
    SELECT 
        sku_id,
        warehouse_id,
        units_depleted,
        rolling_avg_daily_demand,
        COALESCE(rolling_std_daily_demand, 0.0) AS demand_volatility_std,
        ROW_NUMBER() OVER (
            PARTITION BY sku_id, warehouse_id 
            ORDER BY consumption_date DESC
        ) AS rank_recent
    FROM daily_sku_consumption
),

sku_supplier_profiles AS (
    SELECT 
        s.sku_id,
        s.sku_name,
        s.category,
        s.unit_cost_usd,
        s.carrying_cost_pct,
        sup.supplier_id,
        sup.lead_time_days,
        sup.lead_time_variance_days
    FROM logistics_dw.sku_master s
    JOIN logistics_dw.supplier_catalog sup ON s.primary_supplier_id = sup.supplier_id
),

safety_stock_computation AS (
    SELECT 
        p.sku_id,
        p.sku_name,
        p.category,
        p.unit_cost_usd,
        p.lead_time_days,
        d.warehouse_id,
        ROUND(d.rolling_avg_daily_demand, 2) AS avg_daily_demand,
        ROUND(d.demand_volatility_std, 2) AS std_daily_demand,
        
        -- 95% Service Level Benchmark Z-Score = 1.645
        -- Safety Stock = Z * sqrt(LeadTime * Var_Demand + (Avg_Demand^2 * Var_LeadTime))
        ROUND(
            1.645 * SQRT(
                (p.lead_time_days * POWER(d.demand_volatility_std, 2)) +
                (POWER(d.rolling_avg_daily_demand, 2) * POWER(p.lead_time_variance_days, 2))
            )
        ) AS calculated_safety_stock_units,

        -- Reorder Point = (Avg Daily Demand * Lead Time) + Safety Stock
        ROUND(
            (d.rolling_avg_daily_demand * p.lead_time_days) + 
            (1.645 * SQRT((p.lead_time_days * POWER(d.demand_volatility_std, 2))))
        ) AS dynamic_reorder_point_units
    FROM latest_demand_snapshot d
    JOIN sku_supplier_profiles p ON d.sku_id = p.sku_id
    WHERE d.rank_recent = 1
)

SELECT 
    c.warehouse_id,
    c.sku_id,
    c.sku_name,
    c.category,
    c.avg_daily_demand,
    c.lead_time_days,
    c.calculated_safety_stock_units,
    c.dynamic_reorder_point_units,
    curr.units_on_hand,
    curr.units_on_order,
    (curr.units_on_hand + curr.units_on_order) AS total_inventory_position,
    
    -- Stockout Risk Trigger
    CASE 
        WHEN (curr.units_on_hand + curr.units_on_order) <= c.dynamic_reorder_point_units THEN 'CRITICAL_REORDER_REQUIRED'
        WHEN (curr.units_on_hand + curr.units_on_order) <= (c.dynamic_reorder_point_units * 1.15) THEN 'WARNING_APPROACHING_ROP'
        ELSE 'OPTIMAL_STOCK_BUFFER'
    END AS inventory_health_status,

    ROUND(c.calculated_safety_stock_units * c.unit_cost_usd, 2) AS safety_stock_working_capital_usd
FROM safety_stock_computation c
JOIN logistics_dw.current_inventory_snapshot curr 
  ON c.sku_id = curr.sku_id AND c.warehouse_id = curr.warehouse_id
ORDER BY safety_stock_working_capital_usd DESC;