import { ImportOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Avatar,
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tree,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AddEmployeeModal from '../components/AddEmployeeModal'
import ImportEmployeesModal from '../components/ImportEmployeesModal'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  createOrgUnit,
  getToken,
  listEmployees,
  listOrgUnits,
  resetEmployeeInvite,
  updateEmployeeStatus,
  type EmployeeItem,
  type OrgUnitItem,
} from '../services/api'

interface OrgTreeNode extends DataNode {
  key: string | number
  children?: OrgTreeNode[]
}

function buildTree(orgs: OrgUnitItem[]): OrgTreeNode[] {
  const map = new Map<number, OrgTreeNode>()
  orgs.forEach((org) => {
    map.set(org.id, {
      key: org.id,
      title: (
        <Space size={6}>
          <span>{org.name}</span>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            {org.employee_count}
          </Typography.Text>
        </Space>
      ),
      children: [],
    })
  })

  const roots: OrgTreeNode[] = []
  orgs.forEach((org) => {
    const node = map.get(org.id)!
    if (org.parent_id && map.has(org.parent_id)) {
      map.get(org.parent_id)!.children!.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

export default function OrgPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [orgs, setOrgs] = useState<OrgUnitItem[]>([])
  const [employees, setEmployees] = useState<EmployeeItem[]>([])
  const [total, setTotal] = useState(0)
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [orgModalOpen, setOrgModalOpen] = useState(false)
  const [orgForm] = Form.useForm<{ name: string; parent_id?: number }>()

  const treeData = useMemo<OrgTreeNode[]>(
    () => [
      {
        key: 'all',
        title: (
          <Space size={6}>
            <span>全部员工</span>
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>{total}</Typography.Text>
          </Space>
        ),
        children: buildTree(orgs),
      },
    ],
    [orgs, total],
  )

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '组织与员工请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const loadOrgs = useCallback(async () => {
    try {
      const data = await listOrgUnits()
      setOrgs(data.items)
    } catch (error) {
      handleError(error)
    }
  }, [handleError])

  const loadEmployees = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listEmployees({
        org_id: selectedOrgId,
        keyword,
        page: 1,
        page_size: 200,
      })
      setEmployees(data.items)
      setTotal(data.total)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [selectedOrgId, keyword, handleError])

  useEffect(() => {
    void loadOrgs()
  }, [loadOrgs])

  useEffect(() => {
    void loadEmployees()
  }, [loadEmployees])

  const reload = async () => {
    await Promise.all([loadOrgs(), loadEmployees()])
  }

  const handleResetInvite = async (employee: EmployeeItem) => {
    try {
      const updated = await resetEmployeeInvite(employee.id)
      message.success(`已重置 ${employee.name} 的邀请码：${updated.invite_code}`)
      await loadEmployees()
    } catch (error) {
      handleError(error)
    }
  }

  const handleStatus = async (employee: EmployeeItem) => {
    const next = employee.status === 'active' ? 'disabled' : 'active'
    try {
      await updateEmployeeStatus(employee.id, next)
      message.success(next === 'active' ? '员工已启用' : '员工已停用')
      await loadEmployees()
    } catch (error) {
      handleError(error)
    }
  }

  const handleExportInvites = async () => {
    try {
      const data = await listEmployees({ page: 1, page_size: 200 })
      const lines = ['工号,姓名,部门,邀请码,绑定状态']
      data.items.forEach((employee) => {
        lines.push(
          [employee.employee_no, employee.name, employee.org_path, employee.invite_code, employee.invite_status].join(','),
        )
      })
      const blob = new Blob([`﻿${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = '员工邀请码.csv'
      anchor.click()
      URL.revokeObjectURL(url)
      message.success('邀请码已导出')
    } catch (error) {
      handleError(error)
    }
  }

  const handleCreateOrg = async (values: { name: string; parent_id?: number }) => {
    try {
      await createOrgUnit({ name: values.name, parent_id: values.parent_id ?? null })
      message.success('部门已创建')
      setOrgModalOpen(false)
      orgForm.resetFields()
      await loadOrgs()
    } catch (error) {
      handleError(error)
    }
  }

  const columns: ColumnsType<EmployeeItem> = [
    {
      title: '员工',
      dataIndex: 'name',
      render: (_, employee) => (
        <Space>
          <Avatar size={28}>{employee.name.slice(0, 1)}</Avatar>
          <div>
            <Typography.Text strong>{employee.name}</Typography.Text>
            <div style={{ fontSize: 12, opacity: 0.65 }}>{employee.employee_no}</div>
          </div>
        </Space>
      ),
    },
    { title: '部门', dataIndex: 'org_path', width: 220 },
    { title: '角色', dataIndex: 'role', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: EmployeeItem['status']) => <StatusTag kind="employee" status={status} />,
    },
    {
      title: '邀请码',
      dataIndex: 'invite_status',
      width: 160,
      render: (_, employee) => (
        <Space size={6}>
          <StatusTag kind="invite" status={employee.invite_status} />
          <Typography.Text code>{employee.invite_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: '操作',
      width: 200,
      render: (_, employee) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => handleResetInvite(employee)}>
            重置邀请码
          </Button>
          <Button type="link" size="small" danger={employee.status === 'active'} onClick={() => handleStatus(employee)}>
            {employee.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="ORGANIZATION"
        title="组织与员工"
        description="维护部门树、导入员工、生成邀请码。员工首次登录时用邀请码绑定微信。"
        extra={
          <Space wrap>
            <Button icon={<PlusOutlined />} onClick={() => setOrgModalOpen(true)}>
              新增部门
            </Button>
            <Button icon={<UploadOutlined />} onClick={handleExportInvites}>
              导出邀请码
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>
              手动添加
            </Button>
            <Button type="primary" icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
              导入员工
            </Button>
          </Space>
        }
      />

      <Row gutter={[14, 14]}>
        <Col xs={24} lg={7} xl={6}>
          <Card title="组织架构" className="panel-card" extra={<Typography.Text type="secondary">{total} 人</Typography.Text>}>
            <Tree
              blockNode
              defaultExpandAll
              treeData={treeData}
              selectedKeys={[selectedOrgId ?? 'all']}
              onSelect={(keys) => {
                const key = keys[0]
                setSelectedOrgId(key === 'all' || key === undefined ? null : Number(key))
              }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={17} xl={18}>
          <Card
            title={selectedOrgId ? '员工列表' : '全部员工'}
            className="panel-card"
            extra={
              <Input.Search
                allowClear
                placeholder="搜索姓名或工号"
                style={{ width: 220 }}
                onSearch={(value) => setKeyword(value.trim())}
                onChange={(event) => {
                  if (!event.target.value) setKeyword('')
                }}
              />
            }
          >
            <Table
              rowKey="id"
              columns={columns}
              dataSource={employees}
              loading={loading}
              pagination={false}
              scroll={{ x: 1000 }}
            />
          </Card>
        </Col>
      </Row>

      <AddEmployeeModal
        open={addOpen}
        orgs={orgs}
        onCancel={() => setAddOpen(false)}
        onSuccess={reload}
      />

      <ImportEmployeesModal
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onSuccess={reload}
      />

      <Modal
        title="新增部门"
        open={orgModalOpen}
        okText="创建"
        cancelText="取消"
        onCancel={() => setOrgModalOpen(false)}
        onOk={() => orgForm.submit()}
      >
        <Form form={orgForm} layout="vertical" onFinish={handleCreateOrg} requiredMark={false}>
          <Form.Item name="name" label="部门名称" rules={[{ required: true, message: '请输入部门名称' }]}>
            <Input placeholder="例如：华东区" />
          </Form.Item>
          <Form.Item name="parent_id" label="上级部门">
            <Select
              allowClear
              placeholder="不选则为顶级部门"
              options={orgs.map((org) => ({ label: org.path, value: org.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
