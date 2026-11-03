import { App as AntApp, Button, Form, Input, Modal, Space } from 'antd'
import { useEffect, useState } from 'react'
import {
  getKnowledgeCardDetail,
  updateKnowledgeCard,
  type KnowledgeCardPoint,
} from '../services/api'

interface EditKnowledgeCardModalProps {
  open: boolean
  cardId: number | null
  onCancel: () => void
  onSuccess: () => void
}

interface CardFormValues {
  title: string
  excerpt: string
  points: KnowledgeCardPoint[]
}

export default function EditKnowledgeCardModal({
  open,
  cardId,
  onCancel,
  onSuccess,
}: EditKnowledgeCardModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<CardFormValues>()
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open || !cardId) return
    let cancelled = false
    setLoading(true)
    getKnowledgeCardDetail(cardId)
      .then((card) => {
        if (cancelled) return
        form.setFieldsValue({
          title: card.title,
          excerpt: card.excerpt,
          points: card.points.length
            ? card.points
            : [{ heading: '要点', body: card.excerpt }],
        })
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
  }, [open, cardId, form, message])

  const handleFinish = async (values: CardFormValues) => {
    if (!cardId) return
    setSubmitting(true)
    try {
      await updateKnowledgeCard(cardId, {
        title: values.title,
        excerpt: values.excerpt,
        points: values.points || [],
      })
      message.success('知识卡已更新')
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '知识卡更新失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="编辑知识卡"
      open={open}
      okText="保存"
      cancelText="取消"
      confirmLoading={submitting || loading}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
      width={680}
    >
      <Form form={form} layout="vertical" onFinish={handleFinish}>
        <Form.Item
          name="title"
          label="标题"
          rules={[{ required: true, message: '请输入标题' }]}
        >
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item
          name="excerpt"
          label="摘要"
          rules={[{ required: true, message: '请输入摘要' }]}
        >
          <Input.TextArea rows={2} maxLength={1000} showCount />
        </Form.Item>

        <Form.List name="points">
          {(fields, { add, remove }) => (
            <Space direction="vertical" size={10} style={{ width: '100%' }}>
              {fields.map((field) => (
                <div key={field.key} className="panel-card" style={{ padding: 12 }}>
                  <Form.Item
                    name={[field.name, 'heading']}
                    label="小标题"
                    rules={[{ required: true, message: '请输入小标题' }]}
                  >
                    <Input maxLength={60} />
                  </Form.Item>
                  <Form.Item
                    name={[field.name, 'body']}
                    label="正文"
                    rules={[{ required: true, message: '请输入正文' }]}
                  >
                    <Input.TextArea rows={3} maxLength={800} showCount />
                  </Form.Item>
                  <Button danger size="small" onClick={() => remove(field.name)}>
                    删除要点
                  </Button>
                </div>
              ))}
              <Button type="dashed" onClick={() => add({ heading: '', body: '' })}>
                添加要点
              </Button>
            </Space>
          )}
        </Form.List>
      </Form>
    </Modal>
  )
}
