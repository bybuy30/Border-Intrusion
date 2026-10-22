import React from 'react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="panel max-w-lg mx-auto mt-16 p-8 text-center">
      <h1 className="text-lg font-semibold text-slate-100">Page not found</h1>
      <p className="text-sm text-slate-400 mt-2">The requested dashboard page does not exist.</p>
      <Link className="btn-primary inline-flex mt-5" to="/">Return to command center</Link>
    </div>
  )
}
