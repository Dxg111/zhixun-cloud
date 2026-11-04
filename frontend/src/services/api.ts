import Taro from '@tarojs/taro'

// 由 frontend/config/dev.ts、frontend/config/prod.ts 中的 defineConstants 按环境注入
declare const API_BASE_URL: string

const BASE_URL = API_BASE_URL

const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

/* ---- 登录就绪机制：确保页面在登录完成后再请求需要鉴权的接口 ---- */
let _loginResolve: () => void
const _loginReady = new Promise<void>((resolve) => { _loginResolve = resolve })

/** 等待登录流程完成（无论成功或失败） */
export function waitForLogin(): Promise<void> { return _loginReady }

/** 标记登录流程已结束 */
export function resolveLogin() { _loginResolve() }

interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

/** 过滤开发者工具产生的临时头像地址，避免图片请求 404 */
export function getUsableAvatarUrl(url?: string | null): string {
  if (!url) return ''
  if (
    url.startsWith('http://tmp/') ||
    url.includes('/__tmp__/') ||
    url.includes('127.0.0.1') ||
    url.includes('localhost')
  ) {
    return ''
  }
  return url
}

/** 获取本地存储的 token */
export function getToken(): string {
  return Taro.getStorageSync(TOKEN_KEY) || ''
}

/** 保存 token */
export function setToken(token: string) {
  Taro.setStorageSync(TOKEN_KEY, token)
}

/** 清除 token */
export function clearToken() {
  Taro.removeStorageSync(TOKEN_KEY)
  Taro.removeStorageSync(USER_KEY)
}

/** 获取本地缓存的用户信息 */
export function getCachedUser(): UserBrief | null {
  const raw = Taro.getStorageSync(USER_KEY)
  return raw || null
}

/** 缓存用户信息 */
export function setCachedUser(user: UserBrief) {
  Taro.setStorageSync(USER_KEY, user)
}

export async function request<T = any>(
  url: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    timeout?: number
  } = {},
): Promise<T> {
  const { method = 'GET', data, timeout = 120000 } = options

  const header: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = getToken()
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  const res = await Taro.request({
    url: `${BASE_URL}${url}`,
    method,
    data,
    header,
    timeout,
  })

  const body = res.data as ApiResponse<T>

  // 401 未认证 — 清除本地凭证
  if (body.code === 4010) {
    clearToken()
    throw new Error('登录已过期，请重新进入小程序')
  }

  if (body.code !== 0) {
    throw new Error(body.message || '请求失败')
  }

  return body.data
}

/* ---- 核心业务 API ---- */

/** 生成题库（异步任务模式） */
export function generateQuizAsync(
  userInput: string,
  questionCount = 5,
  docId?: string,
  generateImages = false,
) {
  return request<{ task_id: string }>('/quiz/generate/async', {
    method: 'POST',
    data: {
      user_input: userInput,
      question_count: questionCount,
      difficulty: 'mixed',
      doc_id: docId,
      generate_images: generateImages,
    },
  })
}

/** 查询出题任务状态 */
export function getQuizTaskStatus(taskId: string) {
  return request<QuizTaskStatus>(`/quiz/task/${taskId}`)
}

/** 轮询等待出题任务完成 */
export function pollQuizTask(
  taskId: string,
  onProgress?: (status: string) => void,
  intervalMs = 8000,
  maxAttempts = 100,
): Promise<QuizData> {
  return new Promise((resolve, reject) => {
    let attempts = 0
    const timer = setInterval(async () => {
      attempts++
      try {
        const res = await getQuizTaskStatus(taskId)
        onProgress?.(res.status)

        if (res.status === 'completed' && res.result) {
          clearInterval(timer)
          resolve(res.result)
        } else if (res.status === 'failed') {
          clearInterval(timer)
          reject(new Error(res.error_message || '题目生成失败'))
        } else if (attempts >= maxAttempts) {
          clearInterval(timer)
          reject(new Error('生成超时，请稍后重试'))
        }
      } catch (err) {
        clearInterval(timer)
        reject(err)
      }
    }, intervalMs)
  })
}

/** 生成题库（同步，保留兼容） */
export function generateQuiz(userInput: string, questionCount = 5, generateImages = false) {
  return request<QuizData>('/quiz/generate', {
    method: 'POST',
    data: {
      user_input: userInput,
      question_count: questionCount,
      difficulty: 'mixed',
      generate_images: generateImages,
    },
    timeout: 600000,
  })
}

/** 生成复盘报告 */
export function generateReport(params: {
  quiz_id: string
  topic: string
  questions: Question[]
  answer_records: AnswerRecord[]
}) {
  return request<ReportData>('/report/generate', {
    method: 'POST',
    data: params,
    timeout: 600000,
  })
}

/* ---- 用户 API ---- */

/** 微信登录 */
export function loginByCode(code: string) {
  return request<LoginResponse>('/user/login', {
    method: 'POST',
    data: { code },
  })
}

/** 上传小程序临时头像，返回持久化后的可访问地址 */
export function uploadUserAvatar(filePath: string) {
  const token = getToken()
  return Taro.uploadFile({
    url: `${BASE_URL}/user/avatar`,
    filePath,
    name: 'file',
    timeout: 60000,
    header: token ? { Authorization: `Bearer ${token}` } : {},
  }).then((res) => {
    let body: ApiResponse<{ avatar_url: string }>
    try {
      body = JSON.parse(res.data)
    } catch {
      throw new Error('头像上传失败，请稍后重试')
    }
    if (body.code !== 0) {
      throw new Error(body.message || '头像上传失败')
    }
    return body.data.avatar_url
  })
}

/** 获取用户资料（含统计） */
export function getUserProfile() {
  return request<UserProfile>('/user/profile')
}

/** 更新用户资料 */
export function updateUserProfile(data: { nickname?: string; avatar_url?: string }) {
  return request<null>('/user/profile', {
    method: 'PUT',
    data,
  })
}

/** 获取闯关历史（分页） */
export function getQuizHistory(page = 1, pageSize = 10) {
  return request<QuizHistoryList>(`/user/quizzes?page=${page}&page_size=${pageSize}`)
}

/** 获取闯关详情 */
export function getQuizDetail(quizId: string) {
  return request<QuizDetailResponse>(`/user/quizzes/${quizId}`)
}

/* ---- 知识库 API ---- */

/** 上传知识库文档（PDF/Word/Markdown/文本） */
export function uploadKnowledgeDocument(filePath: string, fileName: string): Promise<KnowledgeUploadResponse> {
  const token = getToken()
  const header: Record<string, string> = {}
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    Taro.uploadFile({
      url: `${BASE_URL}/knowledge/documents`,
      filePath,
      name: 'file',
      fileName,
      header,
      timeout: 120000,
      success: (res) => {
        try {
          const body = JSON.parse(res.data) as ApiResponse<KnowledgeUploadResponse>
          if (body.code === 4010) {
            clearToken()
            reject(new Error('登录已过期，请重新进入小程序'))
            return
          }
          if (body.code !== 0) {
            reject(new Error(body.message || '上传失败'))
            return
          }
          resolve(body.data)
        } catch (e) {
          reject(new Error('上传响应解析失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败')),
    })
  })
}

/** 获取知识库文档列表 */
export function getKnowledgeDocuments() {
  return request<KnowledgeListResponse>('/knowledge/documents')
}

/** 查询知识库文档处理状态 */
export function getKnowledgeDocumentStatus(docId: string) {
  return request<KnowledgeDocumentStatus>(`/knowledge/documents/${docId}`)
}

/** 删除知识库文档 */
export function deleteKnowledgeDocument(docId: string) {
  return request<null>(`/knowledge/documents/${docId}`, {
    method: 'DELETE',
  })
}

/* ---- 类型定义 ---- */

export interface QuestionOption {
  key: string
  text: string
}

export interface Question {
  id: string
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: 'easy' | 'medium' | 'hard'
  image_url?: string | null
}

export interface QuizData {
  quiz_id: string
  title: string
  summary: string
  questions: Question[]
  image_notice?: string | null
}

export interface QuizTaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result: QuizData | null
  error_message: string | null
}

export interface AnswerRecord {
  question_id: string
  selected_answers: string[]
  is_correct: boolean
  duration_ms: number
}

export interface ReportData {
  accuracy: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: string[]
  advice: string[]
  share_quote: string
}

export interface UserBrief {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
}

export interface LoginResponse {
  token: string
  user: UserBrief
}

export interface UserProfile {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
  quiz_count: number
  correct_count: number
  average_accuracy: number
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  accuracy: number
  question_count: number
  created_at: string
}

export interface QuizHistoryList {
  items: QuizHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface QuizDetailResponse {
  quiz_id: string
  title: string
  summary: string
  user_input?: string
  questions: Question[]
  answer_records?: AnswerRecord[]
  report?: ReportData
  created_at: string
}

/* ---- 知识库类型定义 ---- */

export type KnowledgeDocumentStatusEnum = 'processing' | 'ready' | 'failed'

export interface KnowledgeUploadResponse {
  doc_id: string
  file_name: string
  status: KnowledgeDocumentStatusEnum
}

export interface KnowledgeDocumentItem {
  doc_id: string
  file_name: string
  file_type: string
  file_size: number
  status: KnowledgeDocumentStatusEnum
  chunk_count: number
  error_message: string | null
  created_at: string
}

export interface KnowledgeListResponse {
  items: KnowledgeDocumentItem[]
}

export interface KnowledgeDocumentStatus {
  doc_id: string
  file_name: string
  status: KnowledgeDocumentStatusEnum
  chunk_count: number
  error_message: string | null
}

/* ---- 企业员工端 API ---- */

const EMPLOYEE_TOKEN_KEY = 'employeeToken'
const EMPLOYEE_USER_KEY = 'employeeUser'

export interface EmployeeInfo {
  id: number
  tenant_code: string
  employee_no: string
  name: string
  org_path: string
}

export interface EmployeeLoginResponse {
  token: string
  employee: EmployeeInfo
}

export interface EmployeeJoinRequest {
  id: number
  tenant_code: string
  tenant_name: string
  user_id: number
  name: string
  employee_no: string
  org_id: number | null
  org_path: string
  role: string
  remark: string | null
  status: 'pending' | 'approved' | 'rejected'
  reject_reason: string | null
  reviewed_by: string | null
  reviewed_at: string
  created_at: string
}

export interface EmployeeMembership {
  status: 'none' | 'pending' | 'rejected' | 'approved' | 'disabled'
  tenant_code: string | null
  tenant_name: string | null
  employee: EmployeeInfo | null
  request: EmployeeJoinRequest | null
  message: string
}

export interface EmployeeExamItem {
  id: number
  title: string
  question_count: number
  duration_minutes: number
  pass_score: number
  max_attempts: number
  start_at?: string | null
  end_at?: string | null
  status: 'published' | 'closed'
  assigned_at: string
  attempt_id: number | null
  attempt_status: string | null
  attempt_count: number
  score: number | null
  passed: boolean | null
  submitted_at: string | null
}

export interface EmployeeExamListResponse {
  items: EmployeeExamItem[]
}

export interface PaperQuestion {
  id: number
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options: QuestionOption[]
  score: number
}

export interface SavedAnswer {
  question_id: number
  selected: string[]
}

export interface EmployeePaperResponse {
  attempt_id: number
  exam_id: number
  title: string
  duration_minutes: number
  expires_at: string
  questions: PaperQuestion[]
  saved_answers: SavedAnswer[]
}

export interface EmployeeAnswerInput {
  question_id: number
  selected: string[]
  duration_ms: number
}

export interface EmployeeResultDetail {
  question_id: number
  type: 'single' | 'multiple' | 'judge'
  stem: string
  selected: string[]
  answer: string[]
  is_correct: boolean
  explanation: string
  score: number
}

export interface EmployeeResultResponse {
  attempt_id: number
  exam_id: number
  title: string
  score: number
  passed: boolean
  correct_count: number
  total_count: number
  submitted_at: string
  details: EmployeeResultDetail[]
}

export function getEmployeeToken(): string {
  return Taro.getStorageSync(EMPLOYEE_TOKEN_KEY) || ''
}

export function setEmployeeAuth(token: string, employee: EmployeeInfo) {
  Taro.setStorageSync(EMPLOYEE_TOKEN_KEY, token)
  Taro.setStorageSync(EMPLOYEE_USER_KEY, employee)
}

export function getEmployeeUser(): EmployeeInfo | null {
  return Taro.getStorageSync(EMPLOYEE_USER_KEY) || null
}

export function clearEmployeeAuth() {
  Taro.removeStorageSync(EMPLOYEE_TOKEN_KEY)
  Taro.removeStorageSync(EMPLOYEE_USER_KEY)
}

export async function employeeRequest<T = any>(
  url: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    timeout?: number
  } = {},
): Promise<T> {
  const { method = 'GET', data, timeout = 120000 } = options
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getEmployeeToken()
  if (token) header.Authorization = `Bearer ${token}`

  const res = await Taro.request({
    url: `${BASE_URL}${url}`,
    method,
    data,
    header,
    timeout,
  })

  const body = res.data as ApiResponse<T>
  if (body.code === 4010) {
    clearEmployeeAuth()
    throw new Error('登录已过期，请重新进入企业培训')
  }
  if (body.code !== 0) {
    throw new Error(body.message || '请求失败')
  }
  return body.data
}

export function getEmployeeMembership() {
  return request<EmployeeMembership>('/employee/membership')
}

export function submitEmployeeJoinRequest(payload: {
  tenant_code: string
  name: string
  employee_no: string
  remark?: string
}) {
  return request<EmployeeJoinRequest>('/employee/join-requests', {
    method: 'POST',
    data: payload,
  })
}

export function createEmployeeSession() {
  return request<EmployeeLoginResponse>('/employee/session', {
    method: 'POST',
  })
}

export function listEmployeeExams() {
  return employeeRequest<EmployeeExamListResponse>('/employee/exams')
}

export function startEmployeeExam(examId: number) {
  return employeeRequest<EmployeePaperResponse>(`/employee/exams/${examId}/start`, {
    method: 'POST',
  })
}

export function saveEmployeeAnswers(attemptId: number, answers: EmployeeAnswerInput[]) {
  return employeeRequest<null>(`/employee/attempts/${attemptId}/answers`, {
    method: 'PUT',
    data: { answers },
  })
}

export function submitEmployeeExam(attemptId: number, answers: EmployeeAnswerInput[]) {
  return employeeRequest<EmployeeResultResponse>(`/employee/attempts/${attemptId}/submit`, {
    method: 'POST',
    data: { answers },
  })
}

export function getEmployeeResult(attemptId: number) {
  return employeeRequest<EmployeeResultResponse>(`/employee/attempts/${attemptId}/result`)
}

/* ---- 考前知识卡 ---- */

export interface EmployeeCardPoint {
  heading: string
  body: string
}

export interface EmployeeCardItem {
  id: number
  title: string
  excerpt: string
  source: string
  points: EmployeeCardPoint[]
  viewed: boolean
  view_count: number
}

export interface EmployeeCardListResponse {
  items: EmployeeCardItem[]
  total: number
}

export function listEmployeeExamCards(examId: number) {
  return employeeRequest<EmployeeCardListResponse>(`/employee/exams/${examId}/cards`)
}

export function recordEmployeeCardView(cardId: number) {
  return employeeRequest<null>(`/employee/cards/${cardId}/view`, { method: 'POST' })
}

/* ---- 错题重练 ---- */

export interface EmployeeWrongQuestionItem {
  id: number
  question_id: number
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options: QuestionOption[]
  knowledge_point: string
  wrong_count: number
  correct_streak: number
  mastered: boolean
  last_wrong_at: string
}

export interface EmployeeWrongQuestionListResponse {
  items: EmployeeWrongQuestionItem[]
  total: number
}

export interface EmployeeWrongRetryResponse {
  is_correct: boolean
  answer: string[]
  explanation: string
  correct_streak: number
  mastered: boolean
}

export function listEmployeeWrongQuestions(mastered?: boolean) {
  const query = mastered === undefined ? '' : `?mastered=${mastered}`
  return employeeRequest<EmployeeWrongQuestionListResponse>(
    `/employee/wrong-questions${query}`,
  )
}

export function retryEmployeeWrongQuestion(wrongId: number, selected: string[]) {
  return employeeRequest<EmployeeWrongRetryResponse>(
    `/employee/wrong-questions/${wrongId}/retry`,
    { method: 'POST', data: { selected } },
  )
}

export function setEmployeeWrongQuestionMastered(wrongId: number, mastered: boolean) {
  return employeeRequest<{ mastered: boolean }>(
    `/employee/wrong-questions/${wrongId}/master`,
    { method: 'POST', data: { mastered } },
  )
}
