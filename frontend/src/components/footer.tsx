import React from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Building2,
  Clock,
  ExternalLink,
  Mail,
  Phone,
  ShieldCheck,
} from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-main)] transition-colors">
      {/* Top Govt Initiative Banner */}
      <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] py-3 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs text-[var(--text-secondary)]">
          <div className="flex items-center gap-2 font-medium">
            <ShieldCheck className="w-4 h-4 text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]" />
            <span>
              National Higher Education Curriculum &amp; Workforce Alignment Mission
            </span>
          </div>
          <div className="flex items-center gap-4 text-[var(--text-muted)]">
            <span>Govt. Education Standards Advisory Portal</span>
            <span className="hidden md:inline">•</span>
            <span className="hidden md:inline">Universal Institutional Access</span>
          </div>
        </div>
      </div>

      {/* Main Multi-Column Footer Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-10">
          {/* Column 1: Portal Overview */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-[var(--border-subtle)] bg-[var(--color-brand-pink)] flex items-center justify-center p-1">
                <Image
                  src="/growth.png"
                  alt="Gapwright Government Portal Emblem"
                  width={28}
                  height={28}
                  className="object-contain"
                />
              </div>
              <div className="flex flex-col">
                <span className="text-base font-bold tracking-tight text-[var(--text-main)]">
                  Gapwright
                </span>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--text-muted)] -mt-0.5">
                  Curriculum Intelligence Portal
                </span>
              </div>
            </div>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Established under the Higher Education Modernization Framework to evaluate academic curricula against verified workforce competencies and assist institutional boards with empirical syllabus updates.
            </p>
            <div className="text-[11px] text-[var(--text-secondary)] font-medium">
              A recognized initiative for university curriculum boards, technical councils, and accredited degree colleges.
            </div>
          </div>

          {/* Column 2: Governance & Institutional Portals */}
          <div className="flex flex-col gap-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">
              Institutions &amp; Boards
            </h4>
            <ul className="flex flex-col gap-2 text-xs text-[var(--text-muted)]">
              <li>
                <Link
                  href="/syllabi"
                  className="hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  Upload Course Syllabus
                </Link>
              </li>
              <li>
                <Link
                  href="/demand"
                  className="hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  National Industry Demand Tracker
                </Link>
              </li>
              <li>
                <Link
                  href="/analysis"
                  className="hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  Curriculum Gap Benchmarking
                </Link>
              </li>
              <li>
                <Link
                  href="/sources"
                  className="hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  Market Data Source Attribution
                </Link>
              </li>
              <li>
                <a
                  href="https://nad.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>National Academic Depository (NAD)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://swayam.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>SWAYAM Central Portal</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3: National Education Portals */}
          <div className="flex flex-col gap-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">
              National Education Portals
            </h4>
            <ul className="flex flex-col gap-2 text-xs text-[var(--text-muted)]">
              <li>
                <a
                  href="https://www.education.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>Ministry of Education (MoE)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.ugc.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>University Grants Commission (UGC)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.aicte-india.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>AICTE Official Portal</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://nsdcindia.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>National Skill Development (NSDC)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.nirfindia.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition"
                >
                  <span>NIRF India Rankings</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Column 4: Official Contact Information */}
          <div className="flex flex-col gap-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">
              Official Contact &amp; Helpdesk
            </h4>
            <div className="flex flex-col gap-2.5 text-xs text-[var(--text-muted)]">
              <div className="flex items-start gap-2">
                <Building2 className="w-4 h-4 text-[var(--color-brand-yellow)] shrink-0 mt-0.5" />
                <span>
                  Department of Higher Education, Central Secretariat, New Delhi – 110001
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-[var(--color-brand-yellow)] shrink-0" />
                <span>National Student Helpline: 1800-111-656 (Toll-Free)</span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-[var(--color-brand-yellow)] shrink-0" />
                <span>contact.moe@gov.in</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[var(--color-brand-yellow)] shrink-0" />
                <span>Mon – Fri: 09:30 AM to 05:30 PM IST</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Legal / Accreditation Bar */}
      <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] py-4 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-[var(--text-muted)] text-center sm:text-left">
          <div>
            © {new Date().getFullYear()} Gapwright — National Higher Education Curriculum Benchmarking Portal. All Rights Reserved.
          </div>
          <div className="flex items-center gap-4">
            <span>Designed for University Councils &amp; Academic Boards</span>
            <span>•</span>
            <Link
              href="/sources"
              className="text-[var(--text-secondary)] hover:underline"
            >
              Public Source Citations
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
