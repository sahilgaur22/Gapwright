"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Code2,
  FileText,
  Filter,
  Loader2,
  Quote,
  Search,
  Sparkles,
} from "lucide-react";
import { api, Syllabus } from "@/lib/api";

export default function SyllabusDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  const [syllabus, setSyllabus] = useState<Syllabus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  useEffect(() => {
    let isMounted = true;
    Promise.resolve(params)
      .then((resolved) => api.getSyllabus(resolved.id))
      .then((data) => {
        if (isMounted) {
          setSyllabus(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Failed to load syllabus details"
          );
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [params]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 flex flex-col items-center justify-center gap-3 text-sm text-[var(--text-muted)]">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--color-brand-yellow)]" />
        <span>Loading syllabus curriculum &amp; extracted competencies...</span>
      </div>
    );
  }

  if (error || !syllabus) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 flex flex-col items-center justify-center text-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-[var(--color-status-missing-bg)] text-[var(--color-status-missing)] flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-[var(--text-main)]">
          Could Not Load Syllabus
        </h2>
        <p className="text-xs text-[var(--text-muted)] max-w-md">
          {error || "The requested syllabus document was not found or has been removed."}
        </p>
        <Link
          href="/syllabi"
          className="mt-2 px-4 py-2 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-xs hover:opacity-90 transition flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Syllabi</span>
        </Link>
      </div>
    );
  }

  const skills = syllabus.skills || [];
  const categories = Array.from(
    new Set(skills.map((s) => s.category || "General"))
  ).sort();

  const filteredSkills = skills.filter((s) => {
    const matchesSearch =
      s.skill_name.toLowerCase().includes(search.toLowerCase()) ||
      s.evidence.toLowerCase().includes(search.toLowerCase());
    const matchesCat =
      selectedCategory === "all" || (s.category || "General") === selectedCategory;
    return matchesSearch && matchesCat;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 flex flex-col gap-8">
      {/* Back Navigation */}
      <div>
        <Link
          href="/syllabi"
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text-main)] transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Syllabi Catalog</span>
        </Link>
      </div>

      {/* Header Banner */}
      <div className="p-6 md:p-8 rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex flex-col gap-2 max-w-3xl">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--color-status-covered-bg)] text-[var(--color-status-covered)] inline-flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>{syllabus.status}</span>
            </span>
            <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>
                {syllabus.created_at
                  ? new Date(syllabus.created_at).toLocaleDateString()
                  : "Recent"}
              </span>
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-main)] tracking-tight">
            {syllabus.title}
          </h1>

          <p className="text-xs text-[var(--text-muted)] flex items-center gap-1.5 font-mono">
            <FileText className="w-3.5 h-3.5 text-[var(--color-brand-yellow)] shrink-0" />
            <span>{syllabus.filename}</span>
          </p>
        </div>

        <Link
          href={`/analysis?syllabus_id=${syllabus.id}`}
          className="px-5 py-3 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-xs hover:opacity-90 transition flex items-center gap-2 shrink-0 shadow-sm"
        >
          <span>Run Gap Analysis</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-status-covered-bg)] text-[var(--color-status-covered)] flex items-center justify-center shrink-0">
            <Code2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)] font-medium">
              Extracted Competencies
            </p>
            <p className="text-xl font-extrabold text-[var(--text-main)] mt-0.5">
              {skills.length}
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-status-warning-bg)] text-[var(--color-brand-yellow)] flex items-center justify-center shrink-0">
            <Filter className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)] font-medium">
              Identified Domains
            </p>
            <p className="text-xl font-extrabold text-[var(--text-main)] mt-0.5">
              {categories.length}
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-brand-pink)] text-[var(--color-brand-navy)] flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)] font-medium">
              Taxonomy Mapping
            </p>
            <p className="text-xl font-extrabold text-[var(--text-main)] mt-0.5">
              Normalized
            </p>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter competencies or syllabus evidence..."
            className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setSelectedCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer whitespace-nowrap ${
              selectedCategory === "all"
                ? "bg-[var(--color-primary)] text-[var(--color-primary-text)]"
                : "bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)]"
            }`}
          >
            All ({skills.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer whitespace-nowrap ${
                selectedCategory === cat
                  ? "bg-[var(--color-primary)] text-[var(--color-primary-text)]"
                  : "bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Extracted Skills List */}
      {filteredSkills.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex flex-col items-center justify-center gap-2">
          <BookOpen className="w-8 h-8 text-[var(--text-muted)]" />
          <p className="text-sm font-bold text-[var(--text-main)]">
            No Competencies Match Your Filter
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            Try adjusting your search query or selected category domain.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredSkills.map((item) => (
            <div
              key={item.id || item.skill_id}
              className="p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex flex-col justify-between gap-3 shadow-sm hover:border-[var(--border-strong)] transition"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-sm font-bold text-[var(--text-main)]">
                  {item.skill_name}
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-muted)]">
                  {item.category || "General"}
                </span>
              </div>

              {item.evidence && (
                <div className="p-3 rounded-xl bg-[var(--bg-page)] border border-[var(--border-subtle)]/60 text-xs text-[var(--text-muted)] flex items-start gap-2 italic">
                  <Quote className="w-3.5 h-3.5 shrink-0 text-[var(--color-brand-yellow)] mt-0.5" />
                  <p className="line-clamp-3">&ldquo;{item.evidence}&rdquo;</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
