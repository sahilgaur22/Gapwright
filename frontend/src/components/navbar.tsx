"use client";

import React, { useSyncExternalStore } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import { api } from "@/lib/api";

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
  let userRole: string | null = null;
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      userEmail = payload.email || "Account";
      userRole = payload.role || null;
    } catch {
      userEmail = null;
      userRole = null;
    }
  }

  const getPortalInfo = (role: string | null) => {
    switch (role) {
      case "policymaker":
        return {
          href: "/policy",
          label: "Governance Portal",
          badge: "Policymaker",
          badgeClass: "bg-[var(--color-brand-pink)] text-[var(--color-brand-navy)]",
        };
      case "student":
        return {
          href: "/demand",
          label: "Market Demand",
          badge: "Student",
          badgeClass: "bg-[var(--color-brand-mint)]/60 text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]",
        };
      case "admin":
        return {
          href: "/policy",
          label: "Admin Portal",
          badge: "Admin",
          badgeClass: "bg-[var(--color-brand-yellow)]/20 text-[var(--color-brand-yellow)]",
        };
      case "educator":
      default:
        return {
          href: "/syllabi",
          label: "Curriculum Portal",
          badge: "Educator",
          badgeClass: "bg-[var(--color-brand-mint)] text-[var(--color-brand-navy)]",
        };
    }
  };

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

        {/* Public Navigation: Common to All Users */}
        <nav className="hidden md:flex items-center gap-7 text-sm font-medium">
          <Link
            href="/"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            Home
          </Link>
          <Link
            href="/#about"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            About Us
          </Link>
          <Link
            href="#contact"
            className="text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition-colors"
          >
            Contact Us
          </Link>
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {token && userEmail ? (
            <div className="flex items-center gap-2.5">
              {(() => {
                const portal = getPortalInfo(userRole);
                return (
                  <div className="flex items-center gap-2">
                    <Link
                      href={portal.href}
                      className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-brand-green)]/15 text-[var(--color-brand-green)] dark:bg-[var(--color-brand-aqua)]/15 dark:text-[var(--color-brand-aqua)] font-semibold hover:opacity-80 transition flex items-center gap-1.5"
                    >
                      <span>{portal.label}</span>
                    </Link>
                    <span
                      className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md ${portal.badgeClass}`}
                    >
                      {portal.badge}
                    </span>
                  </div>
                );
              })()}

              <span
                className="text-xs font-medium text-[var(--text-muted)] hidden lg:inline-block max-w-[130px] truncate"
                title={userEmail}
              >
                {userEmail}
              </span>

              <button
                type="button"
                onClick={async () => {
                  await api.logout();
                  window.location.href = "/login";
                }}
                className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] hover:border-[var(--color-status-missing)] hover:text-[var(--color-status-missing)] transition cursor-pointer font-medium"
              >
                Sign out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={async () => {
                  await api.logout();
                  window.location.href = "/login?force=true";
                }}
                className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)] transition font-medium cursor-pointer"
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={async () => {
                  await api.logout();
                  window.location.href = "/register?force=true";
                }}
                className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:opacity-90 font-medium transition shadow-sm cursor-pointer"
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
