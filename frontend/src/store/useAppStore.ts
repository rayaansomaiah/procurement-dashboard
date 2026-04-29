import { create } from 'zustand'
import type { AnalysisParams, AnalyzeResponse, FilterState } from '../types/procurement'

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
}))
