import { Alert, Button, Descriptions, Drawer, Input, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import type { Question } from '../types'
import StatusTag from './StatusTag'

interface QuestionDrawerProps {
  open: boolean
  question: Question | null
  onClose: () => void
  onApprove: (id: string) => void
  onReject: (id: string, note: string) => void
}

const TYPE_LABELS: Record<Question['type'], string> = {
  single: '单选',
  multiple: '多选',
  judge: '判断',
}

const DIFFICULTY_LABELS: Record<Question['difficulty'], string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const DIFFICULTY_COLORS: Record<Question['difficulty'], string> = {
  easy: 'success',
  medium: 'warning',
  hard: 'error',
}

export default function QuestionDrawer({
  open,
  question,
  onClose,
  onApprove,
  onReject,
}: QuestionDrawerProps) {
  const [note, setNote] = useState('')

  useEffect(() => {
    setNote(question?.note || '')
  }, [question?.id, question?.note])

  if (!question) return null

  const footer = (
    <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <Button
        danger
        disabled={question.status === 'rejected'}
        onClick={() => onReject(question.id, note.trim())}
      >
        驳回
      </Button>
      <Button
        type="primary"
        disabled={question.status === 'approved'}
        onClick={() => onApprove(question.id)}
      >
        通过审核
      </Button>
    </Space>
  )

  return (
    <Drawer
      title="题目审核"
      width={560}
      open={open}
      onClose={onClose}
      footer={footer}
      destroyOnClose
    >
      <Space direction="vertical" size={18} style={{ width: '100%' }}>
        <Space wrap>
          <StatusTag kind="question" status={question.status} />
          <Tag color={DIFFICULTY_COLORS[question.difficulty]}>
            {DIFFICULTY_LABELS[question.difficulty]}
          </Tag>
          <Tag>{TYPE_LABELS[question.type]}</Tag>
          <Typography.Text type="secondary">{question.bank}</Typography.Text>
        </Space>

        <Typography.Title level={4} style={{ margin: 0, lineHeight: 1.55 }}>
          {question.stem}
        </Typography.Title>

        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {question.options.map((option) => {
            const correct = question.answer.includes(option.key)
            return (
              <div key={option.key} className={`question-option ${correct ? 'is-correct' : ''}`}>
                <span className="question-option-key">{option.key}</span>
                <span>{option.text}</span>
                {correct ? <Tag color="success">正确答案</Tag> : null}
              </div>
            )
          })}
        </Space>

        <div>
          <Typography.Text strong>解析</Typography.Text>
          <div className="question-explanation">{question.explanation}</div>
        </div>

        <div className="question-source">
          <Typography.Text type="secondary">来源</Typography.Text>
          <div>{question.source}</div>
        </div>

        {question.status !== 'approved' ? (
          <div>
            <Typography.Text strong>审核意见</Typography.Text>
            <Input.TextArea
              style={{ marginTop: 8 }}
              rows={2}
              maxLength={500}
              showCount
              value={note}
              placeholder="驳回时建议填写原因，例如：答案解析与原文不一致"
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
        ) : null}

        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="知识点">{question.knowledgePoint}</Descriptions.Item>
          <Descriptions.Item label="AI 生成">{question.aiMeta}</Descriptions.Item>
          <Descriptions.Item label="审核状态">
            <StatusTag kind="question" status={question.status} />
          </Descriptions.Item>
          {question.note ? <Descriptions.Item label="驳回原因">{question.note}</Descriptions.Item> : null}
        </Descriptions>

        {question.status === 'rejected' && question.note ? (
          <Alert type="warning" showIcon message="该题未通过审核" description={question.note} />
        ) : null}
      </Space>
    </Drawer>
  )
}
