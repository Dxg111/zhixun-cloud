import { App as AntApp, Button, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { adminLogin, setStoredUser, setToken } from '../services/api'

const { Title, Paragraph, Text } = Typography

interface LoginValues {
  tenant: string
  username: string
  password: string
}

export default function LoginPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)

  const handleFinish = async (values: LoginValues) => {
    setLoading(true)
    try {
      const data = await adminLogin({
        tenant_code: values.tenant,
        login_name: values.username,
        password: values.password,
      })
      setToken(data.token)
      setStoredUser(data.user)
      message.success(`欢迎回来，${data.user.name}`)

      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : '/dashboard', { replace: true })
    } catch (error) {
      const text =
        error instanceof TypeError
          ? error.message
          : error instanceof Error
            ? error.message
            : '登录失败，请稍后重试'
      message.error(text)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <aside className="login-aside">
        <div className="login-brand">
          <div className="login-brand-mark">智</div>
          <span>智训云 · 企业管理后台</span>
        </div>

        <div>
          <Title className="login-title">把培训内容，变成可衡量的学习。</Title>
          <Paragraph className="login-copy">
            上传 SOP、制度和产品资料，AI 生成题目与考前知识卡，人工审核后发布考试，最后把成绩和薄弱点交给培训负责人。
          </Paragraph>
          <ul className="login-points">
            <li><span>01</span>文档一键生成题目与知识卡</li>
            <li><span>02</span>审核后组卷，按部门指派考试</li>
            <li><span>03</span>成绩、薄弱点、培训记录可导出</li>
          </ul>
        </div>

        <Text className="login-foot">页面骨架 V0.1 · 模拟数据</Text>
      </aside>

      <main className="login-form-wrap">
        <div className="login-card">
          <div className="page-eyebrow">TENANT ADMIN</div>
          <Title level={2} className="login-form-title">登录管理后台</Title>
          <Paragraph type="secondary" className="login-form-sub">
            使用租户编码和管理员账号进入。
          </Paragraph>

          <Form
            layout="vertical"
            onFinish={handleFinish}
            initialValues={{ tenant: 'demo', username: 'admin', password: 'demo1234' }}
            requiredMark={false}
          >
            <Form.Item name="tenant" label="租户编码" rules={[{ required: true, message: '请输入租户编码' }]}>
              <Input autoComplete="organization" />
            </Form.Item>
            <Form.Item name="username" label="管理员账号" rules={[{ required: true, message: '请输入管理员账号' }]}>
              <Input autoComplete="username" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>
              进入工作台
            </Button>
          </Form>

          <Paragraph type="secondary" className="login-hint">
            登录会调用后端 <Text code>POST /api/v1/auth/admin/login</Text>。本地默认账号：
            <Text code>demo / admin / demo1234</Text>，可在后端环境变量中修改。
          </Paragraph>
        </div>
      </main>
    </div>
  )
}
