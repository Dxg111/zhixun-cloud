import { useCallback, useEffect, useState } from 'react'
import { View, Text, Input, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  createEmployeeSession,
  getEmployeeMembership,
  getEmployeeToken,
  setEmployeeAuth,
  submitEmployeeJoinRequest,
  waitForLogin,
  type EmployeeMembership,
} from '../../services/api'
import './index.scss'

const STATUS_TEXT: Record<string, string> = {
  pending: '审核中',
  rejected: '未通过',
  disabled: '已停用',
}

export default function EmployeeLoginPage() {
  const [membership, setMembership] = useState<EmployeeMembership | null>(null)
  const [tenantCode, setTenantCode] = useState('')
  const [name, setName] = useState('')
  const [employeeNo, setEmployeeNo] = useState('')
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)

  const loadMembership = useCallback(async () => {
    setChecking(true)
    try {
      await waitForLogin()
      const data = await getEmployeeMembership()
      setMembership(data)

      if (data.status === 'approved') {
        const session = await createEmployeeSession()
        setEmployeeAuth(session.token, session.employee)
        Taro.showToast({ title: '已加入企业', icon: 'success' })
        setTimeout(() => {
          Taro.redirectTo({ url: '/pages/employee-exams/index' })
        }, 300)
      }
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '企业信息加载失败', icon: 'none' })
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    if (getEmployeeToken()) {
      Taro.redirectTo({ url: '/pages/employee-exams/index' })
      return
    }
    void loadMembership()
  }, [loadMembership])

  const handleSubmit = async () => {
    if (!tenantCode.trim() || !name.trim() || !employeeNo.trim()) {
      Taro.showToast({ title: '请填写企业编码、姓名和工号', icon: 'none' })
      return
    }
    setLoading(true)
    try {
      const request = await submitEmployeeJoinRequest({
        tenant_code: tenantCode.trim(),
        name: name.trim(),
        employee_no: employeeNo.trim(),
      })
      setMembership({
        status: 'pending',
        tenant_code: request.tenant_code,
        tenant_name: request.tenant_name,
        employee: null,
        request,
        message: '加入申请审核中',
      })
      Taro.showToast({ title: '申请已提交', icon: 'success' })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '提交失败，请稍后重试', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const showForm = !membership || membership.status === 'none' || membership.status === 'rejected'

  return (
    <View className='employee-login-page paper-bg'>
      <View className='employee-login-brand'>
        <View className='employee-login-brand-mark'>智</View>
        <View className='employee-login-brand-body'>
          <Text className='employee-login-brand-name'>智训云</Text>
          <Text className='employee-login-brand-sub'>企业培训考核平台</Text>
        </View>
      </View>

      {checking ? (
        <View className='employee-login-card'>
          <Text className='employee-login-title'>正在查询企业身份...</Text>
        </View>
      ) : (
        <>
          {membership?.status === 'pending' && membership.request && (
            <View className='employee-login-card employee-join-status'>
              <View className='employee-join-status-head'>
                <Text className='employee-login-kicker'>加入申请</Text>
                <Text className='employee-join-status-tag'>{STATUS_TEXT.pending}</Text>
              </View>
              <Text className='employee-login-title'>{membership.tenant_name}</Text>
              <Text className='employee-login-desc'>
                {membership.request.name}，工号 {membership.request.employee_no}
              </Text>
              <Text className='employee-join-hint'>
                申请已提交，企业管理员审核通过后即可进入培训和考试。
              </Text>
              <Button
                className='employee-primary-btn'
                loading={checking}
                onClick={() => void loadMembership()}
              >
                刷新审核状态
              </Button>
            </View>
          )}

          {membership?.status === 'disabled' && (
            <View className='employee-login-card employee-join-status'>
              <Text className='employee-login-kicker'>企业身份</Text>
              <Text className='employee-login-title'>{membership.tenant_name}</Text>
              <Text className='employee-login-desc'>{membership.message}</Text>
              <Text className='employee-join-hint'>请联系企业管理员恢复账号后再试。</Text>
            </View>
          )}

          {membership?.status === 'rejected' && membership.request && (
            <View className='employee-login-card employee-join-status'>
              <View className='employee-join-status-head'>
                <Text className='employee-login-kicker'>加入申请</Text>
                <Text className='employee-join-status-tag is-muted'>{STATUS_TEXT.rejected}</Text>
              </View>
              <Text className='employee-login-title'>{membership.tenant_name}</Text>
              <Text className='employee-login-desc'>
                驳回原因：{membership.request.reject_reason || '未填写'}
              </Text>
              <Text className='employee-join-hint'>修改资料后可以重新提交申请。</Text>
            </View>
          )}

          {showForm && (
            <View className='employee-login-card'>
              <Text className='employee-login-kicker'>员工入口</Text>
              <Text className='employee-login-title'>
                {membership?.status === 'rejected' ? '重新申请加入' : '加入企业'}
              </Text>
              <Text className='employee-login-desc'>
                输入企业编码并提交资料，企业管理员审核通过后即可进入我的考试。
              </Text>

              <View className='employee-field'>
                <Text className='employee-field-label'>企业编码</Text>
                <Input
                  className='employee-input'
                  value={tenantCode}
                  placeholder='例如：demo'
                  onInput={(event) => setTenantCode(event.detail.value)}
                />
              </View>

              <View className='employee-field'>
                <Text className='employee-field-label'>姓名</Text>
                <Input
                  className='employee-input'
                  value={name}
                  placeholder='请输入真实姓名'
                  maxlength={100}
                  onInput={(event) => setName(event.detail.value)}
                />
              </View>

              <View className='employee-field'>
                <Text className='employee-field-label'>工号</Text>
                <Input
                  className='employee-input'
                  value={employeeNo}
                  placeholder='请输入企业工号'
                  maxlength={64}
                  onInput={(event) => setEmployeeNo(event.detail.value)}
                />
              </View>

              <Button
                className='employee-primary-btn'
                loading={loading}
                disabled={loading}
                onClick={handleSubmit}
              >
                {loading ? '提交中...' : '提交加入申请'}
              </Button>

              <Text className='employee-login-tip'>
                企业编码由企业管理员提供。提交后需要管理员审核，审核通过会自动加入企业。
              </Text>
            </View>
          )}

          <View
            className='employee-back-home'
            onClick={() => Taro.switchTab({ url: '/pages/index/index' })}
          >
            <Text>返回学习首页</Text>
          </View>
        </>
      )}
    </View>
  )
}
