import { useCallback, useEffect, useState } from 'react'
import { View, Text, Switch } from '@tarojs/components'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import {
  getEmployeeToken,
  getNotificationPreferences,
  getWechatSubscribeConfig,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  reportWechatSubscriptions,
  updateNotificationPreferences,
  type NotificationItem,
  type WechatSubscribeConfig,
} from '../../services/api'
import { refreshNotificationSummary } from '../../services/notification'
import './index.scss'

function formatTime(value: string) {
  // created_at 形如 2026-11-05 09:12:00
  return value.length >= 16 ? value.slice(5, 16) : value
}

function buildUrl(item: NotificationItem) {
  if (!item.link_page) return ''
  const page = item.link_page.startsWith('/') ? item.link_page : `/${item.link_page}`
  if (!item.link_params) return page

  try {
    const params = JSON.parse(item.link_params) as Record<string, unknown>
    const query = Object.entries(params)
      .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
      .join('&')
    return query ? `${page}?${query}` : page
  } catch {
    return page
  }
}

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [wechatConfig, setWechatConfig] = useState<WechatSubscribeConfig | null>(null)
  const [notifyDeadline, setNotifyDeadline] = useState(true)
  const [prefSaving, setPrefSaving] = useState(false)

  useEffect(() => {
    if (!getEmployeeToken()) return
    getWechatSubscribeConfig()
      .then(setWechatConfig)
      .catch(() => {})
    getNotificationPreferences()
      .then((prefs) => setNotifyDeadline(prefs.notify_deadline))
      .catch(() => {})
  }, [])

  const handleSubscribe = async () => {
    const tmplIds = Object.values(wechatConfig?.templates || {})
    if (!tmplIds.length) {
      Taro.showToast({ title: '暂未配置微信提醒模板', icon: 'none' })
      return
    }
    try {
      // Taro 4.1 的类型定义要求 entityIds，但微信小程序实际 API 使用 tmplIds
      const result = await Taro.requestSubscribeMessage({ tmplIds } as any)
      const accepted = tmplIds.filter(
        (id) => (result as Record<string, string>)[id] === 'accept',
      )
      if (!accepted.length) {
        Taro.showToast({ title: '未授权，仍可在小程序内收到消息', icon: 'none' })
        return
      }
      await reportWechatSubscriptions(accepted)
      Taro.showToast({ title: '已开启微信提醒', icon: 'none' })
    } catch {
      Taro.showToast({ title: '开启失败，请在微信设置中允许订阅消息', icon: 'none' })
    }
  }

  const handleToggleDeadline = async () => {
    if (prefSaving) return
    const next = !notifyDeadline
    setNotifyDeadline(next)
    setPrefSaving(true)
    try {
      await updateNotificationPreferences({ notify_deadline: next })
    } catch (error: any) {
      setNotifyDeadline(!next)
      Taro.showToast({ title: error?.message || '设置保存失败', icon: 'none' })
    } finally {
      setPrefSaving(false)
    }
  }

  const load = useCallback(async (onlyUnread: boolean) => {
    if (!getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-login/index' })
      return
    }
    setLoading(true)
    try {
      const data = await listNotifications({ unreadOnly: onlyUnread, pageSize: 50 })
      setItems(data.items)
      setUnreadCount(data.unread_count)
      await refreshNotificationSummary()
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '消息加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }, [])

  useDidShow(() => {
    load(unreadOnly)
  })

  usePullDownRefresh(async () => {
    await load(unreadOnly)
    Taro.stopPullDownRefresh()
  })

  const switchTab = (onlyUnread: boolean) => {
    if (onlyUnread === unreadOnly) return
    setUnreadOnly(onlyUnread)
    void load(onlyUnread)
  }

  const handleOpen = async (item: NotificationItem) => {
    if (!item.read) {
      try {
        await markNotificationRead(item.id)
        setItems((prev) =>
          prev.map((current) =>
            current.id === item.id ? { ...current, read: true } : current,
          ),
        )
        setUnreadCount((prev) => Math.max(0, prev - 1))
        await refreshNotificationSummary()
      } catch {
        // 标记失败不阻断跳转
      }
    }

    const url = buildUrl(item)
    if (!url) {
      if (unreadOnly) await load(true)
      return
    }
    try {
      await Taro.navigateTo({ url })
    } catch {
      Taro.showToast({ title: '页面暂时无法打开', icon: 'none' })
    }
  }

  const handleReadAll = async () => {
    if (unreadCount === 0) return
    try {
      await markAllNotificationsRead()
      setUnreadCount(0)
      setItems((prev) => prev.map((item) => ({ ...item, read: true })))
      await refreshNotificationSummary()
      if (unreadOnly) await load(true)
      Taro.showToast({ title: '已全部标为已读', icon: 'none' })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '操作失败', icon: 'none' })
    }
  }

  return (
    <View className='notifications-page paper-bg'>
      <View className='notifications-head'>
        <View className='notifications-tabs'>
          <Text
            className={`notifications-tab ${!unreadOnly ? 'is-active' : ''}`}
            onClick={() => switchTab(false)}
          >
            全部
          </Text>
          <Text
            className={`notifications-tab ${unreadOnly ? 'is-active' : ''}`}
            onClick={() => switchTab(true)}
          >
            未读{unreadCount > 0 ? ` ${unreadCount}` : ''}
          </Text>
        </View>
        <Text
          className={`notifications-read-all ${unreadCount === 0 ? 'is-disabled' : ''}`}
          onClick={handleReadAll}
        >
          全部已读
        </Text>
      </View>

      <View className='notifications-settings'>
        {wechatConfig?.enabled ? (
          <View className='notifications-setting-row' onClick={handleSubscribe}>
            <View className='notifications-setting-body'>
              <Text className='notifications-setting-title'>微信提醒</Text>
              <Text className='notifications-setting-desc'>
                开启后可在微信服务通知中收到考试提醒
              </Text>
            </View>
            <Text className='notifications-setting-action'>开启</Text>
          </View>
        ) : null}

        <View className='notifications-setting-row'>
          <View className='notifications-setting-body'>
            <Text className='notifications-setting-title'>截止前 24 小时提醒</Text>
            <Text className='notifications-setting-desc'>
              关闭后不再收到考试即将截止的提醒
            </Text>
          </View>
          <Switch
            checked={notifyDeadline}
            color='#1f4a38'
            onChange={handleToggleDeadline}
          />
        </View>
      </View>

      {loading && items.length === 0 ? (
        <View className='notifications-empty'><Text>加载中...</Text></View>
      ) : items.length === 0 ? (
        <View className='notifications-empty'>
          <Text className='notifications-empty-mark'>—</Text>
          <Text>{unreadOnly ? '没有未读消息' : '暂时没有消息'}</Text>
          <Text className='notifications-empty-hint'>
            管理员发布新考试或审核加入申请后，会在这里通知你
          </Text>
        </View>
      ) : (
        <View className='notifications-list'>
          {items.map((item) => (
            <View
              key={item.id}
              className={`notification-card ${item.read ? 'is-read' : ''}`}
              onClick={() => handleOpen(item)}
            >
              <View className='notification-top'>
                <View className='notification-title-row'>
                  {!item.read && <View className='notification-dot' />}
                  <Text className='notification-title'>{item.title}</Text>
                </View>
                <Text className='notification-time'>{formatTime(item.created_at)}</Text>
              </View>
              {item.content ? (
                <Text className='notification-content'>{item.content}</Text>
              ) : null}
              {item.link_page ? (
                <Text className='notification-action'>查看详情 ›</Text>
              ) : null}
            </View>
          ))}
        </View>
      )}
    </View>
  )
}
