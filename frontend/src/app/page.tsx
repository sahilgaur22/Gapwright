import React from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle,
  Layers,
  Sparkles,
} from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col gap-12 pb-16">
      {/* Hero Section */}
      <section className="pt-6 sm:pt-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="relative min-h-[460px] md:min-h-[520px] rounded-2xl md:rounded-3xl overflow-hidden shadow-xl border border-[var(--border-subtle)] flex items-center justify-center p-6 sm:p-12 text-center">
            {/* Background Image */}
            <Image
              src="/home_page_pic.jpg"
              alt="University lecture and industry collaboration"
              fill
              priority
              className="object-cover object-center"
            />

            {/* Translucent Darkened Overlay using Brand Navy (tweaked down for image visibility) */}
            <div className="absolute inset-0 bg-gradient-to-b from-[#0C2C47]/50 via-[#0C2C47]/40 to-[#0C2C47]/55 dark:from-[#081826]/65 dark:via-[#081826]/50 dark:to-[#081826]/65 backdrop-blur-[0.5px]" />

            {/* Hero Content */}
            <div className="relative z-10 max-w-3xl flex flex-col items-center gap-6 text-[#EFEAE6]">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#97D3CD]/30 bg-[#97D3CD]/15 text-[#97D3CD] text-xs font-semibold uppercase tracking-wider backdrop-blur-sm">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Automated Syllabus-to-Industry Gap Analyzer</span>
              </div>

              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-tight">
                Gapwright
              </h1>

              <p className="text-xl sm:text-2xl font-medium text-[#97D3CD] max-w-2xl">
                Build the fix for the gap between syllabus and skills.
              </p>

              <p className="text-sm sm:text-base text-[#EFEAE6]/90 max-w-2xl leading-relaxed">
                We don&apos;t tell students which jobs to apply for. We tell universities which topics to
                teach, keep, or drop, using live job-market data.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
                <Link
                  href="/syllabi"
                  className="px-6 py-3 rounded-xl bg-[#97D3CD] text-[#0C2C47] font-semibold text-sm hover:bg-[#85c8c2] transition shadow-md flex items-center gap-2 cursor-pointer"
                >
                  Upload Syllabus
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/demand"
                  className="px-6 py-3 rounded-xl border border-[#EFEAE6]/30 bg-[#EFEAE6]/10 text-[#EFEAE6] font-semibold text-sm hover:bg-[#EFEAE6]/20 transition backdrop-blur-sm cursor-pointer"
                >
                  Explore Market Demand
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Pillars */}
      <section id="about" className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 w-full scroll-mt-24">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-main)]">
            How Gapwright Aligns Academia with Industry
          </h2>
          <p className="text-sm sm:text-base text-[var(--text-muted)] mt-2">
            Evidence-backed gap measurement and actionable recommendations based on real-time hiring trends.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-sm hover:border-[var(--border-strong)] transition-all flex flex-col gap-4">
            <div className="w-12 h-12 rounded-xl bg-[var(--color-status-covered-bg)] text-[var(--color-status-covered)] flex items-center justify-center">
              <BookOpen className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-[var(--text-main)]">
              1. Ingest Course Curriculum
            </h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Upload your current course outlines and syllabus materials. Gapwright maps taught competencies and learning outcomes across your academic programs.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-sm hover:border-[var(--border-strong)] transition-all flex flex-col gap-4">
            <div className="w-12 h-12 rounded-xl bg-[var(--color-status-warning-bg)] text-[var(--color-brand-yellow)] flex items-center justify-center">
              <BarChart3 className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-[var(--text-main)]">
              2. Capture Industry Demand
            </h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Continuously aggregate current hiring trends and employer requirements across target industries, reflecting what leading organizations are actively looking for.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-sm hover:border-[var(--border-strong)] transition-all flex flex-col gap-4">
            <div className="w-12 h-12 rounded-xl bg-[var(--color-brand-pink)] text-[var(--color-brand-navy)] flex items-center justify-center">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-[var(--text-main)]">
              3. Actionable Gap Intelligence
            </h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Identify high-impact emerging skills to introduce and outdated topics to phase out, giving academic leaders clear data to modernize degree offerings.
            </p>
          </div>
        </div>
      </section>

      {/* Feature Highlight / Workflow Preview */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="rounded-2xl md:rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] p-8 sm:p-10 shadow-sm flex flex-col md:flex-row items-center gap-8 justify-between">
          <div className="flex flex-col gap-4 max-w-xl">
            <span className="text-xs uppercase tracking-wider font-semibold text-[var(--color-brand-yellow)]">
              Institutions &amp; Curriculum Designers
            </span>
            <h3 className="text-2xl sm:text-3xl font-bold text-[var(--text-main)]">
              Make Curriculum Reviews Data-Driven
            </h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Replace subjective curriculum debates with empirical job posting demand data. Export accredited gap reports and provide advisory committees with clear, data-backed recommendations.
            </p>
            <ul className="flex flex-col gap-2 pt-2 text-sm text-[var(--text-main)]">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[var(--color-status-covered)]" />
                <span>30-day velocity trends on emerging technical competencies</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[var(--color-status-covered)]" />
                <span>Zero-demand legacy topic detection to recover course credits</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[var(--color-status-covered)]" />
                <span>Full source attribution compliant with all search provider guidelines</span>
              </li>
            </ul>
          </div>

          <div className="flex flex-col gap-3 w-full md:w-auto">
            <Link
              href="/syllabi"
              className="px-6 py-3 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-sm hover:opacity-90 transition text-center shadow-sm"
            >
              Start Analysis Now
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
