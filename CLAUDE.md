# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Teaching/Education Management Platform - a full-stack monorepo with Next.js frontend, FastAPI backend, Supabase (PostgreSQL), Redis caching, and LINE platform integration (OAuth + messaging).

## Development Commands

### Docker Compose (Full Stack)
```bash
docker compose up              # Start all services
docker compose down            # Stop all services
docker compose down -v         # Stop and remove volumes
./pull_build_run.sh           # Quick script: pull + build frontend + start
```

### IMPORTANT: Backend 修改後測試流程
修改 backend 程式碼後，必須重新 build 並啟動才能測試：
```bash
docker compose up --build backend -d   # 重新 build 並啟動 backend
# 或
docker compose down && docker compose up --build -d  # 完整重建所有服務
```

### Frontend (in /frontend)
```bash
npm run dev           # Development server
npm run build         # Production build
npm run lint          # ESLint
npm run type-check    # TypeScript check
```

### Backend (in /backend)
```bash
# Local Python dev
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Run tests
pytest
pytest tests/test_auth.py -v              # Single test file
pytest tests/test_auth.py::test_name -v   # Single test
```

### Service URLs (when running via Docker)
- Frontend: http://localhost:4173
- Backend API: http://localhost:8001
- Backend Swagger: http://localhost:8001/docs
- Supabase Studio: http://localhost:3000
- Kong Gateway: http://localhost:8000

## Architecture

### Service Structure
- **frontend/** - Next.js 14 with App Router, TypeScript, Tailwind, Zustand state management
- **backend/** - FastAPI with dependency injection pattern, services layer, JWT auth via HttpOnly cookies
- **supabase/migrations/** - PostgreSQL schema and RLS policies
- **volumes/** - Docker persistent data (db, storage, logs, etc.)

### Backend Organization
```
backend/app/
├── api/v1/          # Route handlers (auth, users, courses, line_*)
├── services/        # Business logic (supabase_service, auth_service, line_*_service, redis_service)
├── middleware/      # Auth middleware, rate limiting
├── core/            # Security (JWT), dependencies (DI), exceptions
├── models/          # Database models
└── schemas/         # Pydantic request/response schemas
```

### Frontend Organization
```
frontend/src/
├── app/             # Next.js App Router pages (auth/, courses/, login/, profile/)
├── components/      # React components (DashboardLayout, Sidebar)
└── lib/
    ├── supabase/    # Supabase client configuration
    ├── api/         # API client functions (students, courses, contracts)
    └── hooks/       # Custom hooks (useAuth, useLine, useTeachers, useStudents, useRealtime)
```

### Key Patterns
1. **Cookie-Based Auth** - JWT in HttpOnly cookies, sessions backed by Redis
2. **RLS-First Security** - All data access enforced via PostgreSQL Row-Level Security
3. **Service Layer** - Backend business logic in `/backend/app/services/`
4. **LINE Multi-Channel** - Separate messaging channels for students, teachers, employees

### Database
- Schema defined in `supabase/migrations/001_complete_schema.sql`
- RLS policies in `supabase/migrations/002_rls_and_security.sql`
- Key tables: users_profile, courses, bookings, contracts, line_bindings

### Environment Variables
Backend config in `backend/app/config.py`. Key variables:
- Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- Redis: `REDIS_URL`, `REDIS_PASSWORD`
- LINE: `LINE_LOGIN_CHANNEL_*`, `LINE_*_MESSAGING_TOKEN` (student/teacher/employee)
- App: `SECRET_KEY`, `APP_ENV`, `FRONTEND_URL`, `COOKIE_DOMAIN`

## Test Accounts

測試用帳號 (詳見 `backend/tests/secret.md`)：

| 角色 | Email | Password |
|------|-------|----------|
| Student | `test_auth_student_20260128_225617_432708@example.com` | `TestPassword123!` |
| Teacher | `test_auth_teacher_20260128_225618_410286@example.com` | `TestPassword123!` |
| Employee | `test_auth_employee_20260128_225619_347997@example.com` | `TestPassword123!` |

**注意**: Employee 角色可執行 CRUD 操作 (建立/更新/刪除)，Student/Teacher 只有讀取權限。
