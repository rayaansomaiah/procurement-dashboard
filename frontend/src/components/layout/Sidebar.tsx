import { useEffect, useRef } from 'react'
import { Package } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAppStore } from '../../store/useAppStore'
import { runAnalysis } from '../../api/client'
import UploadZone from '../upload/UploadZone'

export default function Sidebar() {
  const { params, setParams, uploadedFile, setUploadedFile, setAnalyzeResult } = useAppStore()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const mutation = useMutation({
    mutationFn: ({ file, p }: { file: File; p: typeof params }) => runAnalysis(file, p),
    onSuccess: (data) => {
      setAnalyzeResult(data)
      if (data.warnings.length > 0) {
        data.warnings.forEach((w) => toast.warning(w))
      }
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

      {/* Controls */}
      <section className="flex flex-col gap-4">
        <label className="text-xs text-gray-400 uppercase tracking-widest mb-0 block">Configuration</label>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">Machines Onboarded</label>
          <input
            type="number"
            min={1}
            value={params.numMachines}
            onChange={(e) => {
              const v = parseInt(e.target.value)
              if (!isNaN(v) && v >= 1) setParams({ numMachines: v })
            }}
            onBlur={(e) => {
              const v = parseInt(e.target.value)
              if (isNaN(v) || v < 1) setParams({ numMachines: 1 })
            }}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-300">Planning Horizon</label>
          <select
            value={params.horizonDays}
            onChange={(e) => setParams({ horizonDays: Number(e.target.value) as 30 | 60 | 90 })}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>

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

      {/* Date */}
      <div className="mt-auto text-xs text-gray-600">
        {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
      </div>
    </aside>
  )
}
