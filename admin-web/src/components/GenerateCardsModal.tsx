import { Alert, App as AntApp, Form, InputNumber, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import {
  generateKnowledgeCards,
  listAdminDocuments,
  type AdminDocument,
} from '../services/api'

interface GenerateCardsModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}

interface CardFormValues {
  doc_id: number
  count: number
  style: '操作要点' | '概念解释' | '易错提醒'
}

export default function GenerateCardsModal({
  open,
  onCancel,
  onSuccess,
}: GenerateCardsModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<CardFormValues>()
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    listAdminDocuments()
      .then((data) => {
        if (cancelled) return
        const readyDocs = data.items.filter(
          (doc) => doc.status === 'ready' && doc.has_file !== false,
        )
        setDocuments(readyDocs)
        if (readyDocs.length) {
          form.setFieldsValue({ doc_id: readyDocs[0].id })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : '文档列表加载失败')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, form, message])

  const handleFinish = async (values: CardFormValues) => {
    const document = documents.find((doc) => doc.id === values.doc_id)
    if (!document) {
      message.warning('请选择来源文档')
      return
    }

    setSubmitting(true)
    try {
      const result = await generateKnowledgeCards({
        doc_id: values.doc_id,
        doc_name: document.file_name,
        count: values.count,
        style: values.style,
      })
      message.success(`已生成 ${result.total} 张草稿知识卡，请审核`)
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '生成知识卡失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="生成知识卡"
      open={open}
      okText="生成草稿"
      cancelText="取消"
      confirmLoading={submitting}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ count: 5, style: '操作要点' }}
      >
        <Form.Item
          name="doc_id"
          label="来源文档"
          rules={[{ required: true, message: '请选择已解析完成的文档' }]}
        >
          <Select
            loading={loading}
            placeholder={documents.length ? '选择文档' : '暂无已解析完成的文档'}
            options={documents.map((doc) => ({
              label: `${doc.file_name}（${doc.chunks} 段）`,
              value: doc.id,
            }))}
          />
        </Form.Item>
        <div className="form-grid">
          <Form.Item name="count" label="生成数量" rules={[{ required: true }]}>
            <InputNumber min={3} max={5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="style" label="卡片风格">
            <Select
              options={[
                { label: '操作要点', value: '操作要点' },
                { label: '概念解释', value: '概念解释' },
                { label: '易错提醒', value: '易错提醒' },
              ]}
            />
          </Form.Item>
        </div>
        <Alert
          type="info"
          showIcon
          message="由 DeepSeek 读取文档内容生成草稿"
          description="生成结果会落库为草稿，需要管理员审核并发布后才能被考试关联和员工查看。生成过程可能需要几十秒。"
        />
      </Form>
    </Modal>
  )
}
