import {
  ApartmentOutlined,
  BellOutlined,
  BookOutlined,
  DashboardOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  IdcardOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MoonOutlined,
  SearchOutlined,
  SettingOutlined,
  SunOutlined,
  TeamOutlined,
  UnorderedListOutlined,
  UsergroupAddOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Dropdown,
  Input,
  Layout,
  Menu,
  Space,
  Tooltip,
  Typography,
  type MenuProps,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { clearToken, getDashboard, getStoredUser } from '../services/api'
import { useThemeMode } from '../theme/ThemeProvider'

const { Header, Sider, Content } = Layout

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': '工作台',
  '/org': '组织与员工',
  '/join-requests': '加入审核',
  '/search': '全局搜索',
  '/knowledge': '知识库',
  '/questions': '题库审核',
  '/cards': '知识卡',
  '/exams': '考试管理',
  '/exports': '导出中心',
  '/admins': '管理员',
  '/audit-logs': '审计日志',
  '/settings': '设置',
}

function buildMenuItems(
  pendingQuestions: number,
  pendingCards: number,
  pendingJoinRequests: number,
): MenuProps['items'] {
  const pendingBadge = (count: number, color: string, hint: string) =>
    count > 0 ? (
      <Tooltip title={hint}>
        <Badge count={count} size="small" color={color} />
      </Tooltip>
    ) : null

  return [
    {
      type: 'group',
      label: '总览',
      children: [{ key: '/dashboard', icon: <DashboardOutlined />, label: '工作台' }],
    },
    {
      type: 'group',
      label: '组织',
      children: [
        { key: '/org', icon: <ApartmentOutlined />, label: '组织与员工' },
        {
          key: '/join-requests',
          icon: <UsergroupAddOutlined />,
          label: (
            <Space size={8}>
              加入审核
              {pendingBadge(pendingJoinRequests, 'blue', '待审核加入申请数量')}
            </Space>
          ),
        },
      ],
    },
    {
      type: 'group',
      label: '内容',
      children: [
        { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
        {
          key: '/questions',
          icon: <UnorderedListOutlined />,
          label: (
            <Space size={8}>
              题库审核
              {pendingBadge(pendingQuestions, 'green', '待审核题目数量')}
            </Space>
          ),
        },
        {
          key: '/cards',
          icon: <IdcardOutlined />,
          label: (
            <Space size={8}>
              知识卡
              {pendingBadge(pendingCards, 'gold', '待发布知识卡数量')}
            </Space>
          ),
        },
      ],
    },
    {
      type: 'group',
      label: '考试',
      children: [
        { key: '/exams', icon: <FileDoneOutlined />, label: '考试管理' },
        { key: '/exports', icon: <DownloadOutlined />, label: '导出中心' },
      ],
    },
    {
      type: 'group',
      label: '系统',
      children: [
        { key: '/admins', icon: <TeamOutlined />, label: '管理员' },
        { key: '/audit-logs', icon: <FileDoneOutlined />, label: '审计日志' },
        { key: '/settings', icon: <SettingOutlined />, label: '设置' },
      ],
    },
  ]
}

export default function AdminLayout() {
  const { mode, toggle } = useThemeMode()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [pendingQuestions, setPendingQuestions] = useState(0)
  const [pendingCards, setPendingCards] = useState(0)
  const [pendingJoinRequests, setPendingJoinRequests] = useState(0)
  const [searchValue, setSearchValue] = useState('')
  const pageTitle = PAGE_TITLES[location.pathname] ?? '工作台'
  const user = getStoredUser()

  useEffect(() => {
    if (location.pathname !== '/search') return
    const query = new URLSearchParams(location.search).get('q')
    if (query) setSearchValue(query)
  }, [location.pathname, location.search])

  const loadBadges = useCallback(async () => {
    try {
      const data = await getDashboard()
      setPendingQuestions(data.pending_questions)
      setPendingCards(data.pending_cards)
      setPendingJoinRequests(data.pending_join_requests)
    } catch {
      // 徽标加载失败不打断页面
    }
  }, [])

  useEffect(() => {
    void loadBadges()
  }, [loadBadges, location.pathname])

  // 停留在同一页面时，新加入申请/待审核内容也能在 1 分钟内冒红点
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void loadBadges()
    }, 60000)
    const handleVisible = () => {
      if (document.visibilityState === 'visible') void loadBadges()
    }
    document.addEventListener('visibilitychange', handleVisible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', handleVisible)
    }
  }, [loadBadges])

  const menuItems = useMemo(
    () => buildMenuItems(pendingQuestions, pendingCards, pendingJoinRequests),
    [pendingQuestions, pendingCards, pendingJoinRequests],
  )
  const displayName = user?.name || '李培训'
  const roleLabel = user?.role === 'tenant_admin' ? '企业管理员' : '管理员'
  const avatarText = displayName.slice(0, 1) || '李'

  const notificationMenu: MenuProps = {
    items: pendingQuestions + pendingCards + pendingJoinRequests > 0
      ? [
          ...(pendingQuestions > 0
            ? [{ key: 'questions', label: `${pendingQuestions} 道题等待审核` }]
            : []),
          ...(pendingCards > 0
            ? [{ key: 'cards', label: `${pendingCards} 张知识卡等待发布` }]
            : []),
          ...(pendingJoinRequests > 0
            ? [{ key: 'join-requests', label: `${pendingJoinRequests} 条加入申请等待审核` }]
            : []),
        ]
      : [{ key: 'empty', label: '暂无待办通知', disabled: true }],
    onClick: ({ key }) => {
      if (key === 'questions') navigate('/questions')
      if (key === 'cards') navigate('/cards')
      if (key === 'join-requests') navigate('/join-requests')
    },
  }

  const userMenu: MenuProps = {
    items: [
      { key: 'login', icon: <UserOutlined />, label: '查看登录页' },
      { key: 'settings', icon: <SettingOutlined />, label: '账号设置' },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
    ],
    onClick: ({ key }) => {
      if (key === 'settings') navigate('/settings')
      if (key === 'login') navigate('/login')
      if (key === 'logout') {
        clearToken()
        navigate('/login', { replace: true })
      }
    },
  }

  return (
    <Layout className="admin-layout">
      <Sider
        className="admin-sider"
        width={236}
        collapsedWidth={64}
        collapsed={collapsed}
        collapsible
        trigger={null}
        breakpoint="lg"
        onBreakpoint={setCollapsed}
      >
        <div className={`admin-logo ${collapsed ? 'is-collapsed' : ''}`}>
          <div className="admin-logo-mark">智</div>
          {!collapsed ? (
            <div className="admin-logo-text">
              <strong>智训云</strong>
              <span>企业管理后台</span>
            </div>
          ) : null}
        </div>

        {!collapsed ? (
          <div className="admin-tenant-card">
            <span className="admin-tenant-label">当前租户</span>
            <strong>演示企业</strong>
            <span className="admin-tenant-meta">连锁零售 / 餐饮 · 120 人</span>
          </div>
        ) : null}

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="admin-menu"
          style={{ background: 'transparent', borderInlineEnd: 0 }}
        />

        {!collapsed ? (
          <div className="admin-sider-foot">
            <span>企业管理后台</span>
            <span>V1.0</span>
          </div>
        ) : null}
      </Sider>

      <Layout>
        <Header className="admin-header">
          <div className="admin-header-left">
            <Button
              type="text"
              className="admin-collapse-btn"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed((value) => !value)}
              aria-label="折叠侧栏"
            />
            <Breadcrumb
              className="admin-breadcrumb"
              items={[{ title: '演示企业' }, { title: pageTitle }]}
            />
          </div>

          <div className="admin-header-right">
            <Input
              className="admin-search"
              value={searchValue}
              prefix={<SearchOutlined />}
              placeholder="搜索员工、题目、考试..."
              allowClear
              onChange={(event) => setSearchValue(event.target.value)}
              onPressEnter={() => {
                const keyword = searchValue.trim()
                if (keyword) navigate(`/search?q=${encodeURIComponent(keyword)}`)
              }}
            />
            <Button
              type="text"
              icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggle}
              aria-label="切换深浅色"
            />
            <Dropdown menu={notificationMenu} trigger={['click']} placement="bottomRight">
              <Button type="text" icon={<BellOutlined />} aria-label="通知" />
            </Dropdown>
            <Dropdown menu={userMenu} trigger={['click']} placement="bottomRight">
              <Button type="text" className="admin-user-button">
                <Avatar size={28} className="admin-avatar">
                  {avatarText}
                </Avatar>
                <span className="admin-user-meta">
                  <Typography.Text strong>{displayName}</Typography.Text>
                  <Typography.Text type="secondary">{roleLabel}</Typography.Text>
                </span>
              </Button>
            </Dropdown>
          </div>
        </Header>

        <Content className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
