import { Alert, App as AntApp, Form, Input, InputNumber, Modal, Select, Spin } from 'antd'
import { useEffect, useState } from 'react'
import {
  generateQuestionsFromDocument,
  listAdminDocuments,
  type AdminDocument,
} from '../services/api'

interface GenerateQuestionsModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}

interface GenerateFormValues {
  doc_id: number
  bank_name: string
  question_count: number
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed'
}

export default function GenerateQuestionsModal({
  open,
  onCancel,
  onSuccess,
}: GenerateQuestionsModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<GenerateFormValues>()
  const [docs, setDocs] = useState<AdminDocument[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoadingDocs(true)
    listAdminDocuments()
      .then((data) => setDocs(data.items.filter((doc) => doc.status === 'ready')))
      .catch((error) => message.error(error instanceof Error ? error.message : '文档加载失败'))
      .finally(() => setLoadingDocs(false))
  }, [open, message])

  const handleFinish = async (values: GenerateFormValues) => {
    setSubmitting(true)
    try {
      const result = await generateQuestionsFromDocument(values.doc_id, {
        bank_name: values.bank_name,
        question_count: values.question_count,
        difficulty: values.difficulty,
      })
      message.success(`已生成 ${result.created} 道草稿题，进入题库：${result.bank_name}`)
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI 出题失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="从文档生成题目"
      open={open}
      okText="开始生成"
      cancelText="取消"
      confirmLoading={submitting}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
    >
      <Spin spinning={loadingDocs}>
        {docs.length ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleFinish}
            initialValues={{
              bank_name: 'AI 生成题库',
              question_count: 5,
              difficulty: 'mixed',
            }}
          >
            <Form.Item name="doc_id" label="来源文档" rules={[{ required: true, message: '请选择已解析文档' }]}>
              <Select
                placeholder="选择已解析完成的文档"
                options={docs.map((doc) => ({
                  label: `${doc.file_name}（${doc.chunks} 个片段）`,
                  value: doc.id,
                }))}
              />
            </Form.Item>
            <div className="form-grid">
              <Form.Item name="bank_name" label="写入题库" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="question_count" label="题目数量" rules={[{ required: true }]}>
                <InputNumber min={3} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </div>
            <Form.Item name="difficulty" label="难度">
              <Select
                options={[
                  { label: '混合', value: 'mixed' },
                  { label: '简单', value: 'easy' },
                  { label: '中等', value: 'medium' },
                  { label: '困难', value: 'hard' },
                ]}
              />
            </Form.Item>
            <Alert
              type="info"
              showIcon
              message="生成需要几十秒"
              description="系统会把文档内容作为参考资料调用 DeepSeek 出题，结果先写入草稿题库，必须审核后才能组卷。"
            />
          </Form>
        ) : (
          <Alert
            type="warning"
            showIcon
            message="没有可用文档"
            description="请先到知识库上传并等待文档解析完成，再来生成题目。"
          />
        )}
      </Spin>
    </Modal>
  )
}
