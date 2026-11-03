import { useEffect, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  getEmployeeToken,
  listEmployeeWrongQuestions,
  retryEmployeeWrongQuestion,
  setEmployeeWrongQuestionMastered,
  type EmployeeWrongQuestionItem,
  type EmployeeWrongRetryResponse,
} from '../../services/api'
import './index.scss'

export default function EmployeeWrongPage() {
  const [items, setItems] = useState<EmployeeWrongQuestionItem[]>([])
  const [onlyTodo, setOnlyTodo] = useState(true)
  const [loading, setLoading] = useState(true)
  const [retryingId, setRetryingId] = useState<number | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [results, setResults] = useState<Record<number, EmployeeWrongRetryResponse>>({})
  const [submitting, setSubmitting] = useState(false)

  const load = (todo: boolean) => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    setLoading(true)
    listEmployeeWrongQuestions(todo ? false : undefined)
      .then((data) => setItems(data.items))
      .catch((error: any) => {
        Taro.showToast({ title: error?.message || '错题加载失败', icon: 'none' })
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(onlyTodo)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyTodo])

  useDidShow(() => {
    load(onlyTodo)
  })

  const startRetry = (item: EmployeeWrongQuestionItem) => {
    if (retryingId === item.id) {
      setRetryingId(null)
      setSelected([])
      return
    }
    setRetryingId(item.id)
    setSelected([])
  }

  const handleOption = (item: EmployeeWrongQuestionItem, key: string) => {
    setSelected((prev) =>
      item.type === 'multiple'
        ? prev.includes(key)
          ? prev.filter((value) => value !== key)
          : [...prev, key]
        : [key],
    )
  }

  const submitRetry = async (item: EmployeeWrongQuestionItem) => {
    if (!selected.length) {
      Taro.showToast({ title: '请先选择答案', icon: 'none' })
      return
    }
    setSubmitting(true)
    try {
      const result = await retryEmployeeWrongQuestion(item.id, selected)
      setResults((prev) => ({ ...prev, [item.id]: result }))
      setItems((prev) =>
        prev.map((value) =>
          value.id === item.id
            ? {
                ...value,
                correct_streak: result.correct_streak,
                mastered: result.mastered,
                wrong_count: result.is_correct ? value.wrong_count : value.wrong_count + 1,
              }
            : value,
        ),
      )
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '提交失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  const toggleMastered = async (item: EmployeeWrongQuestionItem) => {
    try {
      const result = await setEmployeeWrongQuestionMastered(item.id, !item.mastered)
      setItems((prev) =>
        prev.map((value) =>
          value.id === item.id
            ? { ...value, mastered: result.mastered, correct_streak: result.mastered ? value.correct_streak : 0 }
            : value,
        ),
      )
      Taro.showToast({
        title: result.mastered ? '已标记掌握' : '已取消掌握',
        icon: 'none',
      })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '操作失败', icon: 'none' })
    }
  }

  return (
    <View className='employee-wrong-page'>
      <View className='employee-wrong-hero'>
        <Text className='employee-wrong-title'>错题重练</Text>
        <Text className='employee-wrong-desc'>
          连续答对 2 次自动标记掌握；重练不会修改原考试成绩。
        </Text>
      </View>

      <View className='employee-wrong-tabs'>
        <View
          className={`employee-wrong-tab ${onlyTodo ? 'is-active' : ''}`}
          onClick={() => setOnlyTodo(true)}
        >
          <Text>待掌握</Text>
        </View>
        <View
          className={`employee-wrong-tab ${!onlyTodo ? 'is-active' : ''}`}
          onClick={() => setOnlyTodo(false)}
        >
          <Text>全部</Text>
        </View>
      </View>

      {loading && items.length === 0 ? (
        <View className='employee-wrong-empty'><Text>加载中...</Text></View>
      ) : items.length === 0 ? (
        <View className='employee-wrong-empty'>
          <Text className='employee-wrong-empty-icon'>🎉</Text>
          <Text>{onlyTodo ? '暂无待掌握错题' : '暂无错题'}</Text>
        </View>
      ) : (
        <View className='employee-wrong-list'>
          {items.map((item) => {
            const retrying = retryingId === item.id
            const result = results[item.id]
            return (
              <View key={item.id} className='employee-wrong-card'>
                <View className='employee-wrong-card-head'>
                  <View className='employee-wrong-meta'>
                    <Text className='employee-wrong-point'>
                      {item.knowledge_point || '综合'}
                    </Text>
                    <Text className='employee-wrong-count'>错 {item.wrong_count} 次</Text>
                    <Text className='employee-wrong-streak'>
                      连续答对 {item.correct_streak}/2
                    </Text>
                  </View>
                  {item.mastered && <Text className='employee-wrong-mastered'>已掌握</Text>}
                </View>

                <Text className='employee-wrong-stem'>{item.stem}</Text>

                {retrying && (
                  <View className='employee-wrong-options'>
                    {item.options.map((option) => (
                      <View
                        key={option.key}
                        className={`employee-wrong-option ${
                          selected.includes(option.key) ? 'is-selected' : ''
                        }`}
                        onClick={() => handleOption(item, option.key)}
                      >
                        <Text className='employee-wrong-option-key'>{option.key}</Text>
                        <Text className='employee-wrong-option-text'>{option.text}</Text>
                      </View>
                    ))}
                  </View>
                )}

                {result && (
                  <View className={`employee-wrong-result ${result.is_correct ? 'is-pass' : 'is-fail'}`}>
                    <Text className='employee-wrong-result-title'>
                      {result.is_correct ? '✓ 答对了' : '✗ 答错了'}
                    </Text>
                    <Text className='employee-wrong-result-answer'>
                      正确答案：{result.answer.join('、')}
                    </Text>
                    <Text className='employee-wrong-result-explanation'>{result.explanation}</Text>
                  </View>
                )}

                <View className='employee-wrong-actions'>
                  <View className='employee-wrong-btn' onClick={() => startRetry(item)}>
                    <Text>{retrying ? '收起' : '重练'}</Text>
                  </View>
                  {retrying && (
                    <View
                      className={`employee-wrong-btn is-primary ${submitting ? 'is-disabled' : ''}`}
                      onClick={() => {
                        if (!submitting) void submitRetry(item)
                      }}
                    >
                      <Text>提交答案</Text>
                    </View>
                  )}
                  <View className='employee-wrong-btn' onClick={() => void toggleMastered(item)}>
                    <Text>{item.mastered ? '取消掌握' : '标记掌握'}</Text>
                  </View>
                </View>
              </View>
            )
          })}
        </View>
      )}
    </View>
  )
}
