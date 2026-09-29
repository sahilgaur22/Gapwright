# Gapwright

*Automated Syllabus-to-Industry Gap Analyzer*

> "Build the fix for the gap between syllabus and skills."

We don't tell students which jobs to apply for. We tell universities which topics to teach, keep, or drop, using live job-market data.

## Overview

Gapwright ingests university course syllabi and real-time industry job postings, extracts and normalizes discrete skill requirements using LLMs, compares both using semantic skill matching, and computes concrete curriculum gap metrics with targeted recommendations.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Database:** PostgreSQL + pgvector
- **Job Market Ingestion:** Adzuna, Jooble, Remotive, RemoteOK, WWR
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Deployment:** Render (API), Vercel (Web), Neon / Supabase (Database)

## Getting Started

See [`.env.example`](.env.example) for initial configuration. Further setup instructions will follow as services are scaffolded.
