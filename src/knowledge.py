"""
src/knowledge.py
The Semantic Brain. This file translates your specific Amazon business logic 
into a format the LLM can use to 'reason' about data.
"""

DOMAIN_KNOWLEDGE = """
### 1. DATASET OVERVIEW
We have two connected datasets regarding Smartphone sales in Germany (Marketplace 4).
- **Table `shipped_raw` (The Revenue Side):** Tracks the outflow of goods (Sales).
- **Table `concession_raw` (The Cost Side):** Tracks returns, refunds, and financial concessions.

### 2. THE GOLDEN LINKING RULE (CRITICAL)
To link a Return (Concession) back to its original Sale:
- **Foreign Key Logic:** `concession_raw` entries map to `shipped_raw` entries using the **mapped** date columns.
- **Strict Join Clause:** `c.asin = s.asin` 
  AND `c.mapped_year = s.year` 
  AND `c.mapped_month = s.month` 
  AND `c.mapped_week = s.week`

### 3. DETAILED DATA DICTIONARY

#### TABLE A: `shipped_raw` (Revenue/Sales)
* **Identifiers:**
  - `ncrc_su_pk`: Unique Primary Key for the shipment record.
  - `gl_product_group`: General Ledger group (e.g., 107 Wireless).
  - `subcategory_code` / `subcategory_description`: Specific category (e.g., Smart Phone).
  - `fulfillment_channel`: 'RET' (Amazon Retail) or 'AFN'/'FBA' (Fulfilled by Amazon).
  - `child_vendor_code`: Vendor identifier.
* **Time Dimensions:**
  - `year`, `month`, `week`: Date when the shipment occurred.
* **Sales Metrics:**
  - `shipped_units`: Volume of units sold.
  - `product_gms`: Gross Merchandise Sales (Revenue = Sales Price * Units).
  - `shipped_cogs`: Cost of Goods Sold. 
    - **RULE:** If `fulfillment_channel` = 'RET', value = `item_fifo_cost * units * exchange_rate`.
    - **RULE:** If `fulfillment_channel` is 'FBA' or 'FBS', value is 0.

#### TABLE B: `concession_raw` (Returns/Cost)
* **Identifiers & Categorization:**
  - `ncrc_cu_pk`: Unique Primary Key for concession record.
  - `marketplace_id`: Region ID (4 = Germany).
  - `brand_name` / `manufacturer_name`: e.g., Apple, Samsung.
  - `vendor_management_type`: Vendor tier (e.g., 'T1' = Direct Relationship).
  - `product_type`: Technical classification (e.g., CELLULAR_PHONE).
* **Time Dimensions:**
  - `year`, `month`, `week`: Date when the **return/concession happened**.
  - `mapped_year`, `mapped_month`, `mapped_week`: Date when the item was **originally shipped**. (Use these for Joins).
* **Product & Return Attributes:**
  - `asin` / `item_name`: Product ID and Title.
  - `asp_bucket`: Average Selling Price range (e.g., '>500', '100-500').
  - `return_window`: Days since purchase (e.g., '<=15').
  - `recovery_channel`: Fate of item (WAREHOUSE_DEAL, LIQUIDATE, DESTROY).
  - `defect_category` / `root_cause`: Reason for return (e.g., "Product Defect", "Vendor/Seller Controllable").
  - `is_hctp`: "High Cost To Process" flag.
  - `is_premium_flag`: Premium item flag.
* **Financial Metrics (The "NCRC" Logic):**
  - `conceded_units`: Quantity returned.
  - `gcv` (Gross Concession Value): Total amount refunded to customer.
  - `ncv` (Net Concession Value): GCV minus restocking fees/withheld amounts.
  - `ncrc` (Net Cost of Returns): The Total **Loss** to Amazon. (Key metric for profitability).
  - `returned_cogs`: Original cost of the returned good.
  - `recovery_amt_...`: Money recovered via resale (fifo, liquidate, warehouse_deal, vendor_return, repair, destroy).
  - `margin`: Financial impact on P&L for this return.
* **Risk & Alert Flags:**
  - `is_hrr_asin`: Is this a High Return Rate product? (Y/N).
  - `is_hrrc` / `is_errc` / `is_super_errc`: Return rate violation flags.
  - `is_andon_cord`: **CRITICAL** - Was the "Andon Cord" pulled? (Sales stopped due to safety/quality defect).

### 4. CALCULATED METRICS & DEFINITIONS
- **Net Margin (Profit):** `SUM(product_gms) - SUM(shipped_cogs) - SUM(ncrc)`.
- **Return Rate %:** `(SUM(conceded_units) * 100.0) / NULLIF(SUM(shipped_units), 0)`.
- **"Bleeding" Products:** High `ncrc` or High `conceded_units`.
- **"Safe" Products:** Low Return Rate AND `is_andon_cord` = 'N'.

### 5. QUERY STRATEGIES
- **Trend Analysis:** Aggregate by `mapped_year` and `mapped_month` to align returns with their sales month.
- **Root Cause Analysis:** SELECT `root_cause`, `defect_category`, COUNT(*) FROM `concession_raw` WHERE ...
- **Vendor Performance:** Filter by `vendor_management_type` ('T1') and `brand_name`.
"""