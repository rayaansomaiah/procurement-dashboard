export interface KpiSummary {
  total_skus: number
  critical: number
  high: number
  action_needed: number
  est_total_spend_m1: number
  est_total_spend_m2: number
  est_total_spend_m3: number
}

export interface ProcurementRow {
  sku_code: string
  description: string
  category: string
  monthly_demand: number
  current_stock: number
  stock_cover_days: number
  // Period 1 — machines onboarded now
  recommended_order_qty: number
  order_by_date: string
  estimated_cost: number
  // Period 2 — machines onboarding at day 30
  order_qty_m2: number
  order_by_m2: string
  est_cost_m2: number
  // Period 3 — machines onboarding at day 60
  order_qty_m3: number
  order_by_m3: string
  est_cost_m3: number
  // Common
  recommended_vendor: string
  recommended_vendor_sku: string
  recommended_lead_days: number
  recommended_unit_price: number
  urgency: string
  flags: string
  reason: string
  reason_m2: string
  reason_m3: string
}

export interface FilterOptions {
  urgency_levels: string[]
  categories: string[]
  vendors: string[]
}

export interface AnalyzeResponse {
  warnings: string[]
  kpis: KpiSummary
  rows: ProcurementRow[]
  filter_options: FilterOptions
}

export interface AnalysisParams {
  machinesM1: number
  machinesM2: number
  machinesM3: number
  safetyBufferPct: number
  vendorStrategy: 'Prefer L1' | 'Fastest Delivery' | 'Cheapest Price'
}

export interface FilterState {
  urgency: string[]
  category: string[]
  vendor: string[]
  actionOnly: boolean
}
