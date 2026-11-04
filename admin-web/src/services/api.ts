import type { QuestionOption } from '../types'

const API_BASE = '/api/v1'
const TOKEN_KEY = 'admin-web-token'
const USER_KEY = 'admin-web-user'

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface AdminUser {
  id: number
  name: string
  role: string
  tenant_code: string
}

export interface AdminMe {
  login_name: string
  name: string
  role: string
  tenant_code: string
}

export interface AdminLoginResponse {
  token: string
  user: AdminUser
}

export interface AdminUserItem {
  id: number
  tenant_code: string
  login_name: string
  display_name: string
  role: string
  status: 'active' | 'disabled'
  created_at: string
  updated_at: string
}

export interface AdminUserListResponse {
  items: AdminUserItem[]
}

export type ApiQuestionType = 'single' | 'multiple' | 'judge'
export type ApiQuestionStatus = 'draft' | 'approved' | 'rejected'

export interface ApiQuestion {
  id: number
  tenant_code: string
  bank_id: number
  bank_name: string
  type: ApiQuestionType
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: 'easy' | 'medium' | 'hard'
  source: string
  status: ApiQuestionStatus
  ai_meta: string
  review_note?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
  created_at: string
  updated_at: string
}

export interface QuestionBankItem {
  id: number
  name: string
  description?: string | null
  approved_count: number
  total_count: number
}

export interface QuestionBankListResponse {
  items: QuestionBankItem[]
  total: number
}

export interface QuestionCounts {
  all: number
  draft: number
  approved: number
  rejected: number
}

export interface QuestionListResponse {
  items: ApiQuestion[]
  total: number
  page: number
  page_size: number
  counts: QuestionCounts
}

export type KnowledgeCardStatus = 'draft' | 'published' | 'offline'

export interface AdminKnowledgeCard {
  id: number
  tenant_code: string
  doc_id?: number | null
  doc_name: string
  title: string
  excerpt: string
  source: string
  status: KnowledgeCardStatus
  view_rate: number
  created_by?: string | null
  published_at?: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeCardPoint {
  heading: string
  body: string
}

export interface AdminKnowledgeCardDetail extends AdminKnowledgeCard {
  points: KnowledgeCardPoint[]
}

export interface KnowledgeCardListResponse {
  items: AdminKnowledgeCard[]
  total: number
  page: number
  page_size: number
}

export interface OrgUnitItem {
  id: number
  parent_id: number | null
  name: string
  path: string
  sort: number
  employee_count: number
}

export interface OrgUnitListResponse {
  items: OrgUnitItem[]
}

export interface EmployeeItem {
  id: number
  tenant_code: string
  org_id: number | null
  user_id: number | null
  employee_no: string
  name: string
  role: string
  status: 'active' | 'disabled'
  org_path: string
  created_at: string
}

export interface EmployeeListResponse {
  items: EmployeeItem[]
  total: number
  page: number
  page_size: number
}

export interface EmployeeImportResult {
  imported: number
  skipped: number
  errors: string[]
}

export interface AdminDocument {
  id: number
  tenant_code: string
  file_name: string
  file_type: string
  file_size: number
  status: 'processing' | 'ready' | 'failed'
  chunks: number
  error_message?: string | null
  has_file?: boolean
  created_at: string
}

export interface AdminDocumentListResponse {
  items: AdminDocument[]
  total: number
}

export interface AdminExam {
  id: number
  tenant_code: string
  title: string
  bank_id: number
  bank_name: string
  question_count: number
  pass_score: number
  duration_minutes: number
  max_attempts: number
  start_at?: string | null
  end_at?: string | null
  status: 'draft' | 'published' | 'closed'
  assigned: number
  completed: number
  pass_rate: number
  card_view_rate: number
  created_at: string
}

export interface AdminExamDetail extends AdminExam {
  distribution: number[]
  weak_points: string[]
  card_titles: string[]
}

export type ExamAssignScope = 'all' | 'org' | 'employees'

export interface ExamAssignPayload {
  scope: ExamAssignScope
  org_ids: number[]
  employee_ids: number[]
}

export interface ExamAssignResponse {
  assigned: number
  employee_ids: number[]
}

export interface AdminExamListResponse {
  items: AdminExam[]
  total: number
  page: number
  page_size: number
  counts: Record<string, number>
}

export interface AdminExportTask {
  id: number
  tenant_code: string
  exam_id: number | null
  file_name: string
  export_type: string
  status: 'processing' | 'ready' | 'failed'
  rows: number
  created_at: string
}

export interface AdminExportTaskListResponse {
  items: AdminExportTask[]
  total: number
}

export interface TenantSettings {
  tenant_code: string
  tenant_name: string
  admin_email: string | null
  retention: string
  default_pass_score: number
  default_duration: number
  default_attempts: number
  random_order: string
  notify_assigned: boolean
  notify_result: boolean
  notify_deadline: boolean
  notify_cards: boolean
  updated_at: string
}

export interface GlobalSearchItem {
  type: 'employee' | 'question' | 'exam' | 'card' | 'document'
  id: number
  title: string
  subtitle: string
  status: string
  url: string
}

export interface GlobalSearchResult {
  keyword: string
  total: number
  items: GlobalSearchItem[]
}

export interface DashboardTrendPoint {
  exam_id: number
  label: string
  title: string
  assigned: number
  completed: number
  completion_rate: number
  pass_rate: number
}

export interface DashboardData {
  pending_questions: number
  pending_cards: number
  pending_join_requests: number
  active_exams: number
  completion_rate: number
  recent_exams: AdminExam[]
  trend: DashboardTrendPoint[]
  weak_points: Array<{ name?: string; value?: number }>
}

export interface JoinRequestItem {
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

export interface JoinRequestListResponse {
  items: JoinRequestItem[]
  total: number
  page: number
  page_size: number
}

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Ignore storage failures; the current session still works.
  }
}

export function getStoredUser(): AdminUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as AdminUser) : null
  } catch {
    return null
  }
}

export function setStoredUser(user: AdminUser) {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } catch {
    // Ignore storage failures.
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  } catch {
    // Ignore storage failures.
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new TypeError('无法连接后端服务，请确认后端已启动')
  }

  let payload: ApiResponse<T>
  try {
    payload = (await response.json()) as ApiResponse<T>
  } catch {
    throw new Error(`服务器返回格式异常（HTTP ${response.status}）`)
  }

  if (payload.code === 4010) {
    clearToken()
    throw new Error(payload.message || '登录已过期，请重新登录')
  }

  if (payload.code !== 0) {
    throw new Error(payload.message || `请求失败（HTTP ${response.status}）`)
  }

  return payload.data
}

export function adminLogin(params: {
  tenant_code: string
  login_name: string
  password: string
}) {
  return request<AdminLoginResponse>('/auth/admin/login', {
    method: 'POST',
    body: params,
  })
}

export function fetchAdminMe() {
  return request<AdminMe>('/auth/me')
}

export function listAdmins() {
  return request<AdminUserListResponse>('/admin/admins')
}

export function updateAdminStatus(adminId: number, status: AdminUserItem['status']) {
  return request<AdminUserItem>(`/admin/admins/${adminId}/status`, {
    method: 'PUT',
    body: { status },
  })
}

export function createAdmin(params: {
  login_name: string
  display_name: string
  password: string
}) {
  return request<AdminUserItem>('/admin/admins', {
    method: 'POST',
    body: params,
  })
}

export function resetAdminPassword(adminId: number, newPassword: string) {
  return request<AdminUserItem>(`/admin/admins/${adminId}/reset-password`, {
    method: 'POST',
    body: { new_password: newPassword },
  })
}

export function listQuestions(params: {
  status?: string
  keyword?: string
  bank_id?: number | null
  page?: number
  page_size?: number
}) {
  const query = new URLSearchParams()
  if (params.status && params.status !== 'all') query.set('status', params.status)
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.bank_id) query.set('bank_id', String(params.bank_id))
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))
  return request<QuestionListResponse>(`/admin/questions?${query.toString()}`)
}

export function listQuestionBanks() {
  return request<QuestionBankListResponse>('/admin/questions/banks')
}

export function reviewQuestion(
  questionId: number,
  action: 'approve' | 'reject',
  note?: string,
) {
  return request<ApiQuestion>(`/admin/questions/${questionId}/review`, {
    method: 'POST',
    body: { action, note },
  })
}

export function bulkReviewQuestions(
  ids: number[],
  action: 'approve' | 'reject',
  note?: string,
) {
  return request<{ updated: number }>('/admin/questions/bulk-review', {
    method: 'POST',
    body: { ids, action, note },
  })
}

export function listKnowledgeCards(params: {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
} = {}) {
  const query = new URLSearchParams()
  if (params.status && params.status !== 'all') query.set('status', params.status)
  if (params.keyword) query.set('keyword', params.keyword)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 100))
  return request<KnowledgeCardListResponse>(`/admin/knowledge-cards?${query.toString()}`)
}

export function generateKnowledgeCards(params: {
  doc_id: number
  doc_name: string
  count: number
  style: '操作要点' | '概念解释' | '易错提醒'
}) {
  return request<KnowledgeCardListResponse>('/admin/knowledge-cards/generate', {
    method: 'POST',
    body: params,
  })
}

export function getKnowledgeCardDetail(cardId: number) {
  return request<AdminKnowledgeCardDetail>(`/admin/knowledge-cards/${cardId}`)
}

export function updateKnowledgeCard(
  cardId: number,
  payload: {
    title: string
    excerpt: string
    points: KnowledgeCardPoint[]
  },
) {
  return request<AdminKnowledgeCardDetail>(`/admin/knowledge-cards/${cardId}`, {
    method: 'PUT',
    body: payload,
  })
}

export function updateKnowledgeCardStatus(
  cardId: number,
  status: 'published' | 'offline',
) {
  return request<AdminKnowledgeCard>(`/admin/knowledge-cards/${cardId}/status`, {
    method: 'PUT',
    body: { status },
  })
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: form })
  } catch {
    throw new TypeError('无法连接后端服务，请确认后端已启动')
  }

  let payload: ApiResponse<T>
  try {
    payload = (await response.json()) as ApiResponse<T>
  } catch {
    throw new Error(`服务器返回格式异常（HTTP ${response.status}）`)
  }

  if (payload.code === 4010) {
    clearToken()
    throw new Error(payload.message || '登录已过期，请重新登录')
  }
  if (payload.code !== 0) {
    throw new Error(payload.message || `请求失败（HTTP ${response.status}）`)
  }
  return payload.data
}

export function getDashboard() {
  return request<DashboardData>('/admin/dashboard')
}

export function listOrgUnits() {
  return request<OrgUnitListResponse>('/admin/org-units')
}

export function createOrgUnit(payload: { name: string; parent_id?: number | null }) {
  return request<OrgUnitItem>('/admin/org-units', { method: 'POST', body: payload })
}

export function globalSearch(keyword: string, limit = 5) {
  const query = new URLSearchParams()
  query.set('keyword', keyword)
  query.set('limit', String(limit))
  return request<GlobalSearchResult>(`/admin/search?${query.toString()}`)
}

export function listEmployees(params: {
  org_id?: number | null
  keyword?: string
  page?: number
  page_size?: number
} = {}) {
  const query = new URLSearchParams()
  if (params.org_id) query.set('org_id', String(params.org_id))
  if (params.keyword) query.set('keyword', params.keyword)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 200))
  return request<EmployeeListResponse>(`/admin/employees?${query.toString()}`)
}

export function createEmployee(payload: {
  employee_no: string
  name: string
  org_id?: number | null
  role: string
}) {
  return request<EmployeeItem>('/admin/employees', {
    method: 'POST',
    body: payload,
  })
}

export function importEmployees(file: File) {
  return uploadFile<EmployeeImportResult>('/admin/employees/import', file)
}

export function updateEmployeeStatus(employeeId: number, status: 'active' | 'disabled') {
  return request<EmployeeItem>(`/admin/employees/${employeeId}/status`, {
    method: 'PUT',
    body: { status },
  })
}

export function listJoinRequests(params: {
  status?: 'pending' | 'approved' | 'rejected' | 'all'
  page?: number
  page_size?: number
} = {}) {
  const query = new URLSearchParams()
  query.set('status', params.status ?? 'pending')
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 100))
  return request<JoinRequestListResponse>(`/admin/join-requests?${query.toString()}`)
}

export function approveJoinRequest(
  requestId: number,
  payload: { org_id?: number | null; role: string },
) {
  return request<JoinRequestItem>(`/admin/join-requests/${requestId}/approve`, {
    method: 'POST',
    body: payload,
  })
}

export function rejectJoinRequest(requestId: number, reason: string) {
  return request<JoinRequestItem>(`/admin/join-requests/${requestId}/reject`, {
    method: 'POST',
    body: { reason },
  })
}

export function listAdminDocuments() {
  return request<AdminDocumentListResponse>('/admin/documents')
}

export function uploadAdminDocument(file: File) {
  return uploadFile<AdminDocument>('/admin/documents', file)
}

export function generateQuestionsFromDocument(
  docId: number,
  payload: {
    bank_name: string
    question_count: number
    difficulty: 'easy' | 'medium' | 'hard' | 'mixed'
  },
) {
  return request<{ created: number; bank_id: number; bank_name: string }>(
    `/admin/documents/${docId}/generate-questions`,
    { method: 'POST', body: payload },
  )
}

export function deleteAdminDocument(docId: number) {
  return request<null>(`/admin/documents/${docId}`, { method: 'DELETE' })
}

export function listAdminExams(params: {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
} = {}) {
  const query = new URLSearchParams()
  if (params.status && params.status !== 'all') query.set('status', params.status)
  if (params.keyword) query.set('keyword', params.keyword)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 50))
  return request<AdminExamListResponse>(`/admin/exams?${query.toString()}`)
}

export function createAdminExam(payload: {
  title: string
  bank_name: string
  question_count: number
  pass_score: number
  duration_minutes: number
  max_attempts: number
  start_at?: string | null
  end_at?: string | null
}) {
  return request<AdminExam>('/admin/exams', { method: 'POST', body: payload })
}

export function getAdminExam(examId: number) {
  return request<AdminExamDetail>(`/admin/exams/${examId}`)
}

export function publishAdminExam(examId: number) {
  return request<AdminExam>(`/admin/exams/${examId}/publish`, { method: 'POST' })
}

export function closeAdminExam(examId: number) {
  return request<AdminExam>(`/admin/exams/${examId}/close`, { method: 'POST' })
}

export function getExamKnowledgeCards(examId: number) {
  return request<AdminKnowledgeCard[]>(`/admin/exams/${examId}/knowledge-cards`)
}

export function updateExamKnowledgeCards(examId: number, cardIds: number[]) {
  return request<AdminKnowledgeCard[]>(`/admin/exams/${examId}/knowledge-cards`, {
    method: 'PUT',
    body: { card_ids: cardIds },
  })
}

export function getExamAssignments(examId: number) {
  return request<{ employee_ids: number[]; assigned: number }>(
    `/admin/exams/${examId}/assignments`,
  )
}

export function updateExamAssignments(examId: number, payload: ExamAssignPayload) {
  return request<ExamAssignResponse>(`/admin/exams/${examId}/assignments`, {
    method: 'PUT',
    body: payload,
  })
}

export function exportAdminExam(examId: number) {
  return request<AdminExportTask>(`/admin/exams/${examId}/export`, { method: 'POST' })
}

export function listExportTasks() {
  return request<AdminExportTaskListResponse>('/admin/exports')
}

export async function downloadExportTask(taskId: number): Promise<Blob> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_BASE}/admin/exports/${taskId}/download`, { headers })
  } catch {
    throw new TypeError('无法连接后端服务，请确认后端已启动')
  }

  if (!response.ok) {
    let message = `下载失败（HTTP ${response.status}）`
    try {
      const payload = (await response.json()) as ApiResponse<null>
      if (payload.message) message = payload.message
    } catch {
      // ignore non-JSON error body
    }
    throw new Error(message)
  }
  return response.blob()
}

export function getTenantSettings() {
  return request<TenantSettings>('/admin/settings')
}

export function updateTenantSettings(payload: {
  tenant_name: string
  admin_email?: string | null
  retention: string
  default_pass_score: number
  default_duration: number
  default_attempts: number
  random_order: '随机' | '固定'
  notify_assigned: boolean
  notify_result: boolean
  notify_deadline: boolean
  notify_cards: boolean
}) {
  return request<TenantSettings>('/admin/settings', { method: 'PUT', body: payload })
}
