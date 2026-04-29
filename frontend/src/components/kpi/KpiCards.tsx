import type { KpiSummary } from '../../types/procurement'

interface Props { kpis: KpiSummary }

const countCards = [
  { label: 'Total SKUs',    key: 'total_skus',    color: 'text-white',       icon: '📦' },
  { label: 'Critical',      key: 'critical',       color: 'text-red-400',     icon: '🔴' },
  { label: 'High',          key: 'high',           color: 'text-orange-400',  icon: '🟠' },
  { label: 'Action Needed', key: 'action_needed',  color: 'text-gray-300',    icon: '📋' },
] as const

const spendCards = [
  { label: 'Month 1 Spend (Now)',    key: 'est_total_spend_m1', color: 'text-yellow-400' },
  { label: 'Month 2 Spend (Day 30)', key: 'est_total_spend_m2', color: 'text-blue-400'   },
  { label: 'Month 3 Spend (Day 60)', key: 'est_total_spend_m3', color: 'text-purple-400' },
] as const

export default function KpiCards({ kpis }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {/* Count row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {countCards.map((c) => (
          <div key={c.key} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 mb-1">{c.icon} {c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>{kpis[c.key].toLocaleString()}</div>
          </div>
        ))}
      </div>

      {/* Spend row */}
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
