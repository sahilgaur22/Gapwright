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
  course_code?: string | null;
  institution?: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  error_message?: string | null;
  created_at: string;
  skills?: SyllabusSkill[];
}

export interface SourceSummary {
  name: string;
  priority: number;
  enabled: boolean;
  attribution_text?: string | null;
  attribution_url?: string | null;
  may_display_listing?: boolean;
  daily_budget: number;
  daily_calls_used: number;
  remaining_budget: number;
  last_run_at?: string | null;
  category?: string;
  supports_location?: boolean;
}

export interface SkillDemandItem {
  skill_id: string;
  name: string;
  category?: string | null;
  postings_count: number;
  demand_pct: number;
  trend_pct?: number;
}

export interface TopSkillsResponse {
  role_query: string;
  location?: string | null;
  total_postings: number;
  analysis_window_days: number;
  trend_window_days: number;
  skills: SkillDemandItem[];
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

  logout: async (): Promise<void> => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("gapwright_token");
      window.dispatchEvent(new Event("storage"));
      try {
        await fetch("/api/auth/logout", { method: "POST" });
      } catch {
        // Silently handle offline/network errors during logout
      }
    }
  },

  // Syllabi
  uploadSyllabus: async (file: File, title: string): Promise<Syllabus> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);

    const url = `${API_BASE}/api/v1/syllabi`;
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
  getTopSkills: async (
    role: string,
    location?: string,
    days = 30,
    limit = 20
  ): Promise<TopSkillsResponse> => {
    const params = new URLSearchParams({
      role,
      days: String(days),
      limit: String(limit),
    });
    if (location && location.toLowerCase() !== "all" && location.toLowerCase() !== "any") {
      params.set("location", location);
    }
    return request(`/api/v1/jobs/skills/top?${params.toString()}`);
  },

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

  // Policy & Governance
  getPolicyOverview: async (): Promise<PolicyOverviewResponse> => {
    return request("/api/v1/policy/overview");
  },

  // Export
  exportReportUrl: (analysisId: string, format: "csv" | "pdf"): string => {
    return `${API_BASE}/api/v1/reports/${analysisId}/export?format=${format}`;
  },

  downloadReport: async (
    analysisId: string,
    format: "csv" | "pdf"
  ): Promise<void> => {
    const url = `${API_BASE}/api/v1/reports/${analysisId}/export?format=${format}`;
    const headers = new Headers();
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("gapwright_token");
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new ApiError(response.status, "Failed to download export report");
    }
    const blob = await response.blob();
    if (typeof window !== "undefined") {
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `gapwright-analysis-${analysisId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    }
  },
};

export interface SystemicSkillGap {
  skill_name: string;
  category?: string | null;
  occurrences: number;
  average_demand_pct: number;
  total_postings: number;
}

export interface InstitutionAlignmentSummary {
  institution: string;
  evaluations_count: number;
  average_gap_pct: number;
  average_coverage_pct: number;
}

export interface RoleMarketComparison {
  role: string;
  evaluations_count: number;
  average_gap_pct: number;
  average_coverage_pct: number;
}

export interface PolicyOverviewResponse {
  total_analyses: number;
  total_institutions: number;
  average_gap_pct: number;
  average_coverage_pct: number;
  top_systemic_missing_skills: SystemicSkillGap[];
  institutions: InstitutionAlignmentSummary[];
  roles: RoleMarketComparison[];
}
