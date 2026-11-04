import {
  BookOutlined,
  FileDoneOutlined,
  IdcardOutlined,
  SearchOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import {
  App as AntApp,
  Card,
  Empty,
  Input,
  List,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import {
  getToken,
  globalSearch,
  type GlobalSearchItem,
  type GlobalSearchResult,
} from '../services/api'

const TYPE_META: Record<
  GlobalSearchItem['type'],
  { label: string; icon: ReactNode; color: string }
> = {
  employee: { label: '员工', icon: <TeamOutlined />, color: 'blue' },
  question: { label: '题目', icon: <UnorderedListOutlined />, color: 'green' },
  exam: { label: '考试', icon: <FileDoneOutlined />, color: 'purple' },
  card: { label: '知识卡', icon: <IdcardOutlined />, color: 'gold' },
  document: { label: '知识库文档', icon: <BookOutlined />, color: 'default' },
}

const STATUS_TEXT: Record<string, string> = {
  active: '启用',
  disabled: '停用',
  draft: '草稿',
  approved: '已通过',
  rejected: '已驳回',
  published: '已发布',
  closed: '已关闭',
  offline: '已下线',
  processing: '解析中',
  ready: '已就绪',
  failed: '解析失败',
}

function itemStatusText(item: GlobalSearchItem) {
  if (item.type === 'employee') {
    return item.status === 'active' ? '在职' : '停用'
  }
  return STATUS_TEXT[item.status] || item.status
}

function statusColor(status: string) {
  if (['active', 'approved', 'published', 'ready'].includes(status)) return 'green'
  if (['rejected', 'failed'].includes(status)) return 'red'
  if (['draft', 'processing'].includes(status)) return 'gold'
  return 'default'
}

export default function SearchPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const keyword = searchParams.get('q')?.trim() || ''
  const [result, setResult] = useState<GlobalSearchResult | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!keyword) {
      setResult(null)
      return
    }
    setLoading(true)
    try {
      const data = await globalSearch(keyword, 5)
      setResult(data)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '全局搜索失败')
      if (!getToken()) navigate('/login', { replace: true })
    } finally {
      setLoading(false)
    }
  }, [keyword, message, navigate])

  useEffect(() => {
    void load()
  }, [load])

  const groups = useMemo(() => {
    const order: GlobalSearchItem['type'][] = [
      'employee',
      'question',
      'exam',
      'card',
      'document',
    ]
    return order
      .map((type) => ({
        type,
        items: (result?.items || []).filter((item) => item.type === type),
      }))
      .filter((group) => group.items.length > 0)
  }, [result])

  const handleSearch = (value: string) => {
    const next = value.trim()
    if (next) navigate(`/search?q=${encodeURIComponent(next)}`)
  }

  return (
    <>
      <PageHeader
        eyebrow="搜索"
        title="全局搜索"
        description="跨员工、题目、考试、知识卡和知识库文档查找内容。搜索员工支持姓名或工号。"
        extra={
          <Input.Search
            key={keyword}
            allowClear
            defaultValue={keyword}
            prefix={<SearchOutlined />}
            placeholder="输入关键词"
            style={{ width: 320 }}
            onSearch={handleSearch}
          />
        }
      />

      {loading ? (
        <Card className="panel-card">
          <div style={{ padding: 60, textAlign: 'center' }}>
            <Spin />
          </div>
        </Card>
      ) : !keyword ? (
        <Card className="panel-card">
          <Empty description="输入关键词开始搜索，例如员工姓名、工号、考试名称或题目内容" />
        </Card>
      ) : groups.length === 0 ? (
        <Card className="panel-card">
          <Empty description={`没有找到与「${keyword}」相关的内容`} />
        </Card>
      ) : (
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          <Typography.Text type="secondary">
            在「{keyword}」下找到 {result?.total ?? 0} 条结果
          </Typography.Text>
          {groups.map((group) => {
            const meta = TYPE_META[group.type]
            return (
              <Card
                key={group.type}
                className="panel-card"
                title={
                  <Space size={8}>
                    {meta.icon}
                    {meta.label}
                    <Tag>{group.items.length}</Tag>
                  </Space>
                }
              >
                <List
                  dataSource={group.items}
                  renderItem={(item) => (
                    <List.Item
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(item.url)}
                      extra={
                        <Space>
                          <Tag color={statusColor(item.status)}>
                            {itemStatusText(item)}
                          </Tag>
                          <Typography.Text type="secondary">查看</Typography.Text>
                        </Space>
                      }
                    >
                      <List.Item.Meta
                        avatar={<Tag color={meta.color}>{meta.label}</Tag>}
                        title={<Typography.Text strong>{item.title}</Typography.Text>}
                        description={item.subtitle}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            )
          })}
        </Space>
      )}
    </>
  )
}
