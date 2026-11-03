import { useState, useCallback } from 'react'
import { View, Text, Image, Button, Input } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  getUserProfile,
  getQuizHistory,
  updateUserProfile,
  setCachedUser,
  getEmployeeToken,
  getUsableAvatarUrl,
  uploadUserAvatar,
} from '../../services/api'
import type { UserProfile, QuizHistoryItem } from '../../services/api'
import './index.scss'

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [historyItems, setHistoryItems] = useState<QuizHistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [editing, setEditing] = useState(false)
  const [avatarUploading, setAvatarUploading] = useState(false)

  const loadProfile = useCallback(() => {
    return getUserProfile()
      .then((data) => {
        setProfile(data)
        // 同步更新本地缓存，让首页等页面能读到最新信息
        setCachedUser({ id: data.id, nickname: data.nickname, avatar_url: data.avatar_url, total_xp: data.total_xp })
      })
      .catch(() => {})
  }, [])

  const loadHistory = useCallback((p: number, reset = false) => {
    setLoadingMore(true)
    getQuizHistory(p, 10)
      .then((data) => {
        setHistoryItems((prev) => (reset ? data.items : [...prev, ...data.items]))
        setPage(p)
        setHasMore(data.items.length >= 10 && p * 10 < data.total)
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [])

  // 每次 tab 显示时刷新
  useDidShow(() => {
    loadProfile()
    loadHistory(1, true)
  })

  const handleLoadMore = () => {
    if (!hasMore || loadingMore) return
    loadHistory(page + 1)
  }

  const handleViewDetail = (quizId: string) => {
    Taro.navigateTo({
      url: `/pages/report/index?quizId=${quizId}`,
    })
  }

  // 微信头像授权：临时文件必须先上传，否则开发者工具重启后地址会失效
  const handleChooseAvatar = (e) => {
    if (avatarUploading) return
    const avatarUrl = e?.detail?.avatarUrl
    if (!avatarUrl) {
      Taro.showToast({ title: '未获取到头像，请重试', icon: 'none' })
      return
    }

    setAvatarUploading(true)
    Taro.showLoading({ title: '上传头像...' })
    uploadUserAvatar(avatarUrl)
      .then(() => loadProfile())
      .then(() => Taro.showToast({ title: '头像已更新', icon: 'success' }))
      .catch((error: any) => {
        Taro.showToast({ title: error?.message || '头像上传失败', icon: 'none' })
      })
      .finally(() => {
        Taro.hideLoading()
        setAvatarUploading(false)
      })
  }

  // Bug 9: 昵称编辑 — 微信 type='nickname' 选择后触发 onInput，自动提交
  const handleNicknameInput = (e) => {
    const name = (e?.detail?.value || '').trim()
    if (name && name !== profile?.nickname) {
      setEditing(false)
      updateUserProfile({ nickname: name })
        .then(() => loadProfile())
        .catch(() => {})
    }
  }

  return (
    <View className='profile-page paper-bg'>
      <View className='profile-content'>
        <View className='profile-topbar'>
          <Text className='profile-kicker'>个人中心</Text>
          <Text className='profile-topbar-title'>学习档案</Text>
        </View>

        <View className='avatar-section'>
          {/* Bug 8 + Bug 9: 显示真实头像，支持点击授权更换 */}
          <Button
            className='avatar-btn'
            openType='chooseAvatar'
            onChooseAvatar={handleChooseAvatar}
            disabled={avatarUploading}
          >
            {getUsableAvatarUrl(profile?.avatar_url) ? (
              <Image
                className='avatar-img'
                src={getUsableAvatarUrl(profile?.avatar_url)}
                mode='aspectFill'
              />
            ) : (
              <View className='avatar-placeholder'>
                <Text className='avatar-emoji'>{profile?.nickname?.[0] || '智'}</Text>
              </View>
            )}
          </Button>
          {editing ? (
            <Input
              type='nickname'
              className='nickname-input'
              onInput={(e) => handleNicknameInput(e)}
              focus
              placeholder='点击获取微信昵称'
            />
          ) : (
            <Text className='nickname' onClick={() => setEditing(true)}>
              {profile?.nickname || '学习者'}
            </Text>
          )}
          <Text className='slogan'>企业学习档案，持续积累专业能力</Text>
        </View>

        <View className='stats-row'>
          <View className='stat-item'>
            <Text className='stat-num num'>{profile?.quiz_count ?? 0}</Text>
            <Text className='stat-label'>学习次数</Text>
          </View>
          <View className='stat-divider' />
          <View className='stat-item'>
            <Text className='stat-num num'>{profile?.correct_count ?? 0}</Text>
            <Text className='stat-label'>答对题数</Text>
          </View>
          <View className='stat-divider' />
          <View className='stat-item'>
            <Text className='stat-num num'>{profile?.average_accuracy ?? 0}%</Text>
            <Text className='stat-label'>平均正确率</Text>
          </View>
        </View>

        <View className='xp-row'>
          <View className='xp-info'>
            <Text className='xp-label'>累计经验值</Text>
            <Text className='xp-desc'>完成闯关与考试后自动累计</Text>
          </View>
          <View className='xp-value-badge'>
            <Text className='xp-value num'>{profile?.total_xp ?? 0}</Text>
            <Text className='xp-unit'>XP</Text>
          </View>
        </View>

        <Text className='section-kicker'>培训服务</Text>
        <View className='entry-group'>
          <View
            className='knowledge-entry'
            onClick={() => Taro.navigateTo({ url: '/pages/knowledge/index' })}
          >
            <View className='knowledge-entry-left'>
              <View className='knowledge-entry-mark'>知</View>
              <View className='knowledge-entry-body'>
                <Text className='knowledge-entry-text'>我的知识库</Text>
                <Text className='knowledge-entry-desc'>管理学习文档，基于文档生成闯关</Text>
              </View>
            </View>
            <Text className='knowledge-entry-arrow'>›</Text>
          </View>

          <View
            className='knowledge-entry'
            onClick={() => {
              const url = getEmployeeToken()
                ? '/pages/employee-exams/index'
                : '/pages/employee-login/index'
              Taro.navigateTo({ url })
            }}
          >
            <View className='knowledge-entry-left'>
              <View className='knowledge-entry-mark'>企</View>
              <View className='knowledge-entry-body'>
                <Text className='knowledge-entry-text'>企业培训考试</Text>
                <Text className='knowledge-entry-desc'>查看待办考试、考前知识卡与错题</Text>
              </View>
            </View>
            <Text className='knowledge-entry-arrow'>›</Text>
          </View>
        </View>

        {/* 闯关历史 */}
        <Text className='section-title'>学习记录</Text>
        {historyItems.length === 0 ? (
          <View className='empty-history'>
            <Text className='empty-text'>暂无闯关记录，去首页开始学习吧</Text>
          </View>
        ) : (
          <View className='history-list'>
            {historyItems.map((item) => (
              <View
                key={item.quiz_id}
                className='history-item'
                onClick={() => handleViewDetail(item.quiz_id)}
              >
                <View className='history-left'>
                  <Text className='history-title'>{item.title}</Text>
                  <Text className='history-meta'>
                    {item.question_count} 题，正确率 {Math.round(item.accuracy)}%
                  </Text>
                </View>
                <Text className='history-arrow'>›</Text>
              </View>
            ))}
            {hasMore && (
              <View className='load-more' onClick={handleLoadMore}>
                <Text className='load-more-text'>{loadingMore ? '加载中...' : '加载更多'}</Text>
              </View>
            )}
          </View>
        )}
      </View>
    </View>
  )
}
