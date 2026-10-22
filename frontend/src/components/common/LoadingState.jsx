import React from 'react'

export default function LoadingState({ message = 'Loading…', rows = 4 }) {
  return (
    <div className="space-y-2 p-4" role="status" aria-label={message}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-8 bg-surface-700 rounded animate-pulse" style={{ opacity: 1 - i * 0.15 }} />
      ))}
      <p className="text-xs text-slate-500 text-center pt-2">{message}</p>
    </div>
  )
}
