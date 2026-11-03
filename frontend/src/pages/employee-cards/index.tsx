import { useEffect, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import {
  getEmployeeToken,
  listEmployeeExamCards,
  recordEmployeeCardView,
  type EmployeeCardItem,
} from '../../services/api'
import './index.scss'

export default function EmployeeCardsPage() {
  const router = useRouter()
  const examId = Number(router.params.examId || 0)
  const fromExam = router.params.fromExam === '1'
  const [cards, setCards] = useState<EmployeeCardItem[]>([])
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    if (!examId) {
      setLoading(false)
      return
    }
    listEmployeeExamCards(examId)
      .then((data) => setCards(data.items))
      .catch((error: any) => {
        Taro.showToast({ title: error?.message || '知识卡加载失败', icon: 'none' })
      })
      .finally(() => setLoading(false))
  }, [examId])

  const toggleCard = (card: EmployeeCardItem) => {
    const nextId = expandedId === card.id ? null : card.id
    setExpandedId(nextId)
    if (nextId === null || card.viewed) return

    recordEmployeeCardView(card.id)
      .then(() => {
        setCards((prev) =>
          prev.map((item) =>
            item.id === card.id
              ? { ...item, viewed: true, view_count: item.view_count + 1 }
              : item,
          ),
        )
      })
      .catch(() => {})
  }

  const handleStart = () => {
    if (fromExam) {
      Taro.navigateBack()
      return
    }
    Taro.redirectTo({ url: `/pages/employee-exam/index?examId=${examId}` })
  }

  return (
    <View className='employee-cards-page paper-bg'>
      <View className='employee-cards-hero'>
        <Text className='employee-cards-kicker'>考前资料</Text>
        <Text className='employee-cards-title'>考前速览</Text>
        <Text className='employee-cards-desc'>
          3–5 张知识卡，3 分钟读完。点击卡片展开要点，阅读状态会同步给管理员。
        </Text>
        {cards.length > 0 && (
          <View className='employee-cards-progress'>
            <Text className='employee-cards-progress-text'>
              已阅读 {cards.filter((card) => card.viewed).length} / {cards.length} 张
            </Text>
            <View className='employee-cards-progress-track'>
              <View
                className='employee-cards-progress-fill'
                style={{
                  width: `${(cards.filter((card) => card.viewed).length / cards.length) * 100}%`,
                }}
              />
            </View>
          </View>
        )}
      </View>

      {loading ? (
        <View className='employee-cards-empty'><Text>正在加载知识卡...</Text></View>
      ) : cards.length === 0 ? (
        <View className='employee-cards-empty'>
          <View className='employee-cards-empty-mark'>—</View>
          <Text>本场考试暂未配置知识卡</Text>
        </View>
      ) : (
        <View className='employee-cards-list'>
          {cards.map((card) => {
            const expanded = expandedId === card.id
            return (
              <View key={card.id} className='employee-card-item'>
                <View className='employee-card-head' onClick={() => toggleCard(card)}>
                  <View className='employee-card-title-wrap'>
                    <Text className='employee-card-title'>{card.title}</Text>
                    <Text className={`employee-card-read-tag ${card.viewed ? 'is-read' : ''}`}>
                      {card.viewed ? '已读' : '未读'}
                    </Text>
                  </View>
                  <Text className='employee-card-toggle'>{expanded ? '收起' : '展开'}</Text>
                </View>

                <Text className='employee-card-excerpt'>{card.excerpt}</Text>
                <Text className='employee-card-source'>来源：{card.source}</Text>

                {expanded && (
                  <View className='employee-card-content'>
                    {card.points.length ? (
                      card.points.map((point, index) => (
                        <View key={`${point.heading}-${index}`} className='employee-card-point'>
                          <Text className='employee-card-point-heading'>{point.heading}</Text>
                          <Text className='employee-card-point-body'>{point.body}</Text>
                        </View>
                      ))
                    ) : (
                      <Text className='employee-card-point-body'>{card.excerpt}</Text>
                    )}
                  </View>
                )}
              </View>
            )
          })}
        </View>
      )}

      <View className='employee-cards-action' onClick={handleStart}>
        <Text>{fromExam ? '返回考试' : '开始考试'}</Text>
      </View>
    </View>
  )
}
