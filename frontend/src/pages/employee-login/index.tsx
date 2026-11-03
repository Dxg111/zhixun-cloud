import { useEffect, useState } from 'react'
import { View, Text, Input, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  employeeLogin,
  getEmployeeToken,
  setEmployeeAuth,
} from '../../services/api'
import './index.scss'

export default function EmployeeLoginPage() {
  const [tenantCode, setTenantCode] = useState('demo')
  const [inviteCode, setInviteCode] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-exams/index' })
    }
  }, [])

  const handleLogin = async () => {
    if (!tenantCode.trim() || !inviteCode.trim()) {
      Taro.showToast({ title: '请输入租户编码和邀请码', icon: 'none' })
      return
    }

    setLoading(true)
    try {
      const data = await employeeLogin(tenantCode.trim(), inviteCode.trim().toUpperCase())
      setEmployeeAuth(data.token, data.employee)
      Taro.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        Taro.redirectTo({ url: '/pages/employee-exams/index' })
      }, 400)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '登录失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='employee-login-page'>
      <View className='employee-login-card'>
        <View className='employee-login-mark'>🏢</View>
        <Text className='employee-login-title'>企业培训考试</Text>
        <Text className='employee-login-desc'>
          输入企业管理员提供的租户编码和邀请码，进入我的考试。
        </Text>

        <View className='employee-field'>
          <Text className='employee-field-label'>租户编码</Text>
          <Input
            className='employee-input'
            value={tenantCode}
            placeholder='例如：demo'
            onInput={(event) => setTenantCode(event.detail.value)}
          />
        </View>

        <View className='employee-field'>
          <Text className='employee-field-label'>邀请码</Text>
          <Input
            className='employee-input'
            value={inviteCode}
            placeholder='请输入 8 位邀请码'
            maxlength={32}
            onInput={(event) => setInviteCode(event.detail.value)}
          />
        </View>

        <Button
          className='employee-primary-btn'
          loading={loading}
          disabled={loading}
          onClick={handleLogin}
        >
          {loading ? '登录中...' : '进入我的考试'}
        </Button>

        <View
          className='employee-back-home'
          onClick={() => Taro.switchTab({ url: '/pages/index/index' })}
        >
          <Text>返回学习首页</Text>
        </View>
      </View>
    </View>
  )
}
