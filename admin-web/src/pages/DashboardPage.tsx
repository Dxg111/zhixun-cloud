import {
  ArrowRightOutlined,
  BookOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { Button, Card, Col, List, Progress, Row, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import MetricCard from '../components/MetricCard'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import { getDashboard, getToken, type AdminExam, type DashboardData, type DashboardTrendPoint } from '../services/api'

const EMPTY_DASHBOARD: DashboardData = {
  pending_questions: 0,
  pending_cards: 0,
  pending_join_requests: 0,
  active_exams: 0,
  completion_rate: 0,
  recent_exams: [],
  trend: [],
  weak_points: [],
}

const examColumns: ColumnsType<AdminExam> = [
  {
    title: '考试',
    dataIndex: 'title',
    render: (_, exam) => (
      <div>
        <Typography.Text strong>{exam.title}</Typography.Text>
        <div style={{ fontSize: 12, opacity: 0.65 }}>
          {exam.bank_name} · {exam.question_count} 题
        </div>
      </div>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    width: 100,
    render: (status: AdminExam['status']) => <StatusTag kind="exam" status={status} />,
  },
  {
    title: '完成',
    width: 90,
    render: (_, exam) => `${exam.completed} / ${exam.assigned}`,
  },
  {
    title: '通过率',
    width: 90,
    render: (_, exam) => (exam.completed ? `${exam.pass_rate}%` : '—'),
  },
]

function progressColor(value: number) {
  if (value < 60) return '#a33a3a'
  if (value < 75) return '#a96617'
  return '#0d6a4d'
}

const TREND_LEFT = 60
const TREND_RIGHT = 600
const TREND_TOP = 40
const TREND_BOTTOM = 220

function trendX(index: number, count: number) {
  if (count <= 1) return (TREND_LEFT + TREND_RIGHT) / 2
  return TREND_LEFT + (index * (TREND_RIGHT - TREND_LEFT)) / (count - 1)
}

function trendY(value: number) {
  const clamped = Math.max(0, Math.min(100, value))
  return TREND_BOTTOM - (clamped / 100) * (TREND_BOTTOM - TREND_TOP)
}

function trendCoords(
  points: DashboardTrendPoint[],
  key: 'completion_rate' | 'pass_rate',
) {
  return points.map((point, index) => [
    trendX(index, points.length),
    trendY(point[key]),
  ] as const)
}

function trendPolyline(
  points: DashboardTrendPoint[],
  key: 'completion_rate' | 'pass_rate',
) {
  return trendCoords(points, key)
    .map(([x, y]) => `${x},${y}`)
    .join(' ')
}

function trendArea(points: DashboardTrendPoint[], key: 'completion_rate' | 'pass_rate') {
  const coords = trendCoords(points, key)
  if (coords.length === 0) return ''
  const [first, ...rest] = coords
  const last = coords[coords.length - 1]
  const line = rest.map(([x, y]) => `L${x} ${y}`).join(' ')
  return `M${first[0]} ${first[1]} ${line} L${last[0]} ${TREND_BOTTOM} L${first[0]} ${TREND_BOTTOM} Z`
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<DashboardData>(EMPTY_DASHBOARD)

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getDashboard()
      setDashboard(data)
    } catch (error) {
      if (!getToken()) navigate('/login', { replace: true })
      // 首次加载失败时保留空态，不阻塞其他页面导航。
      console.warn('dashboard load failed', error)
    }
  }, [navigate])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  const todos = [
    {
      icon: <UnorderedListOutlined />,
      title: `${dashboard.pending_questions} 道题等待审核`,
      meta: '来自题库的待审核草稿',
      path: '/questions',
    },
    {
      icon: <BookOutlined />,
      title: `${dashboard.pending_cards} 张知识卡待发布`,
      meta: '生成后需要审核发布',
      path: '/cards',
    },
    {
      icon: <FileDoneOutlined />,
      title: `${dashboard.active_exams} 场考试进行中`,
      meta: '查看完成率和通过率',
      path: '/exams',
    },
    {
      icon: <DownloadOutlined />,
      title: '查看最近导出任务',
      meta: '成绩导出结果与下载',
      path: '/exports',
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="DASHBOARD"
        title="工作台"
        description={`当前有 ${dashboard.pending_questions} 道题待审核，${dashboard.pending_cards} 张知识卡待发布，${dashboard.active_exams} 场考试进行中。`}
        extra={
          <Space wrap>
            <Button onClick={() => navigate('/exports')}>导出周报</Button>
            <Button type="primary" onClick={() => navigate('/exams')}>
              新建考试
            </Button>
          </Space>
        }
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} xl={6}>
          <MetricCard label="待审核题目" value={dashboard.pending_questions} tone="amber" meta="来自题库草稿" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <MetricCard label="待发布知识卡" value={dashboard.pending_cards} tone="amber" meta="等待审核发布" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <MetricCard label="进行中考试" value={dashboard.active_exams} tone="blue" meta="已发布未关闭" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <MetricCard label="整体完成率" value={`${dashboard.completion_rate}%`} tone="green" meta="已提交 / 已指派" />
        </Col>
      </Row>

      <Row gutter={[14, 14]} style={{ marginTop: 14 }}>
        <Col xs={24} xl={16}>
          <Card
            title="近 6 场考试趋势"
            extra={<Tag color="success">真实数据</Tag>}
            className="panel-card"
          >
            <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
              完成率与通过率，按最近 {dashboard.trend.length} 场已发布考试统计
            </Typography.Paragraph>
            {dashboard.trend.length ? (
              <>
                <svg className="trend-chart" viewBox="0 0 640 240" role="img" aria-label="考试趋势图">
                  {[100, 75, 50, 25, 0].map((value) => (
                    <line
                      key={`grid-${value}`}
                      x1="52"
                      y1={trendY(value)}
                      x2="604"
                      y2={trendY(value)}
                      stroke="var(--admin-line)"
                      strokeWidth="1"
                    />
                  ))}
                  {[100, 75, 50, 25, 0].map((value) => (
                    <text key={`y-${value}`} x="8" y={trendY(value) + 4} className="chart-label">
                      {value}
                    </text>
                  ))}
                  <path
                    d={trendArea(dashboard.trend, 'completion_rate')}
                    fill="var(--admin-accent-soft)"
                  />
                  <polyline
                    points={trendPolyline(dashboard.trend, 'completion_rate')}
                    fill="none"
                    stroke="var(--admin-accent)"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <polyline
                    points={trendPolyline(dashboard.trend, 'pass_rate')}
                    fill="none"
                    stroke="var(--admin-amber)"
                    strokeWidth="2"
                    strokeDasharray="5 5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {dashboard.trend.map((point, index) => (
                    <g key={point.exam_id}>
                      <circle
                        cx={trendX(index, dashboard.trend.length)}
                        cy={trendY(point.completion_rate)}
                        r="3.2"
                        fill="var(--admin-accent)"
                      >
                        <title>
                          {`${point.title}：完成率 ${point.completion_rate}%（${point.completed}/${point.assigned} 人）`}
                        </title>
                      </circle>
                      <circle
                        cx={trendX(index, dashboard.trend.length)}
                        cy={trendY(point.pass_rate)}
                        r="2.6"
                        fill="var(--admin-amber)"
                      >
                        <title>{`${point.title}：通过率 ${point.pass_rate}%`}</title>
                      </circle>
                    </g>
                  ))}
                  {dashboard.trend.map((point, index) => (
                    <text
                      key={`x-${point.exam_id}`}
                      x={trendX(index, dashboard.trend.length)}
                      y="238"
                      textAnchor="middle"
                      className="chart-label"
                    >
                      {point.label}
                    </text>
                  ))}
                </svg>
                <Space size={18} style={{ marginTop: 8 }}>
                  <Space size={6}>
                    <span className="legend-dot" style={{ background: 'var(--admin-accent)' }} />
                    完成率
                  </Space>
                  <Space size={6}>
                    <span className="legend-dot" style={{ background: 'var(--admin-amber)' }} />
                    通过率
                  </Space>
                </Space>
              </>
            ) : (
              <div className="trend-empty">
                <Typography.Text type="secondary">
                  暂无已发布考试数据，发布考试并产生提交后会显示趋势。
                </Typography.Text>
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card title="最该补的知识点" className="panel-card">
            <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
              按最近考试正确率排序
            </Typography.Paragraph>
            {dashboard.weak_points.length ? (
              <Space direction="vertical" size={14} style={{ width: '100%' }}>
                {dashboard.weak_points.map((item, index) => {
                  const value = item.value ?? 0
                  return (
                    <div key={`${item.name}-${index}`}>
                      <div className="weak-row-head">
                        <span>{item.name || '知识点'}</span>
                        <span>{value}%</span>
                      </div>
                      <Progress percent={value} showInfo={false} strokeColor={progressColor(value)} size="small" />
                    </div>
                  )
                })}
              </Space>
            ) : (
              <Typography.Paragraph type="secondary">
                暂无逐题答题数据，完成考试后生成薄弱知识点。
              </Typography.Paragraph>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[14, 14]} style={{ marginTop: 14 }}>
        <Col xs={24} xl={10}>
          <Card title="今日待办" className="panel-card">
            <List
              dataSource={todos}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Button key={item.path} type="link" onClick={() => navigate(item.path)}>
                      去处理 <ArrowRightOutlined />
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<span className="todo-icon">{item.icon}</span>}
                    title={item.title}
                    description={item.meta}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card
            title="最近考试"
            extra={<Button type="link" onClick={() => navigate('/exams')}>全部</Button>}
            className="panel-card"
          >
            <Table
              rowKey="id"
              size="small"
              columns={examColumns}
              dataSource={dashboard.recent_exams}
              pagination={false}
              onRow={() => ({ onClick: () => navigate('/exams') })}
              rowClassName={() => 'clickable-row'}
            />
          </Card>
        </Col>
      </Row>
    </>
  )
}
