import { App as AntApp, ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

dayjs.locale('zh-cn')

type ThemeMode = 'light' | 'dark'

interface ThemeContextValue {
  mode: ThemeMode
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: 'light',
  toggle: () => undefined,
})

const THEME_STORAGE_KEY = 'admin-web-theme'

function getInitialMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // localStorage can be unavailable in private windows.
  }

  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [mode, setMode] = useState<ThemeMode>(getInitialMode)

  useEffect(() => {
    document.documentElement.dataset.theme = mode
    try {
      localStorage.setItem(THEME_STORAGE_KEY, mode)
    } catch {
      // Ignore storage failures; the theme still works for this session.
    }
  }, [mode])

  const toggle = () => setMode((current) => (current === 'dark' ? 'light' : 'dark'))

  const themeConfig = useMemo(
    () => ({
      algorithm: mode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: {
        colorPrimary: mode === 'dark' ? '#3aa982' : '#0d6a4d',
        borderRadius: 4,
        fontFamily: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif',
        colorBgLayout: mode === 'dark' ? '#101613' : '#eef1ec',
      },
      components: {
        Layout: {
          siderBg: '#14201a',
          headerBg: 'transparent',
          bodyBg: 'transparent',
          triggerBg: '#14201a',
        },
        Menu: {
          darkItemBg: '#14201a',
          darkItemColor: '#93a79b',
          darkItemHoverBg: 'rgba(255,255,255,0.06)',
          darkItemSelectedBg: 'rgba(119,207,168,0.14)',
          darkItemSelectedColor: '#e8efea',
        },
      },
    }),
    [mode],
  )

  return (
    <ThemeContext.Provider value={{ mode, toggle }}>
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </ThemeContext.Provider>
  )
}

export function useThemeMode() {
  return useContext(ThemeContext)
}
