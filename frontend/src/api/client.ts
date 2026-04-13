import type { AnalysisParams, AnalyzeResponse, FilterState } from '../types/procurement'

function buildForm(file: File, params: AnalysisParams): FormData {
  const form = new FormData()
  form.append('file', file)
  form.append('num_machines', String(params.numMachines))
  form.append('horizon_days', String(params.horizonDays))
  form.append('safety_buffer_pct', String(params.safetyBufferPct))
  form.append('vendor_strategy', params.vendorStrategy)
  return form
}

export async function runAnalysis(file: File, params: AnalysisParams): Promise<AnalyzeResponse> {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    body: buildForm(file, params),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Server error ${res.status}`)
  }
  return res.json()
}

export async function downloadExport(
  file: File,
  params: AnalysisParams,
  filters: FilterState,
  mode: 'full' | 'filtered',
): Promise<void> {
  const form = buildForm(file, params)
  if (mode === 'filtered') {
    form.append('filter_urgency', JSON.stringify(filters.urgency))
    form.append('filter_category', JSON.stringify(filters.category))
    form.append('filter_vendor', JSON.stringify(filters.vendor))
    form.append('action_only', String(filters.actionOnly))
  }

  const res = await fetch('/api/export', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  a.download = `procurement_plan_${today}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}
