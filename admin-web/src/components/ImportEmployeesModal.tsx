import { InboxOutlined } from '@ant-design/icons'
import { Alert, App as AntApp, Modal, Typography, Upload } from 'antd'
import { useState } from 'react'
import { importEmployees } from '../services/api'

interface ImportEmployeesModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
}

export default function ImportEmployeesModal({
  open,
  onCancel,
  onSuccess,
}: ImportEmployeesModalProps) {
  const { message } = AntApp.useApp()
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  const handleOk = async () => {
    if (!file) return
    setLoading(true)
    try {
      const result = await importEmployees(file)
      message.success(`导入完成：成功 ${result.imported} 人，跳过 ${result.skipped} 人`)
      if (result.errors.length) {
        message.warning(result.errors.slice(0, 3).join('；'))
      }
      setFile(null)
      onSuccess()
      onCancel()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导入失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="导入员工"
      open={open}
      okText="开始导入"
      cancelText="取消"
      confirmLoading={loading}
      okButtonProps={{ disabled: !file }}
      onCancel={onCancel}
      onOk={handleOk}
      afterClose={() => setFile(null)}
      destroyOnClose
    >
      <Typography.Paragraph type="secondary">
        支持 .xlsx / .csv。字段：工号、姓名、部门路径、角色；部门不存在时自动创建。
      </Typography.Paragraph>

      <Upload.Dragger
        accept=".xlsx,.csv"
        maxCount={1}
        showUploadList={false}
        beforeUpload={(selected) => {
          setFile(selected)
          return false
        }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽员工文件到这里</p>
        <p className="ant-upload-hint">导入后自动生成一次性邀请码</p>
      </Upload.Dragger>

      {file ? (
        <Typography.Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
          已选择：<Typography.Text code>{file.name}</Typography.Text>
        </Typography.Paragraph>
      ) : null}

      <Alert
        style={{ marginTop: 14 }}
        type="info"
        showIcon
        message="导入规则"
        description="工号重复的行会跳过；部门路径用 / 分隔，例如：华东区/上海门店/徐汇店。"
      />
    </Modal>
  )
}
