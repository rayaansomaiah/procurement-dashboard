export interface KpiSummary {
  total_skus: number
  skus_needing_indent: number
  total_indent_qty: number
  total_purchase_amount: number
  total_stock_value: number
  unmatched_count: number
}

export interface IndentRow {
  sku_code: string
  item: string
  category: string
  sub_category: string
  brand: string
  qoh: number
  purchase_price: number
  prev_sales_qty: number
  sales_per_week: number
  arc: number
  sales_proj: number
  mdp_cdp: number
  applicability: number
  consumption_hrs: number
  consumption_load: number
  wallet_proj: number
  flf: number
  effective_demand: number
  indent_qty: number
  purchase_amount: number
  stock_value: number
  matched: boolean
}

export interface FilterOptions {
  categories: string[]
  sub_categories: string[]
  brands: string[]
}

export interface AnalyzeResponse {
  warnings: string[]
  kpis: KpiSummary
  rows: IndentRow[]
  filter_options: FilterOptions
  unmatched_skus: string[]
}

export interface AnalysisParams {
  machineCount: number
  monthlyUsageHrs: number
  arcWeeks: number
  salesFrom: string
  salesTo: string
}

export interface FilterState {
  category: string[]
  subCategory: string[]
  brand: string[]
  needsIndentOnly: boolean
}
