import { App as AntApp, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { createEmployee, type OrgUnitItem } from '../services/api'

interface AddEmployeeModalProps {
  open: boolean
  orgs: OrgUnitItem[]
  onCancel: () => void
  onSuccess: () => void
}

interface EmployeeFormValues {
  employee_no: string
  name: string
  org_id: number
  role: string
}

export default function AddEmployeeModal({
  open,
  orgs,
  onCancel,
  onSuccess,
}: AddEmployeeModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<EmployeeFormValues>()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue({ role: '员工' })
    }
  }, [open, form])

  const handleFinish = async (values: EmployeeFormValues) => {
    setSubmitting(true)
    try {
      await createEmployee({
        employee_no: values.employee_no.trim(),
        name: values.name.trim(),
        org_id: values.org_id,
        role: values.role,
      })
      message.success(`已添加 ${values.name.trim()}，员工可在小程序提交加入申请`)
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '添加员工失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title="手动添加员工"
      open={open}
      okText="添加"
      cancelText="取消"
      confirmLoading={submitting}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
      width={520}
    >
      <Form form={form} layout="vertical" onFinish={handleFinish}>
        <Form.Item
          name="employee_no"
          label="工号"
          rules={[{ required: true, message: '请输入工号' }]}
        >
          <Input placeholder="例如：E1009" maxLength={64} />
        </Form.Item>
        <Form.Item
          name="name"
          label="姓名"
          rules={[{ required: true, message: '请输入姓名' }]}
        >
          <Input placeholder="例如：张敏" maxLength={100} />
        </Form.Item>
        <Form.Item
          name="org_id"
          label="部门"
          rules={[{ required: true, message: '请选择部门' }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="选择员工所属部门"
            options={orgs.map((org) => ({ label: org.path, value: org.id }))}
          />
        </Form.Item>
        <Form.Item name="role" label="角色" rules={[{ required: true }]}>
          <Select
            options={[
              { label: '员工', value: '员工' },
              { label: '店长', value: '店长' },
              { label: '区域经理', value: '区域经理' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
