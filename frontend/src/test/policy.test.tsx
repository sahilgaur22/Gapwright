import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PolicymakerOverviewPage from "../app/policy/page";
import { api, PolicyOverviewResponse } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getPolicyOverview: vi.fn(),
    },
  };
});

const mockPolicyData: PolicyOverviewResponse = {
  total_analyses: 24,
  total_institutions: 8,
  average_gap_pct: 38.5,
  average_coverage_pct: 61.5,
  top_systemic_missing_skills: [
    {
      skill_name: "Kubernetes",
      category: "DevOps",
      occurrences: 18,
      average_demand_pct: 58.2,
      total_postings: 320,
    },
    {
      skill_name: "Microservices Architecture",
      category: "Architecture",
      occurrences: 15,
      average_demand_pct: 51.0,
      total_postings: 280,
    },
  ],
  institutions: [
    {
      institution: "Indian Institute of Technology, Madras",
      evaluations_count: 6,
      average_gap_pct: 28.0,
      average_coverage_pct: 72.0,
    },
    {
      institution: "National Institute of Technology, Trichy",
      evaluations_count: 4,
      average_gap_pct: 35.5,
      average_coverage_pct: 64.5,
    },
  ],
  roles: [
    {
      role: "Full Stack Developer",
      evaluations_count: 12,
      average_gap_pct: 36.0,
      average_coverage_pct: 64.0,
    },
    {
      role: "Cloud Systems Engineer",
      evaluations_count: 8,
      average_gap_pct: 42.0,
      average_coverage_pct: 58.0,
    },
  ],
};

function createJwt(role: string, email = "test@example.com"): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: "usr-123", email, role }));
  return `${header}.${payload}.signature`;
}

describe("PolicymakerOverviewPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(api.getPolicyOverview).mockResolvedValue(mockPolicyData);
  });

  it("renders role guard access-restricted banner when unauthenticated", () => {
    render(<PolicymakerOverviewPage />);

    expect(screen.getByText("Higher Education Policymaker Portal")).toBeInTheDocument();
    expect(screen.getByText(/Restricted Policy Access/i)).toBeInTheDocument();
    expect(screen.getByText(/Sign In with Authorized Account/i)).toBeInTheDocument();
    expect(screen.getByText(/Preview Policymaker View/i)).toBeInTheDocument();
  });

  it("renders role guard when user role is student or educator", () => {
    localStorage.setItem("gapwright_token", createJwt("student", "student@univ.edu"));

    render(<PolicymakerOverviewPage />);

    expect(screen.getByText("Higher Education Policymaker Portal")).toBeInTheDocument();
    expect(screen.getByText(/Role:/i)).toBeInTheDocument();
    expect(screen.getByText("student")).toBeInTheDocument();
  });

  it("bypasses guard when user clicks Preview Policymaker View", async () => {
    render(<PolicymakerOverviewPage />);

    const previewBtn = screen.getByRole("button", { name: /Preview Policymaker View/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText("National Higher Education Curriculum Overview")).toBeInTheDocument();
    });

    expect(screen.getByText("Top Systemic Curriculum Deficits Nationally")).toBeInTheDocument();
  });

  it("directly renders overview dashboard when authenticated as policymaker", async () => {
    localStorage.setItem("gapwright_token", createJwt("policymaker", "council@moe.gov.in"));

    render(<PolicymakerOverviewPage />);

    await waitFor(() => {
      expect(screen.getByText("National Higher Education Curriculum Overview")).toBeInTheDocument();
    });

    // Check summary metrics
    expect(screen.getByText("24")).toBeInTheDocument(); // total analyses
    expect(screen.getByText("8")).toBeInTheDocument();  // total institutions
    expect(screen.getByText("38.5%")).toBeInTheDocument(); // national average gap
    expect(screen.getByText("61.5%")).toBeInTheDocument(); // national coverage average

    // Check systemic missing skills
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("Microservices Architecture")).toBeInTheDocument();
    expect(screen.getByText("18 courses")).toBeInTheDocument();

    // Check institutions leaderboard
    expect(screen.getByText("Indian Institute of Technology, Madras")).toBeInTheDocument();
    expect(screen.getByText("28.0% Gap")).toBeInTheDocument();

    // Check roles
    expect(screen.getByText("Full Stack Developer")).toBeInTheDocument();
    expect(screen.getByText("Cloud Systems Engineer")).toBeInTheDocument();
  });
});
