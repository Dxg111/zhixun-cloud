import { App as AntApp, Button, Card, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  downloadExportTask,
  getToken,
  listExportTasks,
  type AdminExportTask,
} from '../services/api'

export default function ExportsPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<AdminExportTask[]>([])
  const [loading, setLoading] = useState(false)

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '导出请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const loadTasks = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listExportTasks()
      setTasks(data.items)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  const handleDownload = async (task: AdminExportTask) => {
    try {
      const blob = await downloadExportTask(task.id)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = task.file_name
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<AdminExportTask> = [
    {
      title: '文件',
      dataIndex: 'file_name',
      render: (file: string) => <Typography.Text strong>{file}</Typography.Text>,
    },
    { title: '类型', dataIndex: 'export_type', width: 120 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: AdminExportTask['status']) => <StatusTag kind="export" status={status} />,
    },
    {
      title: '行数',
      dataIndex: 'rows',
      width: 90,
      render: (rows: number) => rows || '—',
    },
    { title: '生成时间', dataIndex: 'created_at', width: 170 },
    {
      title: '操作',
      width: 100,
      render: (_, task) => (
        <Button
          type="link"
          size="small"
          disabled={task.status !== 'ready'}
          onClick={() => handleDownload(task)}
        >
          下载
        </Button>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="EXPORTS"
        title="导出中心"
        description="成绩和题目明细异步生成，完成后可下载。目前从考试详情页创建成绩导出。"
        extra={
          <Space>
            <Button type="primary" onClick={() => message.info('请从考试详情页导出成绩')}>
              新建导出
            </Button>
          </Space>
        }
      />

      <Card
        title="导出任务"
        className="panel-card"
        extra={<Typography.Text type="secondary">下载链接有效期 24 小时</Typography.Text>}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={tasks}
          loading={loading}
          pagination={false}
          scroll={{ x: 760 }}
        />
      </Card>
    </>
  )
}
