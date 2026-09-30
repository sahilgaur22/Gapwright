import React from "react";
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SyllabiPage from "@/app/syllabi/page";
import SyllabusDetailPage from "@/app/syllabi/[id]/page";
import { api } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe("Syllabi Management & Detail Portal", () => {
  const mockSyllabi = [
    {
      id: "s-1",
      title: "CS101: Introduction to Computer Systems",
      filename: "cs101_syllabus.pdf",
      status: "ready" as const,
      created_at: "2026-09-15T10:00:00Z",
    },
    {
      id: "s-2",
      title: "DS200: Applied Cloud Computing",
      filename: "ds200_cloud.docx",
      status: "processing" as const,
      created_at: "2026-09-20T10:00:00Z",
    },
  ];

  const mockSyllabusDetail = {
    id: "s-1",
    title: "CS101: Introduction to Computer Systems",
    filename: "cs101_syllabus.pdf",
    status: "ready" as const,
    created_at: "2026-09-15T10:00:00Z",
    skills: [
      {
        id: "sk-1",
        skill_id: "sid-1",
        skill_name: "Python",
        category: "Languages",
        evidence: "Module 2 covers fundamental programming using Python syntax and scripts.",
      },
      {
        id: "sk-2",
        skill_id: "sid-2",
        skill_name: "Docker",
        category: "DevOps",
        evidence: "Students deploy laboratory services inside Docker containers.",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders syllabi list with course titles and status badges", async () => {
    vi.spyOn(api, "listSyllabi").mockResolvedValue(mockSyllabi);

    render(<SyllabiPage />);

    expect(screen.getByText(/loading course syllabi/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("CS101: Introduction to Computer Systems")).toBeInTheDocument();
      expect(screen.getByText("DS200: Applied Cloud Computing")).toBeInTheDocument();
      expect(screen.getByText("ready")).toBeInTheDocument();
      expect(screen.getByText("processing")).toBeInTheDocument();
    });
  });

  it("filters syllabi list by search term", async () => {
    vi.spyOn(api, "listSyllabi").mockResolvedValue(mockSyllabi);

    render(<SyllabiPage />);

    await waitFor(() => {
      expect(screen.getByText("CS101: Introduction to Computer Systems")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search uploaded syllabi/i);
    fireEvent.change(searchInput, { target: { value: "Cloud" } });

    expect(screen.queryByText("CS101: Introduction to Computer Systems")).not.toBeInTheDocument();
    expect(screen.getByText("DS200: Applied Cloud Computing")).toBeInTheDocument();
  });

  it("renders syllabus details with extracted competencies and evidence", async () => {
    vi.spyOn(api, "getSyllabus").mockResolvedValue(mockSyllabusDetail);

    render(<SyllabusDetailPage params={Promise.resolve({ id: "s-1" })} />);

    await waitFor(() => {
      expect(screen.getByText("CS101: Introduction to Computer Systems")).toBeInTheDocument();
      expect(screen.getByText("cs101_syllabus.pdf")).toBeInTheDocument();
      expect(screen.getByText("Python")).toBeInTheDocument();
      expect(screen.getByText("Docker")).toBeInTheDocument();
      expect(
        screen.getByText(/Module 2 covers fundamental programming using Python/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Students deploy laboratory services inside Docker/i)
      ).toBeInTheDocument();
    });
  });

  it("filters competencies by category in detail view", async () => {
    vi.spyOn(api, "getSyllabus").mockResolvedValue(mockSyllabusDetail);

    render(<SyllabusDetailPage params={Promise.resolve({ id: "s-1" })} />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeInTheDocument();
      expect(screen.getByText("Docker")).toBeInTheDocument();
    });

    // Click on Languages category filter
    const languagesButton = screen.getByRole("button", { name: "Languages" });
    fireEvent.click(languagesButton);

    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.queryByText("Docker")).not.toBeInTheDocument();
  });

  it("handles syllabus fetch error gracefully", async () => {
    vi.spyOn(api, "getSyllabus").mockRejectedValue(new Error("Course document not found"));

    render(<SyllabusDetailPage params={Promise.resolve({ id: "s-invalid" })} />);

    await waitFor(() => {
      expect(screen.getByText(/could not load syllabus/i)).toBeInTheDocument();
      expect(screen.getByText("Course document not found")).toBeInTheDocument();
    });
  });
});
