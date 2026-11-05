import { Alert, App as AntApp, Form, Modal, Radio, Select, Typography } from 'antd'
import { useEffect, useState } from 'react'
import {
  getExamAssignments,
  listEmployees,
  listOrgUnits,
  updateExamAssignments,
  type EmployeeItem,
  type ExamAssignScope,
  type OrgUnitItem,
} from '../services/api'

interface AssignExamModalProps {
  open: boolean
  examId: number | null
  examStatus?: 'draft' | 'published' | 'closed'
  onCancel: () => void
  onSuccess: () => void
}

interface AssignFormValues {
  scope: ExamAssignScope
  org_ids: number[]
  employee_ids: number[]
}

export default function AssignExamModal({
  open,
  examId,
  examStatus,
  onCancel,
  onSuccess,
}: AssignExamModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<AssignFormValues>()
  const [orgs, setOrgs] = useState<OrgUnitItem[]>([])
  const [employees, setEmployees] = useState<EmployeeItem[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const scope = Form.useWatch('scope', form)

  useEffect(() => {
    if (!open || !examId) return
    let cancelled = false
    setLoading(true)
    Promise.all([
      listOrgUnits(),
      listEmployees({ page: 1, page_size: 200 }),
      getExamAssignments(examId),
    ])
      .then(([orgData, employeeData, assignment]) => {
        if (cancelled) return
        setOrgs(orgData.items)
        setEmployees(employeeData.items)
        if (assignment.employee_ids.length) {
          form.setFieldsValue({
            scope: 'employees',
            employee_ids: assignment.employee_ids,
            org_ids: [],
          })
        } else {
          form.setFieldsValue({ scope: 'all', employee_ids: [], org_ids: [] })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : '指派信息加载失败')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, examId, form, message])

  const handleFinish = async (values: AssignFormValues) => {
    if (!examId) return
    if (values.scope === 'org' && !values.org_ids?.length) {
      message.warning('请选择至少一个部门')
      return
    }
    if (values.scope === 'employees' && !values.employee_ids?.length) {
      message.warning('请选择至少一名员工')
      return
    }

    setSubmitting(true)
    try {
      const result = await updateExamAssignments(examId, {
        scope: values.scope,
        org_ids: values.scope === 'org' ? values.org_ids || [] : [],
        employee_ids: values.scope === 'employees' ? values.employee_ids || [] : [],
      })
      const added = result.added ?? 0
      message.success(
        added > 0
          ? `指派已更新，共 ${result.assigned} 人，已通知新增的 ${added} 人`
          : `指派已更新，共 ${result.assigned} 人`,
      )
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '更新指派失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={examStatus === 'published' ? '追加指派' : '指派范围'}
      open={open}
      okText={examStatus === 'published' ? '保存并通知' : '保存指派'}
      cancelText="取消"
      confirmLoading={submitting}
      onCancel={onCancel}
      onOk={() => form.submit()}
      afterClose={() => form.resetFields()}
      destroyOnClose
      width={620}
    >
      {examStatus === 'published' ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="考试已发布，只能追加指派"
          description="已有员工不会被移除；新增的员工会收到新考试通知。"
        />
      ) : null}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ scope: 'all', org_ids: [], employee_ids: [] }}
      >
        <Form.Item name="scope" label="指派方式" rules={[{ required: true }]}>
          <Radio.Group>
            <Radio.Button value="all">全部员工</Radio.Button>
            <Radio.Button value="org">按部门</Radio.Button>
            <Radio.Button value="employees">按员工</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {scope === 'org' ? (
          <Form.Item
            name="org_ids"
            label="选择部门（含下级部门）"
            rules={[{ required: true, message: '请选择部门' }]}
          >
            <Select
              mode="multiple"
              loading={loading}
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              listHeight={160}
              placeholder="选择部门"
              options={orgs.map((org) => ({ label: org.path, value: org.id }))}
            />
          </Form.Item>
        ) : null}

        {scope === 'employees' ? (
          <Form.Item
            name="employee_ids"
            label="选择员工"
            rules={[{ required: true, message: '请选择员工' }]}
          >
            <Select
              mode="multiple"
              loading={loading}
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              listHeight={160}
              placeholder="按姓名或工号搜索"
              options={employees.map((employee) => ({
                label: `${employee.name}（${employee.employee_no}）· ${employee.org_path}`,
                value: employee.id,
              }))}
            />
          </Form.Item>
        ) : null}

        <Typography.Text type="secondary">
          发布考试时按这里的配置生成指派记录；未配置时回退为全部在职员工。
        </Typography.Text>
      </Form>
    </Modal>
  )
}
