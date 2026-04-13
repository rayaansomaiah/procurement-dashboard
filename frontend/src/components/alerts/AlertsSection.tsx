import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import type { ProcurementRow } from '../../types/procurement'

interface Props { rows: ProcurementRow[] }

function AlertCard({ row }: { row: ProcurementRow }) {
  const [open, setOpen] = useState(false)
  const isCritical = row.urgency === 'Critical'

  return (
    <div className={`rounded-lg border ${isCritical ? 'border-red-800 bg-red-950/30' : 'border-orange-800 bg-orange-950/20'}`}>
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
        <span className={`text-sm font-medium ${isCritical ? 'text-red-400' : 'text-orange-400'}`}>
          {isCritical ? '🔴' : '🟠'} {row.urgency}
        </span>
        <span className="text-sm text-gray-200">
          {row.sku_code}: {row.description}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Order Qty', value: row.recommended_order_qty },
              { label: 'Vendor', value: row.recommended_vendor || '—' },
              { label: 'Est. Cost', value: `₹${row.estimated_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-800 rounded p-3 text-center">
                <div className="text-xs text-gray-400 mb-1">{label}</div>
                <div className="text-sm font-semibold text-white">{value}</div>
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{row.reason}</p>
        </div>
      )}
    </div>
  )
}

export default function AlertsSection({ rows }: Props) {
  const critical = rows.filter((r) => r.urgency === 'Critical')
  const high = rows.filter((r) => r.urgency === 'High')
  const alertRows = [...critical, ...high]

  if (alertRows.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No critical or high urgency items. All parts are well-stocked.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-400">
        <span className="text-red-400 font-medium">{critical.length} Critical</span>
        {' '}items need immediate ordering
        {high.length > 0 && (
          <> | <span className="text-orange-400 font-medium">{high.length} High</span> items need ordering soon</>
        )}
      </p>
      {alertRows.map((r) => <AlertCard key={r.sku_code} row={r} />)}
    </div>
  )
}
