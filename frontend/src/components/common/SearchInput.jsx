import React from 'react'
import { Search, X } from 'lucide-react'

export default function SearchInput({ value, onChange, placeholder = 'Search…', className = '' }) {
  return (
    <div className={`relative flex items-center ${className}`}>
      <Search className="absolute left-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="input pl-8 pr-7"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-2 text-slate-500 hover:text-slate-300"
          aria-label="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}
