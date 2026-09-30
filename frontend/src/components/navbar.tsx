"use client";

import React, { useSyncExternalStore } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";

function subscribeAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getAuthSnapshot(): string | null {
  return localStorage.getItem("gapwright_token");
}

function getAuthServerSnapshot(): string | null {
  return null;
}

export function Navbar() {
  const router = useRouter();
  const token = useSyncExternalStore(
    subscribeAuth,
    getAuthSnapshot,
    getAuthServerSnapshot
  );

  let userEmail: string | null = null;
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      userEmail = payload.email || "Account";
    } catch {
      userEmail = null;
    }
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative w-9 h-9 rounded-lg overflow-hidden border border-[var(--border-subtle)] bg-[var(--color-brand-pink)] flex items-center justify-center p-1">
            <Image
              src="/growth.png"
              alt="Gapwright Logo"
              width={32}
              height={32}
              className="object-contain"
              priority
            />
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-bold tracking-tight text-[var(--text-main)] group-hover:text-[var(--color-brand-green)] dark:group-hover:text-[var(--color-brand-aqua)] transition-colors">
              Gapwright
            </span>
            <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--text-muted)] -mt-1">
              Curriculum Intelligence
            </span>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
          <Link
            href="/syllabi"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            Syllabi
          </Link>
          <Link
            href="/demand"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            Market Demand
          </Link>
          <Link
            href="/analysis"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            Gap Analysis
          </Link>
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {token && userEmail ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[var(--text-muted)] hidden sm:inline-block">
                {userEmail}
              </span>
              <button
                type="button"
                onClick={() => {
                  localStorage.removeItem("gapwright_token");
                  window.dispatchEvent(new Event("storage"));
                  router.push("/");
                }}
                className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] hover:border-[var(--color-status-missing)] hover:text-[var(--color-status-missing)] transition cursor-pointer"
              >
                Sign out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)] transition font-medium"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:opacity-90 font-medium transition shadow-sm"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
