import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'

interface Props {
  onFile: (f: File) => void
  fileName?: string
}

export default function UploadZone({ onFile, fileName }: Props) {
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const f = e.dataTransfer.files[0]
      if (f) onFile(f)
    },
    [onFile],
  )

  return (
    <label
      className={`flex flex-col items-center justify-center gap-2 w-full rounded-lg border-2 border-dashed cursor-pointer py-6 px-4 transition-colors
        ${dragging ? 'border-blue-400 bg-blue-950/30' : 'border-gray-600 hover:border-gray-400 bg-gray-900/50'}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <Upload className="w-6 h-6 text-gray-400" />
      {fileName ? (
        <span className="text-sm text-green-400 font-medium text-center break-all">{fileName}</span>
      ) : (
        <span className="text-sm text-gray-400 text-center">Drop Excel file here or click to browse</span>
      )}
      <input
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
    </label>
  )
}
