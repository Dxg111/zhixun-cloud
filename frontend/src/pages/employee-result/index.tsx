import { useEffect, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { getEmployeeResult, type EmployeeResultResponse } from '../../services/api'
import './index.scss'

export default function EmployeeResultPage() {
  const router = useRouter()
  const attemptId = Number(router.params.attemptId || 0)
  const [result, setResult] = useState<EmployeeResultResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!attemptId) {
      setLoading(false)
      return
    }
    getEmployeeResult(attemptId)
      .then(setResult)
      .catch((error: any) => {
        Taro.showToast({ title: error?.message || '成绩加载失败', icon: 'none' })
      })
      .finally(() => setLoading(false))
  }, [attemptId])

  if (loading) {
    return (
      <View className='employee-result-page paper-bg'>
        <View className='employee-result-empty'><Text>正在加载成绩...</Text></View>
      </View>
    )
  }

  if (!result) {
    return (
      <View className='employee-result-page paper-bg'>
        <View className='employee-result-empty'><Text>暂无成绩</Text></View>
      </View>
    )
  }

  return (
    <View className='employee-result-page paper-bg'>
      <View className={`employee-result-hero ${result.passed ? 'is-pass' : 'is-fail'}`}>
        <Text className='employee-result-kicker'>考试成绩</Text>
        <View className='employee-result-score-row'>
          <Text className='employee-result-score num'>{result.score}</Text>
          <Text className='employee-result-score-unit'>分</Text>
        </View>
        <Text className='employee-result-label'>本场得分</Text>
        <Text className={`employee-result-status ${result.passed ? 'is-pass' : 'is-fail'}`}>
          {result.passed ? '已通过' : '未通过'}
        </Text>
        <Text className='employee-result-hint'>
          {result.passed ? '成绩已记录，可继续完成错题重练巩固知识。' : '建议先阅读知识卡，再完成错题重练后重考。'}
        </Text>
      </View>

      <View className='employee-result-summary'>
        <View className='employee-result-stat'>
          <Text className='employee-result-stat-value'>{result.correct_count}</Text>
          <Text className='employee-result-stat-label'>答对</Text>
        </View>
        <View className='employee-result-stat'>
          <Text className='employee-result-stat-value'>{result.total_count - result.correct_count}</Text>
          <Text className='employee-result-stat-label'>答错</Text>
        </View>
        <View className='employee-result-stat'>
          <Text className='employee-result-stat-value'>{result.total_count}</Text>
          <Text className='employee-result-stat-label'>总题数</Text>
        </View>
      </View>

      <Text className='employee-result-section-title'>逐题解析</Text>

      <View className='employee-result-list'>
        {result.details.map((detail, index) => (
          <View key={detail.question_id} className='employee-result-item'>
            <View className='employee-result-question-head'>
              <Text className='employee-result-question-index'>第 {index + 1} 题</Text>
              <Text className={`employee-result-correct ${detail.is_correct ? 'is-pass' : 'is-fail'}`}>
                {detail.is_correct ? '✓ 答对' : '✗ 答错'}
              </Text>
            </View>
            <Text className='employee-result-stem'>{detail.stem}</Text>
            <Text className='employee-result-answer'>
              你的答案：{detail.selected.join('、') || '未作答'}
            </Text>
            <Text className='employee-result-answer'>
              正确答案：{detail.answer.join('、')}
            </Text>
            <Text className='employee-result-explanation'>{detail.explanation}</Text>
          </View>
        ))}
      </View>

      <View
        className='employee-result-secondary'
        onClick={() => Taro.navigateTo({ url: '/pages/employee-wrong/index' })}
      >
        <Text>错题重练</Text>
      </View>

      <View
        className='employee-result-action'
        onClick={() =>
          Taro.navigateBack({
            fail: () => Taro.reLaunch({ url: '/pages/employee-exams/index' }),
          })
        }
      >
        <Text>返回我的考试</Text>
      </View>
    </View>
  )
}
