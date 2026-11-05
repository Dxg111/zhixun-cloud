import { App as AntApp, Button, Card, Input, Segmented, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import AssignExamModal from '../components/AssignExamModal'
import CreateExamModal from '../components/CreateExamModal'
import ExamCardsModal from '../components/ExamCardsModal'
import ExamDrawer from '../components/ExamDrawer'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  closeAdminExam,
  downloadExportTask,
  exportAdminExam,
  getAdminExam,
  getExamNotifyPreview,
  getToken,
  listAdminExams,
  publishAdminExam,
  type AdminExam,
  type AdminExamDetail,
  type ExamNotifyPreview,
} from '../services/api'
import type { Exam } from '../types'

const PAGE_SIZE = 20

function toDrawerExam(detail: AdminExamDetail): Exam {
  return {
    id: String(detail.id),
    title: detail.title,
    bank: detail.bank_name,
    status: detail.status,
    assigned: detail.assigned,
    completed: detail.completed,
    passRate: detail.pass_rate,
    endsAt: detail.end_at || '未设置',
    questionCount: detail.question_count,
    cardViewRate: detail.card_view_rate,
    cardTitles: detail.card_titles ?? [],
    distribution: detail.distribution,
    weakPoints: detail.weak_points,
  }
}

export default function ExamsPage() {
  const { message, modal } = AntApp.useApp()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const keywordFromUrl = searchParams.get('keyword') || ''
  const [exams, setExams] = useState<AdminExam[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({ all: 0, published: 0, closed: 0, draft: 0 })
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState('all')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [assignExamId, setAssignExamId] = useState<number | null>(null)
  const [cardsExamId, setCardsExamId] = useState<number | null>(null)

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '考试请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const loadExams = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listAdminExams({
        status: filter,
        keyword,
        page,
        page_size: PAGE_SIZE,
      })
      setExams(data.items)
      setCounts(data.counts)
      setTotal(data.total)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [filter, keyword, page, handleError])

  useEffect(() => {
    if (keywordFromUrl) setKeyword(keywordFromUrl)
  }, [keywordFromUrl])

  useEffect(() => {
    void loadExams()
  }, [loadExams])

  const openExam = async (exam: AdminExam) => {
    try {
      const detail = await getAdminExam(exam.id)
      setSelectedExam(toDrawerExam(detail))
      setDrawerOpen(true)
    } catch (error) {
      handleError(error)
    }
  }

  const refreshSelectedExam = useCallback(async () => {
    if (!selectedExam) return
    try {
      const detail = await getAdminExam(Number(selectedExam.id))
      setSelectedExam(toDrawerExam(detail))
    } catch (error) {
      handleError(error)
    }
    await loadExams()
  }, [selectedExam, handleError, loadExams])

  const handlePublish = async (id: string) => {
    let preview: ExamNotifyPreview
    try {
      preview = await getExamNotifyPreview(Number(id))
    } catch (error) {
      handleError(error)
      return
    }

    if (preview.assigned === 0) {
      message.warning('当前没有可指派的在职员工，请先在组织管理中添加员工')
      return
    }

    const unbound = Math.max(preview.assigned - preview.bound_wechat, 0)
    try {
      await modal.confirm({
        title: '确认发布考试？',
        content: [
          '发布后题目快照将冻结，不能再修改题目。',
          `本次将通知 ${preview.assigned} 名员工`,
          unbound > 0
            ? `其中 ${unbound} 人尚未绑定微信，只能在小程序内看到消息`
            : '全部员工已绑定微信',
        ].join('；'),
        okText: '发布并通知',
        cancelText: '取消',
      })
    } catch {
      return
    }

    try {
      await publishAdminExam(Number(id))
      message.success(`考试已发布，已通知 ${preview.assigned} 名员工`)
      setDrawerOpen(false)
      await loadExams()
    } catch (error) {
      handleError(error)
    }
  }

  const handleCloseExam = async (id: string) => {
    try {
      await closeAdminExam(Number(id))
      message.warning('考试已关闭，已提交成绩保留')
      setDrawerOpen(false)
      await loadExams()
    } catch (error) {
      handleError(error)
    }
  }

  const handleExport = async (id: string) => {
    try {
      const task = await exportAdminExam(Number(id))
      if (task.status === 'ready') {
        const blob = await downloadExportTask(task.id)
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = task.file_name
        link.click()
        URL.revokeObjectURL(url)
      }
      message.success(`导出完成：${task.file_name}（${task.rows} 行）`)
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<AdminExam> = [
    {
      title: '考试',
      dataIndex: 'title',
      render: (_, exam) => (
        <div>
          <Typography.Text strong>{exam.title}</Typography.Text>
          <div style={{ fontSize: 12, opacity: 0.65 }}>
            {exam.bank_name} · {exam.question_count} 题 · {exam.duration_minutes} 分钟
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
      title: '指派 / 完成',
      width: 110,
      render: (_, exam) => `${exam.completed} / ${exam.assigned}`,
    },
    {
      title: '通过率',
      width: 90,
      render: (_, exam) => (exam.completed ? `${exam.pass_rate}%` : '—'),
    },
    { title: '截止时间', dataIndex: 'end_at', width: 170, render: (value: string | null) => value || '未设置' },
    {
      title: '知识卡查看率',
      width: 130,
      render: (_, exam) => `${exam.card_view_rate}%`,
    },
    {
      title: '操作',
      width: 90,
      render: (_, exam) => (
        <Button
          type="link"
          size="small"
          onClick={(event) => {
            event.stopPropagation()
            void openExam(exam)
          }}
        >
          查看
        </Button>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="EXAMS"
        title="考试管理"
        description="组卷、设置及格线和时长、关联考前知识卡，并按部门或员工指派；发布时冻结题目快照。"
        extra={
          <Space>
            <Button onClick={() => message.info('考试模板待接入（骨架）')}>从模板创建</Button>
            <Button type="primary" onClick={() => setCreateOpen(true)}>
              新建考试
            </Button>
          </Space>
        }
      />

      <Card className="panel-card">
        <div className="page-toolbar">
          <Segmented
            value={filter}
            onChange={(value) => {
              setFilter(String(value))
              setPage(1)
            }}
            options={[
              { label: `全部 ${counts.all ?? 0}`, value: 'all' },
              { label: `进行中 ${counts.published ?? 0}`, value: 'published' },
              { label: `已结束 ${counts.closed ?? 0}`, value: 'closed' },
              { label: `草稿 ${counts.draft ?? 0}`, value: 'draft' },
            ]}
          />
          <Input.Search
            allowClear
            key={keyword}
            defaultValue={keyword}
            placeholder="搜索考试名称"
            style={{ width: 240 }}
            onSearch={(value) => {
              setKeyword(value.trim())
              setPage(1)
            }}
            onChange={(event) => {
              if (!event.target.value) {
                setKeyword('')
                setPage(1)
              }
            }}
          />
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={exams}
          loading={loading}
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: (nextPage) => setPage(nextPage),
          }}
          onRow={(exam) => ({ onClick: () => void openExam(exam) })}
          rowClassName={() => 'clickable-row'}
        />
      </Card>

      <CreateExamModal
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onSuccess={loadExams}
      />

      <ExamDrawer
        open={drawerOpen}
        exam={selectedExam}
        onClose={() => setDrawerOpen(false)}
        onPublish={handlePublish}
        onCloseExam={handleCloseExam}
        onExport={handleExport}
        onAssign={(id) => setAssignExamId(Number(id))}
        onCards={(id) => setCardsExamId(Number(id))}
      />

      <AssignExamModal
        open={assignExamId !== null}
        examId={assignExamId}
        onCancel={() => setAssignExamId(null)}
        onSuccess={refreshSelectedExam}
      />

      <ExamCardsModal
        open={cardsExamId !== null}
        examId={cardsExamId}
        onCancel={() => setCardsExamId(null)}
        onSuccess={refreshSelectedExam}
      />
    </>
  )
}
