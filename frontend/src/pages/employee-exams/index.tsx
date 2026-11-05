import { useCallback, useEffect, useRef, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidHide, useDidShow, usePullDownRefresh } from '@tarojs/taro'
import {
  getEmployeeToken,
  getEmployeeUser,
  listEmployeeExams,
  markNotificationsReadByBiz,
  markNotificationsReadByExamIds,
  type EmployeeExamItem,
} from '../../services/api'
import { refreshNotificationSummary } from '../../services/notification'
import './index.scss'

export default function EmployeeExamsPage() {
  const [exams, setExams] = useState<EmployeeExamItem[]>([])
  const [unreadExamIds, setUnreadExamIds] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const employee = getEmployeeUser()

  const loadUnread = useCallback(async (autoRead = false) => {
    const summary = await refreshNotificationSummary()
    const unreadIds = summary?.unread_exam_ids ?? []
    setUnreadExamIds(unreadIds)

    // 进入列表即视为已知悉这些考试提醒：清除角标，下次进入不再显示「新」
    // 当前这一次仍保留标签，让用户看清哪几场是新指派的
    if (autoRead && unreadIds.length > 0) {
      try {
        await markNotificationsReadByExamIds(unreadIds)
        await refreshNotificationSummary()
      } catch {
        // 标记失败不阻断列表展示，下次进入会重试
      }
    }
  }, [])

  const loadExams = useCallback(async () => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    setLoading(true)
    try {
      const data = await listEmployeeExams()
      setExams(data.items)
      await loadUnread(true)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '考试加载失败', icon: 'none' })
      if (!getEmployeeToken()) {
        Taro.redirectTo({ url: '/pages/employee-login/index' })
      }
    } finally {
      setLoading(false)
    }
  }, [loadUnread])

  const refreshUnread = useCallback(() => {
    loadUnread().catch(() => {})
  }, [loadUnread])

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current)
      pollTimer.current = null
    }
  }, [])

  useEffect(() => () => stopPolling(), [stopPolling])

  useDidShow(() => {
    loadExams()
    // 停留在列表页时只轮询轻量未读接口，发现新指派立即打「新」标签
    stopPolling()
    pollTimer.current = setInterval(refreshUnread, 60000)
  })

  useDidHide(() => {
    stopPolling()
  })

  usePullDownRefresh(async () => {
    await loadExams()
    Taro.stopPullDownRefresh()
  })

  const markExamRead = async (examId: number) => {
    if (!unreadExamIds.includes(examId)) return
    try {
      await markNotificationsReadByBiz('exam', examId)
    } catch {
      // 已读失败不阻断进入考试
    }
    setUnreadExamIds((prev) => prev.filter((id) => id !== examId))
    await refreshNotificationSummary()
  }

  const openExam = (exam: EmployeeExamItem) => {
    void markExamRead(exam.id)
    if (exam.attempt_status === 'submitted' && exam.attempt_id) {
      Taro.navigateTo({ url: `/pages/employee-result/index?attemptId=${exam.attempt_id}` })
      return
    }
    Taro.navigateTo({ url: `/pages/employee-exam/index?examId=${exam.id}` })
  }

  const canRetake = (exam: EmployeeExamItem) => {
    if (exam.status !== 'published' || exam.attempt_status !== 'submitted') return false
    if (exam.attempt_count >= exam.max_attempts) return false
    const now = Date.now()
    if (exam.start_at && new Date(exam.start_at.replace(/-/g, '/')).getTime() > now) {
      return false
    }
    if (exam.end_at && new Date(exam.end_at.replace(/-/g, '/')).getTime() < now) {
      return false
    }
    return true
  }

  const openCards = (exam: EmployeeExamItem) => {
    Taro.navigateTo({ url: `/pages/employee-cards/index?examId=${exam.id}` })
  }

  const handleBackHome = () => {
    Taro.switchTab({ url: '/pages/index/index' })
  }

  const pendingCount = exams.filter(
    (exam) => exam.computed_state === 'pending' || exam.computed_state === 'in_progress',
  ).length
  const completedCount = exams.filter((exam) => exam.computed_state === 'done').length

  return (
    <View className='employee-exams-page paper-bg'>
      <View className='employee-exams-header'>
        <View className='employee-header-top'>
          <View className='employee-header-identity'>
            <Text className='employee-hello'>{employee?.name || '同学'}</Text>
            <Text className='employee-org'>{employee?.org_path || '企业培训中心'}</Text>
          </View>
          <View className='employee-header-actions'>
            <View
              className='employee-header-link'
              onClick={() => Taro.navigateTo({ url: '/pages/employee-wrong/index' })}
            >
              <Text>错题重练</Text>
            </View>
            <Text className='employee-logout' onClick={handleBackHome}>首页</Text>
          </View>
        </View>

        <View className='employee-summary'>
          <View className='employee-summary-item'>
            <Text className='employee-summary-num num'>{pendingCount}</Text>
            <Text className='employee-summary-label'>待完成</Text>
          </View>
          <View className='employee-summary-divider' />
          <View className='employee-summary-item'>
            <Text className='employee-summary-num num'>{completedCount}</Text>
            <Text className='employee-summary-label'>已完成</Text>
          </View>
          <View className='employee-summary-divider' />
          <View className='employee-summary-item'>
            <Text className='employee-summary-num num'>{exams.length}</Text>
            <Text className='employee-summary-label'>全部考试</Text>
          </View>
        </View>
      </View>

      <View className='employee-exams-body'>
        <View className='employee-section-head'>
          <Text className='employee-section-title'>我的考试</Text>
          <Text className='employee-section-note'>按截止时间优先完成</Text>
        </View>

        {loading && exams.length === 0 ? (
          <View className='employee-empty'><Text>加载中...</Text></View>
        ) : exams.length === 0 ? (
          <View className='employee-empty'>
            <View className='employee-empty-mark'>—</View>
            <Text>暂无待办考试</Text>
          </View>
        ) : (
        <View className='employee-exam-list'>
          {exams.map((exam) => {
            const submitted = exam.computed_state === 'done'
            const inProgress = exam.computed_state === 'in_progress'
            const expired = exam.computed_state === 'expired'
            const actionText = submitted
              ? '查看成绩'
              : inProgress
                ? '继续答题'
                : expired
                  ? '已截止'
                  : '开始考试'
            return (
              <View
                key={exam.id}
                className={`employee-exam-card ${
                  submitted ? 'is-done' : inProgress ? 'is-progress' : ''
                }`}
              >
                <View className='employee-exam-top'>
                  <View className='employee-exam-title-row'>
                    {unreadExamIds.includes(exam.id) && !submitted && (
                      <Text className='employee-exam-new'>新</Text>
                    )}
                    <Text className='employee-exam-title'>{exam.title}</Text>
                  </View>
                  <Text
                    className={`employee-exam-status ${
                      expired ? 'is-closed' : submitted ? 'is-done' : inProgress ? 'is-progress' : ''
                    }`}
                  >
                    {expired ? '已截止' : submitted ? '已完成' : inProgress ? '进行中' : '待完成'}
                  </Text>
                </View>
                <View className='employee-exam-meta-row'>
                  <Text className='employee-exam-meta'>{exam.question_count} 题</Text>
                  <Text className='employee-exam-meta'>{exam.duration_minutes} 分钟</Text>
                  <Text className='employee-exam-meta'>及格 {exam.pass_score} 分</Text>
                </View>
                {exam.end_at && (
                  <View className='employee-exam-deadline'>
                    <Text>截止时间：{exam.end_at}</Text>
                  </View>
                )}
                {submitted && exam.score != null && (
                  <View className='employee-exam-score-row'>
                    <Text className='employee-exam-score-num num'>{exam.score}</Text>
                    <Text className='employee-exam-score-unit'>分</Text>
                    <Text
                      className={`employee-exam-pass ${exam.passed ? 'is-pass' : 'is-fail'}`}
                    >
                      {exam.passed ? '已通过' : '未通过'}
                    </Text>
                  </View>
                )}
                <View className='employee-exam-secondary-actions'>
                  <View className='employee-exam-secondary' onClick={() => openCards(exam)}>
                    <Text>考前速览</Text>
                  </View>
                  {canRetake(exam) && (
                    <View
                      className='employee-exam-secondary'
                      onClick={() =>
                        Taro.navigateTo({
                          url: `/pages/employee-exam/index?examId=${exam.id}`,
                        })
                      }
                    >
                      <Text>再考一次</Text>
                    </View>
                  )}
                </View>
                <View
                  className={`employee-exam-action ${
                    expired && !submitted && !inProgress ? 'is-disabled' : ''
                  }`}
                  onClick={() => {
                    if (expired && !submitted && !inProgress) return
                    openExam(exam)
                  }}
                >
                  <Text>{actionText}</Text>
                </View>
              </View>
            )
          })}
        </View>
        )}
      </View>
    </View>
  )
}
