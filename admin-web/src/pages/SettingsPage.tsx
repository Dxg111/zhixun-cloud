import {
  App as AntApp,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Switch,
  Typography,
} from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import {
  getTenantSettings,
  getToken,
  updateTenantSettings,
  type TenantSettings,
} from '../services/api'

interface SettingsValues {
  tenantName: string
  tenantCode: string
  adminEmail: string
  retention: string
  passScore: number
  duration: number
  attempts: string
  randomOrder: '随机' | '固定'
  notifyAssigned: boolean
  notifyResult: boolean
  notifyDeadline: boolean
  notifyCards: boolean
}

const DEFAULTS: SettingsValues = {
  tenantName: '演示企业',
  tenantCode: 'demo',
  adminEmail: 'training@demo.com',
  retention: '合同期 + 90 天',
  passScore: 60,
  duration: 30,
  attempts: '1 次',
  randomOrder: '随机',
  notifyAssigned: true,
  notifyResult: true,
  notifyDeadline: false,
  notifyCards: false,
}

export default function SettingsPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [form] = Form.useForm<SettingsValues>()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const applySettings = (settings: TenantSettings) => {
    form.setFieldsValue({
      tenantName: settings.tenant_name,
      tenantCode: settings.tenant_code,
      adminEmail: settings.admin_email || '',
      retention: settings.retention,
      passScore: settings.default_pass_score,
      duration: settings.default_duration,
      attempts: `${settings.default_attempts} 次`,
      randomOrder: settings.random_order === '固定' ? '固定' : '随机',
      notifyAssigned: settings.notify_assigned,
      notifyResult: settings.notify_result,
      notifyDeadline: settings.notify_deadline,
      notifyCards: settings.notify_cards,
    })
  }

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const settings = await getTenantSettings()
      applySettings(settings)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '设置加载失败')
      if (!getToken()) navigate('/login', { replace: true })
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message, navigate])

  useEffect(() => {
    void loadSettings()
  }, [loadSettings])

  const handleFinish = async (values: SettingsValues) => {
    setSaving(true)
    try {
      const settings = await updateTenantSettings({
        tenant_name: values.tenantName,
        admin_email: values.adminEmail || null,
        retention: values.retention,
        default_pass_score: values.passScore,
        default_duration: values.duration,
        default_attempts: Number(values.attempts.replace(/[^\d]/g, '')) || 1,
        random_order: values.randomOrder,
        notify_assigned: values.notifyAssigned,
        notify_result: values.notifyResult,
        notify_deadline: values.notifyDeadline,
        notify_cards: values.notifyCards,
      })
      applySettings(settings)
      message.success('设置已保存')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存设置失败')
      if (!getToken()) navigate('/login', { replace: true })
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="SETTINGS"
        title="设置"
        description="租户信息、考试默认值和通知策略。"
        extra={
          <Button type="primary" loading={saving} onClick={() => form.submit()}>
            保存设置
          </Button>
        }
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={DEFAULTS}
        disabled={loading}
      >
        <Card title="租户信息" className="panel-card" style={{ marginBottom: 14 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="tenantName" label="企业名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="tenantCode" label="租户编码">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="adminEmail" label="管理员邮箱" rules={[{ type: 'email' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="retention" label="数据保留">
                <Select
                  options={[
                    { label: '3 年', value: '3 年' },
                    { label: '合同期 + 90 天', value: '合同期 + 90 天' },
                    { label: '1 年', value: '1 年' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="考试默认值" className="panel-card" style={{ marginBottom: 14 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="passScore" label="默认及格线">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="duration" label="默认时长（分钟）">
                <InputNumber min={5} max={180} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="attempts" label="默认重考次数">
                <Select options={[{ label: '1 次', value: '1 次' }, { label: '2 次', value: '2 次' }, { label: '3 次', value: '3 次' }]} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="randomOrder" label="题目顺序">
                <Select options={[{ label: '随机', value: '随机' }, { label: '固定', value: '固定' }]} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="通知策略" className="panel-card">
          <Typography.Paragraph type="secondary">
            MVP 只发站内通知；微信订阅消息和截止提醒放 P1。
          </Typography.Paragraph>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="notifyAssigned" label="考试指派时通知员工" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="notifyResult" label="成绩生成后通知员工" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="notifyDeadline" label="考试结束前 24 小时提醒" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="notifyCards" label="新知识卡发布时通知员工" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Card>
      </Form>
    </>
  )
}
