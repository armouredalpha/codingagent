// All shared types for robo-assess GUI.

export type TabId = 'config' | 'dashboard' | 'run' | 'questions' | 'review' | 'qdrant'

export interface QdrantPoint {
  _point_id?: number       // numeric Qdrant point ID — injected by scroll handler
  question_id: string
  status: 'approved' | 'rejected'
  topic?: string
  difficulty?: string
  estimated_time_minutes?: number
  question?: string
  context?: string
  files_to_edit?: string[]
  notes?: string[]
  tasks?: string[]
  skill?: string | string[]
  generated_at?: string   // ISO-8601 timestamp from run_metadata / folder name / file mtime
}
export type Difficulty = 'easy' | 'medium' | 'hard'
export type SupervisorVerdict = 'APPROVED' | 'REJECTED'

// Pipeline NDJSON events
export interface RunStartEvent {
  event: 'run_start'
  run_id: string
  topic: string
}
export interface StageStartEvent {
  event: 'stage_start'
  stage: string
  loop?: number
  target?: number
  skill_count?: number
  [key: string]: unknown
}
export interface StageDoneEvent {
  event: 'stage_done'
  stage: string
  tokens_in?: number
  tokens_out?: number
  cost?: number
  verdict?: string
  score?: number
  skill_count?: number
}
export interface StageProgressEvent {
  event: 'stage_progress'
  stage: 'generate'
  generated: number
  tokens_in?: number
  tokens_out?: number
}
export interface QuestionAcceptedEvent {
  event: 'question_accepted'
  question_id: string
  title: string
  difficulty: Difficulty
  confidence: number
  total_accepted: number
}
export interface QuestionRejectedEvent {
  event: 'question_rejected'
  question_id: string
  title: string
  failure_class: string
  issues: string[]
}
export interface RunCompleteEvent {
  event: 'run_complete'
  run_id: string
  topic: string
  loop: number
  generated: number
  approved: number
  rejected: number
  coverage_pct: number
  supervisor_verdict: SupervisorVerdict
  supervisor_score: number
  cost_usd: number
  cost_breakdown: Record<string, number>
  output_dir: string
}
export interface ErrorEvent {
  event: 'error'
  stage: string
  message: string
  retryable: boolean
}
export interface ProcessExitEvent {
  event: 'process_exit'
  code: number | null
}
export type PipelineEvent =
  | RunStartEvent
  | StageStartEvent
  | StageDoneEvent
  | StageProgressEvent
  | QuestionAcceptedEvent
  | QuestionRejectedEvent
  | RunCompleteEvent
  | ErrorEvent

// DB rows (logs/runs.db)
export interface RunRow {
  run_id: string
  topic: string
  started_at: string
  finished_at: string
  n_questions: number
  n_approved: number
  supervisor: string | null
  score: number | null
}
export interface EventRow {
  id: number
  run_id: string
  agent: string
  status: string
  ts: string
  detail: string
}
export interface QuestionTraceRow {
  question_id: string
  agent: string
  decision: string
  reason: string
  ts: string
}

// Dashboard
export interface DashboardKpis {
  totalRuns: number
  totalQuestions: number
  approved: number
  rejected: number
  approvalRate: number
  avgCostPerRun: number
}

// Output file shapes
export interface UsageHistoryEntry {
  run_id: string
  topic: string
  created_at: string
  num_questions: number
  num_approved: number
  supervisor_status: string
  duration_seconds: number
  model: string
  provider: string
  total_calls: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  avg_cost_per_question_usd: number
  heaviest_agent: string
  price_input_per_million_usd?: number
  price_output_per_million_usd?: number
  loop_num?: number
}
export interface RunOutputMeta {
  dir: string
  run_id: string
  topic: string
  loop_num: number
  created_at: string
  num_questions: number
  num_approved: number
  num_rejected: number
  supervisor_status: string
  duration_seconds: number
  estimated_cost_usd: number
}
export interface TokenUsageSummary {
  model: string
  provider: string
  total_calls: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  avg_tokens_per_question: number
  estimated_cost_usd: number
  avg_cost_per_question_usd: number
  heaviest_agent: string
  price_input_per_million_usd?: number
  price_output_per_million_usd?: number
}
export interface RunMetadata {
  run_id: string
  topic: string
  loop_num: number
  created_at: string
  md_hash: string
  md_file: string
  num_questions: number
  num_approved: number
  num_rejected: number
  supervisor_status: string
  duration_seconds: number
  token_usage: TokenUsageSummary
}
export interface QuestionRow {
  question_id: string
  topic: string
  difficulty: Difficulty
  estimated_time_minutes: number
  question: string
  context: string
  files_to_edit: string[]
  notes: string[]
  tasks: string[]
  skill: string
  run_id: string
  run_dir: string
  status: 'approved' | 'rejected'
  boilerplate_code?: string
}
export interface SupervisorVerdictReport {
  supervisor_status: string
  validation_score: number
  issues: string[]
  failing_question_ids: string[]
  question_feedback: Record<string, string>
}
export interface ConfidenceReport {
  run_id: string
  topic: string
  approved: number
  total: number
  questions: {
    question_id: string
    difficulty: string
    confidence: number
    status: string
    breakdown: Record<string, unknown>
    student_confidence?: number
  }[]
}
export interface CoverageMatrixReport {
  matrix: Record<string, boolean>
}
export interface TokenReport {
  model: string
  provider: string
  total_calls: number
  total_input_tokens: number
  total_output_tokens: number
  estimated_cost_usd: number
  avg_cost_per_question_usd: number
  heaviest_agent: string
  by_agent: Record<string, { calls: number; input: number; output: number; total: number; cost_usd: number }>
  per_question: Record<string, { tokens: number; input: number; output: number; cost_usd: number; attempts: number }>
}
export interface RunReports {
  supervisor: SupervisorVerdictReport
  confidence: ConfidenceReport
  coverage: CoverageMatrixReport
  tokens: TokenReport
}

// Config
export interface FullConfig {
  provider: string
  model: string
  temperature: number
  max_tokens: number
  cheap_model: string | null
  cheap_provider: string | null
  agent_models: Record<string, string>
  num_questions: number
  difficulty_distribution: { easy: number; medium: number; hard: number }
  over_generation_factor: number
  max_regeneration_attempts: number
  generation_concurrency: number
  coverage_target: number
  auto_scale_questions: boolean
  max_questions: number
  min_confidence: number
  similarity_reject_threshold: number
  min_realism_score: number
  critic_batch_size: number
  quality_bar: {
    require_discriminating: boolean
    require_judge_approve: boolean
    max_similarity: number
    require_in_scope: boolean
    min_difficulty_fit: number
  }
  grading_backend: string
  sandbox_image: string
  sandbox_timeout_s: number
  sandbox_warmup_s: number
  sandbox_cpus: string
  sandbox_memory: string
  sandbox_pids_limit: number
  max_planner_steps: number
  human_review_enabled: boolean
  human_review_mode: string
  human_review_confidence_min: number
  human_review_confidence_max: number
  pricing: { input_per_million_tokens: number; output_per_million_tokens: number }
  [key: string]: unknown
}
export interface AppConfig {
  provider: string
  connected: boolean
  modelRoute: { generator: string; supervisor: string; judge: string }
  dbPath: string
  dbRows: number | null
  sessionCost: number
}
export interface LintReport {
  path: string
  word_count: number
  section_count: number
  status: 'PASS' | 'WARN' | 'FAIL'
  message: string
}

// Review / Eval
export interface EvalAnnotation {
  approved: boolean | null
  notes: string
}
export interface EvalQuestion extends QuestionRow {
  annotation: EvalAnnotation
}
export interface EvalSet {
  name: string
  created_at: string
  questions: EvalQuestion[]
}
export interface EvalSetMeta {
  name: string
  created_at: string
  count: number
  annotated: number
}

// Export
export type ExportFormat = 'json' | 'xlsx' | 'docx'
export interface ExportOptions {
  format: ExportFormat
  includeSolution?: boolean
}
