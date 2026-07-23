import type { AnalysisParams, AnalyzeResponse, FilterState } from '../types/procurement'

function buildForm(
  file: File,
  params: AnalysisParams,
  qohOverrides: Record<string, number> = {},
  flfOverrides: Record<string, number> = {},
): FormData {
  const form = new FormData()
  form.append('file', file)
  form.append('machine_count', String(params.machineCount))
  form.append('monthly_usage_hrs', String(params.monthlyUsageHrs))
  form.append('arc_weeks', String(params.arcWeeks))
  form.append('sales_from', params.salesFrom)
  form.append('sales_to', params.salesTo)
  form.append('qoh_overrides', JSON.stringify(qohOverrides))
  form.append('flf_overrides', JSON.stringify(flfOverrides))
  return form
}

async function postWithTimeout(url: string, body: FormData, timeoutMs = 180000): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { method: 'POST', body, signal: controller.signal })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error('Request timed out after 3 min — the free-tier server may be cold-starting; try again.')
    }
    throw new Error('Could not reach the backend server.')
  } finally {
    clearTimeout(timer)
  }
}

export async function runAnalysis(
  file: File,
  params: AnalysisParams,
  qohOverrides: Record<string, number> = {},
  flfOverrides: Record<string, number> = {},
): Promise<AnalyzeResponse> {
  const res = await postWithTimeout('/api/analyze', buildForm(file, params, qohOverrides, flfOverrides))
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
  qohOverrides: Record<string, number> = {},
  flfOverrides: Record<string, number> = {},
): Promise<void> {
  const form = buildForm(file, params, qohOverrides, flfOverrides)
  if (mode === 'filtered') {
    form.append('filter_category', JSON.stringify(filters.category))
    form.append('filter_sub_category', JSON.stringify(filters.subCategory))
    form.append('filter_brand', JSON.stringify(filters.brand))
    form.append('needs_indent_only', String(filters.needsIndentOnly))
  }

  const res = await fetch('/api/export', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  a.download = `replenishment_indent_${today}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}
