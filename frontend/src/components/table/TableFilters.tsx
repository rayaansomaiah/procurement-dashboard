import { useAppStore } from '../../store/useAppStore'
import type { FilterOptions } from '../../types/procurement'

interface Props { options: FilterOptions }

function MultiSelect({
  label, options, value, onChange,
}: {
  label: string
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((x) => x !== opt) : [...value, opt])

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-gray-400">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => toggle(opt)}
            className={`px-2 py-0.5 rounded text-xs border transition-colors ${
              value.includes(opt)
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500'
            }`}
          >
            {opt}
          </button>
        ))}
        {value.length > 0 && (
          <button
            onClick={() => onChange([])}
            className="px-2 py-0.5 rounded text-xs border border-gray-700 text-gray-500 hover:text-gray-300"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}

export default function TableFilters({ options }: Props) {
  const { filters, setFilter } = useAppStore()

  return (
    <div className="flex flex-wrap gap-4 items-end bg-gray-900 border border-gray-800 rounded-lg p-4">
      <MultiSelect
        label="Urgency"
        options={options.urgency_levels}
        value={filters.urgency}
        onChange={(v) => setFilter({ urgency: v })}
      />
      <MultiSelect
        label="Category"
        options={options.categories}
        value={filters.category}
        onChange={(v) => setFilter({ category: v })}
      />
      <MultiSelect
        label="Vendor"
        options={options.vendors}
        value={filters.vendor}
        onChange={(v) => setFilter({ vendor: v })}
      />
      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer self-end pb-0.5">
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
