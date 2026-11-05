import {
  Button,
  Col,
  Collapse,
  Drawer,
  List,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import type { Exam } from '../types'
import {
  getExamAnalytics,
  listExamAttempts,
  type ExamAnalytics,
  type ExamAttemptDetail,
  type ExamNotificationStats,
} from '../services/api'
import StatusTag from './StatusTag'

interface ExamDrawerProps {
  open: boolean
  exam: Exam | null
  notifyStats?: ExamNotificationStats | null
  onClose: () => void
  onPublish: (id: string) => void
  onCloseExam: (id: string) => void
  onExport: (id: string) => void
  onAssign: (id: string) => void
  onCards: (id: string) => void
}

const DIST_LABELS = ['0–59', '60–69', '70–79', '80–89', '90–100']

export default function ExamDrawer({
  open,
  exam,
  notifyStats,
  onClose,
  onPublish,
  onCloseExam,
  onExport,
  onAssign,
  onCards,
}: ExamDrawerProps) {
  const [analytics, setAnalytics] = useState<ExamAnalytics | null>(null)
  const [attempts, setAttempts] = useState<ExamAttemptDetail[]>([])
  const [attemptsTotal, setAttemptsTotal] = useState(0)
  const [attemptPage, setAttemptPage] = useState(1)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    if (!open || !exam) return
    let cancelled = false
    setAttemptPage(1)
    setDetailLoading(true)
    Promise.all([
      getExamAnalytics(Number(exam.id)).catch(() => null),
      listExamAttempts(Number(exam.id), 1, 10).catch(() => null),
    ])
      .then(([analyticsData, attemptData]) => {
        if (cancelled) return
        setAnalytics(analyticsData)
        setAttempts(attemptData?.items ?? [])
        setAttemptsTotal(attemptData?.total ?? 0)
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, exam?.id])

  const loadAttemptPage = async (page: number) => {
    if (!exam) return
    setDetailLoading(true)
    try {
      const data = await listExamAttempts(Number(exam.id), page, 10)
      setAttempts(data.items)
      setAttemptsTotal(data.total)
      setAttemptPage(page)
    } finally {
      setDetailLoading(false)
    }
  }

  if (!exam) return null

  const maxCount = Math.max(...exam.distribution, 1)

  const attemptColumns: ColumnsType<ExamAttemptDetail> = [
    { title: '工号', dataIndex: 'employee_no', width: 90 },
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '部门', dataIndex: 'org_path', ellipsis: true },
    {
      title: '分数',
      dataIndex: 'best_score',
      width: 70,
      render: (value: number | null) => (value == null ? '—' : value),
    },
    {
      title: '结果',
      dataIndex: 'passed',
      width: 70,
      render: (value: boolean | null) =>
        value == null ? '—' : value ? <Tag color="green">通过</Tag> : <Tag color="red">未通过</Tag>,
    },
    { title: '提交时间', dataIndex: 'submitted_at', width: 160, render: (value: string | null) => value || '—' },
    { title: '场次', dataIndex: 'attempt_count', width: 60 },
  ]

  const footer = (
    <Space style={{ display: 'flex', justifyContent: 'flex-end' }} wrap>
      {exam.status === 'draft' || exam.status === 'published' ? (
        <Button onClick={() => onAssign(exam.id)}>
          {exam.status === 'published' ? '追加指派' : '指派范围'}
        </Button>
      ) : null}
      {exam.status === 'draft' ? (
        <Button onClick={() => onCards(exam.id)}>关联知识卡</Button>
      ) : null}
      <Button type="primary" onClick={() => onExport(exam.id)}>
        导出成绩
      </Button>
      {exam.status === 'draft' ? (
        <Button type="primary" onClick={() => onPublish(exam.id)}>
          发布考试
        </Button>
      ) : null}
      {exam.status === 'published' ? (
        <Button danger onClick={() => onCloseExam(exam.id)}>
          关闭考试
        </Button>
      ) : null}
    </Space>
  )

  return (
    <Drawer
      title={exam.title}
      width={560}
      open={open}
      onClose={onClose}
      footer={footer}
      destroyOnClose
    >
      <Space direction="vertical" size={20} style={{ width: '100%' }}>
        <Space wrap>
          <StatusTag kind="exam" status={exam.status} />
          <Typography.Text type="secondary">
            {exam.bank} · {exam.questionCount} 题 · 截止 {exam.endsAt}
          </Typography.Text>
        </Space>

        {exam.description ? (
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {exam.description}
          </Typography.Paragraph>
        ) : null}

        <Row gutter={[12, 12]}>
          <Col span={12}>
            <Statistic title="指派人数" value={exam.assigned} />
          </Col>
          <Col span={12}>
            <Statistic title="完成人数" value={exam.completed} />
          </Col>
          <Col span={12}>
            <Statistic title="通过率" value={exam.passRate ?? '—'} suffix={exam.passRate == null ? undefined : '%'} />
          </Col>
          <Col span={12}>
            <Statistic
              title="知识卡查看率"
              value={exam.cardViewRate}
              suffix="%"
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="平均分"
              value={analytics?.avg_score ?? exam.avgScore ?? 0}
            />
          </Col>
        </Row>

        {notifyStats ? (
          <div>
            <Typography.Text strong>通知送达</Typography.Text>
            <Row gutter={[12, 8]} style={{ marginTop: 8 }}>
              <Col span={8}>
                <Statistic
                  title="已通知"
                  value={notifyStats.notified}
                  suffix={`/ ${notifyStats.assigned}`}
                />
              </Col>
              <Col span={8}>
                <Statistic title="已读" value={notifyStats.read} />
              </Col>
              <Col span={8}>
                <Statistic title="已绑定微信" value={notifyStats.bound_wechat} />
              </Col>
            </Row>
            {notifyStats.unbound.length ? (
              <Typography.Paragraph
                type="secondary"
                style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}
              >
                未绑定微信：
                {notifyStats.unbound
                  .slice(0, 8)
                  .map((item) => item.name)
                  .join('、')}
                {notifyStats.unbound.length > 8
                  ? ` 等 ${notifyStats.unbound.length} 人`
                  : ''}
                ，这些员工只能在小程序内看到消息。
              </Typography.Paragraph>
            ) : null}
          </div>
        ) : null}

        <div>
          <Typography.Text strong>成绩分布</Typography.Text>
          <Space direction="vertical" size={6} style={{ width: '100%', marginTop: 10 }}>
            {exam.distribution.map((count, index) => (
              <div key={DIST_LABELS[index]} className="exam-dist-row">
                <span className="exam-dist-label">{DIST_LABELS[index]}</span>
                <Progress
                  percent={Math.round((count / maxCount) * 100)}
                  showInfo={false}
                  size="small"
                  strokeColor="var(--admin-accent)"
                />
                <span className="exam-dist-count">{count}</span>
              </div>
            ))}
          </Space>
        </div>

        <div>
          <Typography.Text strong>
            关联知识卡（{exam.cardTitles?.length ?? 0}）
          </Typography.Text>
          {exam.cardTitles?.length ? (
            <List
              size="small"
              dataSource={exam.cardTitles}
              renderItem={(item) => <List.Item>{item}</List.Item>}
              style={{ marginTop: 6 }}
            />
          ) : (
            <Typography.Paragraph type="secondary" style={{ marginTop: 6 }}>
              暂未关联考前知识卡。
            </Typography.Paragraph>
          )}
        </div>

        <div>
          <Typography.Text strong>薄弱知识点</Typography.Text>
          {exam.weakPoints.length ? (
            <List
              size="small"
              dataSource={exam.weakPoints}
              renderItem={(item) => <List.Item>{item}</List.Item>}
              style={{ marginTop: 6 }}
            />
          ) : (
            <Typography.Paragraph type="secondary" style={{ marginTop: 6 }}>
              暂无数据，考试开始后生成。
            </Typography.Paragraph>
          )}
        </div>

        <Collapse
          items={[
            {
              key: 'attempts',
              label: `成绩明细（${attemptsTotal} 人）`,
              children: (
                <Table
                  size="small"
                  rowKey="employee_id"
                  columns={attemptColumns}
                  dataSource={attempts}
                  loading={detailLoading}
                  pagination={{
                    current: attemptPage,
                    pageSize: 10,
                    total: attemptsTotal,
                    showSizeChanger: false,
                    onChange: (page) => void loadAttemptPage(page),
                  }}
                  scroll={{ x: 720 }}
                />
              ),
            },
            {
              key: 'questions',
              label: '题目正确率',
              children: analytics?.question_accuracy.length ? (
                <Table
                  size="small"
                  rowKey="question_id"
                  dataSource={analytics.question_accuracy}
                  pagination={{ pageSize: 10, hideOnSinglePage: true }}
                  scroll={{ x: 560 }}
                  columns={[
                    { title: '题目', dataIndex: 'stem', ellipsis: true },
                    { title: '知识点', dataIndex: 'knowledge_point', width: 110 },
                    { title: '作答', dataIndex: 'answered', width: 60 },
                    {
                      title: '正确率',
                      dataIndex: 'accuracy',
                      width: 80,
                      render: (value: number) => (
                        <Tag color={value < 60 ? 'red' : value < 80 ? 'gold' : 'green'}>
                          {value}%
                        </Tag>
                      ),
                    },
                  ]}
                />
              ) : (
                <Typography.Text type="secondary">暂无作答数据</Typography.Text>
              ),
            },
            {
              key: 'departments',
              label: '部门对比',
              children: analytics?.departments.length ? (
                <Table
                  size="small"
                  rowKey="org_path"
                  dataSource={analytics.departments}
                  pagination={false}
                  columns={[
                    { title: '部门', dataIndex: 'org_path' },
                    { title: '指派', dataIndex: 'assigned', width: 70 },
                    { title: '完成', dataIndex: 'completed', width: 70 },
                    {
                      title: '完成率',
                      dataIndex: 'completion_rate',
                      width: 90,
                      render: (value: number) => `${value}%`,
                    },
                    {
                      title: '通过率',
                      dataIndex: 'pass_rate',
                      width: 90,
                      render: (value: number) => `${value}%`,
                    },
                  ]}
                />
              ) : (
                <Typography.Text type="secondary">暂无部门数据</Typography.Text>
              ),
            },
          ]}
        />
      </Space>
    </Drawer>
  )
}
