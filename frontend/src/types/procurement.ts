export interface KpiSummary {
  total_skus: number
  critical: number
  high: number
  action_needed: number
  est_total_spend: number
}

export interface ProcurementRow {
  sku_code: string
  description: string
  category: string
  monthly_demand: number
  current_stock: number
  stock_cover_days: number
  recommended_order_qty: number
  recommended_vendor: string
  recommended_lead_days: number
  recommended_unit_price: number
  estimated_cost: number
  order_by_date: string
  urgency: string
  flags: string
  reason: string
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
  numMachines: number
  horizonDays: 30 | 60 | 90
  safetyBufferPct: number
  vendorStrategy: 'Prefer L1' | 'Fastest Delivery' | 'Cheapest Price'
}

export interface FilterState {
  urgency: string[]
  category: string[]
  vendor: string[]
  actionOnly: boolean
}
