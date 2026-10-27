# Supply Chain Inventory Optimization & Safety Stock Engine

A multi-echelon inventory replenishment engine designed to balance cycle service levels against working capital lockup using dynamic safety stock formulas, Reorder Points (ROP), and Economic Order Quantity (EOQ).

## Overview
Retail and e-commerce distribution networks face an ongoing trade-off: over-ordering binds expensive working capital in warehouse holding costs, while under-ordering causes immediate stockouts and missed revenue. This framework calculates statistical replenishment parameters that adjust automatically to demand volatility and supplier lead-time variance.

## Project Structure
- `inventory_reorder_pipeline.sql`: Production SQL CTE pipeline computing rolling 30-day demand variance, combined lead-time uncertainty, and live warehouse reorder alerts.
- `safety_stock_optimizer.py`: Python script evaluating Economic Order Quantity (EOQ) lot sizing and capital trade-offs across 90%, 95%, and 99% cycle service levels.
- `requirements.txt`: Python package dependencies.

## Key Operational Metrics
1. **Dynamic Safety Stock:** Modeled using the dual-variance formula:
   `SS = Z * sqrt(L * sigma_D^2 + D^2 * sigma_L^2)`
   accounting for both customer order spikes and vendor shipping delays.
2. **Reorder Point (ROP):** Automated replenishment triggers based on expected lead-time consumption buffer.
3. **Capital Carrying Analysis:** Quantifies annual holding expenditure deltas between aggressive 99% fill-rate targets versus balanced 95% service targets.

## How to Run

```bash
# Clone the repository
git clone https://github.com/puneetgoswami1/supply-chain-inventory-optimization-engine.git

# Install dependencies
pip install -r requirements.txt

# Run inventory optimization model
python safety_stock_optimizer.py
