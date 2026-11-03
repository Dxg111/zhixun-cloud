import {
  App as AntApp,
  Checkbox,
  Empty,
  Form,
  Input,
  Modal,
  Spin,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'
import {
  getExamKnowledgeCards,
  listKnowledgeCards,
  updateExamKnowledgeCards,
  type AdminKnowledgeCard,
} from '../services/api'

interface ExamCardsModalProps {
  open: boolean
  examId: number | null
  onCancel: () => void
  onSuccess: () => void
}

interface ExamCardsFormValues {
  card_ids: number[]
}

export default function ExamCardsModal({
  open,
  examId,
  onCancel,
  onSuccess,
}: ExamCardsModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<ExamCardsFormValues>()
  const [cards, setCards] = useState<AdminKnowledgeCard[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const selectedIds = Form.useWatch('card_ids', form) || []

  useEffect(() => {
    if (!open || !examId) return
    let cancelled = false
    setLoading(true)
    Promise.all([
      listKnowledgeCards({ status: 'published', page_size: 100 }),
      getExamKnowledgeCards(examId),
    ])
      .then(([cardData, linked]) => {
        if (cancelled) return
        setCards(cardData.items)
        form.setFieldsValue({ card_ids: linked.map((card) => card.id) })
      })
      .catch((error) => {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : '知识卡加载失败')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, examId, form, message])

  const filteredCards = cards.filter((card) => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return true
    return (
      card.title.toLowerCase().includes(normalized) ||
      card.doc_name.toLowerCase().includes(normalized)
    )
  })

  const handleFinish = async (values: ExamCardsFormValues) => {
    if (!examId) return
    setSubmitting(true)
    try {
      const linked = await updateExamKnowledgeCards(examId, values.card_ids || [])
      message.success(`已关联 ${linked.length} 张知识卡`)
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '关联知识卡失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="关联考前知识卡"
      open={open}
      okText="保存关联"
      cancelText="取消"
      confirmLoading={submitting}
      okButtonProps={{ disabled: !loading && cards.length === 0 }}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => {
        form.resetFields()
        setKeyword('')
      }}
      destroyOnClose
      width={620}
    >
      <Spin spinning={loading}>
        {cards.length ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleFinish}
            initialValues={{ card_ids: [] }}
          >
            <Input.Search
              allowClear
              placeholder="搜索知识卡标题或来源文档"
              style={{ marginBottom: 12 }}
              onSearch={setKeyword}
              onChange={(event) => {
                if (!event.target.value) setKeyword('')
              }}
            />
            <Form.Item
              name="card_ids"
              label={`已发布知识卡（已选 ${selectedIds.length} 张）`}
            >
              <Checkbox.Group
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  maxHeight: 320,
                  overflowY: 'auto',
                  padding: '4px 2px',
                }}
              >
                {filteredCards.map((card) => (
                  <Checkbox key={card.id} value={card.id} style={{ alignItems: 'flex-start' }}>
                    <div>
                      <Typography.Text strong>{card.title}</Typography.Text>
                      <div style={{ fontSize: 12, opacity: 0.65 }}>{card.doc_name}</div>
                    </div>
                  </Checkbox>
                ))}
              </Checkbox.Group>
            </Form.Item>
            {filteredCards.length === 0 ? (
              <Empty description="没有匹配的知识卡" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : null}
            <Typography.Text type="secondary">
              只有已发布的知识卡可以被关联；考试发布后员工可在考前速览中查看。
            </Typography.Text>
          </Form>
        ) : (
          <Empty description="暂无已发布知识卡，请先在知识卡页面生成并发布" />
        )}
      </Spin>
    </Modal>
  )
}
