import { Typography } from 'antd'
import type { ReactNode } from 'react'

interface PageHeaderProps {
  eyebrow?: string
  title: string
  description?: string
  extra?: ReactNode
}

export default function PageHeader({ eyebrow, title, description, extra }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div className="page-header-main">
        {eyebrow ? <div className="page-eyebrow">{eyebrow}</div> : null}
        <Typography.Title level={3} className="page-title">
          {title}
        </Typography.Title>
        {description ? (
          <Typography.Text type="secondary" className="page-description">
            {description}
          </Typography.Text>
        ) : null}
      </div>
      {extra ? <div className="page-header-extra">{extra}</div> : null}
    </div>
  )
}
