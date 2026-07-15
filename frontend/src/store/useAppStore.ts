import { create } from 'zustand'
import type { AnalysisParams, AnalyzeResponse, FilterState, SalesData } from '../types/procurement'

interface AppStore {
  params: AnalysisParams
  setParams: (p: Partial<AnalysisParams>) => void

  uploadedFile: File | null
  setUploadedFile: (f: File) => void

  analyzeResult: AnalyzeResponse | null
  setAnalyzeResult: (r: AnalyzeResponse) => void

  filters: FilterState
  setFilter: (f: Partial<FilterState>) => void

  activeTab: 'table' | 'alerts' | 'export'
  setActiveTab: (t: 'table' | 'alerts' | 'export') => void

  // Per-SKU current stock overrides (edited inline in the table)
  stockOverrides: Record<string, number>
  setStockOverride: (sku: string, value: number) => void
  clearStockOverrides: () => void

  // Sales data from Zoho (keyed by sku_code)
  salesData: Record<string, SalesData>
  setSalesData: (d: Record<string, SalesData>) => void
  clearSalesData: () => void

  // Date range for sales query
  salesFromDate: string
  salesToDate: string
  setSalesFromDate: (d: string) => void
  setSalesToDate: (d: string) => void
}

export const useAppStore = create<AppStore>((set) => ({
  params: {
    machinesM1: 0,
    machinesM2: 0,
    machinesM3: 0,
    safetyBufferPct: 20,
    vendorStrategy: 'Prefer L1',
  },
  setParams: (p) => set((s) => ({ params: { ...s.params, ...p } })),

  uploadedFile: null,
  setUploadedFile: (f) => set({ uploadedFile: f }),

  analyzeResult: null,
  setAnalyzeResult: (r) => set({ analyzeResult: r }),

  filters: { urgency: [], category: [], vendor: [], actionOnly: false },
  setFilter: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),

  activeTab: 'table',
  setActiveTab: (t) => set({ activeTab: t }),

  stockOverrides: {},
  setStockOverride: (sku, value) =>
    set((s) => ({ stockOverrides: { ...s.stockOverrides, [sku]: value } })),
  clearStockOverrides: () => set({ stockOverrides: {} }),

  salesData: {},
  setSalesData: (d) => set({ salesData: d }),
  clearSalesData: () => set({ salesData: {} }),

  salesFromDate: (() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 2)
    return d.toISOString().slice(0, 10)
  })(),
  salesToDate: new Date().toISOString().slice(0, 10),
  setSalesFromDate: (d) => set({ salesFromDate: d }),
  setSalesToDate: (d) => set({ salesToDate: d }),
}))
