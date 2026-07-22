import { useEffect, useRef, useState } from 'react'
import { Package } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAppStore } from '../../store/useAppStore'
import { runAnalysis } from '../../api/client'
import UploadZone from '../upload/UploadZone'

function NumberInput({
  label,
  sublabel,
  value,
  onChange,
  min = 0,
  step = 1,
}: {
  label: string
  sublabel?: string
  value: number
  onChange: (v: number) => void
  min?: number
  step?: number
}) {
  const [raw, setRaw] = useState(String(value))
  useEffect(() => { setRaw(String(value)) }, [value])

  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-xs text-gray-300">{label}</label>
      {sublabel && <span className="text-[10px] text-gray-500">{sublabel}</span>}
      <input
        type="number"
        min={min}
        step={step}
        value={raw}
        onChange={(e) => {
          setRaw(e.target.value)
          const v = parseFloat(e.target.value)
          if (!isNaN(v) && v >= min) onChange(v)
        }}
        onBlur={() => {
          const v = parseFloat(raw)
          if (isNaN(v) || v < min) { setRaw(String(min)); onChange(min) }
        }}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
      />
    </div>
  )
}

export default function Sidebar() {
  const {
    params, setParams, uploadedFile, setUploadedFile, setAnalyzeResult,
    analyzeResult, qohOverrides, flfOverrides, clearQohOverrides, clearFlfOverrides,
  } = useAppStore()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const mutation = useMutation({
    mutationFn: ({ file, p, qoh, flf }: {
      file: File; p: typeof params; qoh: Record<string, number>; flf: Record<string, number>
    }) => runAnalysis(file, p, qoh, flf),
    onSuccess: (data) => {
      setAnalyzeResult(data)
      if (data.warnings.length > 0) data.warnings.forEach((w) => toast.warning(w))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const triggerAnalysis = (
    file: File, p: typeof params,
    qoh: Record<string, number>, flf: Record<string, number>,
  ) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => mutation.mutate({ file, p, qoh, flf }), 400)
  }

  const handleFile = (f: File) => {
    setUploadedFile(f)
    clearQohOverrides()
    clearFlfOverrides()
    triggerAnalysis(f, params, {}, {})
  }

  useEffect(() => {
    if (!uploadedFile) return
    triggerAnalysis(uploadedFile, params, qohOverrides, flfOverrides)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, qohOverrides, flfOverrides])

  const total = analyzeResult?.kpis.total_skus ?? 0
  const unmatched = analyzeResult?.kpis.unmatched_count ?? 0

  return (
    <aside className="w-64 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col gap-6 p-5 min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 pb-2 border-b border-gray-800">
        <Package className="w-6 h-6 text-blue-400" />
        <span className="font-semibold text-white text-sm leading-tight">Replenishment<br />Indent</span>
      </div>

      {/* Upload */}
      <section>
        <label className="text-xs text-gray-400 uppercase tracking-widest mb-2 block">Indent Sheet</label>
        <UploadZone onFile={handleFile} fileName={uploadedFile?.name} />
        {mutation.isPending && (
          <p className="text-xs text-blue-400 mt-2 animate-pulse">Analyzing…</p>
        )}
        {analyzeResult && !mutation.isPending && (
          <p className="text-[11px] text-gray-500 mt-2">
            Matched {total - unmatched} of {total} SKUs to Zoho
            {unmatched > 0 && <span className="text-amber-400"> · {unmatched} unmapped</span>}
          </p>
        )}
      </section>

      {/* Machine / consumption inputs */}
      <section className="flex flex-col gap-3">
        <label className="text-xs text-gray-400 uppercase tracking-widest block">Fleet & Consumption</label>
        <NumberInput
          label="Machine Count"
          sublabel="Total machines in the field"
          value={params.machineCount}
          onChange={(v) => setParams({ machineCount: v })}
        />
        <NumberInput
          label="Monthly Usage (hrs)"
          sublabel="Avg. machine running hours / month"
          value={params.monthlyUsageHrs}
          onChange={(v) => setParams({ monthlyUsageHrs: v })}
        />
        <NumberInput
          label="ARC (weeks)"
          sublabel="Auto-replenishment cycle"
          value={params.arcWeeks}
          min={1}
          onChange={(v) => setParams({ arcWeeks: v })}
        />
      </section>

      {/* Sales history range */}
      <section className="flex flex-col gap-3">
        <label className="text-xs text-gray-400 uppercase tracking-widest block">Sales History (Zoho)</label>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">From</label>
          <input
            type="date"
            value={params.salesFrom}
            onChange={(e) => setParams({ salesFrom: e.target.value })}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">To</label>
          <input
            type="date"
            value={params.salesTo}
            onChange={(e) => setParams({ salesTo: e.target.value })}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        <span className="text-[10px] text-gray-500">Weekly sales run-rate is derived from this range.</span>
      </section>

      <div className="mt-auto text-xs text-gray-600">
        {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
      </div>
    </aside>
  )
}
