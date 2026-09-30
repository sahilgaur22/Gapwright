import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AnalysisDetailPage from "../app/analysis/[id]/page";
import AnalysisIndexPage from "../app/analysis/page";
import { api, Analysis, RecommendationsResponse, Syllabus } from "@/lib/api";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock API client
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getAnalysis: vi.fn(),
      getRecommendations: vi.fn(),
      listAnalyses: vi.fn(),
      listSyllabi: vi.fn(),
      createAnalysis: vi.fn(),
    },
  };
});

const mockAnalysis: Analysis = {
  id: "ana-123",
  syllabus_id: "syl-456",
  role_query: "Full Stack Developer",
  location: "Bengaluru",
  gap_pct: 40.0,
  coverage_pct: 60.0,
  created_at: "2026-03-15T10:00:00Z",
  items: [
    {
      skill_id: "sk-1",
      skill_name: "React",
      category: "Frameworks",
      kind: "covered",
      demand_count: 85,
      demand_pct: 70.8,
      rank: 1,
    },
    {
      skill_id: "sk-2",
      skill_name: "TypeScript",
      category: "Languages",
      kind: "covered",
      demand_count: 80,
      demand_pct: 66.6,
      rank: 2,
    },
    {
      skill_id: "sk-3",
      skill_name: "Docker",
      category: "DevOps",
      kind: "missing",
      demand_count: 65,
      demand_pct: 54.1,
      rank: 3,
    },
    {
      skill_id: "sk-4",
      skill_name: "jQuery",
      category: "Frameworks",
      kind: "obsolete",
      demand_count: 5,
      demand_pct: 4.1,
      rank: 25,
    },
  ],
};

const mockRecommendations: RecommendationsResponse = {
  analysis_id: "ana-123",
  syllabus_id: "syl-456",
  course_title: "CS 204: Web Engineering",
  role_query: "Full Stack Developer",
  location: "Bengaluru",
  gap_pct: 40.0,
  coverage_pct: 60.0,
  summary: "Curriculum demonstrates solid foundational coverage with containerization deficits.",
  skills_to_add: [
    {
      skill_id: "sk-3",
      skill_name: "Docker",
      category: "DevOps",
      action: "add",
      demand_pct: 54.1,
      trend_pct: 4.5,
      rationale: "Containerization is required in >50% of junior full stack postings.",
      suggested_module: "Module 4: Deployment & Microservices",
      suggested_weeks: 2,
    },
  ],
  skills_to_drop: [
    {
      skill_id: "sk-4",
      skill_name: "jQuery",
      category: "Frameworks",
      action: "drop",
      demand_pct: 4.1,
      trend_pct: -8.0,
      rationale: "Replaced by modern reactivity models.",
      suggested_module: "Legacy Web APIs",
      suggested_weeks: 1,
    },
  ],
};

const mockSyllabi: Syllabus[] = [
  {
    id: "syl-456",
    title: "CS 204: Web Engineering",
    filename: "cs204.pdf",
    course_code: "CS204",
    institution: "National Technical Institute",
    status: "ready",
    created_at: "2026-03-01T12:00:00Z",
  },
];

describe("Gap Analysis Dashboard & Directory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getAnalysis).mockResolvedValue(mockAnalysis);
    vi.mocked(api.getRecommendations).mockResolvedValue(mockRecommendations);
    vi.mocked(api.listAnalyses).mockResolvedValue([mockAnalysis]);
    vi.mocked(api.listSyllabi).mockResolvedValue(mockSyllabi);
  });

  describe("AnalysisDetailPage (/analysis/[id])", () => {
    it("renders the gap % gauge, alignment label, and coverage metric", async () => {
      render(<AnalysisDetailPage params={Promise.resolve({ id: "ana-123" })} />);

      await waitFor(() => {
        expect(screen.getByText(/Curriculum Gap Assessment: Full Stack Developer/i)).toBeInTheDocument();
      });

      // Gauge metrics
      expect(screen.getByText("40%")).toBeInTheDocument();
      expect(screen.getByText(/60% Covered/i)).toBeInTheDocument();
      expect(screen.getByText(/Moderate Alignment Gap/i)).toBeInTheDocument();
    });

    it("renders the category comparison breakdown", async () => {
      render(<AnalysisDetailPage params={Promise.resolve({ id: "ana-123" })} />);

      await waitFor(() => {
        expect(screen.getByText("Domain Category Comparison")).toBeInTheDocument();
      });

      expect(screen.getAllByText("Frameworks").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Languages").length).toBeGreaterThan(0);
      expect(screen.getAllByText("DevOps").length).toBeGreaterThan(0);
    });

    it("renders actionable curriculum recommendations for skills to add and drop", async () => {
      render(<AnalysisDetailPage params={Promise.resolve({ id: "ana-123" })} />);

      await waitFor(() => {
        expect(screen.getByText("Curriculum Modernization Recommendations")).toBeInTheDocument();
      });

      // Skills to Add
      expect(screen.getByText(/High-Priority Skills to Introduce/i)).toBeInTheDocument();
      expect(screen.getAllByText("Docker").length).toBeGreaterThan(0);
      expect(screen.getByText(/Containerization is required in >50% of junior full stack postings./i)).toBeInTheDocument();
      expect(screen.getByText(/Module: Module 4: Deployment & Microservices/i)).toBeInTheDocument();

      // Skills to Drop
      expect(screen.getByText(/Topics to Prune or Modernize/i)).toBeInTheDocument();
      expect(screen.getAllByText("jQuery").length).toBeGreaterThan(0);
      expect(screen.getByText(/Replaced by modern reactivity models./i)).toBeInTheDocument();
    });

    it("filters detailed competencies by kind (Covered, Missing, Obsolete)", async () => {
      render(<AnalysisDetailPage params={Promise.resolve({ id: "ana-123" })} />);

      await waitFor(() => {
        expect(screen.getByText("Comprehensive Competency Breakdown")).toBeInTheDocument();
      });

      // Initially all skills visible
      expect(screen.getByText("React")).toBeInTheDocument();
      expect(screen.getAllByText("Docker").length).toBeGreaterThan(0);
      expect(screen.getAllByText("jQuery").length).toBeGreaterThan(0);

      // Filter to Missing only
      const missingTab = screen.getByRole("button", { name: /Missing Deficits/i });
      fireEvent.click(missingTab);

      expect(screen.getAllByText("Docker").length).toBeGreaterThan(0);
      expect(screen.queryByText("React")).not.toBeInTheDocument();

      // Filter to Covered only
      const coveredTab = screen.getByRole("button", { name: /Covered/i });
      fireEvent.click(coveredTab);

      expect(screen.getByText("React")).toBeInTheDocument();
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
      // Docker should now only be in recommendations, not in the table
      const dockerInTable = screen.queryByRole("cell", { name: "Docker" });
      expect(dockerInTable).not.toBeInTheDocument();
    });

    it("renders error state when analysis fails to load", async () => {
      vi.mocked(api.getAnalysis).mockRejectedValueOnce(new Error("Analysis not found"));

      render(<AnalysisDetailPage params={Promise.resolve({ id: "nonexistent" })} />);

      await waitFor(() => {
        expect(screen.getByText("Analysis not found")).toBeInTheDocument();
      });
      expect(screen.getByText(/Return to Analysis Directory/i)).toBeInTheDocument();
    });
  });

  describe("AnalysisIndexPage (/analysis)", () => {
    it("renders historical evaluations and the launch form", async () => {
      render(<AnalysisIndexPage />);

      await waitFor(() => {
        expect(screen.getByText("Curriculum Gap Analysis")).toBeInTheDocument();
      });

      expect(screen.getByText("Initiate New Gap Evaluation")).toBeInTheDocument();
      expect(screen.getByText("Evaluated Curriculum Records")).toBeInTheDocument();
      expect(screen.getByText("Bengaluru Market")).toBeInTheDocument();
      expect(screen.getByText("60% Market Coverage")).toBeInTheDocument();
    });
  });
});
