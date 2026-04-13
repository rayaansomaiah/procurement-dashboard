import { create } from 'zustand'
import type { AnalysisParams, AnalyzeResponse, FilterState } from '../types/procurement'

interface AppStore {
  // Sidebar params
  params: AnalysisParams
  setParams: (p: Partial<AnalysisParams>) => void

  // File
  uploadedFile: File | null
  setUploadedFile: (f: File) => void

  // Result
  analyzeResult: AnalyzeResponse | null
  setAnalyzeResult: (r: AnalyzeResponse) => void

  // Filters
  filters: FilterState
  setFilter: (f: Partial<FilterState>) => void

  // Tab
  activeTab: 'table' | 'alerts' | 'export'
  setActiveTab: (t: 'table' | 'alerts' | 'export') => void
}

export const useAppStore = create<AppStore>((set) => ({
  params: {
    numMachines: 1,
    horizonDays: 30,
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
