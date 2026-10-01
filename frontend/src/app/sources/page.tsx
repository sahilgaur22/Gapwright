"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Database, ExternalLink, ShieldCheck } from "lucide-react";
import { api, SourceSummary } from "@/lib/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    api
      .listSources()
      .then((data) => {
        if (isMounted) {
          setSources(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-main)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Navigation Breadcrumb */}
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text-main)] transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Home</span>
          </Link>
        </div>

        {/* Page Header */}
        <div className="space-y-3 border-b border-[var(--border-subtle)] pb-6">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]">
            <Database className="w-4 h-4" />
            <span>Compliance &amp; Data Transparency</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-main)]">
            Job Market Data Sources &amp; Attribution
          </h1>
          <p className="text-sm text-[var(--text-muted)] max-w-2xl leading-relaxed">
            In accordance with legal policies, automated ingestion guidelines, and provider Terms of Service, Gapwright aggregates workforce demand from verified public APIs and feeds.
          </p>
        </div>

        {/* Transparency Policy Banner */}
        <div className="p-4 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-start gap-3 shadow-xs">
          <ShieldCheck className="w-5 h-5 text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] shrink-0 mt-0.5" />
          <div className="text-xs text-[var(--text-muted)] space-y-1">
            <p className="font-semibold text-[var(--text-main)]">
              Fair Use &amp; Direct Citation Policy
            </p>
            <p>
              Job data is processed strictly for academic curriculum benchmarking and labor market skill analysis. Gapwright respects all daily rate budgets, robots.txt directives, and provides direct follow back-links to original postings.
            </p>
          </div>
        </div>

        {/* Sources Cards Grid */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-[var(--text-main)]">
            Integrated Data Connectors
          </h2>

          {loading ? (
            <div className="p-8 text-center text-sm text-[var(--text-muted)] rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
              Loading active source registries...
            </div>
          ) : sources.length === 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  name: "Adzuna Job Search API",
                  url: "https://www.adzuna.in",
                  desc: "Nationwide job posting search covering technology, engineering, and data science sectors in India.",
                },
                {
                  name: "Remotive Remote Jobs API",
                  url: "https://remotive.com",
                  desc: "Curated active remote software engineering, DevOps, and cloud infrastructure postings.",
                },
                {
                  name: "RemoteOK Workforce Feed",
                  url: "https://remoteok.com",
                  desc: "Global tech hiring demand covering AI, full-stack, and distributed systems roles.",
                },
                {
                  name: "We Work Remotely RSS Feed",
                  url: "https://weworkremotely.com",
                  desc: "Syndicated remote job postings for architecture, programming, and cybersecurity.",
                },
                {
                  name: "Jooble Aggregator API",
                  url: "https://jooble.org",
                  desc: "Multi-regional job aggregator with structured competency and role requirements.",
                },
              ].map((src) => (
                <div
                  key={src.name}
                  className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex flex-col justify-between gap-3 shadow-xs"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-[var(--text-main)]">
                        {src.name}
                      </span>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[var(--color-brand-mint)]/40 text-[var(--color-brand-navy)]">
                        <CheckCircle2 className="w-3 h-3 text-[var(--color-brand-green)]" />
                        Active
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                      {src.desc}
                    </p>
                  </div>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline pt-2 border-t border-[var(--border-subtle)]"
                  >
                    <span>Visit Official Platform</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sources.map((src) => (
                <div
                  key={src.name}
                  className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex flex-col justify-between gap-3 shadow-xs"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-[var(--text-main)] capitalize">
                        {src.name}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          src.enabled
                            ? "bg-[var(--color-brand-mint)]/40 text-[var(--color-brand-navy)]"
                            : "bg-[var(--color-status-missing-bg)] text-[var(--color-status-missing)]"
                        }`}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        {src.enabled ? "Active" : "Disabled"}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                      Daily API Quota: {src.daily_budget} calls ({src.remaining_budget} remaining today)
                    </p>
                  </div>
                  {src.attribution_url ? (
                    <a
                      href={src.attribution_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)] hover:underline pt-2 border-t border-[var(--border-subtle)]"
                    >
                      <span>{src.attribution_text || "Visit Official Platform"}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-[11px] text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)]">
                      {src.attribution_text || "Integrated System Source"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
