import Taro from '@tarojs/taro'
import { getEmployeeToken, getNotificationSummary, type NotificationSummary } from './api'

let lastSummary: NotificationSummary | null = null

export function getCachedNotificationSummary(): NotificationSummary | null {
  return lastSummary
}

async function applyTabBadge(count: number) {
  try {
    if (count > 0) {
      await Taro.setTabBarBadge({ index: 0, text: count > 99 ? '99+' : String(count) })
    } else {
      await Taro.removeTabBarBadge({ index: 0 })
    }
  } catch {
    // 非 tabBar 页面或 tabBar 未就绪时失败，忽略即可
  }
}

/**
 * 拉取未读数并同步 tabBar 角标。
 * 未登录员工时跳过，返回 null。
 */
export async function refreshNotificationSummary(): Promise<NotificationSummary | null> {
  if (!getEmployeeToken()) {
    lastSummary = null
    await applyTabBadge(0)
    return null
  }

  try {
    const summary = await getNotificationSummary()
    lastSummary = summary
    await applyTabBadge(summary.unread_count)
    return summary
  } catch {
    return lastSummary
  }
}
