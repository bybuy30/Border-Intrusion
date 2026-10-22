import React from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import EmptyState from '../common/EmptyState'
import { TrendingUp } from 'lucide-react'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="panel px-3 py-2 text-xs shadow-card">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      <p className="text-red-400">High priority: {payload[0]?.value ?? 0}</p>
    </div>
  )
}

export default function AlertTrendChart({ data = [], height = 180 }) {
  const chartData = data.map((d) => ({ date: d.date, high: d.high ?? 0 }))
  const hasData   = chartData.some((d) => d.high > 0)

  if (!hasData) {
    return <EmptyState icon={TrendingUp} title="No alert trends" message="High-priority events will chart here." />
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#232e20" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(248,113,113,0.05)' }} />
        <Bar dataKey="high" fill="#dc2626" radius={[3, 3, 0, 0]} maxBarSize={24} />
      </BarChart>
    </ResponsiveContainer>
  )
}
