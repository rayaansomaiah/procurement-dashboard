import { useMemo } from 'react'
import type { IndentRow } from '../../types/procurement'

interface Props { rows: IndentRow[] }

export default function KpiCards({ rows }: Props) {
  const k = useMemo(() => ({
    total:      rows.length,
    needing:    rows.filter((r) => r.indent_qty > 0).length,
    unmatched:  rows.filter((r) => !r.matched).length,
    indentQty:  rows.reduce((s, r) => s + (r.indent_qty ?? 0), 0),
    purchase:   rows.reduce((s, r) => s + (r.purchase_amount ?? 0), 0),
    stockValue: rows.reduce((s, r) => s + (r.stock_value ?? 0), 0),
  }), [rows])

  const countCards = [
    { label: 'Total SKUs',        value: k.total.toLocaleString(),     color: 'text-white',    icon: '📦' },
    { label: 'SKUs Needing Indent', value: k.needing.toLocaleString(), color: 'text-blue-400', icon: '📋' },
    { label: 'Unmapped SKUs',     value: k.unmatched.toLocaleString(), color: k.unmatched > 0 ? 'text-amber-400' : 'text-gray-300', icon: '⚠️' },
  ]

  const valueCards = [
    { label: 'Total Indent Qty',    value: k.indentQty.toLocaleString('en-IN', { maximumFractionDigits: 0 }), color: 'text-emerald-400', prefix: '' },
    { label: 'Total Purchase Amount', value: k.purchase.toLocaleString('en-IN', { maximumFractionDigits: 0 }), color: 'text-yellow-400', prefix: '₹' },
    { label: 'Total Stock Value',   value: k.stockValue.toLocaleString('en-IN', { maximumFractionDigits: 0 }), color: 'text-purple-400', prefix: '₹' },
  ]

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {countCards.map((c) => (
          <div key={c.label} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 mb-1">{c.icon} {c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {valueCards.map((c) => (
          <div key={c.label} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="text-xs text-gray-400 mb-1">💰 {c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>{c.prefix}{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
