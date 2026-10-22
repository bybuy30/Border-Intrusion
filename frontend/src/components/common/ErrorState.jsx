import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 px-4 text-center">
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-950 border border-red-800">
        <AlertCircle className="w-5 h-5 text-red-400" />
      </div>
      <p className="text-sm text-slate-300 max-w-xs">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary flex items-center gap-1.5">
          <RefreshCw className="w-3 h-3" />
          Retry
        </button>
      )}
    </div>
  )
}
