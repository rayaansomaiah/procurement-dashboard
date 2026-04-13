import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import type { ProcurementRow } from '../../types/procurement'
import { useAppStore } from '../../store/useAppStore'

const URGENCY_ORDER: Record<string, number> = {
  Critical: 0, High: 1, Medium: 2, Low: 3, 'No Action': 4,
}

const URGENCY_BADGE: Record<string, string> = {
  Critical: 'bg-red-600 text-white',
  High: 'bg-orange-500 text-white',
  Medium: 'bg-yellow-500 text-gray-900',
  Low: 'bg-green-600 text-white',
  'No Action': 'bg-gray-600 text-gray-200',
}

const ROW_COLOR: Record<string, string> = {
  Critical: 'bg-red-950/40',
  High: 'bg-orange-950/40',
  Medium: 'bg-yellow-950/20',
  Low: 'bg-green-950/20',
  'No Action': '',
}

const col = createColumnHelper<ProcurementRow>()

const columns = [
  col.accessor('sku_code', { header: 'Part No' }),
  col.accessor('description', { header: 'Description' }),
  col.accessor('category', { header: 'Category' }),
  col.accessor('monthly_demand', {
    header: 'Monthly Demand',
    cell: (i) => i.getValue().toFixed(1),
  }),
  col.accessor('current_stock', { header: 'Current Stock' }),
  col.accessor('stock_cover_days', { header: 'Stock Cover (Days)' }),
  col.accessor('recommended_order_qty', { header: 'Order Qty' }),
  col.accessor('recommended_vendor', { header: 'Vendor' }),
  col.accessor('recommended_lead_days', { header: 'Lead (Days)' }),
  col.accessor('recommended_unit_price', {
    header: 'Unit Price (₹)',
    cell: (i) => `₹${i.getValue().toFixed(2)}`,
  }),
  col.accessor('estimated_cost', {
    header: 'Est. Cost (₹)',
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  col.accessor('order_by_date', { header: 'Order By' }),
  col.accessor('urgency', {
    header: 'Urgency',
    sortingFn: (a, b) =>
      (URGENCY_ORDER[a.original.urgency] ?? 5) - (URGENCY_ORDER[b.original.urgency] ?? 5),
    cell: (i) => (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${URGENCY_BADGE[i.getValue()] ?? ''}`}>
        {i.getValue()}
      </span>
    ),
  }),
  col.accessor('flags', { header: 'Flags' }),
]

interface Props {
  rows: ProcurementRow[]
  onSelectRow: (row: ProcurementRow) => void
  selectedSku: string | null
}

export default function ProcurementTable({ rows, onSelectRow, selectedSku }: Props) {
  const { filters } = useAppStore()
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'urgency', desc: false },
  ])

  const filtered = useMemo(() => {
    let r = rows
    if (filters.urgency.length) r = r.filter((x) => filters.urgency.includes(x.urgency))
    if (filters.category.length) r = r.filter((x) => filters.category.includes(x.category))
    if (filters.vendor.length) r = r.filter((x) => filters.vendor.includes(x.recommended_vendor))
    if (filters.actionOnly) r = r.filter((x) => x.recommended_order_qty > 0)
    return r
  }, [rows, filters])

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="overflow-auto rounded-lg border border-gray-800 max-h-[520px]">
      <table className="w-full text-sm border-collapse min-w-max">
        <thead className="sticky top-0 z-10">
          <tr className="bg-gray-900 border-b border-gray-700">
            {table.getFlatHeaders().map((header) => (
              <th
                key={header.id}
                onClick={header.column.getToggleSortingHandler()}
                className="px-3 py-2.5 text-left text-xs text-gray-400 font-medium whitespace-nowrap cursor-pointer select-none hover:text-gray-200"
              >
                <span className="inline-flex items-center gap-1">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getIsSorted() === 'asc' && <ChevronUp className="w-3 h-3" />}
                  {header.column.getIsSorted() === 'desc' && <ChevronDown className="w-3 h-3" />}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onSelectRow(row.original)}
              className={`border-b border-gray-800/60 cursor-pointer transition-colors hover:bg-gray-700/40
                ${ROW_COLOR[row.original.urgency] ?? ''}
                ${selectedSku === row.original.sku_code ? 'ring-1 ring-inset ring-blue-500' : ''}`}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 text-gray-200 whitespace-nowrap">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {table.getRowModel().rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="text-center py-8 text-gray-500">
                No items match the current filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
