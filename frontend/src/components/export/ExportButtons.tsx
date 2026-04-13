import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'
import { useAppStore } from '../../store/useAppStore'
import { downloadExport } from '../../api/client'

export default function ExportButtons() {
  const { uploadedFile, params, filters } = useAppStore()
  const [loading, setLoading] = useState<'full' | 'filtered' | null>(null)

  const handleExport = async (mode: 'full' | 'filtered') => {
    if (!uploadedFile) return toast.error('No file uploaded')
    setLoading(mode)
    try {
      await downloadExport(uploadedFile, params, filters, mode)
      toast.success('Excel downloaded')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="flex flex-col gap-4 max-w-md">
      <p className="text-sm text-gray-400">Download the procurement plan as a color-coded Excel file.</p>

      <button
        onClick={() => handleExport('full')}
        disabled={!uploadedFile || loading === 'full'}
        className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition-colors"
      >
        <Download className="w-4 h-4" />
        {loading === 'full' ? 'Downloading…' : 'Download Full Plan'}
      </button>

      <button
        onClick={() => handleExport('filtered')}
        disabled={!uploadedFile || loading === 'filtered'}
        className="flex items-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition-colors"
      >
        <Download className="w-4 h-4" />
        {loading === 'filtered' ? 'Downloading…' : 'Download Filtered View'}
      </button>
    </div>
  )
}
