import {
  AskQuestionRequest,
  AskQuestionResponse,
  GenerateQuizRequest,
  GenerateQuizResponse,
  EvaluateQuizRequest,
  QuizEvaluationResponse,
  GetDocumentInfoResponse,
  GetPageRenderResponse,
  GetPageTextResponse,
  UpdateProgressRequest,
  UpdateProgressResponse,
  ListDocumentsResponse,
  DeleteDocumentResponse,
  StorageStatsResponse,
  AccountProgressResponse,
  RevisionSuggestionsResponse,
} from "../types/types";

// Replace this with your actual API base URL
const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") + "/api/v1";

// ================================
// Helper Functions
// ================================

const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Network error" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  return response.json();
};

const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  return handleResponse(response);
};

// ================================
// Document API
// ================================

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response);
};

export const getDocumentInfo = async (
  documentId: string
): Promise<GetDocumentInfoResponse> => {
  return apiCall(`/documents/${documentId}`);
};

export const getDocuments = async () => {
  return apiCall("/documents/list");
};

// ================================
// PDF API
// ================================

export const getPageRender = async (
  documentId: string,
  pageNumber: number
): Promise<GetPageRenderResponse> => {
  return apiCall(`/pdf/${documentId}/page/${pageNumber}/render`);
};

export const getPageText = async (
  documentId: string,
  pageNumber: number
): Promise<GetPageTextResponse> => {
  return apiCall(`/pdf/${documentId}/page/${pageNumber}/text`);
};

// ================================
// Chat API
// ================================

export const askQuestion = async (
  request: AskQuestionRequest
): Promise<AskQuestionResponse> => {
  return apiCall("/chat/ask", {
    method: "POST",
    body: JSON.stringify(request),
  });
};

// ================================
// Quiz API
// ================================

export const generateQuiz = async (
  request: GenerateQuizRequest
): Promise<GenerateQuizResponse> => {
  return apiCall("/quiz/generate", {
    method: "POST",
    body: JSON.stringify(request),
  });
};

export const evaluateQuiz = async (
  request: EvaluateQuizRequest
): Promise<QuizEvaluationResponse> => {
  const { questions, ...requestData } = request;
  return apiCall("/quiz/evaluate", {
    method: "POST",
    body: JSON.stringify({
      request: requestData,
      questions: questions,
    }),
  });
};

// ================================
// Progress Tracking API
// ================================

export const updateProgress = async (
  request: UpdateProgressRequest
): Promise<UpdateProgressResponse> => {
  return apiCall("/progress/update", {
    method: "POST",
    body: JSON.stringify(request),
  });
};

// ================================
// Document Management API
// ================================

export const listDocuments = async (): Promise<ListDocumentsResponse> => {
  return apiCall("/documents/list");
};

export const deleteDocument = async (documentId: string): Promise<DeleteDocumentResponse> => {
  return apiCall(`/documents/${documentId}`, {
    method: "DELETE",
  });
};

export const getStorageStats = async (): Promise<StorageStatsResponse> => {
  return apiCall("/documents/stats/storage");
};

// ================================
// Progress API
// ================================

export const getAccountProgress = async (): Promise<AccountProgressResponse> => {
  return apiCall("/progress/account");
};

export const getRevisionSuggestions = async (): Promise<RevisionSuggestionsResponse> => {
  return apiCall("/progress/suggestions");
};

// Get quiz stats for a specific document
export const getDocumentQuizStats = async (documentId: string) => {
  return apiCall(`/quiz/stats/${documentId}`);
};

// Get revision stats for a specific document
export const getDocumentRevisionStats = async (documentId: string) => {
  return apiCall(`/progress/document/${documentId}/revisions`);
};