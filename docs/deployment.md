# Deployment Runbook: Gapwright

*Production Deployment, Infrastructure Setup, and Operations Guide.*

---

## 1. Architecture Topology

```
GitHub (main)
   │  push / PR
   ▼
GitHub Actions ── CI (ruff, mypy, pytest, eslint, tsc, vitest, next build)
   │  success on main
   ├─► deploy-backend:  alembic upgrade → Render deploy hook → health + smoke
   ├─► deploy-frontend: Vercel CLI build → prod deploy → smoke
   └─► crawl (cron 6h): warm API → POST /api/v1/jobs/crawl

Browser ──► Vercel (Next.js) ──► Render (FastAPI Docker) ──► Neon/Supabase (PostgreSQL + pgvector)
                                        └─► LLM Providers (Gemini / Groq) & Job APIs
```

---

## 2. One-Time Setup Guide

### 2.1 Database Provisioning (Neon or Supabase)
1. Create a cloud PostgreSQL project in the region closest to your users (e.g. Singapore / Asia-South).
2. Enable the `pgvector` extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   *(Note: The initial Alembic migration also executes this idempotently).*
3. Obtain two connection strings:
   - **Application Connection (Pooled)**: Configured in Render as `DATABASE_URL` using scheme `postgresql+asyncpg://`.
   - **Direct Migration Connection**: Configured in GitHub Secrets as `DATABASE_URL_MIGRATE` (direct port 5432 connection avoiding connection pooler transaction limitations).

### 2.2 Backend Service Provisioning (Render)
1. In the Render Dashboard, create a **New Blueprint Instance** and connect the repository. Render will automatically read [`render.yaml`](../render.yaml).
2. Configuration defaults:
   - **Runtime**: Docker (`dockerfilePath: ./backend/Dockerfile`, context `./backend`)
   - **Plan**: Free
   - **Health Check Path**: `/healthz`
   - **Auto-Deploy**: **Off** (Deploys are orchestrated strictly via CI).
3. Set secret environment variables in the Render Dashboard (never commit to git):
   - `DATABASE_URL` (pooled asyncpg connection string)
   - `JWT_SECRET` (generate using `openssl rand -hex 32`)
   - `LLM_PROVIDER` (`gemini` or `groq`)
   - `GEMINI_API_KEY` and/or `GROQ_API_KEY`
   - `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `JOOBLE_API_KEY`
   - `CRAWL_TRIGGER_TOKEN` (shared secret matching GitHub Actions)
   - `CORS_ORIGINS` (production Vercel URL, e.g., `https://gapwright.vercel.app`)
   - `ENV=production`
   - `ENABLE_PLAYWRIGHT=false`
4. Copy the **Deploy Hook** URL from Service Settings into GitHub secret `RENDER_DEPLOY_HOOK_URL`.
5. Note the service URL (e.g. `https://gapwright-api.onrender.com`) for `API_BASE_URL`.

### 2.3 Frontend Application Provisioning (Vercel)
1. Import the repository into Vercel with framework preset **Next.js**.
2. **Leave Root Directory empty** and let GitHub Actions drive prebuilt deployments from `frontend/` (prevents doubled-path issues).
3. Set project environment variable `NEXT_PUBLIC_API_URL` to the Render backend service URL.
4. Disable Vercel's automatic Git integration (enforced repository-wide in [`frontend/vercel.json`](../frontend/vercel.json)).
5. Generate a Vercel Access Token and retrieve the project details:
   - `VERCEL_TOKEN`: Vercel Account Settings -> Tokens.
   - `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`: Found in `.vercel/project.json` after running `vercel link` locally.

### 2.4 GitHub Repository Secrets & Environments
1. Navigate to **Settings -> Environments** and create an environment named `production`.
2. Configure repository and environment secrets:
   - `DATABASE_URL_MIGRATE`: Direct PostgreSQL connection string.
   - `RENDER_DEPLOY_HOOK_URL`: Render deploy webhook URL.
   - `API_BASE_URL`: Public Render API URL (e.g. `https://gapwright-api.onrender.com`).
   - `CRAWL_TRIGGER_TOKEN`: Secret token for crawl authentication.
   - `VERCEL_TOKEN`: Vercel personal access token.
   - `VERCEL_ORG_ID`: Vercel organization ID.
   - `VERCEL_PROJECT_ID`: Vercel project ID.
   - `FRONTEND_URL`: Public production frontend URL.

---

## 3. Operational Characteristics & Free-Tier Design

- **Cold Starts**: Render free services spin down containers after 15 minutes of inactivity and require approximately 50-70 seconds to boot on incoming traffic.
  - The Next.js client features an automatic cold-start banner (`"Connecting to API..."`).
  - The scheduled crawler workflow warms up `/healthz` with up to 20 retries before dispatching jobs.
- **Lightweight Runtime**: The backend container uses multi-stage builds and excludes browser drivers (`ENABLE_PLAYWRIGHT=false`), maintaining an image size < 300 MB and memory footprint under 250 MB.
- **Quota Protection**: All LLM queries and dense embeddings are cached and deduplicated by content hash. If a third-party job source exhausts its daily allocation, it automatically stops querying without failing the ingestion cycle.

---

## 4. Rollback and Incident Response

| Incident Scenario | Response Procedure |
|---|---|
| **Failed API Release** | In Render Dashboard, click **Rollback** to the last successful deployment. All database migrations are backward compatible. |
| **Failed Frontend Release** | In Vercel Dashboard, promote the previous deployment or execute `vercel rollback`. |
| **Source Quota Exhaustion** | In Render environment settings, set `ENABLED_SOURCES=fixture` and redeploy. Gapwright will continue serving Indian market gap analyses from offline fixture data. |
| **Secret Compromise** | Immediately rotate the affected key at the provider (Gemini, Groq, Neon, Adzuna), update the secret in Render and GitHub Secrets, and trigger a redeploy. |

---

## 5. Post-Deployment Verification Checklist

Verify the following items after every production deployment:
- [ ] `GET /healthz` responds with status `200 OK` and `"database": "connected"`.
- [ ] `GET /api/v1/sources` lists enabled providers, freshness timestamps, and remaining daily limits.
- [ ] Production web application loads without CORS errors in browser developer tools.
- [ ] Uploading a sample syllabus extracts skills and updates status to `ready`.
- [ ] Triggering manual `Scheduled Crawl` workflow runs without errors.
- [ ] Source attribution links in web footer render as standard follow links without `nofollow`.
- [ ] Curriculum gap dashboard correctly computes and displays add/remove recommendations.
