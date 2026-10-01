"use client";

import React, { Suspense, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowRight, BookOpen, GraduationCap, Landmark, Loader2, Lock, Mail } from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawRedirect = searchParams.get("redirect");
  const redirectTarget = rawRedirect || "/syllabi";

  const [role, setRole] = useState<"educator" | "policymaker" | "student">("educator");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fillDemo = (roleChoice: "educator" | "policymaker" | "student") => {
    setRole(roleChoice);
    if (roleChoice === "educator") {
      setEmail("educator@gapwright.edu");
      setPassword("Password123!");
    } else if (roleChoice === "policymaker") {
      setEmail("policymaker@highered.gov.in");
      setPassword("Password123!");
    } else if (roleChoice === "student") {
      setEmail("student@gapwright.edu");
      setPassword("Password123!");
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      // Store token for client-side API requests and update navbar
      if (data.access_token) {
        localStorage.setItem("gapwright_token", data.access_token);
        window.dispatchEvent(new Event("storage"));
      }

      const redirectTarget =
        rawRedirect ||
        (role === "policymaker"
          ? "/policy"
          : role === "student"
            ? "/demand"
            : "/syllabi");

      router.push(redirectTarget);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-xl flex flex-col gap-6">
      <div className="flex flex-col items-center text-center gap-3">
        <div className="relative w-12 h-12 rounded-2xl overflow-hidden border border-[var(--border-subtle)] bg-[var(--color-brand-pink)] flex items-center justify-center p-1.5 shadow-sm">
          <Image
            src="/growth.png"
            alt="Gapwright Logo"
            width={40}
            height={40}
            className="object-contain"
            priority
          />
        </div>
        <div className="flex flex-col">
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-main)]">
            Sign In to Gapwright
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Access institutional curriculum intelligence &amp; gap benchmarks
          </p>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="p-3 rounded-xl bg-[var(--color-status-missing-bg)] border border-[var(--color-status-missing)] text-[var(--color-status-missing)] text-xs flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Role Selection Toggle */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-[var(--text-main)]">
              Sign In Persona / Role
            </label>
            <span className="text-[10px] text-[var(--text-muted)]">
              Select portal type
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[
              {
                id: "educator",
                label: "Educator",
                desc: "Syllabi & Gaps",
                icon: GraduationCap,
              },
              {
                id: "policymaker",
                label: "Policymaker",
                desc: "Governance",
                icon: Landmark,
              },
              {
                id: "student",
                label: "Student",
                desc: "Market Skills",
                icon: BookOpen,
              },
            ].map((option) => {
              const Icon = option.icon;
              const isSelected = role === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => fillDemo(option.id as "educator" | "policymaker" | "student")}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-xl border text-center transition cursor-pointer ${
                    isSelected
                      ? "border-[var(--color-brand-green)] bg-[var(--color-brand-mint)]/40 dark:border-[var(--color-brand-aqua)] dark:bg-[var(--color-brand-aqua)]/15 font-semibold shadow-xs"
                      : "border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-muted)] hover:border-[var(--text-muted)]/60"
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 mb-1 ${
                      isSelected
                        ? "text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]"
                        : "text-[var(--text-muted)]"
                    }`}
                  />
                  <span className={`text-xs ${isSelected ? "text-[var(--text-main)]" : "text-[var(--text-muted)]"}`}>
                    {option.label}
                  </span>
                  <span className="text-[10px] text-[var(--text-muted)] leading-tight mt-0.5 hidden sm:inline">
                    {option.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="email"
            className="text-xs font-semibold text-[var(--text-main)]"
          >
            Institutional Email
          </label>
          <div className="relative flex items-center">
            <Mail className="w-4 h-4 text-[var(--text-muted)] absolute left-3 pointer-events-none" />
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={
                role === "policymaker"
                  ? "policymaker@highered.gov.in"
                  : role === "student"
                    ? "student@university.edu"
                    : "educator@gapwright.edu"
              }
              required
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="password"
            className="text-xs font-semibold text-[var(--text-main)]"
          >
            Password
          </label>
          <div className="relative flex items-center">
            <Lock className="w-4 h-4 text-[var(--text-muted)] absolute left-3 pointer-events-none" />
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 w-full py-2.5 px-4 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-sm hover:opacity-90 transition flex items-center justify-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Verifying credentials...</span>
            </>
          ) : (
            <>
              <span>Sign In</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      <div className="pt-2 border-t border-[var(--border-subtle)] text-center text-xs text-[var(--text-muted)]">
        <span>Need an institutional account? </span>
        <Link
          href={`/register?redirect=${encodeURIComponent(redirectTarget)}`}
          className="font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline"
        >
          Register here
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-[calc(100vh-16rem)] flex items-center justify-center px-4 py-12">
      <Suspense fallback={<div className="text-sm text-[var(--text-muted)]">Loading login form...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
