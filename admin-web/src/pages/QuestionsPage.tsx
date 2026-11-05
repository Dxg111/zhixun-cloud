import { App as AntApp, Button, Card, Input, Segmented, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState, type Key } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import EditQuestionModal from '../components/EditQuestionModal'
import GenerateQuestionsModal from '../components/GenerateQuestionsModal'
import QuestionDrawer from '../components/QuestionDrawer'
import StatusTag from '../components/StatusTag'
import {
  bulkReviewQuestions,
  deleteAdminQuestion,
  getToken,
  listQuestionBanks,
  listQuestions,
  reviewQuestion,
  type ApiQuestion,
  type QuestionBankItem,
  type QuestionCounts,
} from '../services/api'
import type { Question } from '../types'

const TYPE_LABELS: Record<Question['type'], string> = {
  single: '单选',
  multiple: '多选',
  judge: '判断',
}

const DIFFICULTY_LABELS: Record<Question['difficulty'], string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const DIFFICULTY_COLORS: Record<Question['difficulty'], string> = {
  easy: 'success',
  medium: 'warning',
  hard: 'error',
}

const PAGE_SIZE = 10

function toDrawerQuestion(item: ApiQuestion): Question {
  return {
    id: String(item.id),
    bank: item.bank_name,
    type: item.type,
    stem: item.stem,
    options: item.options,
    answer: item.answer,
    explanation: item.explanation,
    knowledgePoint: item.knowledge_point,
    difficulty: item.difficulty,
    source: item.source,
    status: item.status,
    aiMeta: item.ai_meta,
    note: item.review_note ?? undefined,
  }
}

export default function QuestionsPage() {
  const { message, modal } = AntApp.useApp()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const keywordFromUrl = searchParams.get('keyword') || ''
  const [questions, setQuestions] = useState<ApiQuestion[]>([])
  const [counts, setCounts] = useState<QuestionCounts>({
    all: 0,
    draft: 0,
    approved: 0,
    rejected: 0,
  })
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('all')
  const [keyword, setKeyword] = useState('')
  const [bankId, setBankId] = useState<number | null>(null)
  const [banks, setBanks] = useState<QuestionBankItem[]>([])
  const [page, setPage] = useState(1)
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([])
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState<ApiQuestion | null>(null)

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '题库请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const fetchQuestions = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listQuestions({
        status: filter,
        keyword,
        bank_id: bankId,
        page,
        page_size: PAGE_SIZE,
      })
      setQuestions(data.items)
      setCounts(data.counts)
      setTotal(data.total)
      setSelectedRowKeys([])
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [filter, keyword, bankId, page, handleError])

  useEffect(() => {
    if (keywordFromUrl) setKeyword(keywordFromUrl)
  }, [keywordFromUrl])

  useEffect(() => {
    void fetchQuestions()
  }, [fetchQuestions])

  useEffect(() => {
    listQuestionBanks()
      .then((data) => setBanks(data.items))
      .catch(() => {})
  }, [])

  const openQuestion = (question: ApiQuestion) => {
    setSelectedQuestion(toDrawerQuestion(question))
    setDrawerOpen(true)
  }

  const handleApprove = async (id: string) => {
    try {
      await reviewQuestion(Number(id), 'approve')
      setDrawerOpen(false)
      message.success('题目已通过审核')
      await fetchQuestions()
    } catch (error) {
      handleError(error)
    }
  }

  const handleReject = async (id: string, note: string) => {
    try {
      await reviewQuestion(Number(id), 'reject', note || undefined)
      setDrawerOpen(false)
      message.warning('题目已驳回')
      await fetchQuestions()
    } catch (error) {
      handleError(error)
    }
  }

  const handleBatchApprove = async () => {
    if (!selectedRowKeys.length) return
    try {
      const result = await bulkReviewQuestions(
        selectedRowKeys.map((key) => Number(key)),
        'approve',
      )
      message.success(`已批量通过 ${result.updated} 道题`)
      await fetchQuestions()
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<ApiQuestion> = [
    {
      title: '题目',
      dataIndex: 'stem',
      render: (_, question) => (
        <div>
          <Typography.Text strong>{question.stem}</Typography.Text>
          <div style={{ fontSize: 12, opacity: 0.65 }}>{question.bank_name}</div>
        </div>
      ),
    },
    {
      title: '题型',
      dataIndex: 'type',
      width: 80,
      render: (type: ApiQuestion['type']) => TYPE_LABELS[type],
    },
    { title: '知识点', dataIndex: 'knowledge_point', width: 120 },
    {
      title: '难度',
      dataIndex: 'difficulty',
      width: 80,
      render: (difficulty: ApiQuestion['difficulty']) => (
        <Tag color={DIFFICULTY_COLORS[difficulty]}>{DIFFICULTY_LABELS[difficulty]}</Tag>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 210,
      render: (source: string) => <Typography.Text type="secondary">{source}</Typography.Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: ApiQuestion['status']) => <StatusTag kind="question" status={status} />,
    },
    {
      title: '操作',
      width: 190,
      render: (_, question) => (
        <Space size={0}>
          <Button
            type="link"
            size="small"
            onClick={(event) => {
              event.stopPropagation()
              openQuestion(question)
            }}
          >
            {question.status === 'draft' ? '审核' : '查看'}
          </Button>
          <Button
            type="link"
            size="small"
            onClick={(event) => {
              event.stopPropagation()
              setEditingQuestion(question)
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={(event) => {
              event.stopPropagation()
              modal.confirm({
                title: '删除题目？',
                content: '删除后不会再出现在题库和组卷中，已发布考试的题目快照不受影响。',
                okText: '删除',
                okButtonProps: { danger: true },
                cancelText: '取消',
                onOk: async () => {
                  try {
                    await deleteAdminQuestion(question.id)
                    message.success('题目已删除')
                    await fetchQuestions()
                  } catch (error) {
                    handleError(error)
                  }
                },
              })
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="QUESTION REVIEW"
        title="题库审核"
        description="AI 只生成草稿题。通过审核的题目才能进入组卷；驳回需要写明原因。"
        extra={
          <Space>
            <Button disabled={!selectedRowKeys.length} onClick={handleBatchApprove}>
              批量通过
            </Button>
            <Button type="primary" onClick={() => setGenerateOpen(true)}>
              生成题目
            </Button>
          </Space>
        }
      />

      <Card className="panel-card">
        <div className="page-toolbar">
          <Space wrap>
            <Segmented
              value={filter}
              onChange={(value) => {
                setFilter(String(value))
                setPage(1)
              }}
              options={[
                { label: `全部 ${counts.all}`, value: 'all' },
                { label: `待审核 ${counts.draft}`, value: 'draft' },
                { label: `已通过 ${counts.approved}`, value: 'approved' },
                { label: `已驳回 ${counts.rejected}`, value: 'rejected' },
              ]}
            />
            <Select
              allowClear
              value={bankId ?? undefined}
              placeholder="按题库筛选"
              style={{ width: 220 }}
              onChange={(value) => {
                setBankId(value ?? null)
                setPage(1)
              }}
              options={banks.map((bank) => ({
                label: `${bank.name}（${bank.total_count}）`,
                value: bank.id,
              }))}
            />
          </Space>
          <Input.Search
            allowClear
            key={keyword}
            defaultValue={keyword}
            placeholder="搜索题干或知识点"
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
          dataSource={questions}
          loading={loading}
          scroll={{ x: 980 }}
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: (nextPage) => setPage(nextPage),
          }}
          onRow={(question) => ({
            onClick: () => openQuestion(question),
          })}
          rowClassName={() => 'clickable-row'}
        />
      </Card>

      <GenerateQuestionsModal
        open={generateOpen}
        onCancel={() => setGenerateOpen(false)}
        onSuccess={() => {
          setFilter('draft')
          setPage(1)
        }}
      />

      <EditQuestionModal
        open={editingQuestion !== null}
        question={editingQuestion}
        onCancel={() => setEditingQuestion(null)}
        onSuccess={() => {
          setDrawerOpen(false)
          void fetchQuestions()
        }}
      />

      <QuestionDrawer
        open={drawerOpen}
        question={selectedQuestion}
        onClose={() => setDrawerOpen(false)}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </>
  )
}
