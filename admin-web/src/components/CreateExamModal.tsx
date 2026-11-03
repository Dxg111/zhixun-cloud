import {
  Alert,
  App as AntApp,
  Button,
  Checkbox,
  DatePicker,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Select,
  Typography,
} from 'antd'
import { useEffect, useRef, useState } from 'react'
import {
  createAdminExam,
  listEmployees,
  listKnowledgeCards,
  listOrgUnits,
  listQuestionBanks,
  publishAdminExam,
  updateExamAssignments,
  updateExamKnowledgeCards,
  type AdminKnowledgeCard,
  type EmployeeItem,
  type OrgUnitItem,
  type QuestionBankItem,
} from '../services/api'

interface CreateExamModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}

type AssignScope = 'all' | 'org' | 'employees'
type SubmitMode = 'draft' | 'publish'

interface ExamFormValues {
  title: string
  bank: string
  questionCount: number
  passScore: number
  duration: number
  attempts: string
  window?: Array<{ format: (format: string) => string }>
  card_ids?: number[]
  scope?: AssignScope
  org_ids?: number[]
  employee_ids?: number[]
}

export default function CreateExamModal({
  open,
  onCancel,
  onSuccess,
}: CreateExamModalProps) {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<ExamFormValues>()
  const submitModeRef = useRef<SubmitMode>('draft')
  const [submitting, setSubmitting] = useState<SubmitMode | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [banks, setBanks] = useState<QuestionBankItem[]>([])
  const [cards, setCards] = useState<AdminKnowledgeCard[]>([])
  const [orgs, setOrgs] = useState<OrgUnitItem[]>([])
  const [employees, setEmployees] = useState<EmployeeItem[]>([])

  const selectedBank = Form.useWatch('bank', form)
  const scope = Form.useWatch('scope', form) || 'all'
  const selectedCardIds = Form.useWatch('card_ids', form) || []
  const selectedBankItem = banks.find((bank) => bank.name === selectedBank)
  const maxQuestionCount = Math.max(1, selectedBankItem?.approved_count || 100)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoadingOptions(true)
    Promise.all([
      listQuestionBanks(),
      listKnowledgeCards({ status: 'published', page_size: 100 }),
      listOrgUnits(),
      listEmployees({ page: 1, page_size: 200 }),
    ])
      .then(([bankData, cardData, orgData, employeeData]) => {
        if (cancelled) return
        setBanks(bankData.items)
        setCards(cardData.items)
        setOrgs(orgData.items)
        setEmployees(employeeData.items)

        const preferred =
          bankData.items.find((bank) => bank.approved_count > 0) || bankData.items[0]
        form.setFieldsValue({
          bank: preferred?.name,
          card_ids: [],
          scope: 'all',
          org_ids: [],
          employee_ids: [],
        })
      })
      .catch((error) => {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : '考试配置加载失败')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingOptions(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, form, message])

  const handleFinish = async (values: ExamFormValues) => {
    const mode = submitModeRef.current
    const assignScope = values.scope || 'all'

    if (assignScope === 'org' && !values.org_ids?.length) {
      message.warning('请选择至少一个指派部门')
      return
    }
    if (assignScope === 'employees' && !values.employee_ids?.length) {
      message.warning('请选择至少一名指派员工')
      return
    }

    setSubmitting(mode)
    let examId: number | null = null
    try {
      const exam = await createAdminExam({
        title: values.title,
        bank_name: values.bank,
        question_count: values.questionCount,
        pass_score: values.passScore,
        duration_minutes: values.duration,
        max_attempts: Number(values.attempts.replace(/[^\d]/g, '')) || 1,
        start_at: values.window?.[0]?.format('YYYY-MM-DD HH:mm:ss') ?? null,
        end_at: values.window?.[1]?.format('YYYY-MM-DD HH:mm:ss') ?? null,
      })
      examId = exam.id

      try {
        await updateExamAssignments(exam.id, {
          scope: assignScope,
          org_ids: assignScope === 'org' ? values.org_ids || [] : [],
          employee_ids:
            assignScope === 'employees' ? values.employee_ids || [] : [],
        })
        await updateExamKnowledgeCards(exam.id, values.card_ids || [])
      } catch (error) {
        message.warning(
          `考试已保存为草稿，但指派或知识卡配置失败：${
            error instanceof Error ? error.message : '请到考试详情中重新配置'
          }`,
        )
        onSuccess()
        onCancel()
        return
      }

      if (mode === 'publish') {
        await publishAdminExam(exam.id)
        message.success('考试已保存并发布，题目快照已冻结')
      } else {
        message.success('考试已保存为草稿')
      }
      form.resetFields()
      onSuccess()
      onCancel()
    } catch (error) {
      const detail = error instanceof Error ? error.message : '操作失败'
      if (examId !== null) {
        message.error(`考试已保存为草稿，但发布失败：${detail}`)
        onSuccess()
        onCancel()
      } else {
        message.error(detail)
      }
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <Modal
      title="新建考试"
      open={open}
      cancelText="取消"
      onCancel={onCancel}
      afterClose={() => form.resetFields()}
      width={760}
      destroyOnClose
      styles={{ body: { maxHeight: '68vh', overflowY: 'auto', paddingRight: 8 } }}
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onCancel}>取消</Button>
          <Button
            loading={submitting === 'draft'}
            disabled={submitting === 'publish'}
            onClick={() => {
              submitModeRef.current = 'draft'
              form.submit()
            }}
          >
            保存草稿
          </Button>
          <Button
            type="primary"
            loading={submitting === 'publish'}
            disabled={submitting === 'draft'}
            onClick={() => {
              submitModeRef.current = 'publish'
              form.submit()
            }}
          >
            保存并发布
          </Button>
        </div>
      }
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{
          title: '门店 SOP 月度复训',
          questionCount: 3,
          passScore: 60,
          duration: 30,
          attempts: '1 次',
          scope: 'all',
        }}
      >
        <Form.Item name="title" label="考试名称" rules={[{ required: true, message: '请输入考试名称' }]}>
          <Input />
        </Form.Item>

        <div className="form-grid">
          <Form.Item
            name="bank"
            label="题库"
            rules={[{ required: true, message: '请选择题库' }]}
          >
            <Select
              loading={loadingOptions}
              placeholder={banks.length ? '选择题库' : '暂无题库'}
              options={banks.map((bank) => ({
                label: `${bank.name}（${bank.approved_count} 道已通过）`,
                value: bank.name,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="questionCount"
            label={`题量（可用 ${selectedBankItem?.approved_count ?? 0} 道）`}
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={maxQuestionCount} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="passScore" label="及格线" rules={[{ required: true }]}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="duration" label="时长（分钟）" rules={[{ required: true }]}>
            <InputNumber min={5} max={180} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="attempts" label="重考次数">
            <Select options={[{ label: '1 次', value: '1 次' }, { label: '2 次', value: '2 次' }, { label: '3 次', value: '3 次' }]} />
          </Form.Item>
        </div>

        <Form.Item name="window" label="考试时间">
          <DatePicker.RangePicker showTime style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left" plain>
          考前知识卡
        </Divider>
        <Form.Item
          name="card_ids"
          label={`关联已发布知识卡（已选 ${selectedCardIds.length} 张）`}
          extra="员工可在考试前通过「考前速览」查看；不关联也可以发布。"
        >
          {cards.length ? (
            <Checkbox.Group
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                maxHeight: 180,
                overflowY: 'auto',
                padding: '4px 2px',
              }}
            >
              {cards.map((card) => (
                <Checkbox key={card.id} value={card.id} style={{ alignItems: 'flex-start' }}>
                  <div>
                    <Typography.Text strong>{card.title}</Typography.Text>
                    <div style={{ fontSize: 12, opacity: 0.65 }}>{card.doc_name}</div>
                  </div>
                </Checkbox>
              ))}
            </Checkbox.Group>
          ) : (
            <Typography.Text type="secondary">暂无已发布知识卡</Typography.Text>
          )}
        </Form.Item>

        <Divider orientation="left" plain>
          指派范围
        </Divider>
        <Form.Item name="scope" label="指派方式">
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
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              listHeight={160}
              placement="topLeft"
              loading={loadingOptions}
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
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              listHeight={160}
              placement="topLeft"
              loading={loadingOptions}
              placeholder="按姓名或工号搜索"
              options={employees.map((employee) => ({
                label: `${employee.name}（${employee.employee_no}）· ${employee.org_path}`,
                value: employee.id,
              }))}
            />
          </Form.Item>
        ) : null}

        <Alert
          type="info"
          showIcon
          message="保存并发布会冻结题目快照"
          description="发布时从题库抽取已通过题目并冻结快照，员工立即可以看到考试。未配置指派时默认指派全部在职员工。"
        />
      </Form>
    </Modal>
  )
}
