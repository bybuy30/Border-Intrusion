import React from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import EmptyState from '../common/EmptyState'
import { BarChart2 } from 'lucide-react'

const COLOURS = { animal: '#68a356', person: '#60a5fa', firearm: '#f87171' }

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="panel px-3 py-2 text-xs shadow-card">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {p.value}
        </p>
      ))}
    </div>
  )
}

export default function ActivityChart({ data = [], height = 220 }) {
  if (!data.length) {
    return <EmptyState icon={BarChart2} title="No detection data" message="Run detection to see activity over time." />
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <defs>
          {Object.entries(COLOURS).map(([key, colour]) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={colour} stopOpacity={0.3} />
              <stop offset="95%" stopColor={colour} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#232e20" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 10, color: '#94a3b8' }} />
        {Object.entries(COLOURS).map(([key, colour]) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={colour}
            strokeWidth={1.5}
            fill={`url(#grad-${key})`}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
