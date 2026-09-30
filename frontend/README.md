# Gapwright Web (`gapwright-web`)

The Next.js web application for **Gapwright**, the Automated Syllabus-to-Industry Gap Analyzer.

## Overview
- Built with Next.js (App Router), TypeScript, and Tailwind CSS.
- Color palette configured through CSS tokens based on institutional branding tokens.
- Light and dark theme support with automatic system preference detection and manual toggle.
- Typed API client with automatic token attachment and backend health status monitoring.

## Getting Started

### Prerequisites
- Node.js 20+
- npm 10+
- Running Gapwright backend API (defaults to `http://localhost:8000`)

### Environment Setup
Copy the example environment configuration:
```bash
cp .env.example .env.local
```

### Development
```bash
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the application.

### Quality Checks
```bash
npm run lint
npm run build
```
