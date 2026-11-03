import { App as AntApp, Button, Card, Col, Empty, Progress, Row, Space, Spin, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import EditKnowledgeCardModal from '../components/EditKnowledgeCardModal'
import GenerateCardsModal from '../components/GenerateCardsModal'
import PageHeader from '../components/PageHeader'
import StatusTag from '../components/StatusTag'
import {
  getToken,
  listKnowledgeCards,
  updateKnowledgeCardStatus,
  type AdminKnowledgeCard,
} from '../services/api'

export default function CardsPage() {
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const [cards, setCards] = useState<AdminKnowledgeCard[]>([])
  const [loading, setLoading] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [editingCardId, setEditingCardId] = useState<number | null>(null)

  const handleError = useCallback(
    (error: unknown) => {
      message.error(error instanceof Error ? error.message : '知识卡请求失败')
      if (!getToken()) navigate('/login', { replace: true })
    },
    [message, navigate],
  )

  const loadCards = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listKnowledgeCards({ page_size: 100 })
      setCards(data.items)
    } catch (error) {
      handleError(error)
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    void loadCards()
  }, [loadCards])

  const handleStatus = async (card: AdminKnowledgeCard) => {
    const nextStatus = card.status === 'published' ? 'offline' : 'published'
    try {
      await updateKnowledgeCardStatus(card.id, nextStatus)
      message.success(
        nextStatus === 'published'
          ? `知识卡「${card.title}」已发布`
          : `知识卡「${card.title}」已下线`,
      )
      await loadCards()
    } catch (error) {
      handleError(error)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="KNOWLEDGE CARDS"
        title="知识卡"
        description="考前速览卡片，3–5 张一组。发布后才能关联考试，员工端会记录阅读率。"
        extra={
          <Space>
            <Button onClick={() => message.info('知识卡模板待接入（骨架）')}>查看模板</Button>
            <Button type="primary" onClick={() => setGenerateOpen(true)}>
              生成知识卡
            </Button>
          </Space>
        }
      />

      <Spin spinning={loading}>
        {cards.length ? (
          <Row gutter={[12, 12]}>
            {cards.map((card) => (
              <Col key={card.id} xs={24} xl={12}>
                <Card
                  className="panel-card knowledge-card"
                  title={<Typography.Text strong>{card.title}</Typography.Text>}
                  extra={<StatusTag kind="card" status={card.status} />}
                >
                  <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                    {card.excerpt}
                  </Typography.Paragraph>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    来源：{card.source} · 更新：{card.updated_at}
                  </Typography.Text>

                  <div className="knowledge-read-row">
                    <Typography.Text type="secondary">阅读率 {card.view_rate}%</Typography.Text>
                    <Progress
                      percent={card.view_rate}
                      showInfo={false}
                      size="small"
                      strokeColor="var(--admin-accent)"
                    />
                  </div>

                  <Space wrap>
                    <Button size="small" onClick={() => setEditingCardId(card.id)}>
                      编辑
                    </Button>
                    {card.status === 'published' ? (
                      <Button size="small" onClick={() => handleStatus(card)}>
                        下线
                      </Button>
                    ) : card.status === 'draft' ? (
                      <Button size="small" type="primary" onClick={() => handleStatus(card)}>
                        审核发布
                      </Button>
                    ) : (
                      <Button size="small" onClick={() => handleStatus(card)}>
                        重新发布
                      </Button>
                    )}
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Card className="panel-card">
            <Empty description="暂无知识卡，点击右上角生成" />
          </Card>
        )}
      </Spin>

      <GenerateCardsModal
        open={generateOpen}
        onCancel={() => setGenerateOpen(false)}
        onSuccess={loadCards}
      />

      <EditKnowledgeCardModal
        open={editingCardId !== null}
        cardId={editingCardId}
        onCancel={() => setEditingCardId(null)}
        onSuccess={loadCards}
      />
    </>
  )
}
