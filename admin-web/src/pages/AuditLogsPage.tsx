import { App as AntApp, Card, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { getToken, listAuditLogs, type AuditLogItem } from '../services/api'

const ACTION_LABELS: Record<string, string> = {
  'question.review': '审核题目',
  'question.bulk_review': '批量审核题目',
  'question.update': '编辑题目',
  'question.delete': '删除题目',
  'exam.create': '创建考试',
  'exam.publish': '发布考试',
  'exam.close': '关闭考试',
  'exam.assign': '指派考试',
  'exam.export': '导出成绩',
  'exam.set_cards': '关联知识卡',
  'card.generate': '生成知识卡',
  'card.update': '编辑知识卡',
  'card.status': '发布/下线知识卡',
  'document.upload': '上传文档',
  'document.delete': '删除文档',
  'org.create': '创建部门',
  'org.update': '编辑部门',
  'org.delete': '删除部门',
  'employee.create': '新增员工',
  'employee.import': '导入员工',
  'employee.status': '停用/启用员工',
  'admin.create': '新增管理员',
  'admin.reset_password': '重置密码',
  'admin.status': '停用/启用管理员',
  'join.approve': '通过加入申请',
  'join.reject': '驳回加入申请',
}

const ACTION_OPTIONS = Object.entries(ACTION_LABELS).map(([value, label]) => ({
  value,
  label,
}))

export default function AuditLogsPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listAuditLogs({ action, page, page_size: 20 })
      setItems(data.items)
      setTotal(data.total)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '审计日志加载失败')
      if (!getToken()) navigate('/login', { replace: true })
    } finally {
      setLoading(false)
    }
  }, [action, page, message, navigate])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
    },
    {
      title: '操作人',
      dataIndex: 'operator_name',
      width: 130,
    },
    {
      title: '动作',
      dataIndex: 'action',
      width: 170,
      render: (value: string) => (
        <Tag color="blue">{ACTION_LABELS[value] || value}</Tag>
      ),
    },
    {
      title: '对象',
      dataIndex: 'target_type',
      width: 130,
      render: (value: string, record) =>
        value ? `${value}${record.target_id ? ` #${record.target_id}` : ''}` : '—',
    },
    {
      title: '详情',
      dataIndex: 'detail',
      render: (value: string) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {value || '—'}
        </Typography.Text>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="系统"
        title="审计日志"
        description="记录发布、审核、指派、导出、删除等关键操作，只追加不修改。"
        extra={
          <Space>
            <Select
              allowClear
              placeholder="按动作筛选"
              style={{ width: 200 }}
              options={ACTION_OPTIONS}
              value={action || undefined}
              onChange={(value) => {
                setPage(1)
                setAction(value || '')
              }}
            />
          </Space>
        }
      />

      <Card className="panel-card">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{
            current: page,
            pageSize: 20,
            total,
            showSizeChanger: false,
            onChange: setPage,
          }}
          scroll={{ x: 900 }}
        />
      </Card>
    </>
  )
}
