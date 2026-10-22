import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

export default function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', danger = false, onConfirm, onCancel }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />

      {/* Panel */}
      <div className="relative panel w-full max-w-sm p-5 shadow-card z-10">
        <div className="flex items-start gap-3 mb-4">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full shrink-0 ${danger ? 'bg-red-950 border border-red-800' : 'bg-amber-950 border border-amber-800'}`}>
            <AlertTriangle className={`w-4 h-4 ${danger ? 'text-red-400' : 'text-amber-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-100">{title}</p>
            {message && <p className="text-xs text-slate-400 mt-1">{message}</p>}
          </div>
          <button onClick={onCancel} className="btn-ghost p-1 shrink-0" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
          <button
            onClick={onConfirm}
            className={danger ? 'btn-danger' : 'btn-primary'}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
