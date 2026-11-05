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
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [cardOpen, setCardOpen] = useState(false)

  const answersRef = useRef<Record<number, string[]>>({})
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const submittedRef = useRef(false)
  const saveSeq = useRef(0)

  const questions = paper?.questions || []
  const currentQuestion = questions[currentIndex]
  const stationCount = 10
  const currentStation = Math.min(
    stationCount - 1,
    Math.floor((currentIndex / Math.max(1, questions.length)) * stationCount),
  )

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

  const persist = (attemptId: number) => {
    const seq = ++saveSeq.current
    setSaveState('saving')
    saveEmployeeAnswers(attemptId, buildPayload(questions, answersRef.current))
      .then(() => {
        if (seq === saveSeq.current) setSaveState('saved')
      })
      .catch(() => {
        if (seq === saveSeq.current) setSaveState('error')
      })
  }

  const flushSave = () => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    if (!paper?.attempt_id || submittedRef.current) return
    persist(paper.attempt_id)
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
      persist(paper.attempt_id)
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

  const answeredCount = useMemo(
    () => questions.filter((question) => (answers[question.id] || []).length > 0).length,
    [answers, questions],
  )

  if (loading) {
    return (
      <View className='employee-exam-page paper-bg'>
        <View className='employee-exam-empty'><Text>正在加载试卷...</Text></View>
      </View>
    )
  }

  if (!paper || !currentQuestion) {
    return (
      <View className='employee-exam-page paper-bg'>
        <View className='employee-exam-empty'><Text>试卷加载失败</Text></View>
      </View>
    )
  }

  return (
    <View className='employee-exam-page paper-bg'>
      <View
        className='employee-exam-cards-link'
        onClick={() => {
          flushSave()
          Taro.navigateTo({
            url: `/pages/employee-cards/index?examId=${examId}&fromExam=1`,
          })
        }}
      >
        <Text>考前速览</Text>
        <Text className='employee-exam-cards-arrow'>›</Text>
      </View>

      <View className='employee-exam-head'>
        <View className='employee-exam-head-left'>
          <Text className='employee-exam-kicker'>答题进度</Text>
          <Text className='employee-exam-progress-text'>
            第 {currentIndex + 1} / {questions.length} 题
          </Text>
        </View>
        <View className='employee-exam-timer-block'>
          <Text className='employee-exam-timer-label'>剩余时间</Text>
          <Text className={`employee-exam-timer ${remaining <= 60 ? 'is-warning' : ''}`}>
            {formatRemaining(remaining)}
          </Text>
        </View>
      </View>

      {saveState !== 'idle' && (
        <View
          className={`employee-save-state is-${saveState}`}
          onClick={() => {
            if (saveState === 'error' && paper.attempt_id) persist(paper.attempt_id)
          }}
        >
          <Text>
            {saveState === 'saving'
              ? '保存中…'
              : saveState === 'saved'
                ? '答案已保存'
                : '保存失败，点击重试'}
          </Text>
        </View>
      )}

      <View className='employee-progress'>
        <View className='employee-progress-rail' />
        <View
          className='employee-progress-rail is-done'
          style={{ width: `${(currentStation / (stationCount - 1)) * 100}%` }}
        />
        {Array.from({ length: stationCount }).map((_, index) => (
          <View
            key={index}
            className={`employee-progress-station ${
              index < currentStation ? 'is-done' : ''
            } ${index === currentStation ? 'is-current' : ''}`}
          />
        ))}
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

      <View className='employee-answer-card-link' onClick={() => setCardOpen(true)}>
        <Text>答题卡</Text>
        <Text className='employee-answer-card-count'>
          已答 {answeredCount} / {questions.length}
        </Text>
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

      <Text className='employee-exam-autosave'>
        答案已自动保存，倒计时结束后系统将自动交卷
      </Text>

      {cardOpen && (
        <View className='answer-card-mask' onClick={() => setCardOpen(false)}>
          <View className='answer-card-panel' onClick={(event) => event.stopPropagation()}>
            <View className='answer-card-head'>
              <Text className='answer-card-title'>答题卡</Text>
              <Text className='answer-card-close' onClick={() => setCardOpen(false)}>
                关闭
              </Text>
            </View>
            <View className='answer-card-summary'>
              <Text>已答 {answeredCount}</Text>
              <Text>未答 {questions.length - answeredCount}</Text>
            </View>
            <View className='answer-card-grid'>
              {questions.map((question, index) => {
                const answered = (answers[question.id] || []).length > 0
                return (
                  <View
                    key={question.id}
                    className={`answer-card-item ${answered ? 'is-answered' : ''} ${
                      index === currentIndex ? 'is-current' : ''
                    }`}
                    onClick={() => {
                      setCurrentIndex(index)
                      setCardOpen(false)
                    }}
                  >
                    <Text>{index + 1}</Text>
                  </View>
                )
              })}
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
