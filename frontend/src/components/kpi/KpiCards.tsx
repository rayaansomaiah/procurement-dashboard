import { useMemo } from 'react'
import type { ProcurementRow } from '../../types/procurement'

interface Props { rows: ProcurementRow[] }

export default function KpiCards({ rows }: Props) {
  const kpis = useMemo(() => ({
    total_skus:       rows.length,
    critical:         rows.filter((r) => r.urgency === 'Critical').length,
    high:             rows.filter((r) => r.urgency === 'High').length,
    action_needed:    rows.filter((r) => r.recommended_order_qty > 0).length,
    est_total_spend_m1: rows.reduce((s, r) => s + (r.estimated_cost  ?? 0), 0),
    est_total_spend_m2: rows.reduce((s, r) => s + (r.est_cost_m2     ?? 0), 0),
    est_total_spend_m3: rows.reduce((s, r) => s + (r.est_cost_m3     ?? 0), 0),
  }), [rows])

  const countCards = [
    { label: 'Total SKUs',    key: 'total_skus'   as const, color: 'text-white',      icon: '📦' },
    { label: 'Critical',      key: 'critical'      as const, color: 'text-red-400',    icon: '🔴' },
    { label: 'High',          key: 'high'          as const, color: 'text-orange-400', icon: '🟠' },
    { label: 'Action Needed', key: 'action_needed' as const, color: 'text-gray-300',   icon: '📋' },
  ]

  const spendCards = [
    { label: 'Month 1 Spend (Now)',    key: 'est_total_spend_m1' as const, color: 'text-yellow-400' },
    { label: 'Month 2 Spend (Day 30)', key: 'est_total_spend_m2' as const, color: 'text-blue-400'   },
    { label: 'Month 3 Spend (Day 60)', key: 'est_total_spend_m3' as const, color: 'text-purple-400' },
  ]

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {countCards.map((c) => (
          <div key={c.key} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 mb-1">{c.icon} {c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>{kpis[c.key].toLocaleString()}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {spendCards.map((c) => (
          <div key={c.key} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 mb-1">💰 {c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>
              ₹{kpis[c.key].toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
