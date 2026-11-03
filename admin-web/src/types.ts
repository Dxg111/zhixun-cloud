export type QuestionType = 'single' | 'multiple' | 'judge'
export type QuestionStatus = 'draft' | 'approved' | 'rejected'
export type ExamStatus = 'draft' | 'published' | 'closed'
export type EmployeeStatus = 'active' | 'disabled'
export type InviteStatus = 'bound' | 'unbound'
export type DocStatus = 'processing' | 'ready' | 'failed'
export type CardStatus = 'draft' | 'published' | 'offline'
export type ExportStatus = 'processing' | 'ready' | 'failed'

export interface QuestionOption {
  key: string
  text: string
}

export interface Question {
  id: string
  bank: string
  type: QuestionType
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledgePoint: string
  difficulty: 'easy' | 'medium' | 'hard'
  source: string
  status: QuestionStatus
  aiMeta: string
  note?: string
}

export interface Exam {
  id: string
  title: string
  bank: string
  status: ExamStatus
  assigned: number
  completed: number
  passRate: number | null
  endsAt: string
  questionCount: number
  cardViewRate: number
  cardTitles?: string[]
  distribution: number[]
  weakPoints: string[]
}

export interface Employee {
  id: string
  name: string
  dept: string
  role: string
  status: EmployeeStatus
  invite: InviteStatus
}

export interface KnowledgeDoc {
  id: string
  name: string
  type: string
  size: string
  status: DocStatus
  chunks: number
  uploadedAt: string
}

export interface KnowledgeCard {
  id: string
  title: string
  status: CardStatus
  excerpt: string
  source: string
  viewRate: number
  updatedAt: string
}

export interface ExportTask {
  id: string
  file: string
  type: string
  status: ExportStatus
  rows: number
  createdAt: string
}
