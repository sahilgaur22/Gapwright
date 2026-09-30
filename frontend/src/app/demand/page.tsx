"use client";

import React, { useState, useEffect, useCallback, useId } from "react";
import Link from "next/link";
import { api, SkillDemandItem, TopSkillsResponse, SourceSummary } from "@/lib/api";

type MarketMode = "location" | "remote";

const POPULAR_ROLES = [
  "Full Stack Developer",
  "Backend Engineer",
  "Data Scientist",
  "DevOps Engineer",
  "Machine Learning Engineer",
  "Frontend Developer",
  "Cloud Solutions Architect",
];

const POPULAR_LOCATIONS = [
  "All India",
  "Bengaluru",
  "Hyderabad",
  "Pune",
  "Mumbai",
  "Delhi NCR",
  "Chennai",
];

export default function MarketDemandPage() {
  const [marketMode, setMarketMode] = useState<MarketMode>("location");
  const [roleQuery, setRoleQuery] = useState("Full Stack Developer");
  const [locationQuery, setLocationQuery] = useState("All India");
  const [windowDays, setWindowDays] = useState(30);
  const [skillLimit, setSkillLimit] = useState(20);
  const [selectedCategory, setSelectedCategory] = useState("ALL");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demandData, setDemandData] = useState<TopSkillsResponse | null>(null);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  const [refreshKey, setRefreshKey] = useState(0);

  const roleInputId = useId();
  const locationInputId = useId();
  const windowDaysId = useId();
  const skillLimitId = useId();

  // Load data sources info
  useEffect(() => {
    let isMounted = true;
    api
      .listSources()
      .then((data) => {
        if (isMounted) {
          setSources(data);
          setSourcesLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSourcesLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loc =
      marketMode === "remote"
        ? "Remote"
        : locationQuery === "All India"
        ? undefined
        : locationQuery;

    api
      .getTopSkills(roleQuery, loc, windowDays, skillLimit)
      .then((data) => {
        if (isMounted) {
          setDemandData(data);
          setLastFetched(new Date());
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error
              ? err.message
              : "Failed to load market demand metrics";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [marketMode, roleQuery, locationQuery, windowDays, skillLimit, refreshKey]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    setRefreshKey((k) => k + 1);
  }, []);

  // Extract unique categories
  const categories = React.useMemo(() => {
    if (!demandData?.skills) return ["ALL"];
    const cats = new Set<string>();
    demandData.skills.forEach((s) => {
      if (s.category) cats.add(s.category);
    });
    return ["ALL", ...Array.from(cats)];
  }, [demandData]);

  // Filter skills by selected category
  const filteredSkills = React.useMemo(() => {
    if (!demandData?.skills) return [];
    if (selectedCategory === "ALL") return demandData.skills;
    return demandData.skills.filter((s) => s.category === selectedCategory);
  }, [demandData, selectedCategory]);

  return (
    <div className="min-h-screen bg-[var(--bg-main)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header & Subheading */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/20 px-2.5 py-0.5 rounded-full">
                Labour Market Intelligence
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-main)] sm:text-4xl">
              Market Demand Explorer
            </h1>
            <p className="mt-2 text-sm sm:text-base text-[var(--text-muted)] max-w-2xl">
              Real-time skill requirements aggregated from major national and global hiring portals. Analyze industry trends to ground academic curricula in current workplace needs.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/syllabi"
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition"
            >
              Curriculum Catalog
            </Link>
            <Link
              href={`/syllabi?role=${encodeURIComponent(roleQuery)}`}
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:opacity-90 transition shadow-sm"
            >
              Analyze a Syllabus
            </Link>
          </div>
        </div>

        {/* Market Mode Tabs (Location-based vs Remote Roles) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-surface)] p-2 rounded-xl border border-[var(--border-subtle)] shadow-sm">
          <div className="flex items-center gap-2 p-1 bg-[var(--bg-surface-elevated)] rounded-lg">
            <button
              type="button"
              onClick={() => {
                setMarketMode("location");
              }}
              className={`px-4 py-2 text-xs sm:text-sm font-semibold rounded-md transition cursor-pointer ${
                marketMode === "location"
                  ? "bg-[var(--bg-surface)] text-[var(--text-main)] shadow-sm border border-[var(--border-subtle)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
              }`}
            >
              Location-Based Roles (India & Regional Hubs)
            </button>
            <button
              type="button"
              onClick={() => {
                setMarketMode("remote");
              }}
              className={`px-4 py-2 text-xs sm:text-sm font-semibold rounded-md transition cursor-pointer ${
                marketMode === "remote"
                  ? "bg-[var(--bg-surface)] text-[var(--text-main)] shadow-sm border border-[var(--border-subtle)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-main)]"
              }`}
            >
              Remote Roles (Global & Distributed Market)
            </button>
          </div>

          <div className="text-xs text-[var(--text-muted)] px-3">
            {marketMode === "location" ? (
              <span>Sourced from primary domestic job engines (Adzuna, Jooble)</span>
            ) : (
              <span>Sourced from dedicated remote exchanges (Remotive, RemoteOK, WWR)</span>
            )}
          </div>
        </div>

        {/* Filter Controls Grid */}
        <div className="bg-[var(--bg-surface)] p-6 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Target Role Input & Presets */}
            <div className="md:col-span-2 space-y-1.5">
              <label htmlFor={roleInputId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Target Professional Role
              </label>
              <input
                id={roleInputId}
                type="text"
                value={roleQuery}
                onChange={(e) => setRoleQuery(e.target.value)}
                placeholder="e.g. Full Stack Developer, Data Scientist..."
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
              />
              {/* Presets pills */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {POPULAR_ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRoleQuery(r)}
                    className={`text-[11px] px-2 py-0.5 rounded-full border transition cursor-pointer ${
                      roleQuery === r
                        ? "border-[var(--color-brand-green)] bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/30 text-[var(--color-brand-navy)] dark:text-[var(--color-brand-aqua)] font-medium"
                        : "border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)]"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Location Selector (Disabled if Remote Mode) */}
            <div className="space-y-1.5">
              <label htmlFor={locationInputId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Location
              </label>
              {marketMode === "remote" ? (
                <div className="px-3.5 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] text-[var(--text-muted)] font-medium">
                  Remote / Global Anywhere
                </div>
              ) : (
                <>
                  <select
                    id={locationInputId}
                    value={locationQuery}
                    onChange={(e) => setLocationQuery(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
                  >
                    {POPULAR_LOCATIONS.map((loc) => (
                      <option key={loc} value={loc}>
                        {loc}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-[var(--text-muted)]">
                    Filter by Indian technological clusters
                  </p>
                </>
              )}
            </div>

            {/* Trend Window & Limit Selectors */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <label htmlFor={windowDaysId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Window
                </label>
                <select
                  id={windowDaysId}
                  value={windowDays}
                  onChange={(e) => setWindowDays(Number(e.target.value))}
                  className="w-full px-2.5 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
                >
                  <option value={15}>15 days</option>
                  <option value={30}>30 days</option>
                  <option value={60}>60 days</option>
                  <option value={90}>90 days</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor={skillLimitId} className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Skill Cap
                </label>
                <select
                  id={skillLimitId}
                  value={skillLimit}
                  onChange={(e) => setSkillLimit(Number(e.target.value))}
                  className="w-full px-2.5 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-green)]"
                >
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                  <option value={30}>Top 30</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Freshness & Metadata Bar */}
        <div className="bg-[var(--bg-surface)] p-4 rounded-xl border border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-status-covered)] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[var(--color-status-covered)]"></span>
            </span>
            <span className="font-semibold text-[var(--text-main)]">
              Based on {demandData?.total_postings ?? 0} active job postings
            </span>
            <span className="text-[var(--text-muted)]">•</span>
            <span className="text-[var(--text-muted)]">
              Trend baseline: {windowDays} days
            </span>
          </div>

          <div className="text-xs text-[var(--text-muted)] flex items-center gap-2">
            <span>
              Last updated: {lastFetched ? lastFetched.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "Checking..."}
            </span>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="text-xs px-2.5 py-1 rounded border border-[var(--border-subtle)] hover:bg-[var(--bg-surface-elevated)] text-[var(--text-main)] transition cursor-pointer"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Category Pills Filter */}
        {categories.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-xs font-semibold text-[var(--text-muted)] whitespace-nowrap">
              Domain Filter:
            </span>
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`text-xs px-3 py-1 rounded-full font-medium transition cursor-pointer whitespace-nowrap ${
                  selectedCategory === cat
                    ? "bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)] shadow-sm"
                    : "bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)]"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* Main Content Area: Chart & Breakdown */}
        {loading ? (
          <div className="bg-[var(--bg-surface)] p-8 rounded-2xl border border-[var(--border-subtle)] space-y-4">
            <div className="h-6 bg-[var(--bg-surface-elevated)] rounded-md w-1/4 animate-pulse"></div>
            <div className="space-y-3 pt-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="h-4 bg-[var(--bg-surface-elevated)] rounded w-28 animate-pulse"></div>
                  <div className="h-6 bg-[var(--bg-surface-elevated)] rounded-full flex-1 animate-pulse"></div>
                  <div className="h-4 bg-[var(--bg-surface-elevated)] rounded w-16 animate-pulse"></div>
                </div>
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="bg-[var(--bg-surface)] p-8 rounded-2xl border border-[var(--color-status-missing)]/30 text-center space-y-3">
            <p className="text-sm font-semibold text-[var(--color-status-missing)]">
              {error}
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              Please verify your network connection or try a different role query.
            </p>
            <button
              type="button"
              onClick={handleRefresh}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-[var(--color-brand-navy)] text-white dark:bg-[var(--color-brand-aqua)] dark:text-[var(--color-brand-navy)]"
            >
              Retry Demand Query
            </button>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="bg-[var(--bg-surface)] p-12 rounded-2xl border border-[var(--border-subtle)] text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-full bg-[var(--color-brand-pink)] flex items-center justify-center text-[var(--color-brand-navy)] font-bold text-lg">
              ?
            </div>
            <h3 className="text-base font-semibold text-[var(--text-main)]">
              No Skill Data Available for this Query
            </h3>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] max-w-md mx-auto">
              No recent postings matched &quot;{roleQuery}&quot; in {marketMode === "remote" ? "Remote" : locationQuery}. Try selecting one of the popular roles or broadening the location.
            </p>
          </div>
        ) : (
          <div className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[var(--border-subtle)] pb-4">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-main)]">
                  Top Demanded Competencies for {demandData?.role_query}
                </h2>
                <p className="text-xs text-[var(--text-muted)]">
                  Calculated as percentage of postings requiring each skill, with {windowDays}-day trend movement.
                </p>
              </div>
              <div className="text-xs font-semibold text-[var(--text-muted)]">
                Showing {filteredSkills.length} competencies
              </div>
            </div>

            {/* Visual Bar Chart */}
            <div className="space-y-4">
              {filteredSkills.map((skill: SkillDemandItem, index: number) => {
                const trend = skill.trend_pct ?? 0;
                const isPositive = trend > 0;
                const isNegative = trend < 0;

                return (
                  <div
                    key={skill.skill_id || skill.name}
                    className="group flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 p-2.5 rounded-xl hover:bg-[var(--bg-surface-elevated)] transition"
                  >
                    {/* Rank & Skill Name */}
                    <div className="flex items-center gap-3 sm:w-60 min-w-0">
                      <span className="text-xs font-bold text-[var(--text-muted)] w-6 text-right">
                        #{index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-[var(--text-main)] truncate">
                          {skill.name}
                        </div>
                        {skill.category && (
                          <span className="inline-block text-[10px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
                            {skill.category}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Horizontal Bar Chart Container */}
                    <div className="flex-1 flex items-center gap-3">
                      <div className="flex-1 bg-[var(--bg-main)] h-5 rounded-full overflow-hidden border border-[var(--border-subtle)] p-0.5">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[var(--color-brand-green)] to-[var(--color-brand-aqua)] transition-all duration-500 ease-out"
                          style={{
                            width: `${Math.min(100, Math.max(4, skill.demand_pct))}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs font-bold text-[var(--text-main)] w-14 text-right">
                        {skill.demand_pct.toFixed(1)}%
                      </span>
                    </div>

                    {/* Postings Count & Trend Indicator Badge */}
                    <div className="flex items-center justify-between sm:justify-end gap-3 sm:w-48 text-xs">
                      <span className="text-[var(--text-muted)] text-[11px]">
                        {skill.postings_count} {skill.postings_count === 1 ? "posting" : "postings"}
                      </span>

                      <div
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                          isPositive
                            ? "bg-[var(--color-brand-mint)] dark:bg-[var(--color-brand-green)]/30 text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]"
                            : isNegative
                            ? "bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]"
                            : "bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]"
                        }`}
                      >
                        {isPositive ? (
                          <>
                            <span>▲</span>
                            <span>+{trend.toFixed(1)}%</span>
                          </>
                        ) : isNegative ? (
                          <>
                            <span>▼</span>
                            <span>{trend.toFixed(1)}%</span>
                          </>
                        ) : (
                          <span>0.0%</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Sources Footer with Plain Follow Links per §5 */}
        <section className="bg-[var(--bg-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--border-subtle)] shadow-sm space-y-6">
          <div className="border-b border-[var(--border-subtle)] pb-4">
            <h2 className="text-lg font-bold text-[var(--text-main)] flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-brand-navy)] dark:bg-[var(--color-brand-aqua)]"></span>
              Job Market Data Sources & Compliance Attribution
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-[var(--text-muted)]">
              In accordance with Section 5 of the system architecture and provider terms of service, all data sources used for market extraction are listed below with quota status and direct attribution back-links.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Adzuna */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">Adzuna</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--color-brand-mint)] text-[var(--color-brand-green)] dark:bg-[var(--color-brand-green)]/20 dark:text-[var(--color-brand-aqua)]">
                  P1 • Domestic
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Primary API for verified Indian tech listings with role and location targeting.
              </p>
              <div className="pt-2 text-xs">
                {/* Note: Terms require follow link per §5 */}
                <a
                  href="https://www.adzuna.in"
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline inline-flex items-center gap-1"
                >
                  Jobs powered by Adzuna ↗
                </a>
              </div>
            </div>

            {/* Jooble */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">Jooble</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--color-brand-mint)] text-[var(--color-brand-green)] dark:bg-[var(--color-brand-green)]/20 dark:text-[var(--color-brand-aqua)]">
                  P1 • Domestic
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                National search aggregator providing localized vacancy distribution.
              </p>
              <div className="pt-2 text-xs">
                <a
                  href="https://jooble.org"
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline inline-flex items-center gap-1"
                >
                  Postings via Jooble API ↗
                </a>
              </div>
            </div>

            {/* Remotive */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">Remotive</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]">
                  P2 • Remote Only
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Public feed utilized for internal skill aggregate metrics (~24h delay).
              </p>
              <div className="pt-2 text-xs">
                <a
                  href="https://remotive.com"
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline inline-flex items-center gap-1"
                >
                  Data provided by Remotive ↗
                </a>
              </div>
            </div>

            {/* RemoteOK */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">RemoteOK</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]">
                  P2 • Remote Only
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Global remote listings exchange. Non-commercial aggregated skill analysis.
              </p>
              <div className="pt-2 text-xs">
                {/* Note: Terms strictly require follow (no nofollow) link per §5 */}
                <a
                  href="https://remoteok.com"
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline inline-flex items-center gap-1"
                >
                  Remote Jobs by RemoteOK ↗
                </a>
              </div>
            </div>

            {/* We Work Remotely */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">We Work Remotely</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--color-brand-pink)] text-[var(--color-brand-yellow)]">
                  P2 • Remote Only
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Syndicated remote tech opportunity feeds and category boards.
              </p>
              <div className="pt-2 text-xs">
                <a
                  href="https://weworkremotely.com"
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline inline-flex items-center gap-1"
                >
                  Syndicated via We Work Remotely ↗
                </a>
              </div>
            </div>

            {/* FixtureSource (Offline / Resilience Fallback) */}
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-main)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[var(--text-main)]">FixtureSource</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]">
                  Resilience • Curated
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Curated national benchmark dataset ensuring high availability during quota maintenance.
              </p>
              <div className="pt-2 text-xs text-[var(--text-muted)]">
                Internal reference baseline
              </div>
            </div>
          </div>

          {/* Live System Source Status Table */}
          {!sourcesLoading && sources.length > 0 && (
            <div className="pt-4 border-t border-[var(--border-subtle)]">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-3">
                Live Daily Quota & Health Status
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 pr-4 font-semibold">Source</th>
                      <th className="py-2 pr-4 font-semibold">Priority</th>
                      <th className="py-2 pr-4 font-semibold">Status</th>
                      <th className="py-2 pr-4 font-semibold">Daily Budget</th>
                      <th className="py-2 pr-4 font-semibold">Used Today</th>
                      <th className="py-2 font-semibold">Remaining</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)]">
                    {sources.map((src) => (
                      <tr key={src.name} className="hover:bg-[var(--bg-main)]/50">
                        <td className="py-2 pr-4 font-semibold text-[var(--text-main)] capitalize">
                          {src.name}
                        </td>
                        <td className="py-2 pr-4 text-[var(--text-muted)]">
                          P{src.priority}
                        </td>
                        <td className="py-2 pr-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              src.enabled
                                ? "bg-[var(--color-brand-mint)] text-[var(--color-brand-green)] dark:bg-[var(--color-brand-green)]/20 dark:text-[var(--color-brand-aqua)]"
                                : "bg-[var(--bg-surface-elevated)] text-[var(--text-muted)]"
                            }`}
                          >
                            {src.enabled ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="py-2 pr-4 text-[var(--text-muted)]">
                          {src.daily_budget} calls
                        </td>
                        <td className="py-2 pr-4 text-[var(--text-muted)]">
                          {src.daily_calls_used}
                        </td>
                        <td className="py-2 font-semibold text-[var(--text-main)]">
                          {src.remaining_budget}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="text-[11px] text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)]">
            Notice: All crawler executions respect robots.txt politeness delays and rate limits as defined in Section 5. Remote listings are analyzed for statistical trends only. Attribution links strictly follow standard open web specifications without `nofollow` attributes.
          </div>
        </section>
      </div>
    </div>
  );
}
