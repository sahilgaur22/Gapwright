"use client";

import React, { useState, useEffect, useCallback, useSyncExternalStore } from "react";
import Link from "next/link";
import { api, PolicyOverviewResponse, SystemicSkillGap, InstitutionAlignmentSummary, RoleMarketComparison } from "@/lib/api";

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

export default function PolicymakerOverviewPage() {
  const token = useSyncExternalStore(
    subscribeAuth,
    getAuthSnapshot,
    getAuthServerSnapshot
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [policyData, setPolicyData] = useState<PolicyOverviewResponse | null>(null);
  const [demoBypass, setDemoBypass] = useState(false);

  // Check user role from JWT token
  let userRole: string | null = null;
  let userEmail: string | null = null;
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      userRole = payload.role || null;
      userEmail = payload.email || null;
    } catch {
      userRole = null;
    }
  }

  const isAuthorized = demoBypass || userRole === "policymaker" || userRole === "admin";

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!isAuthorized) {
      return;
    }
    let isMounted = true;
    api
      .getPolicyOverview()
      .then((data) => {
        if (isMounted) {
          setPolicyData(data);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error
              ? err.message
              : "Failed to load policy overview";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isAuthorized, refreshKey]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    setRefreshKey((k) => k + 1);
  }, []);

  // If not authorized by role, show the institutional role guard screen
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-[var(--bg-main)] py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-xl mx-auto bg-[var(--bg-surface)] p-8 sm:p-10 rounded-2xl border border-[var(--border-subtle)] shadow-sm text-center space-y-6">
          <div className="w-14 h-14 mx-auto rounded-full bg-[var(--color-brand-pink)] flex items-center justify-center text-[var(--color-brand-navy)] font-bold text-2xl">
            🏛️
          </div>

          <div className="space-y-2">
            <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-yellow)] bg-[var(--color-brand-pink)] px-3 py-1 rounded-full">
              Restricted Policy Access
            </span>
            <h1 className="text-2xl font-extrabold text-[var(--text-main)]">
              Higher Education Policymaker Portal
            </h1>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] max-w-md mx-auto leading-relaxed">
              This overview is restricted to State Higher Education Councils, AICTE/UGC Officers, and accredited University Senate committees for systemic curriculum planning.
            </p>
          </div>

          {userEmail && (
            <div className="p-3 rounded-lg bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-xs text-[var(--text-muted)]">
              Signed in as <span className="font-semibold text-[var(--text-main)]">{userEmail}</span> (Role: <span className="font-semibold uppercase">{userRole || "User"}</span>)
            </div>
          )}

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/login"
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)] hover:opacity-90 transition"
            >
              Sign In with Authorized Account
            </Link>

            <button
              type="button"
              onClick={() => setDemoBypass(true)}
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition cursor-pointer"
            >
              Preview Policymaker View
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-main)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/20 px-2.5 py-0.5 rounded-full">
                Institutional Governance & Macro Planning
              </span>
              {demoBypass && (
                <span className="text-[10px] uppercase font-bold text-[var(--color-brand-yellow)] bg-[var(--color-brand-pink)] px-2 py-0.5 rounded">
                  Evaluation Mode
                </span>
              )}
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-main)] sm:text-4xl">
              National Higher Education Curriculum Overview
            </h1>
            <p className="mt-2 text-sm sm:text-base text-[var(--text-muted)] max-w-2xl">
              Aggregated curriculum gap metrics across accredited Indian technological institutions. Identify structural curriculum deficits across computer science and engineering disciplines to inform national policy directives.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition cursor-pointer"
            >
              Refresh Governance Data
            </button>
            <Link
              href="/analysis"
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)] hover:opacity-90 transition shadow-sm"
            >
              Course Analysis Catalog
            </Link>
          </div>
        </div>

        {/* Macro Summary Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[var(--bg-surface)] p-5 rounded-2xl border border-[var(--border-subtle)] shadow-sm">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Evaluated Curricula
            </span>
            <div className="mt-2 text-3xl font-extrabold text-[var(--text-main)]">
              {policyData?.total_analyses ?? 0}
            </div>
            <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
              Accredited courses analyzed
            </span>
          </div>

          <div className="bg-[var(--bg-surface)] p-5 rounded-2xl border border-[var(--border-subtle)] shadow-sm">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Institutions Monitored
            </span>
            <div className="mt-2 text-3xl font-extrabold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]">
              {policyData?.total_institutions ?? 0}
            </div>
            <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
              Universities and colleges
            </span>
          </div>

          <div className="bg-[var(--bg-surface)] p-5 rounded-2xl border border-[var(--border-subtle)] shadow-sm">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              National Average Gap
            </span>
            <div className="mt-2 text-3xl font-extrabold text-[var(--color-brand-yellow)]">
              {policyData?.average_gap_pct?.toFixed(1) ?? "0.0"}%
            </div>
            <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
              Aggregate curriculum skill deficit
            </span>
          </div>

          <div className="bg-[var(--bg-surface)] p-5 rounded-2xl border border-[var(--border-subtle)] shadow-sm">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              National Coverage Average
            </span>
            <div className="mt-2 text-3xl font-extrabold text-[var(--text-main)]">
              {policyData?.average_coverage_pct?.toFixed(1) ?? "0.0"}%
            </div>
            <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
              Workplace readiness baseline
            </span>
          </div>
        </div>

        {loading ? (
          <div className="bg-[var(--bg-surface)] p-8 rounded-2xl border border-[var(--border-subtle)] space-y-4">
            <div className="h-6 bg-[var(--bg-surface-elevated)] rounded w-1/4 animate-pulse"></div>
            <div className="space-y-3 pt-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-[var(--bg-surface-elevated)] rounded-xl animate-pulse"></div>
              ))}
            </div>
          </div>
        ) : error && !policyData ? (
          <div className="bg-[var(--bg-surface)] p-8 rounded-2xl border border-[var(--color-status-missing)]/30 text-center space-y-3">
            <p className="text-sm font-semibold text-[var(--color-status-missing)]">
              {error}
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              Unable to load macro governance data from the policy endpoint.
            </p>
            <button
              type="button"
              onClick={handleRefresh}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)]"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Top Systemic Missing Skills Section */}
            <section className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
              <div className="border-b border-[var(--border-subtle)] pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-brand-yellow)]"></span>
                  <h2 className="text-lg font-bold text-[var(--text-main)]">
                    Top Systemic Curriculum Deficits Nationally
                  </h2>
                </div>
                <p className="text-xs sm:text-sm text-[var(--text-muted)]">
                  Competencies most frequently absent across evaluated university syllabi despite high market demand across hiring channels.
                </p>
              </div>

              {(!policyData?.top_systemic_missing_skills || policyData.top_systemic_missing_skills.length === 0) ? (
                <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                  No systemic missing skills recorded yet. Complete course evaluations to aggregate macro deficit statistics.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                        <th className="py-2.5 pr-4 font-semibold w-12 text-center">Rank</th>
                        <th className="py-2.5 pr-4 font-semibold">Competency</th>
                        <th className="py-2.5 pr-4 font-semibold">Domain Category</th>
                        <th className="py-2.5 pr-4 font-semibold text-center">Absent Across</th>
                        <th className="py-2.5 pr-4 font-semibold text-right">Avg Market Demand</th>
                        <th className="py-2.5 font-semibold text-right">Active Vacancies</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {policyData.top_systemic_missing_skills.map((skill: SystemicSkillGap, idx: number) => (
                        <tr key={skill.skill_name} className="hover:bg-[var(--bg-main)]/50 transition">
                          <td className="py-3 pr-4 text-center font-bold text-[var(--text-muted)]">
                            #{idx + 1}
                          </td>
                          <td className="py-3 pr-4 font-bold text-sm text-[var(--text-main)]">
                            {skill.skill_name}
                          </td>
                          <td className="py-3 pr-4">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]">
                              {skill.category || "General"}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-center">
                            <span className="inline-block px-2.5 py-0.5 rounded-full font-bold text-[11px] bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]">
                              {skill.occurrences} {skill.occurrences === 1 ? "course" : "courses"}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-right font-bold text-[var(--text-main)]">
                            {skill.average_demand_pct.toFixed(1)}%
                          </td>
                          <td className="py-3 text-right text-[var(--text-muted)]">
                            {skill.total_postings}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Institutional Alignment Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Institutions Leaderboard */}
              <section className="bg-[var(--bg-surface)] p-6 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-4">
                <div className="border-b border-[var(--border-subtle)] pb-3">
                  <h3 className="text-base font-bold text-[var(--text-main)]">
                    Institution Curriculum Readiness
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    Average gap percentages reported across participating universities.
                  </p>
                </div>

                {(!policyData?.institutions || policyData.institutions.length === 0) ? (
                  <div className="p-6 text-center text-xs text-[var(--text-muted)]">
                    No institutional records registered.
                  </div>
                ) : (
                  <div className="space-y-3 pt-1">
                    {policyData.institutions.map((inst: InstitutionAlignmentSummary) => (
                      <div key={inst.institution} className="p-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
                        <div className="flex items-center justify-between text-xs font-bold text-[var(--text-main)]">
                          <span>{inst.institution}</span>
                          <span className="text-[var(--color-brand-yellow)]">
                            {inst.average_gap_pct.toFixed(1)}% Gap
                          </span>
                        </div>
                        {/* Progress bar */}
                        <div className="w-full bg-[var(--bg-surface-elevated)] h-2 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[var(--color-brand-green)] to-[var(--color-brand-aqua)]"
                            style={{ width: `${Math.round(inst.average_coverage_pct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-[var(--text-muted)]">
                          <span>{inst.evaluations_count} courses evaluated</span>
                          <span>{inst.average_coverage_pct.toFixed(1)}% workplace coverage</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Roles Comparison */}
              <section className="bg-[var(--bg-surface)] p-6 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-4">
                <div className="border-b border-[var(--border-subtle)] pb-3">
                  <h3 className="text-base font-bold text-[var(--text-main)]">
                    Occupational Track Alignment
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    Relative alignment across technical career specializations.
                  </p>
                </div>

                {(!policyData?.roles || policyData.roles.length === 0) ? (
                  <div className="p-6 text-center text-xs text-[var(--text-muted)]">
                    No occupational role benchmarks aggregated yet.
                  </div>
                ) : (
                  <div className="space-y-3 pt-1">
                    {policyData.roles.map((r: RoleMarketComparison) => (
                      <div key={r.role} className="p-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
                        <div className="flex items-center justify-between text-xs font-bold text-[var(--text-main)]">
                          <span>{r.role}</span>
                          <span className="text-[var(--color-brand-yellow)]">
                            {r.average_gap_pct.toFixed(1)}% Deficit
                          </span>
                        </div>
                        <div className="w-full bg-[var(--bg-surface-elevated)] h-2 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[var(--color-brand-green)] to-[var(--color-brand-aqua)]"
                            style={{ width: `${Math.round(r.average_coverage_pct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-[var(--text-muted)]">
                          <span>{r.evaluations_count} evaluations</span>
                          <span>{r.average_coverage_pct.toFixed(1)}% alignment</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
