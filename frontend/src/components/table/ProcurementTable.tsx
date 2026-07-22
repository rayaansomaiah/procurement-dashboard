import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnDef,
} from '@tanstack/react-table'
import { useState, useEffect, useMemo } from 'react'
import { ChevronUp, ChevronDown, Pencil, Search, X, Check } from 'lucide-react'
import type { IndentRow } from '../../types/procurement'
import { useAppStore } from '../../store/useAppStore'

// ---------------------------------------------------------------------------
// Inline-editable numeric cell (used for QOH and FLF)
// ---------------------------------------------------------------------------
function EditableNumberCell({
  value,
  overridden,
  onCommit,
  min = 0,
  max,
  step = 1,
  fmt = (v: number) => String(v),
}: {
  value: number
  overridden: boolean
  onCommit: (v: number) => void
  min?: number
  max?: number
  step?: number
  fmt?: (v: number) => string
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value))

  useEffect(() => {
    if (!editing) setDraft(String(value))
  }, [value, editing])

  const commit = () => {
    let v = parseFloat(draft)
    if (isNaN(v)) v = min
    if (v < min) v = min
    if (max !== undefined && v > max) v = max
    onCommit(v)
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={draft}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit()
          if (e.key === 'Escape') { setDraft(String(value)); setEditing(false) }
        }}
        onClick={(e) => e.stopPropagation()}
        className="w-full bg-gray-700 border border-blue-500 rounded px-1.5 py-0.5 text-sm text-white focus:outline-none"
      />
    )
  }

  return (
    <button
      onClick={(e) => { e.stopPropagation(); setEditing(true) }}
      className={`group flex items-center gap-1 w-full rounded px-1 -mx-1 hover:bg-gray-700/60 transition-colors ${
        overridden ? 'text-blue-300' : 'text-gray-200'
      }`}
      title="Click to edit"
    >
      <span className="truncate">{fmt(value)}</span>
      <Pencil className="w-2.5 h-2.5 shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Cell components that read overrides from the store
// ---------------------------------------------------------------------------
function QohCell({ row }: { row: IndentRow }) {
  const { qohOverrides, setQohOverride } = useAppStore()
  const overridden = qohOverrides[row.sku_code] !== undefined
  const value = overridden ? qohOverrides[row.sku_code] : row.qoh
  return (
    <EditableNumberCell
      value={value}
      overridden={overridden}
      onCommit={(v) => setQohOverride(row.sku_code, v)}
      min={0}
    />
  )
}

function FlfCell({ row }: { row: IndentRow }) {
  const { flfOverrides, setFlfOverride } = useAppStore()
  const overridden = flfOverrides[row.sku_code] !== undefined
  const value = overridden ? flfOverrides[row.sku_code] : row.flf
  return (
    <EditableNumberCell
      value={value}
      overridden={overridden}
      onCommit={(v) => setFlfOverride(row.sku_code, v)}
      min={0}
      max={1}
      step={0.1}
      fmt={(v) => v.toFixed(2)}
    />
  )
}

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------
const col = createColumnHelper<IndentRow>()

const money = (v: number) => `₹${(v ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
const num2 = (v: number) => (v ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })

const columns: ColumnDef<IndentRow, any>[] = [
  col.accessor('sku_code',     { header: 'SKU',          size: 110, minSize: 80,  maxSize: 220 }),
  col.accessor('item',         { header: 'Item',         size: 190, minSize: 110, maxSize: 400 }),
  col.accessor('category',     { header: 'Category',     size: 110, minSize: 80,  maxSize: 200 }),
  col.accessor('sub_category', { header: 'Sub Category', size: 120, minSize: 80,  maxSize: 220 }),
  col.accessor('brand',        { header: 'Brand',        size: 90,  minSize: 60,  maxSize: 180 }),
  col.accessor('qoh', {
    header: 'QOH', size: 90, minSize: 65, maxSize: 140,
    cell: (i) => <QohCell row={i.row.original} />,
  }),
  col.accessor('purchase_price', {
    header: 'Purchase Price', size: 115, minSize: 90, maxSize: 160,
    cell: (i) => money(i.getValue()),
  }),
  col.accessor('prev_sales_qty', { header: 'Prev Sales',  size: 90,  minSize: 70, maxSize: 130, cell: (i) => num2(i.getValue()) }),
  col.accessor('sales_per_week', { header: 'Sales / Wk',  size: 90,  minSize: 70, maxSize: 130, cell: (i) => num2(i.getValue()) }),
  col.accessor('arc',            { header: 'ARC',         size: 65,  minSize: 50, maxSize: 100 }),
  col.accessor('sales_proj',     { header: 'Sales Proj',  size: 95,  minSize: 70, maxSize: 140, cell: (i) => num2(i.getValue()) }),
  col.accessor('mdp_cdp',        { header: 'MDP/CDP',     size: 90,  minSize: 65, maxSize: 130, cell: (i) => num2(i.getValue()) }),
  col.accessor('consumption_hrs',  { header: 'Cons. Hrs',  size: 90, minSize: 65, maxSize: 130 }),
  col.accessor('consumption_load', { header: 'Cons. Load', size: 95, minSize: 70, maxSize: 130, cell: (i) => num2(i.getValue()) }),
  col.accessor('wallet_proj',    { header: 'Wallet Proj', size: 100, minSize: 75, maxSize: 150, cell: (i) => num2(i.getValue()) }),
  col.accessor('flf', {
    header: 'FLF', size: 75, minSize: 60, maxSize: 120,
    cell: (i) => <FlfCell row={i.row.original} />,
  }),
  col.accessor('effective_demand', { header: 'Eff. Demand', size: 105, minSize: 80, maxSize: 150 }),
  col.accessor('indent_qty', {
    header: 'Indent', size: 90, minSize: 65, maxSize: 130,
    cell: (i) => (
      <span className={i.getValue() > 0 ? 'font-semibold text-amber-300' : 'text-gray-500'}>
        {i.getValue()}
      </span>
    ),
  }),
  col.accessor('purchase_amount', {
    header: 'Purchase Amt', size: 115, minSize: 90, maxSize: 170,
    cell: (i) => money(i.getValue()),
  }),
  col.accessor('stock_value', {
    header: 'Stock Value', size: 115, minSize: 90, maxSize: 170,
    cell: (i) => money(i.getValue()),
  }),
  col.accessor('matched', {
    header: 'Zoho', size: 65, minSize: 55, maxSize: 90,
    cell: (i) => i.getValue()
      ? <Check className="w-3.5 h-3.5 text-emerald-400" />
      : <span className="text-amber-400" title="No Zoho match">—</span>,
  }),
]

// ---------------------------------------------------------------------------
interface Props {
  rows: IndentRow[]
  onSelectRow: (row: IndentRow) => void
  selectedSku: string | null
}

export default function ProcurementTable({ rows, onSelectRow, selectedSku }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'indent_qty', desc: true }])
  const [search, setSearch] = useState('')

  const filteredRows = useMemo(() => {
    if (!search.trim()) return rows
    const q = search.trim().toLowerCase()
    return rows.filter((r) => {
      const targets = [r.sku_code, r.item, r.category, r.sub_category, r.brand]
      return targets.some((v) => v && v.toLowerCase().includes(q))
    })
  }, [rows, search])

  const table = useReactTable({
    data: filteredRows,
    columns,
    columnResizeMode: 'onChange',
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="flex flex-col gap-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search SKU, item, category, brand…"
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 pl-8 pr-8 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        {search.trim()
          ? <p className="text-xs text-gray-500">{filteredRows.length} of {rows.length} SKUs</p>
          : <span />}
        <span className="text-xs text-gray-600">Click QOH or FLF to edit · drag column edges to resize</span>
      </div>

      {/* Table */}
      <div className="overflow-auto rounded-lg border border-gray-800 max-h-[560px]">
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
                  <div
                    onMouseDown={header.getResizeHandler()}
                    onTouchStart={header.getResizeHandler()}
                    className={`absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none transition-colors ${
                      header.column.getIsResizing() ? 'bg-blue-500' : 'bg-transparent hover:bg-gray-600'
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
                  ${row.original.indent_qty > 0 ? 'bg-amber-950/20' : ''}
                  ${!row.original.matched ? 'opacity-70' : ''}
                  ${selectedSku === row.original.sku_code ? 'ring-1 ring-inset ring-blue-500' : ''}`}
              >
                {row.getVisibleCells().map((cell) => {
                  const raw = cell.getValue()
                  const titleText = raw !== null && raw !== undefined ? String(raw) : ''
                  return (
                    <td
                      key={cell.id}
                      style={{ width: cell.column.getSize() }}
                      className="px-3 py-2 text-gray-200 overflow-hidden"
                      title={titleText}
                    >
                      <div className="truncate">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-gray-500">
                  No SKUs match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
