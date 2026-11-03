import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  clearEmployeeAuth,
  getEmployeeToken,
  getEmployeeUser,
  listEmployeeExams,
  type EmployeeExamItem,
} from '../../services/api'
import './index.scss'

export default function EmployeeExamsPage() {
  const [exams, setExams] = useState<EmployeeExamItem[]>([])
  const [loading, setLoading] = useState(false)
  const employee = getEmployeeUser()

  const loadExams = async () => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    setLoading(true)
    try {
      const data = await listEmployeeExams()
      setExams(data.items)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '考试加载失败', icon: 'none' })
      if (!getEmployeeToken()) {
        Taro.redirectTo({ url: '/pages/employee-login/index' })
      }
    } finally {
      setLoading(false)
    }
  }

  useDidShow(() => {
    loadExams()
  })

  const openExam = (exam: EmployeeExamItem) => {
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

  const handleLogout = () => {
    clearEmployeeAuth()
    Taro.redirectTo({ url: '/pages/employee-login/index' })
  }

  return (
    <View className='employee-exams-page'>
      <View className='employee-exams-header'>
        <View>
          <Text className='employee-hello'>你好，{employee?.name || '同学'}</Text>
          <Text className='employee-org'>{employee?.org_path || '企业培训'}</Text>
        </View>
        <View className='employee-header-actions'>
          <Text
            className='employee-header-link'
            onClick={() => Taro.navigateTo({ url: '/pages/employee-wrong/index' })}
          >
            错题重练
          </Text>
          <Text className='employee-logout' onClick={handleLogout}>退出</Text>
        </View>
      </View>

      <Text className='employee-section-title'>我的考试</Text>

      {loading && exams.length === 0 ? (
        <View className='employee-empty'><Text>加载中...</Text></View>
      ) : exams.length === 0 ? (
        <View className='employee-empty'>
          <Text className='employee-empty-icon'>📭</Text>
          <Text>暂无待办考试</Text>
        </View>
      ) : (
        <View className='employee-exam-list'>
          {exams.map((exam) => {
            const submitted = exam.attempt_status === 'submitted'
            const inProgress = exam.attempt_status === 'in_progress'
            const closed = exam.status === 'closed'
            const actionText = submitted
              ? '查看成绩'
              : inProgress
                ? '继续答题'
                : closed
                  ? '已结束'
                  : '开始考试'
            return (
              <View key={exam.id} className='employee-exam-card'>
                <View className='employee-exam-top'>
                  <Text className='employee-exam-title'>{exam.title}</Text>
                  <Text className={`employee-exam-status ${closed ? 'is-closed' : ''}`}>
                    {closed ? '已结束' : submitted ? '已完成' : inProgress ? '进行中' : '待完成'}
                  </Text>
                </View>
                <Text className='employee-exam-meta'>
                  {exam.question_count} 题 · {exam.duration_minutes} 分钟 · 及格 {exam.pass_score} 分
                </Text>
                {exam.end_at && (
                  <Text className='employee-exam-meta'>截止：{exam.end_at}</Text>
                )}
                {submitted && exam.score != null && (
                  <Text className={`employee-exam-score ${exam.passed ? 'is-pass' : 'is-fail'}`}>
                    得分 {exam.score} · {exam.passed ? '已通过' : '未通过'}
                  </Text>
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
                    closed && !submitted && !inProgress ? 'is-disabled' : ''
                  }`}
                  onClick={() => {
                    if (closed && !submitted && !inProgress) return
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
  )
}
