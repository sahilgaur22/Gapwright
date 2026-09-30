# API Reference: Gapwright

*FastAPI REST Application Programming Interface for Gapwright.*

Base path for all API v1 endpoints: `/api/v1`

---

## 1. System Health

### `GET /healthz`
Returns system health status and database connectivity check.

- **Authentication**: None
- **Response** (`200 OK`):
  ```json
  {
    "status": "ok",
    "environment": "production",
    "database": "connected"
  }
  ```
- **Error Response** (`503 Service Unavailable`):
  ```json
  {
    "status": "error",
    "environment": "production",
    "database": "unreachable"
  }
  ```

---

## 2. Authentication

### `POST /api/v1/auth/register`
Registers a new user account with argon2 password hashing.

- **Authentication**: None
- **Request Body**:
  ```json
  {
    "email": "curriculum.lead@institution.edu",
    "password": "SecurePassword123!",
    "role": "educator",
    "institution_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```
- **Roles**: `admin`, `educator`, `student`, `policymaker`
- **Response** (`201 Created`):
  ```json
  {
    "id": "c1f7362a-8ef7-47be-b1e6-28e4695b2171",
    "email": "curriculum.lead@institution.edu",
    "role": "educator",
    "institution_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```

### `POST /api/v1/auth/login`
Authenticates user credentials and returns a signed JSON Web Token (JWT).

- **Authentication**: None
- **Request Body**:
  ```json
  {
    "email": "curriculum.lead@institution.edu",
    "password": "SecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "c1f7362a-8ef7-47be-b1e6-28e4695b2171",
      "email": "curriculum.lead@institution.edu",
      "role": "educator",
      "institution_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  }
  ```

### `GET /api/v1/auth/me`
Retrieves currently authenticated user profile.

- **Authentication**: Bearer Token (`Authorization: Bearer <token>`)
- **Response** (`200 OK`):
  ```json
  {
    "id": "c1f7362a-8ef7-47be-b1e6-28e4695b2171",
    "email": "curriculum.lead@institution.edu",
    "role": "educator",
    "institution_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```

---

## 3. Syllabi Management

### `POST /api/v1/syllabi`
Uploads a course syllabus document (`.pdf` or `.docx`, max 10 MB). Extraction is processed asynchronously.

- **Authentication**: Bearer Token (or optional unauthenticated demo fallback if enabled)
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: Binary document file (`.pdf` or `.docx`)
  - `title`: Course title (string)
  - `department`: Academic department (optional string)
- **Response** (`202 Accepted`):
  ```json
  {
    "id": "7b587da4-6dfb-4f90-85dc-f661d90f23cb",
    "title": "CS301: Machine Learning & Intelligent Systems",
    "department": "Computer Science & Engineering",
    "filename": "cs301_syllabus.pdf",
    "status": "processing",
    "created_at": "2026-09-30T10:00:00Z"
  }
  ```

### `GET /api/v1/syllabi`
Lists course syllabi associated with the caller's institution.

- **Authentication**: Bearer Token
- **Query Parameters**:
  - `limit`: Integer (default 50, max 100)
  - `offset`: Integer (default 0)
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": "7b587da4-6dfb-4f90-85dc-f661d90f23cb",
      "title": "CS301: Machine Learning & Intelligent Systems",
      "department": "Computer Science & Engineering",
      "status": "ready",
      "created_at": "2026-09-30T10:00:00Z"
    }
  ]
  ```

### `GET /api/v1/syllabi/{id}`
Retrieves metadata and processing state for a single syllabus.

- **Authentication**: Bearer Token
- **Response** (`200 OK`):
  ```json
  {
    "id": "7b587da4-6dfb-4f90-85dc-f661d90f23cb",
    "title": "CS301: Machine Learning & Intelligent Systems",
    "department": "Computer Science & Engineering",
    "filename": "cs301_syllabus.pdf",
    "status": "ready",
    "raw_text_length": 18450,
    "created_at": "2026-09-30T10:00:00Z"
  }
  ```

### `GET /api/v1/syllabi/{id}/skills`
Retrieves normalized skills extracted from the syllabus, complete with supporting evidence snippets and confidence ratings.

- **Authentication**: Bearer Token
- **Response** (`200 OK`):
  ```json
  [
    {
      "skill_id": "a823b102-1249-43a9-959c-6a7f920272b1",
      "name": "Supervised Learning",
      "category": "Machine Learning",
      "evidence": "Module 2: Linear and Logistic Regression, Support Vector Machines",
      "confidence": 0.95
    },
    {
      "skill_id": "b934c213-2350-54b0-060d-7b80031383c2",
      "name": "Neural Networks",
      "category": "Deep Learning",
      "evidence": "Module 4: Feedforward networks, backpropagation algorithm",
      "confidence": 0.92
    }
  ]
  ```

---

## 4. Job Ingestion & Market Demand

### `POST /api/v1/jobs/crawl`
Triggers an automated job market ingestion crawl across registered sources.

- **Authentication**: `X-Crawl-Token: <token>` header OR Admin Bearer Token
- **Request Body**:
  ```json
  {
    "role": "Data Scientist",
    "location": "Bangalore"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "status": "completed",
    "role": "Data Scientist",
    "location": "Bangalore",
    "postings_collected": 28,
    "sources_queried": ["adzuna", "jooble", "remotive", "fixture"]
  }
  ```

### `GET /api/v1/jobs`
Searches stored job postings by role and location.

- **Query Parameters**:
  - `role`: Role keyword query (e.g. `Backend Developer`)
  - `location`: City or region (e.g. `Bangalore`)
  - `limit`: Integer (default 50)
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": "119e8312-3294-4d89-b82b-8a7c290123cb",
      "title": "Senior Data Scientist",
      "company": "Tech Corp",
      "location": "Bangalore",
      "source": "adzuna",
      "url": "https://www.adzuna.in/details/...",
      "description_is_truncated": true,
      "posted_at": "2026-09-29T14:30:00Z"
    }
  ]
  ```

### `GET /api/v1/jobs/skills/top`
Retrieves top in-demand skills for a given role query and location.

- **Query Parameters**:
  - `role`: Role query string
  - `location`: Location string (optional; omit or specify `Remote` for remote jobs)
  - `limit`: Top N skills (default 20)
- **Response** (`200 OK`):
  ```json
  [
    {
      "skill_id": "a823b102-1249-43a9-959c-6a7f920272b1",
      "name": "Python",
      "category": "Programming Languages",
      "postings_count": 42,
      "demand_pct": 0.84
    },
    {
      "skill_id": "c105e424-3461-65c1-171e-8c91142494d3",
      "name": "Docker",
      "category": "DevOps & Cloud",
      "postings_count": 31,
      "demand_pct": 0.62
    }
  ]
  ```

### `GET /api/v1/sources`
Returns statuses, priorities, remaining daily budgets, and attribution metadata for all job sources.

- **Authentication**: None
- **Response** (`200 OK`):
  ```json
  [
    {
      "source": "adzuna",
      "priority": 1,
      "enabled": true,
      "daily_budget": 30,
      "remaining_budget": 24,
      "attribution_text": "Powered by Adzuna",
      "attribution_url": "https://www.adzuna.com",
      "may_display_listing": true
    },
    {
      "source": "remotive",
      "priority": 2,
      "enabled": true,
      "daily_budget": 4,
      "remaining_budget": 3,
      "attribution_text": "Jobs from Remotive",
      "attribution_url": "https://remotive.com",
      "may_display_listing": false
    }
  ]
  ```

---

## 5. Curriculum Gap Analysis

### `POST /api/v1/analysis`
Executes an end-to-end curriculum gap evaluation comparing a syllabus against market demand for a target role and region.

- **Authentication**: Bearer Token
- **Request Body**:
  ```json
  {
    "syllabus_id": "7b587da4-6dfb-4f90-85dc-f661d90f23cb",
    "role_query": "Data Scientist",
    "location": "Bangalore"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "f519d084-3c67-427f-9ce0-48e02d6b38da",
    "syllabus_id": "7b587da4-6dfb-4f90-85dc-f661d90f23cb",
    "role_query": "Data Scientist",
    "location": "Bangalore",
    "gap_pct": 34.5,
    "coverage_pct": 65.5,
    "created_at": "2026-09-30T10:05:00Z"
  }
  ```

### `GET /api/v1/analysis/{id}`
Retrieves detailed breakdown of covered, missing, obsolete, and emerging skills.

- **Authentication**: Bearer Token
- **Response** (`200 OK`):
  ```json
  {
    "id": "f519d084-3c67-427f-9ce0-48e02d6b38da",
    "gap_pct": 34.5,
    "coverage_pct": 65.5,
    "role_query": "Data Scientist",
    "location": "Bangalore",
    "covered_skills": [
      {
        "name": "Python",
        "category": "Programming Languages",
        "demand_pct": 0.84,
        "evidence": "Lab exercises in Python"
      }
    ],
    "missing_skills": [
      {
        "name": "MLOps",
        "category": "Machine Learning Operations",
        "demand_pct": 0.58,
        "is_emerging": true
      }
    ],
    "obsolete_skills": [
      {
        "name": "Weka GUI",
        "category": "Data Mining Tools",
        "demand_pct": 0.00,
        "evidence": "Introduction to Weka data mining software"
      }
    ],
    "recommendations": [
      {
        "action": "add",
        "skill": "MLOps",
        "priority": "high",
        "reasoning": "High demand (58% of postings) and growing market presence."
      },
      {
        "action": "remove",
        "skill": "Weka GUI",
        "priority": "medium",
        "reasoning": "Less than 1% demand in live listings; replace with modern Python ML toolkits."
      }
    ]
  }
  ```

---

## 6. Reports & Policy Analytics

### `GET /api/v1/reports/{id}/export`
Exports a curriculum gap report in PDF or CSV format.

- **Authentication**: Bearer Token
- **Query Parameters**:
  - `format`: `pdf` or `csv` (default `pdf`)
- **Response**: Binary file stream with `Content-Disposition: attachment; filename="gap_report_{id}.[pdf|csv]"`.

### `GET /api/v1/policy/overview`
Retrieves aggregated curriculum gap metrics across all institutions, departments, and geographic markets.

- **Authentication**: Bearer Token (restricted to `policymaker` or `admin` roles)
- **Response** (`200 OK`):
  ```json
  {
    "total_institutions": 12,
    "total_syllabi_analyzed": 48,
    "average_gap_pct": 38.2,
    "most_frequent_missing_skills": [
      { "name": "Docker & Containerization", "occurrences": 39 },
      { "name": "CI/CD & DevOps", "occurrences": 34 }
    ],
    "top_lagging_departments": [
      { "department": "Information Technology", "average_gap_pct": 42.1 },
      { "department": "Computer Science", "average_gap_pct": 35.8 }
    ]
  }
  ```
