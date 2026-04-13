import type { ProcurementRow } from '../../types/procurement'

interface Props {
  rows: ProcurementRow[]
  selected: ProcurementRow | null
  onSelect: (row: ProcurementRow) => void
}

const URGENCY_COLOR: Record<string, string> = {
  Critical: 'text-red-400',
  High: 'text-orange-400',
  Medium: 'text-yellow-400',
  Low: 'text-green-400',
  'No Action': 'text-gray-400',
}

export default function ReasoningPanel({ rows, selected, onSelect }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-400 whitespace-nowrap">View reasoning for:</label>
        <select
          value={selected?.sku_code ?? ''}
          onChange={(e) => {
            const row = rows.find((r) => r.sku_code === e.target.value)
            if (row) onSelect(row)
          }}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white flex-1 focus:outline-none focus:border-blue-500"
        >
          <option value="">— select a part —</option>
          {rows.map((r) => (
            <option key={r.sku_code} value={r.sku_code}>
              {r.sku_code}: {r.description}
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-200 leading-relaxed border-l-4 border-blue-600">
          <div className="flex items-center gap-2 mb-2">
            <span className={`font-semibold ${URGENCY_COLOR[selected.urgency] ?? ''}`}>
              {selected.urgency}
            </span>
            <span className="text-gray-400">|</span>
            <span className="text-gray-300 font-medium">{selected.sku_code} — {selected.description}</span>
          </div>
          <p>{selected.reason}</p>
        </div>
      )}
    </div>
  )
}
