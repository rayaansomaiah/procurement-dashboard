import { useState, useMemo } from 'react'
import { Toaster } from 'sonner'
import { useAppStore } from './store/useAppStore'
import Sidebar from './components/layout/Sidebar'
import KpiCards from './components/kpi/KpiCards'
import TableFilters from './components/table/TableFilters'
import ProcurementTable from './components/table/ProcurementTable'
import ReasoningPanel from './components/reasoning/ReasoningPanel'
import AlertsSection from './components/alerts/AlertsSection'
import ExportButtons from './components/export/ExportButtons'
import type { ProcurementRow } from './types/procurement'

export default function App() {
  const { analyzeResult, activeTab, setActiveTab, filters } = useAppStore()
  const [selectedRow, setSelectedRow] = useState<ProcurementRow | null>(null)

  // Apply filters centrally so KPIs and table both use the same filtered set
  const filteredRows = useMemo(() => {
    if (!analyzeResult) return []
    let r = analyzeResult.rows
    if (filters.urgency.length)  r = r.filter((x) => filters.urgency.includes(x.urgency))
    if (filters.category.length) r = r.filter((x) => filters.category.includes(x.category.trim()))
    if (filters.vendor.length)   r = r.filter((x) => filters.vendor.includes(x.recommended_vendor))
    if (filters.actionOnly)      r = r.filter((x) => x.recommended_order_qty > 0)
    return r
  }, [analyzeResult, filters])

  const alertCount = analyzeResult
    ? analyzeResult.rows.filter((r) => r.urgency === 'Critical' || r.urgency === 'High').length
    : 0

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100">
      <Toaster theme="dark" position="top-right" />
      <Sidebar />

      <main className="flex-1 overflow-auto p-6 flex flex-col gap-6">
        {!analyzeResult ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center min-h-[60vh]">
            <div className="text-6xl">📦</div>
            <h1 className="text-2xl font-bold text-white">Procurement Planning Dashboard</h1>
            <p className="text-gray-400 max-w-sm">
              Upload your Excel file in the sidebar to generate procurement recommendations.
            </p>
          </div>
        ) : (
          <>
            <div>
              <h1 className="text-xl font-bold text-white mb-4">Procurement Planning Dashboard</h1>
              <KpiCards rows={filteredRows} />
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-800 flex gap-1">
              {(['table', 'alerts', 'export'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                    activeTab === tab
                      ? 'border-blue-500 text-white'
                      : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {tab === 'table' && 'Procurement Table'}
                  {tab === 'alerts' && `Alerts (${alertCount})`}
                  {tab === 'export' && 'Export'}
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
                <ReasoningPanel
                  rows={filteredRows}
                  selected={selectedRow}
                  onSelect={setSelectedRow}
                />
              </div>
            )}

            {activeTab === 'alerts' && <AlertsSection rows={analyzeResult.rows} />}
            {activeTab === 'export' && <ExportButtons />}
          </>
        )}
      </main>
    </div>
  )
}
