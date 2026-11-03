import { Card } from 'antd'
import type { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: ReactNode
  meta?: ReactNode
  tone?: 'default' | 'amber' | 'blue' | 'green'
  icon?: ReactNode
}

export default function MetricCard({ label, value, meta, tone = 'default', icon }: MetricCardProps) {
  return (
    <Card className={`metric-card metric-${tone}`} size="small">
      <div className="metric-card-head">
        <div className="metric-label">{label}</div>
        {icon ? <span className="metric-icon">{icon}</span> : null}
      </div>
      <div className="metric-value">{value}</div>
      {meta ? <div className="metric-meta">{meta}</div> : null}
    </Card>
  )
}
