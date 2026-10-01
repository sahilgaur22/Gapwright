import React from "react";
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import { middleware } from "@/middleware";
import { NextRequest } from "next/server";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => ({
    get: (key: string) => (key === "redirect" ? "/syllabi" : null),
  }),
}));

describe("Authentication Pages & Forms", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    global.fetch = vi.fn();
  });

  it("renders login form with email and password fields", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText(/institutional email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("submits login form and stores token on success", async () => {
    const mockResponse = {
      access_token: "test-token-xyz",
      user: { id: "u-1", email: "dean@university.edu" },
    };

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/institutional email/i), {
      target: { value: "dean@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "securepassword123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/auth/login", expect.any(Object));
      expect(localStorage.getItem("gapwright_token")).toBe("test-token-xyz");
      expect(mockPush).toHaveBeenCalledWith("/syllabi");
    });
  });

  it("displays error message on invalid login", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Invalid email or password" }),
    } as Response);

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/institutional email/i), {
      target: { value: "wrong@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrongpass" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password");
    });
  });

  it("validates password mismatch on registration", async () => {
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/academic \/ administrator name/i), {
      target: { value: "Dr. Sharma" },
    });
    fireEvent.change(screen.getByLabelText(/institutional email/i), {
      target: { value: "sharma@iit.ac.in" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "different123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match");
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("submits registration with selected role and redirects", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        user: { id: "u-1", email: "dr.patel@stateuniv.edu", role: "policymaker" },
        access_token: "token-policymaker",
      }),
    } as Response);

    render(<RegisterPage />);

    // Select Policymaker persona
    fireEvent.click(screen.getByRole("button", { name: /policymaker/i }));

    fireEvent.change(screen.getByLabelText(/academic \/ administrator name/i), {
      target: { value: "Dr. Patel" },
    });
    fireEvent.change(screen.getByLabelText(/institutional email/i), {
      target: { value: "dr.patel@stateuniv.edu" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "securepassword123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "securepassword123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/auth/register",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "dr.patel@stateuniv.edu",
            password: "securepassword123",
            full_name: "Dr. Patel",
            role: "policymaker",
          }),
        })
      );
      expect(mockPush).toHaveBeenCalledWith("/syllabi");
    });
  });
});

describe("Route Protection Middleware", () => {
  it("redirects unauthenticated user accessing /syllabi to /login", () => {
    const req = new NextRequest("http://localhost:3000/syllabi");
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost:3000/login?redirect=%2Fsyllabi"
    );
  });

  it("allows authenticated user with session cookie to access /syllabi", () => {
    const req = new NextRequest("http://localhost:3000/syllabi", {
      headers: {
        cookie: "gapwright_session=valid-jwt-token",
      },
    });
    const res = middleware(req);

    expect(res.status).toBe(200);
  });

  it("redirects authenticated user away from /login to /syllabi", () => {
    const req = new NextRequest("http://localhost:3000/login", {
      headers: {
        cookie: "gapwright_session=valid-jwt-token",
      },
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/syllabi");
  });
});
