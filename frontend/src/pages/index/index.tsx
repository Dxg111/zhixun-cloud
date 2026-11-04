import { useState, useEffect, useCallback, useRef } from 'react'
import { View, Text, Textarea, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  generateQuizAsync,
  pollQuizTask,
  getCachedUser,
  getQuizHistory,
  waitForLogin,
  getEmployeeToken,
  getEmployeeUser,
  getUsableAvatarUrl,
  listEmployeeExams,
} from '../../services/api'
import type { UserBrief, QuizHistoryItem } from '../../services/api'
import './index.scss'

export default function IndexPage() {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('生成中...')
  const [generateImages, setGenerateImages] = useState(false)
  const [user, setUser] = useState<UserBrief | null>(null)
  const [historyItems, setHistoryItems] = useState<QuizHistoryItem[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [employeePending, setEmployeePending] = useState<number | null>(null)
  const didShowRef = useRef(false)

  const loadEmployeePending = useCallback(() => {
    if (!getEmployeeToken()) {
      setEmployeePending(null)
      return
    }
    listEmployeeExams()
      .then((res) => {
        const pending = res.items.filter(
          (item) => item.status !== 'closed' && item.attempt_status !== 'submitted',
        )
        setEmployeePending(pending.length)
      })
      .catch(() => setEmployeePending(null))
  }, [])

  const loadData = useCallback(async () => {
    await waitForLogin()
    const cached = getCachedUser()
    if (cached) setUser(cached)

    getQuizHistory(1, 4)
      .then((res) => {
        setHistoryItems(res.items)
        setHistoryTotal(res.total)
      })
      .catch(() => {})
    loadEmployeePending()
  }, [loadEmployeePending])

  useEffect(() => { loadData() }, [loadData])

  // 每次页面显示时刷新（从其他页面返回后）。首次显示由 useEffect 负责，避免登录完成前抢先请求。
  useDidShow(() => {
    if (!didShowRef.current) {
      didShowRef.current = true
      return
    }
    void loadData()
  })

  const handleGenerate = async () => {
    const trimmed = inputValue.trim()
    if (!trimmed) {
      Taro.showToast({ title: '请输入学习内容', icon: 'none' })
      return
    }

    setLoading(true)
    setLoadingText('正在创建任务...')
    try {
      // 1. 创建异步任务（秒级返回）
      const { task_id } = await generateQuizAsync(trimmed, 5, undefined, generateImages)

      setLoadingText('AI 正在联网搜索并生成题目...')

      // 2. 轮询等待任务完成
      const quizData = await pollQuizTask(task_id, (status) => {
        if (status === 'running') setLoadingText('AI 正在生成题目...')
      })

      // 若配图有提示（如未登录/额度不足），友好告知，不阻断闯关
      if (quizData.image_notice) {
        Taro.showToast({ title: quizData.image_notice, icon: 'none', duration: 3000 })
      }

      // 3. 跳转闯关页
      Taro.navigateTo({
        url: `/pages/quiz/index?quizData=${encodeURIComponent(JSON.stringify(quizData))}`,
      })
    } catch (err: any) {
      Taro.showToast({ title: err.message || '生成失败，请稍后重试', icon: 'none' })
    } finally {
      setLoading(false)
      setLoadingText('生成中...')
    }
  }

  const avatarUrl = getUsableAvatarUrl(user?.avatar_url)
  const employeeUser = getEmployeeUser()
  const displayName = employeeUser?.name || user?.nickname || '同学'
  const displayOrg = employeeUser?.org_path || '企业学习中心'

  return (
    <View className='index-page paper-bg'>
      {/* 顶部账号栏 */}
      <View className='toolbar'>
        <View className='hello-user'>
          {avatarUrl ? (
            <Image className='hello-avatar-img' src={avatarUrl} mode='aspectFill' />
          ) : (
            <View className='hello-avatar'>
              <Text>{displayName[0] || '智'}</Text>
            </View>
          )}
          <View className='hello-body'>
            <Text className='hello-name'>{displayName}</Text>
            <Text className='hello-org'>{displayOrg}</Text>
          </View>
        </View>
        <View className='coin-badge'>
          <Text className='coin-text num'>{user?.total_xp ?? 0}</Text>
          <Text className='coin-unit'>XP</Text>
        </View>
      </View>

      {/* 企业培训入口 */}
      <View
        className='enterprise-entry'
        onClick={() => {
          const url = getEmployeeToken()
            ? '/pages/employee-exams/index'
            : '/pages/employee-login/index'
          Taro.navigateTo({ url })
        }}
      >
        <View className='enterprise-entry-main'>
          <View className='enterprise-entry-mark'>企</View>
          <View className='enterprise-entry-body'>
            <View className='enterprise-entry-title-row'>
              <Text className='enterprise-entry-title'>企业培训</Text>
              {employeePending !== null && employeePending > 0 && (
                <Text className='enterprise-entry-badge'>{employeePending} 项待办</Text>
              )}
            </View>
            <Text className='enterprise-entry-desc'>
              {employeePending === null
                ? '登录后查看待办考试与考前知识卡'
                : employeePending > 0
                  ? '有考试待完成，先读知识卡再进入考试'
                  : '暂无待办考试，可查看错题与知识卡'}
            </Text>
          </View>
        </View>
        <Text className='enterprise-entry-arrow'>›</Text>
      </View>

      {/* 标题 */}
      <View className='home-heading'>
        <Text className='page-title'>每日随问</Text>
        <Text className='home-subtitle'>输入主题，生成 5 道闯关题</Text>
      </View>

      {/* 输入区域 */}
      <View className='quick-input'>
        <View className='input-head'>
          <Text className='input-label'>学习主题</Text>
          <Text className='input-hint'>知识点 / 业务问题 / 文档主题</Text>
        </View>
        <Textarea
          className='input-area'
          placeholder={'例如：RAG 和传统搜索有什么区别？\n我想搞懂向量数据库是怎么配合工作的。\n最好通过闯关题帮我记住重点。'}
          value={inputValue}
          onInput={(e) => setInputValue(e.detail.value)}
          maxlength={500}
          autoHeight
        />
        <View
          className={`image-toggle-row ${generateImages ? 'is-active' : ''}`}
          onClick={() => setGenerateImages((prev) => !prev)}
        >
          <View className='image-toggle-info'>
            <Text className='image-toggle-label'>为题目生成配图</Text>
            <Text className='image-toggle-desc'>开启后生成时间会略有增加</Text>
          </View>
          <View className={`toggle-pill ${generateImages ? 'is-on' : ''}`}>
            <View className='toggle-knob' />
          </View>
        </View>
        <View
          className={`btn-primary generate-btn ${loading ? 'is-loading' : ''}`}
          onClick={!loading ? handleGenerate : undefined}
        >
          {loading ? <Text>{loadingText}</Text> : <Text>生成题目</Text>}
        </View>
      </View>

      {/* 最近学习 */}
      <View className='history-section'>
        <View className='section-head'>
          <Text className='section-title'>最近学习</Text>
          <Text
            className='section-more'
            onClick={() => Taro.switchTab({ url: '/pages/profile/index' })}
          >
            全部记录
          </Text>
        </View>
        {historyItems.length === 0 ? (
          <View className='recent-empty'>
            <Text>还没有学习记录，先在上面生成一组题目</Text>
          </View>
        ) : (
          <View className='recent-grid'>
            {historyItems.map((item) => (
              <View
                key={item.quiz_id}
                className='recent'
                onClick={() => {
                  Taro.navigateTo({
                    url: `/pages/report/index?quizId=${item.quiz_id}`,
                  })
                }}
              >
                <Text className='recent-title'>{item.title}</Text>
                <Text className='recent-accuracy num'>{Math.round(item.accuracy)}%</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* 学习概览 */}
      <View className='mini-stats'>
        <View className='mini-stat'>
          <Text className='mini-stat-value num'>{historyTotal}</Text>
          <Text className='mini-stat-label'>累计闯关</Text>
        </View>
        <View className='mini-stat'>
          <Text className='mini-stat-value num'>{user?.total_xp ?? 0}</Text>
          <Text className='mini-stat-label'>经验值</Text>
        </View>
      </View>
    </View>
  )
}
