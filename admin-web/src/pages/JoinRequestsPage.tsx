import { CheckOutlined, CloseOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import {
  approveJoinRequest,
  getToken,
  listJoinRequests,
  listOrgUnits,
  rejectJoinRequest,
  type JoinRequestItem,
  type OrgUnitItem,
} from '../services/api'

const STATUS_META: Record<JoinRequestItem['status'], { text: string; color: string }> = {
  pending: { text: '待审核', color: 'gold' },
  approved: { text: '已通过', color: 'green' },
  rejected: { text: '已驳回', color: 'red' },
}

export default function JoinRequestsPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [items, setItems] = useState<JoinRequestItem[]>([])
  const [orgs, setOrgs] = useState<OrgUnitItem[]>([])
  const [status, setStatus] = useState<'pending' | 'all'>('pending')
  const [loading, setLoading] = useState(false)
  const [approveTarget, setApproveTarget] = useState<JoinRequestItem | null>(null)
  const [rejectTarget, setRejectTarget] = useState<JoinRequestItem | null>(null)
  const [approveForm] = Form.useForm<{ org_id?: number; role: string }>()
  const [rejectForm] = Form.useForm<{ reason: string }>()

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '加入申请请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listJoinRequests({ status, page: 1, page_size: 200 })
      setItems(data.items)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [status, handleError])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    listOrgUnits()
      .then((data) => setOrgs(data.items))
      .catch(() => {})
  }, [])

  const openApprove = (item: JoinRequestItem) => {
    setApproveTarget(item)
    approveForm.setFieldsValue({ org_id: undefined, role: '员工' })
  }

  const handleApprove = async (values: { org_id?: number; role: string }) => {
    if (!approveTarget) return
    try {
      await approveJoinRequest(approveTarget.id, {
        org_id: values.org_id ?? null,
        role: values.role || '员工',
      })
      message.success(`已通过 ${approveTarget.name} 的加入申请`)
      setApproveTarget(null)
      await load()
    } catch (error) {
      handleError(error)
    }
  }

  const handleReject = async (values: { reason: string }) => {
    if (!rejectTarget) return
    try {
      await rejectJoinRequest(rejectTarget.id, values.reason)
      message.success(`已驳回 ${rejectTarget.name} 的加入申请`)
      setRejectTarget(null)
      rejectForm.resetFields()
      await load()
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<JoinRequestItem> = [
    {
      title: '申请人',
      dataIndex: 'name',
      render: (_, item) => (
        <div>
          <Typography.Text strong>{item.name}</Typography.Text>
          <div style={{ fontSize: 12, opacity: 0.65 }}>工号 {item.employee_no}</div>
        </div>
      ),
    },
    {
      title: '申请企业',
      dataIndex: 'tenant_name',
      width: 180,
      render: (_, item) => (
        <div>
          <div>{item.tenant_name}</div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {item.tenant_code}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: '申请说明',
      dataIndex: 'remark',
      ellipsis: true,
      render: (remark: string | null) => remark || <Typography.Text type="secondary">未填写</Typography.Text>,
    },
    { title: '申请时间', dataIndex: 'created_at', width: 170 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value: JoinRequestItem['status'], item) => (
        <Space direction="vertical" size={2}>
          <Tag color={STATUS_META[value].color}>{STATUS_META[value].text}</Tag>
          {value === 'rejected' && item.reject_reason ? (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {item.reject_reason}
            </Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: '操作',
      width: 180,
      render: (_, item) =>
        item.status === 'pending' ? (
          <Space size={4}>
            <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => openApprove(item)}>
              通过
            </Button>
            <Button type="link" size="small" danger icon={<CloseOutlined />} onClick={() => setRejectTarget(item)}>
              驳回
            </Button>
          </Space>
        ) : (
          <Typography.Text type="secondary">
            {item.reviewed_by ? `${item.reviewed_by} 已处理` : '已处理'}
          </Typography.Text>
        ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="成员管理"
        title="加入审核"
        description="员工在小程序输入企业编码并提交资料后，在这里审核。通过后自动绑定微信账号并进入企业培训。"
      />

      <Card
        className="panel-card"
        title="加入申请"
        extra={
          <Space>
            <Typography.Text type="secondary">待审核 {items.filter((item) => item.status === 'pending').length} 条</Typography.Text>
            <Select
              value={status}
              style={{ width: 120 }}
              onChange={setStatus}
              options={[
                { label: '待审核', value: 'pending' },
                { label: '全部', value: 'all' },
              ]}
            />
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          scroll={{ x: 900 }}
        />
      </Card>

      <Modal
        title={`通过加入申请${approveTarget ? `：${approveTarget.name}` : ''}`}
        open={Boolean(approveTarget)}
        okText="通过并绑定"
        cancelText="取消"
        onCancel={() => setApproveTarget(null)}
        onOk={() => approveForm.submit()}
      >
        <Form form={approveForm} layout="vertical" onFinish={handleApprove} requiredMark={false}>
          <Form.Item label="分配部门" name="org_id">
            <Select
              allowClear
              placeholder="可暂不分配"
              options={orgs.map((org) => ({ label: org.path, value: org.id }))}
            />
          </Form.Item>
          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请输入角色' }]}
          >
            <Input placeholder="员工" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`驳回加入申请${rejectTarget ? `：${rejectTarget.name}` : ''}`}
        open={Boolean(rejectTarget)}
        okText="驳回"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        onCancel={() => setRejectTarget(null)}
        onOk={() => rejectForm.submit()}
      >
        <Form form={rejectForm} layout="vertical" onFinish={handleReject} requiredMark={false}>
          <Form.Item
            label="驳回原因"
            name="reason"
            rules={[{ required: true, message: '请填写驳回原因' }]}
          >
            <Input.TextArea rows={3} placeholder="例如：工号与员工名册不一致，请联系 HR" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
