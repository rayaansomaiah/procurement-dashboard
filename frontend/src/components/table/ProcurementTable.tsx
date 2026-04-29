import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnDef,
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

// Common columns shown in all views
const commonCols = [
  col.accessor('sku_code', { header: 'Part No' }),
  col.accessor('description', { header: 'Description' }),
  col.accessor('category', { header: 'Category' }),
  col.accessor('current_stock', { header: 'Current Stock' }),
  col.accessor('stock_cover_days', { header: 'Stock Cover (Days)' }),
  col.accessor('recommended_vendor', { header: 'Vendor' }),
  col.accessor('recommended_lead_days', { header: 'Lead (Days)' }),
  col.accessor('recommended_unit_price', {
    header: 'Unit Price (₹)',
    cell: (i) => `₹${i.getValue().toFixed(2)}`,
  }),
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

// Side-by-side: all 3 periods in one row
const sideBySideCols = [
  col.accessor('sku_code', { header: 'Part No' }),
  col.accessor('description', { header: 'Description' }),
  col.accessor('category', { header: 'Category' }),
  col.accessor('current_stock', { header: 'Current Stock' }),
  col.accessor('stock_cover_days', { header: 'Stock Cover' }),
  col.accessor('recommended_vendor', { header: 'Vendor' }),
  col.accessor('recommended_lead_days', { header: 'Lead (Days)' }),
  col.accessor('recommended_unit_price', {
    header: 'Unit Price (₹)',
    cell: (i) => `₹${i.getValue().toFixed(2)}`,
  }),
  // Month 1
  col.accessor('recommended_order_qty', { header: 'M1 Order Qty' }),
  col.accessor('order_by_date', { header: 'M1 Order By' }),
  col.accessor('estimated_cost', {
    header: 'M1 Cost (₹)',
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  // Month 2
  col.accessor('order_qty_m2', { header: 'M2 Order Qty' }),
  col.accessor('order_by_m2', { header: 'M2 Order By' }),
  col.accessor('est_cost_m2', {
    header: 'M2 Cost (₹)',
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  // Month 3
  col.accessor('order_qty_m3', { header: 'M3 Order Qty' }),
  col.accessor('order_by_m3', { header: 'M3 Order By' }),
  col.accessor('est_cost_m3', {
    header: 'M3 Cost (₹)',
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
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

// Tab view columns for a specific period
function tabCols(period: 1 | 2 | 3): ColumnDef<ProcurementRow, any>[] {
  const periodCols =
    period === 1
      ? [
          col.accessor('recommended_order_qty', { header: 'Order Qty' }),
          col.accessor('order_by_date', { header: 'Order By' }),
          col.accessor('estimated_cost', {
            header: 'Est. Cost (₹)',
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]
      : period === 2
      ? [
          col.accessor('order_qty_m2', { header: 'Order Qty' }),
          col.accessor('order_by_m2', { header: 'Order By' }),
          col.accessor('est_cost_m2', {
            header: 'Est. Cost (₹)',
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]
      : [
          col.accessor('order_qty_m3', { header: 'Order Qty' }),
          col.accessor('order_by_m3', { header: 'Order By' }),
          col.accessor('est_cost_m3', {
            header: 'Est. Cost (₹)',
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]

  return [...commonCols.slice(0, 5), ...periodCols, ...commonCols.slice(5)]
}

interface Props {
  rows: ProcurementRow[]
  onSelectRow: (row: ProcurementRow) => void
  selectedSku: string | null
}

function TableView({
  data,
  columns,
  onSelectRow,
  selectedSku,
}: {
  data: ProcurementRow[]
  columns: ColumnDef<ProcurementRow, any>[]
  onSelectRow: (row: ProcurementRow) => void
  selectedSku: string | null
}) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'urgency', desc: false }])

  const table = useReactTable({
    data,
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

export default function ProcurementTable({ rows, onSelectRow, selectedSku }: Props) {
  const { filters } = useAppStore()
  const [viewMode, setViewMode] = useState<'sidebyside' | 'tabs'>('sidebyside')
  const [activeMonth, setActiveMonth] = useState<1 | 2 | 3>(1)

  const filtered = useMemo(() => {
    let r = rows
    if (filters.urgency.length) r = r.filter((x) => filters.urgency.includes(x.urgency))
    if (filters.category.length) r = r.filter((x) => filters.category.includes(x.category.trim()))
    if (filters.vendor.length) r = r.filter((x) => filters.vendor.includes(x.recommended_vendor))
    if (filters.actionOnly) r = r.filter((x) => x.recommended_order_qty > 0)
    return r
  }, [rows, filters])

  const MONTH_LABELS: Record<1 | 2 | 3, string> = {
    1: 'Month 1 — Now',
    2: 'Month 2 — Day 30',
    3: 'Month 3 — Day 60',
  }

  return (
    <div className="flex flex-col gap-3">
      {/* View toggle */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400 mr-1">View:</span>
        {(['sidebyside', 'tabs'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              viewMode === mode
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {mode === 'sidebyside' ? 'Side by Side' : 'By Month'}
          </button>
        ))}

        {/* Month tabs — only show in tab view */}
        {viewMode === 'tabs' && (
          <div className="flex items-center gap-1 ml-4 border-l border-gray-700 pl-4">
            {([1, 2, 3] as const).map((m) => (
              <button
                key={m}
                onClick={() => setActiveMonth(m)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  activeMonth === m
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {MONTH_LABELS[m]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Table */}
      {viewMode === 'sidebyside' ? (
        <TableView
          data={filtered}
          columns={sideBySideCols}
          onSelectRow={onSelectRow}
          selectedSku={selectedSku}
        />
      ) : (
        <TableView
          data={filtered}
          columns={tabCols(activeMonth)}
          onSelectRow={onSelectRow}
          selectedSku={selectedSku}
        />
      )}
    </div>
  )
}
