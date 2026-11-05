import { App as AntApp, Button, Checkbox, Form, Input, Modal, Select, Space } from 'antd'
import { useEffect, useState } from 'react'
import {
  updateAdminQuestion,
  type AdminQuestionUpdatePayload,
  type ApiQuestion,
} from '../services/api'

interface EditQuestionModalProps {
  open: boolean
  question: ApiQuestion | null
  onCancel: () => void
  onSuccess: () => void
}

interface OptionField {
  key: string
  text: string
}

interface EditFormValues {
  stem: string
  options: OptionField[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export default function EditQuestionModal({
  open,
  question,
  onCancel,
  onSuccess,
}: EditQuestionModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<EditFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const options = Form.useWatch('options', form) || []

  useEffect(() => {
    if (!open || !question) return
    form.setFieldsValue({
      stem: question.stem,
      options: question.options.map((item) => ({ key: item.key, text: item.text })),
      answer: question.answer,
      explanation: question.explanation,
      knowledge_point: question.knowledge_point,
      difficulty: question.difficulty,
    })
  }, [open, question, form])

  const handleFinish = async (values: EditFormValues) => {
    if (!question) return
    const payload: AdminQuestionUpdatePayload = {
      stem: values.stem.trim(),
      options: (values.options || []).map((item) => ({
        key: (item.key || '').trim(),
        text: (item.text || '').trim(),
      })),
      answer: values.answer || [],
      explanation: (values.explanation || '').trim(),
      knowledge_point: (values.knowledge_point || '').trim(),
      difficulty: values.difficulty,
    }
    setSubmitting(true)
    try {
      await updateAdminQuestion(question.id, payload)
      message.success('题目已更新，状态回到草稿，需要重新审核')
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '题目更新失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="编辑题目"
      open={open}
      okText="保存修改"
      cancelText="取消"
      width={720}
      confirmLoading={submitting}
      onCancel={onCancel}
      onOk={() => form.submit()}
      destroyOnClose
      afterClose={() => form.resetFields()}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ options: [], answer: [] }}
      >
        <Form.Item
          name="stem"
          label="题干"
          rules={[{ required: true, message: '请输入题干' }]}
        >
          <Input.TextArea rows={3} maxLength={2000} showCount />
        </Form.Item>

        <Form.List name="options">
          {(fields) => (
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              {fields.map((field) => (
                <Space key={field.key} align="baseline" style={{ width: '100%' }}>
                  <Form.Item
                    name={[field.name, 'key']}
                    rules={[{ required: true, message: 'key' }]}
                    style={{ marginBottom: 0, width: 80 }}
                  >
                    <Input placeholder="A" maxLength={4} />
                  </Form.Item>
                  <Form.Item
                    name={[field.name, 'text']}
                    rules={[{ required: true, message: '选项内容不能为空' }]}
                    style={{ marginBottom: 0, width: 480 }}
                  >
                    <Input placeholder="选项内容" maxLength={500} />
                  </Form.Item>
                </Space>
              ))}
            </Space>
          )}
        </Form.List>

        <Form.Item
          name="answer"
          label="正确答案"
          rules={[{ required: true, message: '请选择正确答案' }]}
          style={{ marginTop: 16 }}
        >
          <Checkbox.Group
            options={options
              .filter((item) => item?.key)
              .map((item) => ({ label: `${item.key}. ${item.text}`, value: item.key }))}
          />
        </Form.Item>

        <Form.Item name="explanation" label="解析">
          <Input.TextArea rows={3} maxLength={2000} showCount />
        </Form.Item>

        <div className="form-grid">
          <Form.Item name="knowledge_point" label="知识点">
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item name="difficulty" label="难度">
            <Select
              options={[
                { value: 'easy', label: '简单' },
                { value: 'medium', label: '中等' },
                { value: 'hard', label: '困难' },
              ]}
            />
          </Form.Item>
        </div>

        <Button type="link" style={{ paddingLeft: 0 }} onClick={onCancel}>
          取消并返回审核
        </Button>
      </Form>
    </Modal>
  )
}
