import { create } from 'zustand'
import type { AnalysisParams, AnalyzeResponse, FilterState } from '../types/procurement'

function defaultRange(): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 56) // 8 weeks
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) }
}

const { from, to } = defaultRange()

interface AppStore {
  params: AnalysisParams
  setParams: (p: Partial<AnalysisParams>) => void

  uploadedFile: File | null
  setUploadedFile: (f: File) => void

  analyzeResult: AnalyzeResponse | null
  setAnalyzeResult: (r: AnalyzeResponse) => void

  filters: FilterState
  setFilter: (f: Partial<FilterState>) => void

  activeTab: 'table' | 'export'
  setActiveTab: (t: 'table' | 'export') => void

  // Per-SKU overrides edited inline in the table
  qohOverrides: Record<string, number>
  setQohOverride: (sku: string, value: number) => void
  clearQohOverrides: () => void

  flfOverrides: Record<string, number>
  setFlfOverride: (sku: string, value: number) => void
  clearFlfOverrides: () => void
}

export const useAppStore = create<AppStore>((set) => ({
  params: {
    machineCount: 500,
    monthlyUsageHrs: 130,
    arcWeeks: 1,
    salesFrom: from,
    salesTo: to,
  },
  setParams: (p) => set((s) => ({ params: { ...s.params, ...p } })),

  uploadedFile: null,
  setUploadedFile: (f) => set({ uploadedFile: f }),

  analyzeResult: null,
  setAnalyzeResult: (r) => set({ analyzeResult: r }),

  filters: { category: [], subCategory: [], brand: [], needsIndentOnly: false },
  setFilter: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),

  activeTab: 'table',
  setActiveTab: (t) => set({ activeTab: t }),

  qohOverrides: {},
  setQohOverride: (sku, value) =>
    set((s) => ({ qohOverrides: { ...s.qohOverrides, [sku]: value } })),
  clearQohOverrides: () => set({ qohOverrides: {} }),

  flfOverrides: {},
  setFlfOverride: (sku, value) =>
    set((s) => ({ flfOverrides: { ...s.flfOverrides, [sku]: value } })),
  clearFlfOverrides: () => set({ flfOverrides: {} }),
}))
