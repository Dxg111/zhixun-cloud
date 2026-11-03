import { App as AntApp, Form, Input, Modal, Typography } from 'antd'
import { useState } from 'react'
import { createAdmin } from '../services/api'

interface AdminCreateModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}

interface AdminCreateValues {
  login_name: string
  display_name: string
  password: string
  confirm: string
}

export default function AdminCreateModal({
  open,
  onCancel,
  onSuccess,
}: AdminCreateModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<AdminCreateValues>()
  const [loading, setLoading] = useState(false)

  const handleFinish = async (values: AdminCreateValues) => {
    if (values.password !== values.confirm) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      const admin = await createAdmin({
        login_name: values.login_name,
        display_name: values.display_name,
        password: values.password,
      })
      message.success(`管理员「${admin.display_name}」已创建`)
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '创建管理员失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="新增管理员"
      open={open}
      okText="创建"
      cancelText="取消"
      confirmLoading={loading}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
    >
      <Typography.Paragraph type="secondary">
        新管理员属于当前租户，密码以 bcrypt 哈希保存，创建后不会显示明文。
      </Typography.Paragraph>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        requiredMark={false}
      >
        <Form.Item
          name="login_name"
          label="登录名"
          rules={[
            { required: true, message: '请输入登录名' },
            { min: 3, message: '登录名至少 3 位' },
            { pattern: /^[A-Za-z0-9_.-]+$/, message: '只允许字母、数字、下划线、点和短横线' },
          ]}
        >
          <Input placeholder="例如：ops" autoComplete="off" />
        </Form.Item>

        <Form.Item
          name="display_name"
          label="显示名称"
          rules={[{ required: true, message: '请输入显示名称' }]}
        >
          <Input placeholder="例如：运营管理员" autoComplete="off" />
        </Form.Item>

        <Form.Item
          name="password"
          label="初始密码"
          rules={[
            { required: true, message: '请输入初始密码' },
            { min: 8, message: '密码至少 8 位' },
          ]}
        >
          <Input.Password placeholder="至少 8 位" autoComplete="new-password" />
        </Form.Item>

        <Form.Item
          name="confirm"
          label="确认密码"
          dependencies={['password']}
          rules={[
            { required: true, message: '请再次输入密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) return Promise.resolve()
                return Promise.reject(new Error('两次输入的密码不一致'))
              },
            }),
          ]}
        >
          <Input.Password placeholder="再次输入密码" autoComplete="new-password" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
