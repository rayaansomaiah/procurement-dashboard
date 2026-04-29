import { useEffect, useRef, useState } from 'react'
import { Package } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAppStore } from '../../store/useAppStore'
import { runAnalysis } from '../../api/client'
import UploadZone from '../upload/UploadZone'

function MachineInput({
  label,
  sublabel,
  value,
  onChange,
}: {
  label: string
  sublabel: string
  value: number
  onChange: (v: number) => void
}) {
  const [raw, setRaw] = useState(value === 0 ? '' : String(value))

  useEffect(() => {
    setRaw(value === 0 ? '' : String(value))
  }, [value])

  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-xs text-gray-300">{label}</label>
      <span className="text-[10px] text-gray-500">{sublabel}</span>
      <input
        type="number"
        min={0}
        placeholder="0"
        value={raw}
        onChange={(e) => {
          setRaw(e.target.value)
          const v = parseInt(e.target.value)
          if (!isNaN(v) && v >= 0) onChange(v)
        }}
        onBlur={() => {
          const v = parseInt(raw)
          if (isNaN(v) || v < 0) {
            setRaw('')
            onChange(0)
          }
        }}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
      />
    </div>
  )
}

export default function Sidebar() {
  const { params, setParams, uploadedFile, setUploadedFile, setAnalyzeResult } = useAppStore()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const mutation = useMutation({
    mutationFn: ({ file, p }: { file: File; p: typeof params }) => runAnalysis(file, p),
    onSuccess: (data) => {
      setAnalyzeResult(data)
      if (data.warnings.length > 0) data.warnings.forEach((w) => toast.warning(w))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const triggerAnalysis = (file: File, p: typeof params) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => mutation.mutate({ file, p }), 400)
  }

  const handleFile = (f: File) => {
    setUploadedFile(f)
    triggerAnalysis(f, params)
  }

  useEffect(() => {
    if (!uploadedFile) return
    triggerAnalysis(uploadedFile, params)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  return (
    <aside className="w-64 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col gap-6 p-5 min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 pb-2 border-b border-gray-800">
        <Package className="w-6 h-6 text-blue-400" />
        <span className="font-semibold text-white text-sm leading-tight">Procurement<br />Planner</span>
      </div>

      {/* Upload */}
      <section>
        <label className="text-xs text-gray-400 uppercase tracking-widest mb-2 block">Excel File</label>
        <UploadZone onFile={handleFile} fileName={uploadedFile?.name} />
        {mutation.isPending && (
          <p className="text-xs text-blue-400 mt-2 animate-pulse">Analyzing…</p>
        )}
      </section>

      {/* Machine Onboarding */}
      <section className="flex flex-col gap-3">
        <label className="text-xs text-gray-400 uppercase tracking-widest block">Machines Onboarded</label>

        <MachineInput
          label="Month 1 (Now)"
          sublabel="Onboarding today"
          value={params.machinesM1}
          onChange={(v) => setParams({ machinesM1: v })}
        />
        <MachineInput
          label="Month 2 (Day 30)"
          sublabel="Onboarding at day 30"
          value={params.machinesM2}
          onChange={(v) => setParams({ machinesM2: v })}
        />
        <MachineInput
          label="Month 3 (Day 60)"
          sublabel="Onboarding at day 60"
          value={params.machinesM3}
          onChange={(v) => setParams({ machinesM3: v })}
        />
      </section>

      {/* Other Settings */}
      <section className="flex flex-col gap-4">
        <label className="text-xs text-gray-400 uppercase tracking-widest block">Settings</label>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">
            Safety Buffer: <span className="text-white font-medium">{params.safetyBufferPct}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={params.safetyBufferPct}
            onChange={(e) => setParams({ safetyBufferPct: Number(e.target.value) })}
            className="accent-blue-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">Vendor Strategy</label>
          {(['Prefer L1', 'Fastest Delivery', 'Cheapest Price'] as const).map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="radio"
                name="vendorStrategy"
                value={s}
                checked={params.vendorStrategy === s}
                onChange={() => setParams({ vendorStrategy: s })}
                className="accent-blue-500"
              />
              {s}
            </label>
          ))}
        </div>
      </section>

      <div className="mt-auto text-xs text-gray-600">
        {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
      </div>
    </aside>
  )
}
