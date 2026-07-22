from pydantic import BaseModel
from typing import List


class KpiSummary(BaseModel):
    total_skus: int
    skus_needing_indent: int
    total_indent_qty: float = 0.0
    total_purchase_amount: float = 0.0
    total_stock_value: float = 0.0
    unmatched_count: int = 0


class IndentRow(BaseModel):
    sku_code: str
    item: str = ""
    category: str = ""
    sub_category: str = ""
    brand: str = ""
    qoh: float = 0.0
    purchase_price: float = 0.0
    prev_sales_qty: float = 0.0
    sales_per_week: float = 0.0
    arc: float = 1.0
    sales_proj: float = 0.0
    mdp_cdp: float = 0.0
    applicability: float = 1.0
    consumption_hrs: float = 0.0
    consumption_load: float = 0.0
    wallet_proj: float = 0.0
    flf: float = 0.0
    effective_demand: int = 0
    indent_qty: int = 0
    purchase_amount: float = 0.0
    stock_value: float = 0.0
    matched: bool = False


class FilterOptions(BaseModel):
    categories: List[str]
    sub_categories: List[str]
    brands: List[str]


class AnalyzeResponse(BaseModel):
    warnings: List[str]
    kpis: KpiSummary
    rows: List[IndentRow]
    filter_options: FilterOptions
    unmatched_skus: List[str]
