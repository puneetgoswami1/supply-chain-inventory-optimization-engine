"""
Supply Chain Safety Stock & Inventory Optimization Engine
Author: Puneet Goswami
Description: Models demand distribution uncertainty, calculates EOQ lot sizes,
             and simulates working capital vs stockout trade-offs across service levels.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm


def generate_inventory_catalog(n_skus: int = 500) -> pd.DataFrame:
    """Generates synthetic product inventory profiles across fulfillment nodes."""
    np.random.seed(42)

    sku_ids = [f"SKU-{1000 + i}" for i in range(n_skus)]
    categories = np.random.choice(["Home & Living", "Apparel", "Electronics", "Wellness"], size=n_skus, p=[0.35, 0.30, 0.20, 0.15])
    unit_cost = np.round(np.random.uniform(8.0, 140.0, size=n_skus), 2)
    annual_demand = np.random.randint(1200, 35000, size=n_skus)
    daily_demand_mean = annual_demand / 365.0
    daily_demand_std = daily_demand_mean * np.random.uniform(0.18, 0.45, size=n_skus)
    lead_time_days = np.random.choice([7, 14, 21, 30], size=n_skus, p=[0.25, 0.40, 0.25, 0.10])
    lead_time_std = lead_time_days * 0.15

    return pd.DataFrame({
        "sku_id": sku_ids,
        "category": categories,
        "unit_cost_usd": unit_cost,
        "annual_demand": annual_demand,
        "daily_demand_mean": daily_demand_mean,
        "daily_demand_std": daily_demand_std,
        "lead_time_days": lead_time_days,
        "lead_time_std": lead_time_std
    })


def evaluate_inventory_tradeoffs(df: pd.DataFrame):
    """Calculates EOQ, safety stock buffer, and total holding cost exposure."""
    ordering_cost_per_po = 65.0  # Assumed cost to process a purchase order (USD)
    annual_holding_cost_rate = 0.22  # 22% cost of capital + warehousing storage

    # 1. Economic Order Quantity (EOQ = sqrt((2 * D * S) / H))
    h_cost = df["unit_cost_usd"] * annual_holding_cost_rate
    df["eoq_units"] = np.round(np.sqrt((2 * df["annual_demand"] * ordering_cost_per_po) / h_cost)).astype(int)

    # 2. Safety Stock comparison at 90%, 95%, and 99% Service Levels
    service_levels = [0.90, 0.95, 0.99]
    print("==========================================================================")
    print("SUPPLY CHAIN INVENTORY OPTIMIZATION: SERVICE LEVEL VS CAPITAL ALLOCATION")
    print("==========================================================================")

    for sl in service_levels:
        z = norm.ppf(sl)
        # Combined demand + lead time variance formula
        ss = z * np.sqrt(
            (df["lead_time_days"] * np.power(df["daily_demand_std"], 2)) +
            (np.power(df["daily_demand_mean"], 2) * np.power(df["lead_time_std"], 2))
        )
        total_ss_capital = (ss * df["unit_cost_usd"]).sum()
        annual_carrying_cost = total_ss_capital * annual_holding_cost_rate

        print(f"\n[Target Service Level: {sl*100:.0f}% | Z-Score: {z:.3f}]")
        print(f" - Total Safety Stock Reserve Capital : ${total_ss_capital:,.2f}")
        print(f" - Annual Inventory Carrying Expense  : ${annual_carrying_cost:,.2f}")

    # Top Capital Inefficiencies (SKUs requiring highest working capital reserve)
    z_95 = norm.ppf(0.95)
    df["safety_stock_95"] = np.round(z_95 * np.sqrt(
        (df["lead_time_days"] * np.power(df["daily_demand_std"], 2)) +
        (np.power(df["daily_demand_mean"], 2) * np.power(df["lead_time_std"], 2))
    )).astype(int)
    
    df["rop_units"] = np.round((df["daily_demand_mean"] * df["lead_time_days"]) + df["safety_stock_95"]).astype(int)
    df["ss_capital_usd"] = np.round(df["safety_stock_95"] * df["unit_cost_usd"], 2)

    top_skus = df.sort_values("ss_capital_usd", ascending=False).head(5)
    print("\nTop 5 Working Capital Allocations (95% Cycle Service Level):")
    summary = top_skus[["sku_id", "category", "unit_cost_usd", "eoq_units", "safety_stock_95", "rop_units", "ss_capital_usd"]]
    print(summary.to_string(index=False))


if __name__ == "__main__":
    catalog = generate_inventory_catalog(500)
    print(f"Ingested {len(catalog)} active catalog SKUs. Evaluating replenishment parameters...\n")
    evaluate_inventory_tradeoffs(catalog)