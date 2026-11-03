import { App as AntApp, Form, Input, Modal, Typography } from 'antd'
import { useState } from 'react'
import { resetAdminPassword, type AdminUserItem } from '../services/api'

interface AdminResetPasswordModalProps {
  open: boolean
  admin: AdminUserItem | null
  onCancel: () => void
  onSuccess: () => void
}

interface ResetValues {
  password: string
  confirm: string
}

export default function AdminResetPasswordModal({
  open,
  admin,
  onCancel,
  onSuccess,
}: AdminResetPasswordModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<ResetValues>()
  const [loading, setLoading] = useState(false)

  if (!admin) return null

  const handleFinish = async (values: ResetValues) => {
    if (values.password !== values.confirm) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      await resetAdminPassword(admin.id, values.password)
      message.success(`已重置管理员「${admin.display_name}」的密码`)
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '重置密码失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={`重置密码 · ${admin.display_name}`}
      open={open}
      okText="重置密码"
      cancelText="取消"
      confirmLoading={loading}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
    >
      <Typography.Paragraph type="secondary">
        登录名：<Typography.Text code>{admin.login_name}</Typography.Text>。重置后请通知对方使用新密码登录。
      </Typography.Paragraph>

      <Form form={form} layout="vertical" onFinish={handleFinish} requiredMark={false}>
        <Form.Item
          name="password"
          label="新密码"
          rules={[
            { required: true, message: '请输入新密码' },
            { min: 8, message: '密码至少 8 位' },
          ]}
        >
          <Input.Password placeholder="至少 8 位" autoComplete="new-password" />
        </Form.Item>

        <Form.Item
          name="confirm"
          label="确认新密码"
          dependencies={['password']}
          rules={[
            { required: true, message: '请再次输入新密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) return Promise.resolve()
                return Promise.reject(new Error('两次输入的密码不一致'))
              },
            }),
          ]}
        >
          <Input.Password placeholder="再次输入新密码" autoComplete="new-password" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
