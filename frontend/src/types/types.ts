// ================================
// Chat Types
// ================================

export type ChatMode =
  | "quick_answer"
  | "explain_concept"
  | "step_by_step"
  | "practice_problems"
  | "deep_analysis";

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export interface AskQuestionRequest {
  document_id: string;
  question: string;
  mode: ChatMode;
  page_number?: number;
  history: ChatHistoryItem[];
  session_id?: string;
}

export interface AskQuestionResponse {
  success: boolean;
  answer: string;
  mode: ChatMode;
  error?: string;
  cached_embeddings_used?: boolean;
  // Adaptation B — mode suggestion fields
  suggested_mode?: ChatMode | null;
  suggestion_reason?: string | null;
}

// ================================
// Quiz Types
// ================================

export interface QuizQuestion {
  question: string;
  options: Record<string, string>;
  correct_answer: string;
}

export interface GenerateQuizRequest {
  document_id: string;
  page_number: number;
  num_questions: number;
}

export interface GenerateQuizResponse {
  success: boolean;
  questions: QuizQuestion[];
  error?: string;
}

export interface EvaluateQuizRequest {
  document_id: string;
  page_number: number;
  answers: Record<number, string>;
  questions: QuizQuestion[];
}

export interface QuizEvaluationResponse {
  score: number;
  correct_count: number;
  total_questions: number;
  results: string[];
}

// ================================
// Document Types
// ================================

export interface DocumentMetadata {
  document_id: string;
  user_id: string;
  original_filename: string;
  stored_path: string;
  page_count: number;
  file_size_bytes: number;
  upload_timestamp: string;
  last_accessed: string;
  embeddings_cached: boolean;
}

export interface GetDocumentInfoResponse {
  success: boolean;
  title: string;
  page_count: number;
  error?: string;
}

export interface GetPageRenderResponse {
  success: boolean;
  base64_pdf: string;
  error?: string;
}

export interface GetPageTextResponse {
  success: boolean;
  text: string;
  error?: string;
}

// ================================
// Progress Tracking Types
// ================================

export interface UpdateProgressRequest {
  document_id: string;
  page_number: number;
  interaction_type: "page_view" | "question_asked" | "quiz_completed";
  time_spent: number;
  metadata?: Record<string, any>;
}

export interface UpdateProgressResponse {
  success: boolean;
  error?: string;
}

// ================================
// Document Metadata & Stats Types
// ================================

export interface DocumentStats {
  total_documents: number;
  total_pages: number;
  total_size_bytes: number;
  total_size_mb: number;
  storage_path: string;
  embeddings_storage?: {
    total_documents: number;
    total_chunks: number;
    total_size_mb: number;
  };
}

export interface ProgressResponse {
  total_pages_viewed: number;
  total_questions_asked: number;
  total_quizzes_completed: number;
  average_quiz_score: number;
  study_time_minutes: number;
  last_accessed?: string;
}

// Matches actual backend response shape:
// { document_id, page_number, priority, reasons[], suggestion }
export interface RevisionSuggestion {
  document_id: string;
  page_number: number;
  priority: number;
  reasons: string[];
  suggestion: string;
}

// ================================
// API Response Wrappers
// ================================

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  document: DocumentMetadata;
  embeddings_cached: boolean;
}

export interface ListDocumentsResponse {
  success: boolean;
  documents: DocumentMetadata[];
  total_count: number;
  error?: string;
}

export interface DeleteDocumentResponse {
  success: boolean;
  message: string;
  caches_deleted?: boolean;
  error?: string;
}

export interface StorageStatsResponse {
  success: boolean;
  stats: DocumentStats;
  error?: string;
}

export interface AccountProgressResponse {
  success: boolean;
  progress: ProgressResponse;
  error?: string;
}

// Backend returns a plain array of RevisionSuggestion
export type RevisionSuggestionsResponse = RevisionSuggestion[];

// ================================
// Embeddings / Vector Store Types
// ================================

export interface EmbeddingInfo {
  num_chunks: number;
  embedding_dim: number;
  created_at: string;
  updated_at: string;
}

export interface EmbeddingStatusResponse {
  document_id: string;
  has_embeddings: boolean;
  info?: EmbeddingInfo;
}

export interface CachedDocumentInfo {
  document_id: string;
  num_chunks: number;
  embedding_dim: number;
  created_at: string;
  updated_at: string;
}

export interface ListCachedEmbeddingsResponse {
  cached_documents: CachedDocumentInfo[];
  total_count: number;
}

export interface DeleteEmbeddingResponse {
  success: boolean;
  document_id: string;
  message: string;
}

export interface EmbeddingStorageStatsResponse {
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
  total_size_mb: number;
  storage_path: string;
}

// ================================
// Document Quiz Statistics
// ================================

export interface QuizAttempt {
  quiz_id: string;
  attempted_at: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  time_taken_seconds?: number;
}

export interface DocumentQuizStatsResponse {
  success: boolean;
  document_id: string;
  total_quizzes_taken: number;
  average_score: number;
  best_score: number;
  last_quiz_date?: string;
  recent_attempts: QuizAttempt[];
  total_questions_answered: number;
  total_correct_answers: number;
  error?: string;
}

// ================================
// Document Revision Statistics
// ================================

export interface RevisionSession {
  session_id: string;
  reviewed_at: string;
  pages_reviewed: number[];
  duration_seconds?: number;
}

export interface DocumentRevisionStatsResponse {
  success: boolean;
  document_id: string;
  total_revisions: number;
  last_revision_date?: string;
  next_suggested_revision?: string;
  revision_streak: number;
  recent_sessions: RevisionSession[];
  total_time_spent_seconds: number;
  revision_frequency: "high" | "medium" | "low" | "none";
  mastery_level: number;
  error?: string;
}