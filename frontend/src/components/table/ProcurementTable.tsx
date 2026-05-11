import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnDef,
} from '@tanstack/react-table'
import { useState, useEffect } from 'react'
import { ChevronUp, ChevronDown, Pencil } from 'lucide-react'
import type { ProcurementRow } from '../../types/procurement'
import { useAppStore } from '../../store/useAppStore'

// ---------------------------------------------------------------------------
// Inline-editable current stock cell
// ---------------------------------------------------------------------------
function EditableStockCell({ sku, value }: { sku: string; value: number }) {
  const { stockOverrides, setStockOverride } = useAppStore()
  const displayValue = stockOverrides[sku] !== undefined ? stockOverrides[sku] : value
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(displayValue))

  useEffect(() => {
    if (!editing) setDraft(String(displayValue))
  }, [displayValue, editing])

  const commit = () => {
    const parsed = parseFloat(draft)
    const finalVal = isNaN(parsed) || parsed < 0 ? 0 : parsed
    setDraft(String(finalVal))
    setStockOverride(sku, finalVal)
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        type="number"
        min={0}
        value={draft}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit()
          if (e.key === 'Escape') { setDraft(String(displayValue)); setEditing(false) }
        }}
        onClick={(e) => e.stopPropagation()}
        className="w-full bg-gray-700 border border-blue-500 rounded px-1.5 py-0.5 text-sm text-white focus:outline-none"
      />
    )
  }

  const isOverridden = stockOverrides[sku] !== undefined
  return (
    <button
      onClick={(e) => { e.stopPropagation(); setEditing(true) }}
      className={`group flex items-center gap-1 w-full rounded px-1 -mx-1 hover:bg-gray-700/60 transition-colors ${
        isOverridden ? 'text-blue-300' : 'text-gray-200'
      }`}
      title="Click to edit stock"
    >
      <span className="truncate">{displayValue}</span>
      <Pencil className="w-2.5 h-2.5 shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Urgency badge colours
// ---------------------------------------------------------------------------
const URGENCY_ORDER: Record<string, number> = {
  Critical: 0, High: 1, Medium: 2, Low: 3, 'No Action': 4,
}

const URGENCY_BADGE: Record<string, string> = {
  Critical:    'bg-red-600 text-white',
  High:        'bg-orange-500 text-white',
  Medium:      'bg-yellow-500 text-gray-900',
  Low:         'bg-green-600 text-white',
  'No Action': 'bg-gray-600 text-gray-200',
}

const ROW_COLOR: Record<string, string> = {
  Critical:    'bg-red-950/40',
  High:        'bg-orange-950/40',
  Medium:      'bg-yellow-950/20',
  Low:         'bg-green-950/20',
  'No Action': '',
}

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------
const col = createColumnHelper<ProcurementRow>()

const commonCols = [
  col.accessor('sku_code',     { header: 'Part No',       size: 120, minSize: 80,  maxSize: 300 }),
  col.accessor('description',  { header: 'Description',   size: 180, minSize: 100, maxSize: 400 }),
  col.accessor('category',     { header: 'Category',      size: 110, minSize: 80,  maxSize: 200 }),
  col.accessor('current_stock', {
    header: 'Current Stock',
    size: 100, minSize: 70, maxSize: 160,
    cell: (i) => <EditableStockCell sku={i.row.original.sku_code} value={i.getValue()} />,
  }),
  col.accessor('stock_cover_days', {
    header: 'Stock Cover',
    size: 100, minSize: 80, maxSize: 140,
    cell: (i) => i.getValue() >= 999 ? '—' : i.getValue(),
  }),
  col.accessor('recommended_vendor', {
    header: 'Vendor',
    size: 160, minSize: 100, maxSize: 300,
    cell: (i) => {
      const sku = i.row.original.recommended_vendor_sku
      return sku ? `${i.getValue()} (${sku})` : i.getValue()
    },
  }),
  col.accessor('recommended_lead_days', { header: 'Lead (Days)', size: 85, minSize: 65, maxSize: 120 }),
  col.accessor('recommended_unit_price', {
    header: 'Unit Price (₹)',
    size: 105, minSize: 80, maxSize: 150,
    cell: (i) => `₹${i.getValue().toFixed(2)}`,
  }),
  col.accessor('urgency', {
    header: 'Urgency',
    size: 95, minSize: 75, maxSize: 130,
    sortingFn: (a, b) =>
      (URGENCY_ORDER[a.original.urgency] ?? 5) - (URGENCY_ORDER[b.original.urgency] ?? 5),
    cell: (i) => (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${URGENCY_BADGE[i.getValue()] ?? ''}`}>
        {i.getValue()}
      </span>
    ),
  }),
  col.accessor('flags', { header: 'Flags', size: 105, minSize: 70, maxSize: 220 }),
]

// Side-by-side: all 3 periods in one row
const sideBySideCols = [
  col.accessor('sku_code',    { header: 'Part No',     size: 120, minSize: 80,  maxSize: 300 }),
  col.accessor('description', { header: 'Description', size: 180, minSize: 100, maxSize: 400 }),
  col.accessor('category',    { header: 'Category',    size: 110, minSize: 80,  maxSize: 200 }),
  col.accessor('current_stock', {
    header: 'Current Stock',
    size: 100, minSize: 70, maxSize: 160,
    cell: (i) => <EditableStockCell sku={i.row.original.sku_code} value={i.getValue()} />,
  }),
  col.accessor('stock_cover_days', {
    header: 'Stock Cover',
    size: 100, minSize: 80, maxSize: 140,
    cell: (i) => i.getValue() >= 999 ? '—' : i.getValue(),
  }),
  col.accessor('recommended_vendor', {
    header: 'Vendor',
    size: 160, minSize: 100, maxSize: 300,
    cell: (i) => {
      const sku = i.row.original.recommended_vendor_sku
      return sku ? `${i.getValue()} (${sku})` : i.getValue()
    },
  }),
  col.accessor('recommended_lead_days', { header: 'Lead (Days)', size: 85, minSize: 65, maxSize: 120 }),
  col.accessor('recommended_unit_price', {
    header: 'Unit Price (₹)',
    size: 105, minSize: 80, maxSize: 150,
    cell: (i) => `₹${i.getValue().toFixed(2)}`,
  }),
  // Month 1
  col.accessor('recommended_order_qty', { header: 'M1 Qty',     size: 80,  minSize: 65, maxSize: 120 }),
  col.accessor('order_by_date',          { header: 'M1 Order By', size: 105, minSize: 85, maxSize: 140 }),
  col.accessor('estimated_cost', {
    header: 'M1 Cost (₹)',
    size: 110, minSize: 90, maxSize: 160,
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  // Month 2
  col.accessor('order_qty_m2', { header: 'M2 Qty',     size: 80,  minSize: 65, maxSize: 120 }),
  col.accessor('order_by_m2',  { header: 'M2 Order By', size: 105, minSize: 85, maxSize: 140 }),
  col.accessor('est_cost_m2', {
    header: 'M2 Cost (₹)',
    size: 110, minSize: 90, maxSize: 160,
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  // Month 3
  col.accessor('order_qty_m3', { header: 'M3 Qty',     size: 80,  minSize: 65, maxSize: 120 }),
  col.accessor('order_by_m3',  { header: 'M3 Order By', size: 105, minSize: 85, maxSize: 140 }),
  col.accessor('est_cost_m3', {
    header: 'M3 Cost (₹)',
    size: 110, minSize: 90, maxSize: 160,
    cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  }),
  col.accessor('urgency', {
    header: 'Urgency',
    size: 95, minSize: 75, maxSize: 130,
    sortingFn: (a, b) =>
      (URGENCY_ORDER[a.original.urgency] ?? 5) - (URGENCY_ORDER[b.original.urgency] ?? 5),
    cell: (i) => (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${URGENCY_BADGE[i.getValue()] ?? ''}`}>
        {i.getValue()}
      </span>
    ),
  }),
  col.accessor('flags', { header: 'Flags', size: 105, minSize: 70, maxSize: 220 }),
]

function tabCols(period: 1 | 2 | 3): ColumnDef<ProcurementRow, any>[] {
  const periodCols =
    period === 1
      ? [
          col.accessor('recommended_order_qty', { header: 'Order Qty',    size: 90,  minSize: 70, maxSize: 130 }),
          col.accessor('order_by_date',          { header: 'Order By',     size: 105, minSize: 85, maxSize: 140 }),
          col.accessor('estimated_cost', {
            header: 'Est. Cost (₹)',
            size: 110, minSize: 90, maxSize: 160,
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]
      : period === 2
      ? [
          col.accessor('order_qty_m2', { header: 'Order Qty',    size: 90,  minSize: 70, maxSize: 130 }),
          col.accessor('order_by_m2',  { header: 'Order By',     size: 105, minSize: 85, maxSize: 140 }),
          col.accessor('est_cost_m2', {
            header: 'Est. Cost (₹)',
            size: 110, minSize: 90, maxSize: 160,
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]
      : [
          col.accessor('order_qty_m3', { header: 'Order Qty',    size: 90,  minSize: 70, maxSize: 130 }),
          col.accessor('order_by_m3',  { header: 'Order By',     size: 105, minSize: 85, maxSize: 140 }),
          col.accessor('est_cost_m3', {
            header: 'Est. Cost (₹)',
            size: 110, minSize: 90, maxSize: 160,
            cell: (i) => `₹${i.getValue().toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
          }),
        ]

  return [...commonCols.slice(0, 5), ...periodCols, ...commonCols.slice(5)]
}

// ---------------------------------------------------------------------------
// Table view component
// ---------------------------------------------------------------------------
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
    columnResizeMode: 'onChange',
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="overflow-auto rounded-lg border border-gray-800 max-h-[520px]">
      <table
        className="text-sm border-collapse"
        style={{ width: table.getCenterTotalSize(), tableLayout: 'fixed' }}
      >
        <thead className="sticky top-0 z-10">
          <tr className="bg-gray-900 border-b border-gray-700">
            {table.getFlatHeaders().map((header) => (
              <th
                key={header.id}
                style={{ width: header.getSize(), position: 'relative' }}
                className="px-3 py-2.5 text-left text-xs text-gray-400 font-medium overflow-hidden"
              >
                {/* Sort trigger */}
                <span
                  onClick={header.column.getToggleSortingHandler()}
                  className="inline-flex items-center gap-1 cursor-pointer select-none hover:text-gray-200 truncate max-w-full"
                >
                  <span className="truncate">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </span>
                  {header.column.getIsSorted() === 'asc'  && <ChevronUp   className="w-3 h-3 shrink-0" />}
                  {header.column.getIsSorted() === 'desc' && <ChevronDown className="w-3 h-3 shrink-0" />}
                </span>

                {/* Resize handle */}
                <div
                  onMouseDown={header.getResizeHandler()}
                  onTouchStart={header.getResizeHandler()}
                  className={`absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none transition-colors ${
                    header.column.getIsResizing()
                      ? 'bg-blue-500'
                      : 'bg-transparent hover:bg-gray-600'
                  }`}
                />
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
                <td
                  key={cell.id}
                  style={{ width: cell.column.getSize() }}
                  className="px-3 py-2 text-gray-200 overflow-hidden"
                >
                  <div className="truncate">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
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

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------
export default function ProcurementTable({ rows, onSelectRow, selectedSku }: Props) {
  const [viewMode, setViewMode] = useState<'sidebyside' | 'tabs'>('sidebyside')
  const [activeMonth, setActiveMonth] = useState<1 | 2 | 3>(1)

  const MONTH_LABELS: Record<1 | 2 | 3, string> = {
    1: 'Month 1 — Now',
    2: 'Month 2 — Day 30',
    3: 'Month 3 — Day 60',
  }

  return (
    <div className="flex flex-col gap-3">
      {/* View toggle */}
      <div className="flex items-center gap-2 flex-wrap">
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

        <span className="ml-auto text-xs text-gray-600">Drag column edges to resize</span>
      </div>

      {/* Table */}
      {viewMode === 'sidebyside' ? (
        <TableView
          data={rows}
          columns={sideBySideCols}
          onSelectRow={onSelectRow}
          selectedSku={selectedSku}
        />
      ) : (
        <TableView
          data={rows}
          columns={tabCols(activeMonth)}
          onSelectRow={onSelectRow}
          selectedSku={selectedSku}
        />
      )}
    </div>
  )
}
