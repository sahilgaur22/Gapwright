/**
 * Typed API Client for Gapwright API Gateway
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SyllabusSkill {
  id: string;
  skill_id: string;
  skill_name: string;
  category?: string | null;
  evidence: string;
}

export interface Syllabus {
  id: string;
  title: string;
  filename: string;
  status: "pending" | "processing" | "ready" | "failed";
  error_message?: string | null;
  created_at: string;
  skills?: SyllabusSkill[];
}

export interface SourceSummary {
  name: string;
  category: string;
  enabled: boolean;
  priority: number;
  supports_location: boolean;
  daily_budget: number;
  calls_today: number;
  budget_exhausted: boolean;
  attribution_text?: string;
  source_url?: string;
}

export interface DemandMetric {
  skill_id: string;
  skill_name: string;
  category?: string | null;
  postings_count: number;
  demand_pct: number;
}

export interface DemandStatsResponse {
  role_query: string;
  location: string;
  total_postings: number;
  window_days: number;
  as_of: string;
  top_skills: DemandMetric[];
}

export interface AnalysisItem {
  skill_id: string;
  skill_name: string;
  category?: string | null;
  kind: "covered" | "missing" | "obsolete";
  demand_count: number;
  demand_pct: number;
  rank: number;
}

export interface Analysis {
  id: string;
  syllabus_id: string;
  role_query: string;
  location: string;
  gap_pct: number;
  coverage_pct: number;
  created_at: string;
  items: AnalysisItem[];
}

export interface SkillRecommendation {
  skill_id: string;
  skill_name: string;
  category?: string | null;
  action: "add" | "drop";
  demand_pct: number;
  trend_pct: number;
  rationale: string;
  suggested_module: string;
  suggested_weeks: number;
}

export interface RecommendationsResponse {
  analysis_id: string;
  syllabus_id: string;
  course_title: string;
  role_query: string;
  location: string;
  gap_pct: number;
  coverage_pct: number;
  skills_to_add: SkillRecommendation[];
  skills_to_drop: SkillRecommendation[];
  summary: string;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  // Add auth token from localStorage if in browser
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("gapwright_token");
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let data: unknown = null;
    try {
      data = await response.json();
      if (typeof data === "object" && data !== null && "detail" in data) {
        errorDetail = String((data as { detail: unknown }).detail);
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(response.status, errorDetail, data);
  }

  return response.json();
}

export const api = {
  // Health
  checkHealth: async (): Promise<{ status: string; database?: string }> => {
    return request("/healthz");
  },

  // Auth
  register: async (email: string, password: string, fullName?: string): Promise<User> => {
    return request("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined" && res.access_token) {
      localStorage.setItem("gapwright_token", res.access_token);
    }
    return res;
  },

  getMe: async (): Promise<User> => {
    return request("/api/v1/auth/me");
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("gapwright_token");
    }
  },

  // Syllabi
  uploadSyllabus: async (file: File, title: string): Promise<Syllabus> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);

    const url = `${API_BASE}/api/v1/syllabi/upload`;
    const headers = new Headers();
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("gapwright_token");
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || "Failed to upload syllabus"
      );
    }
    return response.json();
  },

  listSyllabi: async (): Promise<Syllabus[]> => {
    return request("/api/v1/syllabi");
  },

  getSyllabus: async (id: string): Promise<Syllabus> => {
    return request(`/api/v1/syllabi/${id}`);
  },

  getSyllabusStatus: async (id: string): Promise<Syllabus> => {
    return request(`/api/v1/syllabi/${id}/status`);
  },

  // Sources
  listSources: async (): Promise<SourceSummary[]> => {
    return request("/api/v1/sources");
  },

  // Demand
  getDemand: async (roleQuery: string, location?: string, days = 45): Promise<DemandStatsResponse> => {
    const params = new URLSearchParams({ role_query: roleQuery, days: String(days) });
    if (location) params.set("location", location);
    return request(`/api/v1/jobs/demand?${params.toString()}`);
  },

  // Analysis
  createAnalysis: async (
    syllabusId: string,
    roleQuery: string,
    location?: string,
    remoteOnly = false
  ): Promise<Analysis> => {
    return request("/api/v1/analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        syllabus_id: syllabusId,
        role_query: roleQuery,
        location,
        remote_only: remoteOnly,
      }),
    });
  },

  getAnalysis: async (id: string): Promise<Analysis> => {
    return request(`/api/v1/analysis/${id}`);
  },

  listAnalyses: async (syllabusId?: string): Promise<Analysis[]> => {
    const qs = syllabusId ? `?syllabus_id=${syllabusId}` : "";
    return request(`/api/v1/analysis${qs}`);
  },

  getRecommendations: async (
    analysisId: string,
    maxAdd = 5,
    maxDrop = 5
  ): Promise<RecommendationsResponse> => {
    return request(
      `/api/v1/analysis/${analysisId}/recommendations?max_add=${maxAdd}&max_drop=${maxDrop}`
    );
  },
};
