"use client";

import React, { Suspense, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowRight, Loader2, Lock, Mail, User } from "lucide-react";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/syllabi";

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      if (data.access_token) {
        localStorage.setItem("gapwright_token", data.access_token);
        window.dispatchEvent(new Event("storage"));
      }

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
            Create Account
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Register your institution for syllabus gap analysis &amp; market intelligence
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
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="fullName"
            className="text-xs font-semibold text-[var(--text-main)]"
          >
            Academic / Administrator Name
          </label>
          <div className="relative flex items-center">
            <User className="w-4 h-4 text-[var(--text-muted)] absolute left-3 pointer-events-none" />
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Dr. Rajesh Kumar"
              required
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
            />
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
              placeholder="rajesh.kumar@iit.ac.in"
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
              placeholder="Minimum 8 characters"
              required
              minLength={8}
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="confirmPassword"
            className="text-xs font-semibold text-[var(--text-main)]"
          >
            Confirm Password
          </label>
          <div className="relative flex items-center">
            <Lock className="w-4 h-4 text-[var(--text-muted)] absolute left-3 pointer-events-none" />
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
              required
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
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
              <span>Registering account...</span>
            </>
          ) : (
            <>
              <span>Create Account</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      <div className="pt-2 border-t border-[var(--border-subtle)] text-center text-xs text-[var(--text-muted)]">
        <span>Already have an institutional account? </span>
        <Link
          href={`/login?redirect=${encodeURIComponent(redirectTarget)}`}
          className="font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline"
        >
          Sign in
        </Link>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <div className="min-h-[calc(100vh-16rem)] flex items-center justify-center px-4 py-12">
      <Suspense fallback={<div className="text-sm text-[var(--text-muted)]">Loading registration form...</div>}>
        <RegisterForm />
      </Suspense>
    </div>
  );
}
