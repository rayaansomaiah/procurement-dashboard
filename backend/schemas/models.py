from pydantic import BaseModel
from typing import List, Optional


class KpiSummary(BaseModel):
    total_skus: int
    critical: int
    high: int
    action_needed: int
    est_total_spend_m1: float = 0.0
    est_total_spend_m2: float = 0.0
    est_total_spend_m3: float = 0.0


class ProcurementRow(BaseModel):
    sku_code: str
    description: str
    category: Optional[str] = None
    monthly_demand: float
    current_stock: int
    stock_cover_days: int
    # Period 1 (machines onboarded now)
    recommended_order_qty: int
    order_by_date: str
    estimated_cost: float
    # Period 2 (machines onboarding at day 30)
    order_qty_m2: int = 0
    order_by_m2: str = "—"
    est_cost_m2: float = 0.0
    # Period 3 (machines onboarding at day 60)
    order_qty_m3: int = 0
    order_by_m3: str = "—"
    est_cost_m3: float = 0.0
    # Common
    recommended_vendor: Optional[str] = None
    recommended_lead_days: int = 0
    recommended_unit_price: float = 0.0
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
