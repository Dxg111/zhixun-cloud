import { Button, Col, Drawer, List, Progress, Row, Space, Statistic, Typography } from 'antd'
import type { Exam } from '../types'
import type { ExamNotificationStats } from '../services/api'
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
  if (!exam) return null

  const maxCount = Math.max(...exam.distribution, 1)

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
      </Space>
    </Drawer>
  )
}
