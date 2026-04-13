import type { KpiSummary } from '../../types/procurement'

interface Props { kpis: KpiSummary }

const cards = [
  { label: 'Total SKUs', key: 'total_skus', color: 'text-white', icon: '📦' },
  { label: 'Critical', key: 'critical', color: 'text-red-400', icon: '🔴' },
  { label: 'High', key: 'high', color: 'text-orange-400', icon: '🟠' },
  { label: 'Action Needed', key: 'action_needed', color: 'text-gray-300', icon: '📋' },
] as const

export default function KpiCards({ kpis }: Props) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      {cards.map((c) => (
        <div key={c.key} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <div className="text-xs text-gray-400 mb-1">{c.icon} {c.label}</div>
          <div className={`text-2xl font-bold ${c.color}`}>{kpis[c.key].toLocaleString()}</div>
        </div>
      ))}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 lg:col-span-1">
        <div className="text-xs text-gray-400 mb-1">💰 Est. Total Spend</div>
        <div className="text-2xl font-bold text-yellow-400">
          ₹{kpis.est_total_spend.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
        </div>
      </div>
    </div>
  )
}
