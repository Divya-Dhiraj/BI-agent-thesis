class SQLGuardian:
    """The Compulsory Narrative for all 100+ columns."""
    
    SHIPPED_COLUMNS = {
        "Volume & Revenue": "shipped_units (Total units sent), product_gms (Gross Revenue), shipped_cogs (Cost to Amazon).",
        "Hierarchy": "gl_product_group, subcategory_description, category, product_type, brand_name, manufacturer_name.",
        "Time": "mapped_year, mapped_month, mapped_week (Always use 'mapped' to align returns with sales).",
        "Flags": "is_hctp (Consumer Trust), is_premium_flag, is_b2b, is_hrr_asin (High Return Risk), is_pls_eligible."
    }
    
    CONCESSION_COLUMNS = {
        "Metrics": "ncrc (Net Concession Cost - TRUE LOSS), conceded_units (Volume of returns), margin (Profit after loss).",
        "Financials": "gcv (Gross), ncv (Net), returned_cogs, seller_reimbursement, damage_allowance, total_retrocharge_amt.",
        "Recovery": "recovery_amt_liquidate, recovery_amt_warehouse_deal, recovery_amt_repair, recovery_amt_destroy.",
        "Costs": "processing_cost, return_ship_cost, outbound_ship_cost_whd, trans_cost_internal, repair_cost.",
        "Diagnostics": "is_andon_cord (Stop Sale flag), defect_category, root_cause, is_hb (High Bolus returns), is_sioc."
    }

    @classmethod
    def get_narrative(cls, intent: str):
        if "sales" in intent.lower():
            return cls.SHIPPED_COLUMNS
        return {**cls.SHIPPED_COLUMNS, **cls.CONCESSION_COLUMNS}