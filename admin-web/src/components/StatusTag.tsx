import { Tag } from 'antd'

type StatusKind = 'question' | 'exam' | 'card' | 'doc' | 'employee' | 'invite' | 'export' | 'admin'

interface StatusTagProps {
  kind: StatusKind
  status: string
}

const META: Record<StatusKind, Record<string, { label: string; color: string }>> = {
  question: {
    draft: { label: '待审核', color: 'warning' },
    approved: { label: '已通过', color: 'success' },
    rejected: { label: '已驳回', color: 'error' },
  },
  exam: {
    draft: { label: '草稿', color: 'warning' },
    published: { label: '进行中', color: 'success' },
    closed: { label: '已结束', color: 'default' },
  },
  card: {
    draft: { label: '待审核', color: 'warning' },
    published: { label: '已发布', color: 'success' },
    offline: { label: '已下线', color: 'default' },
  },
  doc: {
    processing: { label: '处理中', color: 'processing' },
    ready: { label: '已就绪', color: 'success' },
    failed: { label: '失败', color: 'error' },
  },
  employee: {
    active: { label: '在职', color: 'success' },
    disabled: { label: '停用', color: 'default' },
  },
  invite: {
    bound: { label: '已绑定', color: 'success' },
    unbound: { label: '未绑定', color: 'warning' },
  },
  export: {
    processing: { label: '生成中', color: 'processing' },
    ready: { label: '已完成', color: 'success' },
    failed: { label: '失败', color: 'error' },
  },
  admin: {
    active: { label: '启用', color: 'success' },
    disabled: { label: '停用', color: 'default' },
  },
}

export default function StatusTag({ kind, status }: StatusTagProps) {
  const meta = META[kind][status] ?? { label: status, color: 'default' }
  return <Tag color={meta.color}>{meta.label}</Tag>
}
