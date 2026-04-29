import { useState, useRef, useEffect } from 'react'
import { ChevronDown, X, Search } from 'lucide-react'
import { useAppStore } from '../../store/useAppStore'
import type { FilterOptions } from '../../types/procurement'

interface Props { options: FilterOptions }

// Generic dropdown multi-select
function DropdownFilter({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((x) => x !== opt) : [...value, opt])

  const summary =
    value.length === 0 ? 'All' : value.length === 1 ? value[0] : `${value.length} selected`

  return (
    <div className="relative flex flex-col gap-1" ref={ref}>
      <span className="text-xs text-gray-400">{label}</span>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between gap-2 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 min-w-[140px] hover:border-gray-500 focus:outline-none focus:border-blue-500"
      >
        <span className="truncate">{summary}</span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-xl min-w-[160px] py-1">
          {options.map((opt) => (
            <label
              key={opt}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-700 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={value.includes(opt)}
                onChange={() => toggle(opt)}
                className="accent-blue-500"
              />
              {opt}
            </label>
          ))}
          {value.length > 0 && (
            <button
              onClick={() => { onChange([]); setOpen(false) }}
              className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 border-t border-gray-700 mt-1"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Vendor dropdown with search bar
function VendorFilter({
  options,
  value,
  onChange,
}: {
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (open) setTimeout(() => searchRef.current?.focus(), 50)
  }, [open])

  const filtered = options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))
  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((x) => x !== opt) : [...value, opt])

  const summary =
    value.length === 0 ? 'All' : value.length === 1 ? value[0] : `${value.length} selected`

  return (
    <div className="relative flex flex-col gap-1" ref={ref}>
      <span className="text-xs text-gray-400">Vendor</span>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between gap-2 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 min-w-[160px] hover:border-gray-500 focus:outline-none focus:border-blue-500"
      >
        <span className="truncate">{summary}</span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-xl min-w-[200px] py-1">
          {/* Search bar */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700">
            <Search className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <input
              ref={searchRef}
              type="text"
              placeholder="Search vendors..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-sm text-gray-200 placeholder-gray-500 focus:outline-none w-full"
            />
            {search && (
              <button onClick={() => setSearch('')}>
                <X className="w-3 h-3 text-gray-400 hover:text-gray-200" />
              </button>
            )}
          </div>

          {/* Options */}
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-3 py-2 text-xs text-gray-500">No vendors found.</p>
            ) : (
              filtered.map((opt) => (
                <label
                  key={opt}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-700 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={value.includes(opt)}
                    onChange={() => toggle(opt)}
                    className="accent-blue-500"
                  />
                  {opt}
                </label>
              ))
            )}
          </div>

          {value.length > 0 && (
            <button
              onClick={() => { onChange([]); setOpen(false); setSearch('') }}
              className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 border-t border-gray-700 mt-1"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function TableFilters({ options }: Props) {
  const { filters, setFilter } = useAppStore()

  return (
    <div className="flex flex-wrap gap-4 items-end bg-gray-900 border border-gray-800 rounded-lg p-4">
      <DropdownFilter
        label="Urgency"
        options={options.urgency_levels}
        value={filters.urgency}
        onChange={(v) => setFilter({ urgency: v })}
      />
      <DropdownFilter
        label="Category"
        options={options.categories}
        value={filters.category}
        onChange={(v) => setFilter({ category: v })}
      />
      <VendorFilter
        options={options.vendors}
        value={filters.vendor}
        onChange={(v) => setFilter({ vendor: v })}
      />
      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer self-end pb-1">
        <input
          type="checkbox"
          checked={filters.actionOnly}
          onChange={(e) => setFilter({ actionOnly: e.target.checked })}
          className="accent-blue-500"
        />
        Needs order only
      </label>
    </div>
  )
}
