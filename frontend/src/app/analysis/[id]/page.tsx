"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  api,
  Analysis,
  AnalysisItem,
  RecommendationsResponse,
  SkillRecommendation,
} from "@/lib/api";

type SkillFilter = "all" | "covered" | "missing" | "obsolete";

export default function AnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [recommendations, setRecommendations] =
    useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<SkillFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);

  const handleExport = async (format: "csv" | "pdf") => {
    if (!analysisId) return;
    setExporting(format);
    try {
      await api.downloadReport(analysisId, format);
    } catch {
      window.open(api.exportReportUrl(analysisId, format), "_blank");
    } finally {
      setExporting(null);
    }
  };

  useEffect(() => {
    let isMounted = true;
    Promise.resolve(params).then((resolved) => {
      if (isMounted) {
        setAnalysisId(resolved.id);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [params]);

  useEffect(() => {
    if (!analysisId) return;
    let isMounted = true;

    Promise.all([
      api.getAnalysis(analysisId),
      api.getRecommendations(analysisId).catch(() => null),
    ])
      .then(([analysisData, recsData]) => {
        if (isMounted) {
          setAnalysis(analysisData);
          setRecommendations(recsData);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error ? err.message : "Failed to load gap analysis";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  // Break items into covered, missing, obsolete
  const { coveredItems, missingItems, obsoleteItems } = useMemo(() => {
    if (!analysis?.items) {
      return { coveredItems: [], missingItems: [], obsoleteItems: [] };
    }
    const covered = analysis.items.filter((i) => i.kind === "covered");
    const missing = analysis.items.filter((i) => i.kind === "missing");
    const obsolete = analysis.items.filter((i) => i.kind === "obsolete");
    return {
      coveredItems: covered,
      missingItems: missing,
      obsoleteItems: obsolete,
    };
  }, [analysis]);

  // Domain categories
  const categories = useMemo(() => {
    if (!analysis?.items) return ["ALL"];
    const cats = new Set<string>();
    analysis.items.forEach((item) => {
      if (item.category) cats.add(item.category);
    });
    return ["ALL", ...Array.from(cats)];
  }, [analysis]);

  // Category comparison stats
  const categoryStats = useMemo(() => {
    if (!analysis?.items) return [];
    const map = new Map<
      string,
      { category: string; covered: number; missing: number; obsolete: number }
    >();

    analysis.items.forEach((it) => {
      const cat = it.category || "General";
      const existing = map.get(cat) || {
        category: cat,
        covered: 0,
        missing: 0,
        obsolete: 0,
      };
      if (it.kind === "covered") existing.covered++;
      else if (it.kind === "missing") existing.missing++;
      else if (it.kind === "obsolete") existing.obsolete++;
      map.set(cat, existing);
    });

    return Array.from(map.values());
  }, [analysis]);

  // Filtered skills
  const filteredItems = useMemo(() => {
    if (!analysis?.items) return [];
    return analysis.items.filter((item) => {
      const matchesKind =
        activeFilter === "all" ? true : item.kind === activeFilter;
      const matchesCategory =
        categoryFilter === "ALL" ? true : item.category === categoryFilter;
      return matchesKind && matchesCategory;
    });
  }, [analysis, activeFilter, categoryFilter]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-main)] py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="h-8 bg-[var(--bg-surface-elevated)] rounded-md w-1/3 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="h-64 bg-[var(--bg-surface)] rounded-2xl animate-pulse" />
            <div className="h-64 bg-[var(--bg-surface)] rounded-2xl animate-pulse md:col-span-2" />
          </div>
          <div className="h-96 bg-[var(--bg-surface)] rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-[var(--bg-main)] py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-xl mx-auto bg-[var(--bg-surface)] p-8 rounded-2xl border border-[var(--color-status-missing)]/30 text-center space-y-4">
          <h2 className="text-lg font-bold text-[var(--color-status-missing)]">
            {error || "Analysis report not found"}
          </h2>
          <p className="text-xs sm:text-sm text-[var(--text-muted)]">
            The requested curriculum gap report could not be loaded. It may have been removed or an invalid identifier was supplied.
          </p>
          <div className="pt-2">
            <Link
              href="/analysis"
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)]"
            >
              Return to Analysis Directory
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const gapPct = Math.round(analysis.gap_pct);
  const coveragePct = Math.round(analysis.coverage_pct);

  // SVG Gauge calculations
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const gapStrokeDashoffset = circumference - (gapPct / 100) * circumference;

  return (
    <div className="min-h-screen bg-[var(--bg-main)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Navigation Breadcrumb & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Link
                href="/analysis"
                className="text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
              >
                ← All Analyses
              </Link>
              <span className="text-[var(--text-muted)] text-xs">/</span>
              <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/20 px-2 py-0.5 rounded-full">
                Evaluation Report
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-main)] tracking-tight">
              Curriculum Gap Assessment: {analysis.role_query}
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-[var(--text-muted)]">
              Market benchmark: {analysis.location || "Global Remote Market"} • Evaluated on{" "}
              {new Date(analysis.created_at).toLocaleDateString([], {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => handleExport("csv")}
                disabled={exporting !== null}
                className="px-3 py-2 text-xs font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition cursor-pointer"
              >
                {exporting === "csv" ? "Exporting CSV..." : "Export CSV"}
              </button>
              <button
                type="button"
                onClick={() => handleExport("pdf")}
                disabled={exporting !== null}
                className="px-3 py-2 text-xs font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition cursor-pointer"
              >
                {exporting === "pdf" ? "Exporting PDF..." : "Export PDF"}
              </button>
            </div>
            <Link
              href={`/syllabi/${analysis.syllabus_id}`}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition"
            >
              View Syllabus Details
            </Link>
            <Link
              href={`/demand?role=${encodeURIComponent(analysis.role_query)}`}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)] hover:opacity-90 transition shadow-sm"
            >
              Explore Live Vacancies
            </Link>
          </div>
        </div>

        {/* Top Summary Metrics: Gauge & Category Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Circular Gap & Coverage Gauge Card */}
          <div className="bg-[var(--bg-surface)] p-6 rounded-2xl border border-[var(--border-subtle)] shadow-sm flex flex-col items-center justify-center text-center">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] mb-4">
              Curriculum Alignment Metric
            </h2>

            {/* Circular Gauge */}
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                {/* Background Track */}
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  className="text-[var(--bg-surface-elevated)] stroke-current"
                  strokeWidth="12"
                  fill="transparent"
                />
                {/* Coverage Arc (Pine Green / Aqua) */}
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  className="text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] stroke-current transition-all duration-1000 ease-out"
                  strokeWidth="12"
                  strokeDasharray={circumference}
                  strokeDashoffset={gapStrokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>

              {/* Center Metrics Label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-extrabold text-[var(--text-main)]">
                  {gapPct}%
                </span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-brand-yellow)]">
                  Skill Deficit
                </span>
                <span className="text-[10px] text-[var(--text-muted)] mt-0.5">
                  {coveragePct}% Covered
                </span>
              </div>
            </div>

            {/* Qualitative Assessment Tag */}
            <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] w-full">
              <span
                className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                  gapPct <= 25
                    ? "bg-[var(--color-brand-mint)] text-[var(--color-brand-green)] dark:bg-[var(--color-brand-green)]/20 dark:text-[var(--color-brand-aqua)]"
                    : gapPct <= 45
                    ? "bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]"
                    : "bg-[var(--color-status-missing)]/10 text-[var(--color-status-missing)]"
                }`}
              >
                {gapPct <= 25
                  ? "High Industry Alignment"
                  : gapPct <= 45
                  ? "Moderate Alignment Gap"
                  : "Critical Revision Required"}
              </span>
              <p className="text-[11px] text-[var(--text-muted)] mt-1.5">
                Reflects weighted demand presence across {analysis.items.length} core market competencies.
              </p>
            </div>
          </div>

          {/* Category Comparison Chart Card */}
          <div className="bg-[var(--bg-surface)] p-6 rounded-2xl border border-[var(--border-subtle)] shadow-sm lg:col-span-2 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Domain Category Comparison
                </h2>
                <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[var(--color-brand-green)]"></span>
                    Covered
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[var(--color-brand-yellow)]"></span>
                    Missing
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[var(--border-subtle)]"></span>
                    Obsolete
                  </span>
                </div>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-2">
                Comparative competency alignment across technical domains identified in the syllabus versus hiring market requirements.
              </p>
            </div>

            {/* Comparative Bars */}
            <div className="space-y-3 pt-2">
              {categoryStats.map((stat) => {
                const total = stat.covered + stat.missing + stat.obsolete;
                const coveredPct = total > 0 ? (stat.covered / total) * 100 : 0;
                const missingPct = total > 0 ? (stat.missing / total) * 100 : 0;
                const obsoletePct = total > 0 ? (stat.obsolete / total) * 100 : 0;

                return (
                  <div key={stat.category} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-[var(--text-main)]">
                      <span>{stat.category}</span>
                      <span className="text-[var(--text-muted)] text-[11px]">
                        {stat.covered} covered / {stat.missing} missing ({total} total)
                      </span>
                    </div>
                    {/* Stacked Bar */}
                    <div className="h-4 w-full bg-[var(--bg-main)] rounded-full overflow-hidden flex border border-[var(--border-subtle)]">
                      {coveredPct > 0 && (
                        <div
                          style={{ width: `${coveredPct}%` }}
                          className="bg-[var(--color-brand-green)] h-full transition-all duration-500"
                          title={`${stat.covered} Covered`}
                        />
                      )}
                      {missingPct > 0 && (
                        <div
                          style={{ width: `${missingPct}%` }}
                          className="bg-[var(--color-brand-yellow)] h-full transition-all duration-500"
                          title={`${stat.missing} Missing`}
                        />
                      )}
                      {obsoletePct > 0 && (
                        <div
                          style={{ width: `${obsoletePct}%` }}
                          className="bg-[var(--border-subtle)] h-full transition-all duration-500"
                          title={`${stat.obsolete} Obsolete`}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="text-[11px] text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between">
              <span>{coveredItems.length} skills covered in syllabus</span>
              <span>{missingItems.length} industry gaps to introduce</span>
            </div>
          </div>
        </div>

        {/* Executive Curriculum Recommendations (Skills to Add & Skills to Drop) */}
        {recommendations && (
          <section className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
            <div className="border-b border-[var(--border-subtle)] pb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/20 px-2.5 py-0.5 rounded-full">
                  Actionable Blueprint
                </span>
              </div>
              <h2 className="text-xl font-bold text-[var(--text-main)]">
                Curriculum Modernization Recommendations
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-[var(--text-muted)] max-w-3xl">
                {recommendations.summary ||
                  "Targeted modular adjustments to bridge the syllabus gap and prepare students for immediate industry placement."}
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Skills to Add */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-[var(--border-subtle)]">
                  <h3 className="text-sm font-bold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-brand-green)]"></span>
                    High-Priority Skills to Introduce ({recommendations.skills_to_add.length})
                  </h3>
                  <span className="text-[11px] text-[var(--text-muted)] font-medium">
                    Emergent Demand
                  </span>
                </div>

                <div className="space-y-3">
                  {recommendations.skills_to_add.map((rec: SkillRecommendation) => (
                    <div
                      key={rec.skill_id}
                      className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2 hover:border-[var(--color-brand-green)] transition"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-bold text-[var(--text-main)]">
                            {rec.skill_name}
                          </div>
                          {rec.category && (
                            <span className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">
                              {rec.category}
                            </span>
                          )}
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-bold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]">
                            {rec.demand_pct.toFixed(1)}% Demand
                          </span>
                          {rec.trend_pct > 0 && (
                            <span className="block text-[10px] text-[var(--color-brand-green)]">
                              ▲ +{rec.trend_pct.toFixed(1)}% trend
                            </span>
                          )}
                        </div>
                      </div>

                      <p className="text-xs text-[var(--text-main)]/90 leading-relaxed">
                        {rec.rationale}
                      </p>

                      <div className="flex items-center justify-between text-[11px] font-medium text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)]">
                        <span>Module: {rec.suggested_module}</span>
                        <span>Allocated: ~{rec.suggested_weeks} weeks</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Skills to Drop / Deprecate */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-[var(--border-subtle)]">
                  <h3 className="text-sm font-bold text-[var(--color-brand-yellow)] uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-brand-yellow)]"></span>
                    Topics to Prune or Modernize ({recommendations.skills_to_drop.length})
                  </h3>
                  <span className="text-[11px] text-[var(--text-muted)] font-medium">
                    Declining Relevance
                  </span>
                </div>

                <div className="space-y-3">
                  {recommendations.skills_to_drop.length === 0 ? (
                    <div className="p-6 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] text-center text-xs text-[var(--text-muted)]">
                      No obsolete topics flagged for removal in this curriculum.
                    </div>
                  ) : (
                    recommendations.skills_to_drop.map((rec: SkillRecommendation) => (
                      <div
                        key={rec.skill_id}
                        className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2 hover:border-[var(--color-brand-yellow)] transition"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-sm font-bold text-[var(--text-main)]">
                              {rec.skill_name}
                            </div>
                            {rec.category && (
                              <span className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">
                                {rec.category}
                              </span>
                            )}
                          </div>
                          <div className="text-right">
                            <span className="text-xs font-bold text-[var(--text-muted)]">
                              {rec.demand_pct.toFixed(1)}% Demand
                            </span>
                            <span className="block text-[10px] text-[var(--color-brand-yellow)]">
                              Low Market Value
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-[var(--text-main)]/90 leading-relaxed">
                          {rec.rationale}
                        </p>

                        <div className="flex items-center justify-between text-[11px] font-medium text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)]">
                          <span>Reallocate time to contemporary frameworks</span>
                          <span>Reclaimed: ~{rec.suggested_weeks} weeks</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Detailed Competency Table (Covered, Missing, Obsolete) */}
        <section className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
            <div>
              <h2 className="text-lg font-bold text-[var(--text-main)]">
                Comprehensive Competency Breakdown
              </h2>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                Full itemized inventory of market competencies with coverage status.
              </p>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center gap-1.5 p-1 bg-[var(--bg-surface-elevated)] rounded-lg">
              <button
                type="button"
                onClick={() => setActiveFilter("all")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
                  activeFilter === "all"
                    ? "bg-[var(--bg-surface)] text-[var(--text-main)] shadow-sm border border-[var(--border-subtle)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
                }`}
              >
                All ({analysis.items.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter("covered")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
                  activeFilter === "covered"
                    ? "bg-[var(--bg-surface)] text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] shadow-sm border border-[var(--border-subtle)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
                }`}
              >
                Covered ({coveredItems.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter("missing")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
                  activeFilter === "missing"
                    ? "bg-[var(--bg-surface)] text-[var(--color-brand-yellow)] shadow-sm border border-[var(--border-subtle)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
                }`}
              >
                Missing Deficits ({missingItems.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter("obsolete")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
                  activeFilter === "obsolete"
                    ? "bg-[var(--bg-surface)] text-[var(--text-main)] shadow-sm border border-[var(--border-subtle)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
                }`}
              >
                Obsolete ({obsoleteItems.length})
              </button>
            </div>
          </div>

          {/* Domain Category Filter */}
          {categories.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              <span className="text-xs font-semibold text-[var(--text-muted)] whitespace-nowrap">
                Filter by Category:
              </span>
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium transition cursor-pointer whitespace-nowrap ${
                    categoryFilter === cat
                      ? "bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)]"
                      : "bg-[var(--bg-main)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)]"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}

          {/* Skills Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="py-2.5 pr-4 font-semibold w-12 text-center">Rank</th>
                  <th className="py-2.5 pr-4 font-semibold">Competency Name</th>
                  <th className="py-2.5 pr-4 font-semibold">Domain</th>
                  <th className="py-2.5 pr-4 font-semibold">Alignment Status</th>
                  <th className="py-2.5 pr-4 font-semibold text-right">Market Demand</th>
                  <th className="py-2.5 font-semibold text-right">Job Postings</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {filteredItems.map((it: AnalysisItem, idx: number) => {
                  const isCovered = it.kind === "covered";
                  const isMissing = it.kind === "missing";

                  return (
                    <tr
                      key={it.skill_id}
                      className="hover:bg-[var(--bg-main)]/60 transition"
                    >
                      <td className="py-3 pr-4 text-center font-bold text-[var(--text-muted)]">
                        #{it.rank > 0 ? it.rank : idx + 1}
                      </td>
                      <td className="py-3 pr-4 font-bold text-sm text-[var(--text-main)]">
                        {it.skill_name}
                      </td>
                      <td className="py-3 pr-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]">
                          {it.category || "General"}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                            isCovered
                              ? "bg-[var(--color-brand-mint)] text-[var(--color-brand-green)] dark:bg-[var(--color-brand-green)]/20 dark:text-[var(--color-brand-aqua)]"
                              : isMissing
                              ? "bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]"
                              : "bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isCovered
                                ? "bg-[var(--color-brand-green)]"
                                : isMissing
                                ? "bg-[var(--color-brand-yellow)]"
                                : "bg-[var(--text-muted)]"
                            }`}
                          />
                          {isCovered
                            ? "Covered in Course"
                            : isMissing
                            ? "Missing Market Gap"
                            : "Low Relevance"}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right font-bold text-[var(--text-main)]">
                        {it.demand_pct.toFixed(1)}%
                      </td>
                      <td className="py-3 text-right text-[var(--text-muted)]">
                        {it.demand_count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
