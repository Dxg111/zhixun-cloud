import { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidHide, useRouter } from '@tarojs/taro'
import {
  getEmployeeToken,
  saveEmployeeAnswers,
  startEmployeeExam,
  submitEmployeeExam,
  type EmployeeAnswerInput,
  type EmployeePaperResponse,
  type PaperQuestion,
} from '../../services/api'
import './index.scss'

function buildPayload(
  questions: PaperQuestion[],
  answers: Record<number, string[]>,
): EmployeeAnswerInput[] {
  return questions.map((question) => ({
    question_id: question.id,
    selected: answers[question.id] || [],
    duration_ms: 0,
  }))
}

function formatRemaining(seconds: number) {
  if (seconds <= 0) return '已超时'
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

export default function EmployeeExamPage() {
  const router = useRouter()
  const examId = Number(router.params.examId || 0)
  const [paper, setPaper] = useState<EmployeePaperResponse | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<number, string[]>>({})
  const [loading, setLoading] = useState(true)
  const [remaining, setRemaining] = useState(0)

  const answersRef = useRef<Record<number, string[]>>({})
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const submittedRef = useRef(false)

  const questions = paper?.questions || []
  const currentQuestion = questions[currentIndex]
  const progress = questions.length ? ((currentIndex + 1) / questions.length) * 100 : 0

  const loadPaper = async () => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    setLoading(true)
    try {
      const data = await startEmployeeExam(examId)
      setPaper(data)
      const restored: Record<number, string[]> = {}
      data.saved_answers.forEach((answer) => {
        restored[answer.question_id] = answer.selected
      })
      answersRef.current = restored
      setAnswers(restored)
      Taro.setNavigationBarTitle({ title: data.title.slice(0, 10) })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '考试加载失败', icon: 'none' })
      setTimeout(() => Taro.navigateBack(), 800)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPaper()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId])

  const flushSave = () => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    if (!paper?.attempt_id || submittedRef.current) return
    saveEmployeeAnswers(
      paper.attempt_id,
      buildPayload(questions, answersRef.current),
    ).catch(() => {})
  }

  useDidHide(() => {
    flushSave()
  })

  const doSubmit = async (auto: boolean) => {
    if (!paper || submittedRef.current) return
    submittedRef.current = true
    if (saveTimer.current) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    Taro.showLoading({ title: auto ? '自动交卷中...' : '判分中...' })
    try {
      const result = await submitEmployeeExam(
        paper.attempt_id,
        buildPayload(questions, answersRef.current),
      )
      Taro.redirectTo({
        url: `/pages/employee-result/index?attemptId=${result.attempt_id}`,
      })
    } catch (error: any) {
      submittedRef.current = false
      Taro.showToast({ title: error?.message || '提交失败', icon: 'none' })
    } finally {
      Taro.hideLoading()
    }
  }

  useEffect(() => {
    if (!paper?.expires_at) return
    const expireAt = new Date(paper.expires_at.replace(/-/g, '/')).getTime()
    const tick = () => {
      const left = Math.max(0, Math.floor((expireAt - Date.now()) / 1000))
      setRemaining(left)
      if (left <= 0 && !submittedRef.current) {
        void doSubmit(true)
      }
    }
    tick()
    const timer = setInterval(tick, 1000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paper?.expires_at, paper?.attempt_id])

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    }
  }, [])

  const persistAnswers = (nextAnswers: Record<number, string[]>) => {
    answersRef.current = nextAnswers
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      saveTimer.current = null
      if (!paper?.attempt_id || submittedRef.current) return
      saveEmployeeAnswers(
        paper.attempt_id,
        buildPayload(questions, answersRef.current),
      ).catch(() => {})
    }, 500)
  }

  const handleOptionClick = (key: string) => {
    if (!currentQuestion || remaining <= 0 || submittedRef.current) return
    const existing = answersRef.current[currentQuestion.id] || []
    const selected =
      currentQuestion.type === 'multiple'
        ? existing.includes(key)
          ? existing.filter((item) => item !== key)
          : [...existing, key]
        : [key]

    const nextAnswers = { ...answersRef.current, [currentQuestion.id]: selected }
    setAnswers(nextAnswers)
    persistAnswers(nextAnswers)
  }

  const handleSubmit = () => {
    if (!paper) return
    const unanswered = questions.filter(
      (question) => !(answersRef.current[question.id] || []).length,
    ).length
    Taro.showModal({
      title: '提交答卷',
      content: unanswered
        ? `还有 ${unanswered} 题未作答，提交后不能修改，确定提交吗？`
        : '提交后不能修改，确定提交吗？',
      success: (res) => {
        if (res.confirm) {
          void doSubmit(false)
        }
      },
    })
  }

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((index) => index + 1)
    } else {
      handleSubmit()
    }
  }

  const selected = useMemo(
    () => (currentQuestion ? answers[currentQuestion.id] || [] : []),
    [answers, currentQuestion],
  )

  if (loading) {
    return (
      <View className='employee-exam-page'>
        <View className='employee-exam-empty'><Text>正在加载试卷...</Text></View>
      </View>
    )
  }

  if (!paper || !currentQuestion) {
    return (
      <View className='employee-exam-page'>
        <View className='employee-exam-empty'><Text>试卷加载失败</Text></View>
      </View>
    )
  }

  return (
    <View className='employee-exam-page'>
      <View
        className='employee-exam-cards-link'
        onClick={() => {
          flushSave()
          Taro.navigateTo({
            url: `/pages/employee-cards/index?examId=${examId}&fromExam=1`,
          })
        }}
      >
        <Text>📚 考前速览</Text>
      </View>

      <View className='employee-exam-head'>
        <Text className='employee-exam-progress-text'>
          第 {currentIndex + 1} / {questions.length} 题
        </Text>
        <Text className={`employee-exam-timer ${remaining <= 60 ? 'is-warning' : ''}`}>
          {formatRemaining(remaining)}
        </Text>
      </View>

      <View className='employee-progress-track'>
        <View className='employee-progress-fill' style={{ width: `${progress}%` }} />
      </View>

      <View className='employee-question-card'>
        <Text className='employee-question-type'>
          {currentQuestion.type === 'single'
            ? '单选题'
            : currentQuestion.type === 'multiple'
              ? '多选题'
              : '判断题'}
        </Text>
        <Text className='employee-question-stem'>{currentQuestion.stem}</Text>

        <View className='employee-option-list'>
          {currentQuestion.options.map((option) => (
            <View
              key={option.key}
              className={`employee-option ${selected.includes(option.key) ? 'is-selected' : ''}`}
              onClick={() => handleOptionClick(option.key)}
            >
              <Text className='employee-option-key'>{option.key}</Text>
              <Text className='employee-option-text'>{option.text}</Text>
            </View>
          ))}
        </View>
      </View>

      <View className='employee-exam-actions'>
        {currentIndex > 0 && (
          <View
            className='employee-secondary-btn'
            onClick={() => setCurrentIndex((index) => index - 1)}
          >
            <Text>上一题</Text>
          </View>
        )}
        <View
          className={`employee-primary-action ${selected.length === 0 ? 'is-disabled' : ''}`}
          onClick={() => {
            if (!selected.length) {
              Taro.showToast({ title: '请先选择答案', icon: 'none' })
              return
            }
            handleNext()
          }}
        >
          <Text>{currentIndex < questions.length - 1 ? '下一题' : '提交答卷'}</Text>
        </View>
      </View>
    </View>
  )
}
