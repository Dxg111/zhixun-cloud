import { InboxOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Button,
  Card,
  Input,
  Popconfirm,
  Space,
  Table,
  Typography,
  Upload,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  deleteAdminDocument,
  getToken,
  listAdminDocuments,
  uploadAdminDocument,
  type AdminDocument,
} from '../services/api'

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function KnowledgePage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const keywordFromUrl = searchParams.get('keyword') || ''
  const [docs, setDocs] = useState<AdminDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '知识库请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const loadDocs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listAdminDocuments()
      setDocs(data.items)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    if (keywordFromUrl) setKeyword(keywordFromUrl)
  }, [keywordFromUrl])

  useEffect(() => {
    void loadDocs()
  }, [loadDocs])

  const filteredDocs = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return docs
    return docs.filter((doc) => doc.file_name.toLowerCase().includes(normalized))
  }, [docs, keyword])

  const handleDelete = async (doc: AdminDocument) => {
    try {
      await deleteAdminDocument(doc.id)
      message.success('文档已删除')
      await loadDocs()
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<AdminDocument> = [
    {
      title: '文件',
      dataIndex: 'file_name',
      render: (_, doc) => (
        <div>
          <Typography.Text strong>{doc.file_name}</Typography.Text>
          <div style={{ fontSize: 12, opacity: 0.65 }}>{doc.file_type.toUpperCase()}</div>
        </div>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      width: 100,
      render: (size: number) => formatSize(size),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: AdminDocument['status']) => <StatusTag kind="doc" status={status} />,
    },
    {
      title: '知识片段',
      dataIndex: 'chunks',
      width: 100,
      render: (chunks: number) => chunks || '—',
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      width: 170,
    },
    {
      title: '说明',
      dataIndex: 'error_message',
      render: (error: string | null | undefined) =>
        error ? <Typography.Text type="danger">{error}</Typography.Text> : '—',
    },
    {
      title: '操作',
      width: 90,
      render: (_, doc) => (
        <Popconfirm
          title="确定删除该文档？"
          description="删除后需要重新上传才能再次解析。"
          okText="删除"
          cancelText="取消"
          onConfirm={() => handleDelete(doc)}
        >
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="KNOWLEDGE BASE"
        title="知识库"
        description="上传培训资料后，系统会自动解析、分块并统计知识片段。题目和知识卡都从这里生成。"
        extra={
          <Space>
            <Input.Search
              allowClear
              key={keyword}
              defaultValue={keyword}
              placeholder="搜索文档名称"
              style={{ width: 220 }}
              onSearch={(value) => setKeyword(value.trim())}
            />
            <Button
              onClick={() => {
                const failed = docs.find((doc) => doc.status === 'failed')
                message.info(failed?.error_message || '暂无失败文档')
              }}
            >
              查看失败原因
            </Button>
          </Space>
        }
      />

      <Card className="panel-card" style={{ marginBottom: 14 }}>
        <Upload.Dragger
          accept=".pdf,.docx,.md,.txt"
          multiple
          showUploadList={false}
          customRequest={async (options) => {
            try {
              await uploadAdminDocument(options.file as File)
              message.success(`${(options.file as File).name} 已上传并完成解析`)
              options.onSuccess?.({})
              await loadDocs()
            } catch (error) {
              message.error(
                `${(options.file as File).name}：${
                  error instanceof Error ? error.message : '上传失败'
                }`,
              )
              options.onError?.(error as Error)
            }
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">上传 PDF / Word / Markdown / TXT，支持多选</p>
          <p className="ant-upload-hint">
            可一次选择多个文件，单文件 ≤ 20MB；上传后在服务端解析并统计知识片段。
          </p>
        </Upload.Dragger>
      </Card>

      <Card
        title="我的文档"
        className="panel-card"
        extra={<Typography.Text type="secondary">{docs.length} 篇</Typography.Text>}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredDocs}
          loading={loading}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
    </>
  )
}
