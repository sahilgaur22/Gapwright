import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import MarketDemandPage from "../app/demand/page";
import { api, TopSkillsResponse, SourceSummary } from "@/lib/api";

// Mock the API client
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getTopSkills: vi.fn(),
      listSources: vi.fn(),
    },
  };
});

const mockDemandResponse: TopSkillsResponse = {
  role_query: "Full Stack Developer",
  location: "All India",
  total_postings: 142,
  analysis_window_days: 30,
  trend_window_days: 30,
  skills: [
    {
      skill_id: "s1",
      name: "TypeScript",
      category: "Languages",
      postings_count: 98,
      demand_pct: 69.0,
      trend_pct: 5.2,
    },
    {
      skill_id: "s2",
      name: "React",
      category: "Frameworks",
      postings_count: 92,
      demand_pct: 64.8,
      trend_pct: -1.8,
    },
    {
      skill_id: "s3",
      name: "PostgreSQL",
      category: "Databases",
      postings_count: 76,
      demand_pct: 53.5,
      trend_pct: 0.0,
    },
  ],
};

const mockSourcesResponse: SourceSummary[] = [
  {
    name: "adzuna",
    priority: 1,
    enabled: true,
    attribution_text: "Jobs powered by Adzuna",
    attribution_url: "https://www.adzuna.in",
    may_display_listing: true,
    daily_budget: 30,
    daily_calls_used: 12,
    remaining_budget: 18,
  },
  {
    name: "remoteok",
    priority: 2,
    enabled: true,
    attribution_text: "Remote Jobs by RemoteOK",
    attribution_url: "https://remoteok.com",
    may_display_listing: false,
    daily_budget: 4,
    daily_calls_used: 2,
    remaining_budget: 2,
  },
];

describe("MarketDemandPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getTopSkills).mockResolvedValue(mockDemandResponse);
    vi.mocked(api.listSources).mockResolvedValue(mockSourcesResponse);
  });

  it("renders the explorer with header, filters, and freshness label", async () => {
    render(<MarketDemandPage />);

    expect(screen.getByText("Market Demand Explorer")).toBeInTheDocument();
    expect(screen.getByText(/Labour Market Intelligence/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Based on 142 active job postings/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Trend baseline: 30 days/i)).toBeInTheDocument();
  });

  it("renders top demanded competencies with demand percentage and trend indicators", async () => {
    render(<MarketDemandPage />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
      expect(screen.getByText("React")).toBeInTheDocument();
      expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
    });

    // Check demand percentages
    expect(screen.getByText("69.0%")).toBeInTheDocument();
    expect(screen.getByText("64.8%")).toBeInTheDocument();
    expect(screen.getByText("53.5%")).toBeInTheDocument();

    // Check trend indicators: TypeScript +5.2%, React -1.8%, PostgreSQL 0.0%
    expect(screen.getByText("+5.2%")).toBeInTheDocument();
    expect(screen.getByText("-1.8%")).toBeInTheDocument();
    expect(screen.getByText("0.0%")).toBeInTheDocument();
  });

  it("switches to Remote Roles mode and triggers remote query", async () => {
    render(<MarketDemandPage />);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });

    const remoteTab = screen.getByText(/Remote Roles/i);
    fireEvent.click(remoteTab);

    await waitFor(() => {
      expect(api.getTopSkills).toHaveBeenCalledWith(
        "Full Stack Developer",
        "Remote",
        30,
        20
      );
    });

    expect(screen.getByText("Remote / Global Anywhere")).toBeInTheDocument();
  });

  it("renders Section 5 source attribution links without nofollow", async () => {
    render(<MarketDemandPage />);

    await waitFor(() => {
      expect(screen.getByText("Job Market Data Sources & Compliance Attribution")).toBeInTheDocument();
    });

    // Verify presence of sources
    expect(screen.getByText("Adzuna")).toBeInTheDocument();
    expect(screen.getByText("Jooble")).toBeInTheDocument();
    expect(screen.getByText("Remotive")).toBeInTheDocument();
    expect(screen.getByText("RemoteOK")).toBeInTheDocument();
    expect(screen.getByText("We Work Remotely")).toBeInTheDocument();
    expect(screen.getByText("FixtureSource")).toBeInTheDocument();

    // Check anchor elements: MUST NOT contain nofollow per §5 terms
    const adzunaLink = screen.getByRole("link", { name: /Jobs powered by Adzuna/i });
    expect(adzunaLink).toHaveAttribute("href", "https://www.adzuna.in");
    expect(adzunaLink.getAttribute("rel") || "").not.toContain("nofollow");

    const remoteOkLink = screen.getByRole("link", { name: /Remote Jobs by RemoteOK/i });
    expect(remoteOkLink).toHaveAttribute("href", "https://remoteok.com");
    expect(remoteOkLink.getAttribute("rel") || "").not.toContain("nofollow");

    const remotiveLink = screen.getByRole("link", { name: /Data provided by Remotive/i });
    expect(remotiveLink).toHaveAttribute("href", "https://remotive.com");
    expect(remotiveLink.getAttribute("rel") || "").not.toContain("nofollow");

    const wwrLink = screen.getByRole("link", { name: /Syndicated via We Work Remotely/i });
    expect(wwrLink).toHaveAttribute("href", "https://weworkremotely.com");
    expect(wwrLink.getAttribute("rel") || "").not.toContain("nofollow");
  });

  it("handles empty results gracefully", async () => {
    vi.mocked(api.getTopSkills).mockResolvedValueOnce({
      role_query: "UnknownRole123",
      location: "Nowhere",
      total_postings: 0,
      analysis_window_days: 30,
      trend_window_days: 30,
      skills: [],
    });

    render(<MarketDemandPage />);

    await waitFor(() => {
      expect(screen.getByText("No Skill Data Available for this Query")).toBeInTheDocument();
    });
  });

  it("handles error state and allows retry", async () => {
    vi.mocked(api.getTopSkills).mockRejectedValueOnce(new Error("Network connection dropped"));

    render(<MarketDemandPage />);

    await waitFor(() => {
      expect(screen.getByText("Network connection dropped")).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole("button", { name: /Retry Demand Query/i });
    expect(retryBtn).toBeInTheDocument();

    vi.mocked(api.getTopSkills).mockResolvedValueOnce(mockDemandResponse);
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });
  });
});
