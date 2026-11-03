export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/quiz/index',
    'pages/report/index',
    'pages/profile/index',
    'pages/knowledge/index',
    'pages/employee-login/index',
    'pages/employee-exams/index',
    'pages/employee-exam/index',
    'pages/employee-result/index',
    'pages/employee-cards/index',
    'pages/employee-wrong/index',
  ],
  networkTimeout: {
    request: 600000,
    connectSocket: 600000,
    uploadFile: 600000,
    downloadFile: 600000,
  },
  window: {
    backgroundTextStyle: 'dark',
    backgroundColor: '#eceee6',
    navigationBarBackgroundColor: '#eceee6',
    navigationBarTitleText: '智训云',
    navigationBarTextStyle: 'black',
  },
  tabBar: {
    color: '#6b7166',
    selectedColor: '#1f4a38',
    backgroundColor: '#fbfaf3',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '学习',
        iconPath: 'assets/tab-home.png',
        selectedIconPath: 'assets/tab-home-active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tab-me.png',
        selectedIconPath: 'assets/tab-me-active.png',
      },
    ],
  },
})
