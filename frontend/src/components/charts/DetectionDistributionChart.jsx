import React from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import EmptyState from '../common/EmptyState'
import { PieChart as PieIcon } from 'lucide-react'

const COLOURS = ['#68a356', '#60a5fa', '#f87171']
const LABELS  = { animal: 'Animal', person: 'Person', firearm: 'Firearm' }

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="panel px-3 py-2 text-xs shadow-card">
      <p style={{ color: payload[0].payload.fill }}>{name}: {value}</p>
    </div>
  )
}

export default function DetectionDistributionChart({ data = {} }) {
  const entries = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([key, value], i) => ({ name: LABELS[key] ?? key, value, fill: COLOURS[i % COLOURS.length] }))

  if (!entries.length) {
    return <EmptyState icon={PieIcon} title="No class data" message="Detection events will appear here after running inference." />
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {entries.map((entry, i) => (
            <Cell key={i} fill={entry.fill} stroke="transparent" />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 10, color: '#94a3b8' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
