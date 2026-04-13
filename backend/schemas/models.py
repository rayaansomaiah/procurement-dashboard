from pydantic import BaseModel
from typing import List, Optional


class KpiSummary(BaseModel):
    total_skus: int
    critical: int
    high: int
    action_needed: int
    est_total_spend: float


class ProcurementRow(BaseModel):
    sku_code: str
    description: str
    category: Optional[str] = None
    monthly_demand: float
    current_stock: int
    stock_cover_days: int
    recommended_order_qty: int
    recommended_vendor: Optional[str] = None
    recommended_lead_days: int
    recommended_unit_price: float
    estimated_cost: float
    order_by_date: str
    urgency: str
    flags: str
    reason: str


class FilterOptions(BaseModel):
    urgency_levels: List[str]
    categories: List[str]
    vendors: List[str]


class AnalyzeResponse(BaseModel):
    warnings: List[str]
    kpis: KpiSummary
    rows: List[ProcurementRow]
    filter_options: FilterOptions
