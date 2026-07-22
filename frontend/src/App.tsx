import { useState, useMemo } from 'react'
import { Toaster } from 'sonner'
import { AlertTriangle } from 'lucide-react'
import { useAppStore } from './store/useAppStore'
import Sidebar from './components/layout/Sidebar'
import KpiCards from './components/kpi/KpiCards'
import TableFilters from './components/table/TableFilters'
import ProcurementTable from './components/table/ProcurementTable'
import ExportButtons from './components/export/ExportButtons'
import type { IndentRow } from './types/procurement'

export default function App() {
  const { analyzeResult, activeTab, setActiveTab, filters } = useAppStore()
  const [selectedRow, setSelectedRow] = useState<IndentRow | null>(null)

  // Apply filters centrally so KPIs and table share the same filtered set
  const filteredRows = useMemo(() => {
    if (!analyzeResult) return []
    let r = analyzeResult.rows
    if (filters.category.length)    r = r.filter((x) => filters.category.includes(x.category.trim()))
    if (filters.subCategory.length) r = r.filter((x) => filters.subCategory.includes(x.sub_category.trim()))
    if (filters.brand.length)       r = r.filter((x) => filters.brand.includes(x.brand.trim()))
    if (filters.needsIndentOnly)    r = r.filter((x) => x.indent_qty > 0)
    return r
  }, [analyzeResult, filters])

  const unmatched = analyzeResult?.kpis.unmatched_count ?? 0

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100">
      <Toaster theme="dark" position="top-right" />
      <Sidebar />

      <main className="flex-1 overflow-auto p-6 flex flex-col gap-6">
        {!analyzeResult ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center min-h-[60vh]">
            <div className="text-6xl">📦</div>
            <h1 className="text-2xl font-bold text-white">Replenishment Indent Dashboard</h1>
            <p className="text-gray-400 max-w-sm">
              Upload your indent sheet in the sidebar. QOH and sales are pulled live from Zoho.
            </p>
          </div>
        ) : (
          <>
            <div>
              <h1 className="text-xl font-bold text-white mb-4">Replenishment Indent Dashboard</h1>
              <KpiCards rows={filteredRows} />
            </div>

            {unmatched > 0 && (
              <div className="flex items-start gap-2 bg-amber-950/40 border border-amber-800/50 rounded-lg px-4 py-3 text-sm text-amber-200">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>
                  <strong>{unmatched}</strong> SKU(s) could not be matched to Zoho (treated as 0 stock &amp; 0 sales).
                  Check the "Zoho Matched" column and correct their SKU codes if needed.
                </span>
              </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-800 flex gap-1">
              {(['table', 'export'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                    activeTab === tab
                      ? 'border-blue-500 text-white'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {tab === 'table' ? 'Indent Table' : 'Export'}
                </button>
              ))}
            </div>

            {activeTab === 'table' && (
              <div className="flex flex-col gap-4">
                <TableFilters options={analyzeResult.filter_options} />
                <ProcurementTable
                  rows={filteredRows}
                  onSelectRow={setSelectedRow}
                  selectedSku={selectedRow?.sku_code ?? null}
                />
              </div>
            )}

            {activeTab === 'export' && <ExportButtons />}
          </>
        )}
      </main>
    </div>
  )
}
