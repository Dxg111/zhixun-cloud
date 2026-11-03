import { PlusOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Avatar,
  Button,
  Card,
  Popconfirm,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AdminCreateModal from '../components/AdminCreateModal'
import AdminResetPasswordModal from '../components/AdminResetPasswordModal'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  getStoredUser,
  getToken,
  listAdmins,
  updateAdminStatus,
  type AdminUserItem,
} from '../services/api'

export default function AdminUsersPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [admins, setAdmins] = useState<AdminUserItem[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [resetTarget, setResetTarget] = useState<AdminUserItem | null>(null)
  const currentUser = getStoredUser()

  const handleError = (error: unknown) => {
    const text = error instanceof Error ? error.message : '管理员操作失败'
    message.error(text)

    // 401 时 request 已清除 token，直接回登录页。
    if (!getToken()) navigate('/login', { replace: true })
  }

  const loadAdmins = async () => {
    setLoading(true)
    try {
      const data = await listAdmins()
      setAdmins(data.items)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAdmins()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleStatus = async (admin: AdminUserItem) => {
    const nextStatus = admin.status === 'active' ? 'disabled' : 'active'
    try {
      const updated = await updateAdminStatus(admin.id, nextStatus)
      setAdmins((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      message.success(
        nextStatus === 'disabled'
          ? `已停用管理员「${admin.display_name}」`
          : `已启用管理员「${admin.display_name}」`,
      )
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<AdminUserItem> = [
    {
      title: '管理员',
      dataIndex: 'display_name',
      render: (_, admin) => {
        const isSelf = currentUser?.id === admin.id
        return (
          <Space>
            <Avatar size={30}>{admin.display_name.slice(0, 1)}</Avatar>
            <div>
              <Space size={6}>
                <Typography.Text strong>{admin.display_name}</Typography.Text>
                {isSelf ? <Tag color="blue">当前账号</Tag> : null}
              </Space>
              <div style={{ fontSize: 12, opacity: 0.65 }}>{admin.login_name}</div>
            </div>
          </Space>
        )
      },
    },
    { title: '租户编码', dataIndex: 'tenant_code', width: 120 },
    {
      title: '角色',
      dataIndex: 'role',
      width: 120,
      render: (role: string) => (role === 'tenant_admin' ? '企业管理员' : '平台管理员'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: AdminUserItem['status']) => <StatusTag kind="admin" status={status} />,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180 },
    {
      title: '操作',
      width: 210,
      render: (_, admin) => {
        const isSelf = currentUser?.id === admin.id

        return (
          <Space size={0}>
            <Button type="link" size="small" onClick={() => setResetTarget(admin)}>
              重置密码
            </Button>
            {admin.status === 'disabled' ? (
              <Button size="small" onClick={() => handleStatus(admin)}>
                启用
              </Button>
            ) : isSelf ? (
              <Tooltip title="不能停用当前登录账号">
                <Button size="small" danger disabled>
                  停用
                </Button>
              </Tooltip>
            ) : (
              <Popconfirm
                title="确定停用该管理员？"
                description="停用后该账号将无法登录，历史操作记录保留。"
                okText="停用"
                cancelText="取消"
                onConfirm={() => handleStatus(admin)}
              >
                <Button size="small" danger>
                  停用
                </Button>
              </Popconfirm>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="ADMIN ACCOUNTS"
        title="管理员"
        description="管理后台登录账号。停用只影响登录，不删除历史操作记录；至少保留一个启用状态的管理员。"
        extra={
          <Space>
            <Button onClick={loadAdmins} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新增管理员
            </Button>
          </Space>
        }
      />

      <Card
        title="管理员账号"
        className="panel-card"
        extra={<Typography.Text type="secondary">{admins.length} 个账号</Typography.Text>}
      >
        <Typography.Paragraph type="secondary">
          当前租户：{currentUser?.tenant_code || 'demo'}。不能停用当前登录账号，也不能停用最后一个启用的管理员。
        </Typography.Paragraph>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={admins}
          loading={loading}
          pagination={false}
          scroll={{ x: 1000 }}
        />
      </Card>

      <AdminCreateModal
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onSuccess={loadAdmins}
      />

      <AdminResetPasswordModal
        open={Boolean(resetTarget)}
        admin={resetTarget}
        onCancel={() => setResetTarget(null)}
        onSuccess={loadAdmins}
      />
    </>
  )
}
