"use client";

import React, { useState, useEffect, useId } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, Analysis, Syllabus } from "@/lib/api";

const PRESET_ROLES = [
  "Full Stack Developer",
  "Backend Engineer",
  "Data Scientist",
  "DevOps Engineer",
  "Machine Learning Engineer",
  "Frontend Developer",
  "Cloud Solutions Architect",
];

const PRESET_LOCATIONS = [
  "All India",
  "Bengaluru",
  "Hyderabad",
  "Pune",
  "Mumbai",
  "Delhi NCR",
];

export default function AnalysisIndexPage() {
  const router = useRouter();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states for new analysis
  const [selectedSyllabusId, setSelectedSyllabusId] = useState("");
  const [roleQuery, setRoleQuery] = useState("Full Stack Developer");
  const [locationQuery, setLocationQuery] = useState("All India");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const syllabusSelectId = useId();
  const roleInputId = useId();
  const locationSelectId = useId();
  const remoteCheckboxId = useId();

  useEffect(() => {
    let isMounted = true;
    Promise.all([api.listAnalyses(), api.listSyllabi()])
      .then(([analysesData, syllabiData]) => {
        if (isMounted) {
          setAnalyses(analysesData);
          setSyllabi(syllabiData);
          if (syllabiData.length > 0) {
            setSelectedSyllabusId(syllabiData[0].id);
          }
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load data";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleCreateAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSyllabusId) {
      setFormError("Please select a syllabus to analyze.");
      return;
    }
    if (!roleQuery.trim()) {
      setFormError("Please enter or select a target role.");
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      const loc = remoteOnly
        ? undefined
        : locationQuery === "All India"
        ? undefined
        : locationQuery;

      const created = await api.createAnalysis(
        selectedSyllabusId,
        roleQuery.trim(),
        loc,
        remoteOnly
      );
      router.push(`/analysis/${created.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create gap analysis";
      setFormError(msg);
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-main)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/20 px-2.5 py-0.5 rounded-full">
                Curriculum Evaluation
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-main)] sm:text-4xl">
              Curriculum Gap Analysis
            </h1>
            <p className="mt-2 text-sm sm:text-base text-[var(--text-muted)] max-w-2xl">
              Compare accredited higher education course syllabi against active labor market vacancies. Compute quantifiable coverage metrics, identify emergent skill deficits, and receive curriculum revision advice.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/syllabi"
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition"
            >
              Upload Syllabus
            </Link>
            <Link
              href="/demand"
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:opacity-90 transition shadow-sm"
            >
              Explore Market Demand
            </Link>
          </div>
        </div>

        {/* Launch New Analysis Form Card */}
        <div className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
          <div className="border-b border-[var(--border-subtle)] pb-4">
            <h2 className="text-xl font-bold text-[var(--text-main)] flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-brand-green)]"></span>
              Initiate New Gap Evaluation
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
              Select an uploaded syllabus and define the target occupational profile to calculate curriculum alignment.
            </p>
          </div>

          {formError && (
            <div className="p-3.5 rounded-lg bg-[var(--color-status-missing)]/10 border border-[var(--color-status-missing)]/30 text-xs font-medium text-[var(--color-status-missing)]">
              {formError}
            </div>
          )}

          <form onSubmit={handleCreateAnalysis} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Syllabus Select */}
              <div className="space-y-2">
                <label htmlFor={syllabusSelectId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Academic Syllabus
                </label>
                {syllabi.length === 0 ? (
                  <div className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-xs text-[var(--text-muted)]">
                    No syllabi uploaded yet.{" "}
                    <Link href="/syllabi" className="font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] underline">
                      Upload a course syllabus first
                    </Link>
                    .
                  </div>
                ) : (
                  <select
                    id={syllabusSelectId}
                    value={selectedSyllabusId}
                    onChange={(e) => setSelectedSyllabusId(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
                    required
                  >
                    {syllabi.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.course_code ? `[${s.course_code}] ` : ""}
                        {s.title}
                        {s.institution ? ` (${s.institution})` : ""}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Target Role */}
              <div className="space-y-2">
                <label htmlFor={roleInputId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Target Role / Occupational Specialization
                </label>
                <input
                  id={roleInputId}
                  type="text"
                  value={roleQuery}
                  onChange={(e) => setRoleQuery(e.target.value)}
                  placeholder="e.g. Full Stack Developer, Data Scientist..."
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
                  required
                />
                {/* Presets */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {PRESET_ROLES.map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setRoleQuery(r)}
                      className={`text-[11px] px-2 py-0.5 rounded-full border transition cursor-pointer ${
                        roleQuery === r
                          ? "border-[var(--color-brand-green)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/30 text-[var(--color-brand-navy)] dark:text-[var(--color-brand-aqua)] font-medium"
                          : "border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)]"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Location & Remote Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-[var(--border-subtle)]">
              <div className="space-y-2">
                <label htmlFor={locationSelectId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Geographic Market Filter
                </label>
                <select
                  id={locationSelectId}
                  value={locationQuery}
                  onChange={(e) => setLocationQuery(e.target.value)}
                  disabled={remoteOnly}
                  className={`w-full px-3.5 py-2.5 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)] ${
                    remoteOnly ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  {PRESET_LOCATIONS.map((loc) => (
                    <option key={loc} value={loc}>
                      {loc}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3 pt-6">
                <input
                  id={remoteCheckboxId}
                  type="checkbox"
                  checked={remoteOnly}
                  onChange={(e) => setRemoteOnly(e.target.checked)}
                  className="w-4 h-4 rounded text-[var(--color-brand-green)] focus:ring-[var(--color-brand-green)] border-[var(--border-subtle)]"
                />
                <label htmlFor={remoteCheckboxId} className="text-xs sm:text-sm font-medium text-[var(--text-main)] cursor-pointer">
                  Evaluate Against Global Remote Vacancies Only
                  <span className="block text-[11px] text-[var(--text-muted)]">
                    Filters exclusively to remote listings from Remotive, RemoteOK, and WWR.
                  </span>
                </label>
              </div>
            </div>

            {/* Submit Action */}
            <div className="flex justify-end pt-4 border-t border-[var(--border-subtle)]">
              <button
                type="submit"
                disabled={submitting || syllabi.length === 0}
                className="px-6 py-2.5 rounded-lg bg-[var(--color-brand-navy)] dark:bg-[var(--color-brand-aqua)] text-white dark:text-[var(--color-brand-navy)] font-semibold text-sm hover:opacity-90 transition disabled:opacity-50 shadow-sm cursor-pointer"
              >
                {submitting ? "Analyzing Curriculum Alignment..." : "Run Gap Analysis"}
              </button>
            </div>
          </form>
        </div>

        {/* Historical Analyses List */}
        <div className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-4">
            <div>
              <h2 className="text-xl font-bold text-[var(--text-main)]">
                Evaluated Curriculum Records
              </h2>
              <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
                Historical gap analysis reports generated for accredited courses.
              </p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]">
              {analyses.length} {analyses.length === 1 ? "report" : "reports"}
            </span>
          </div>

          {loading ? (
            <div className="space-y-3 py-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-[var(--bg-surface-elevated)] rounded-xl animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="p-6 text-center text-sm font-semibold text-[var(--color-status-missing)]">
              {error}
            </div>
          ) : analyses.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-[var(--color-brand-pink)] flex items-center justify-center text-[var(--color-brand-navy)] font-bold text-lg">
                📊
              </div>
              <h3 className="text-base font-semibold text-[var(--text-main)]">
                No Analysis Reports Yet
              </h3>
              <p className="text-xs sm:text-sm text-[var(--text-muted)] max-w-sm mx-auto">
                Select an academic syllabus above and choose a target career track to compute your first curriculum gap assessment.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analyses.map((a) => {
                const gap = Math.round(a.gap_pct);
                const coverage = Math.round(a.coverage_pct);
                const dateStr = new Date(a.created_at).toLocaleDateString([], {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                });

                return (
                  <Link
                    key={a.id}
                    href={`/analysis/${a.id}`}
                    className="group block p-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] hover:border-[var(--color-brand-green)] hover:shadow-md transition"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wider text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]">
                          {a.role_query}
                        </div>
                        <h4 className="text-base font-bold text-[var(--text-main)] group-hover:text-[var(--color-brand-green)] dark:group-hover:text-[var(--color-brand-aqua)] transition-colors mt-0.5">
                          {a.location ? `${a.location} Market` : "Global Remote Market"}
                        </h4>
                      </div>

                      {/* Gap % Badge */}
                      <div className="text-right">
                        <div className="text-lg font-extrabold text-[var(--text-main)]">
                          {gap}%
                        </div>
                        <div className="text-[10px] uppercase font-semibold text-[var(--color-brand-yellow)]">
                          Deficit
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-[var(--bg-surface-elevated)] h-2 rounded-full overflow-hidden my-3">
                      <div
                        className="h-full bg-gradient-to-r from-[var(--color-brand-green)] to-[var(--color-brand-aqua)]"
                        style={{ width: `${coverage}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs text-[var(--text-muted)] pt-1">
                      <span>{coverage}% Market Coverage</span>
                      <span>Evaluated: {dateStr}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
