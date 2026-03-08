# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Teaching/Education Management Platform — full-stack monorepo with Next.js frontend, FastAPI backend, PostgreSQL (direct asyncpg), Redis caching, and LINE platform integration (OAuth + messaging).

## Development Commands

### Docker Compose (Full Stack)
```bash
docker compose up              # Start all services
docker compose up -d           # Start in background
docker compose down            # Stop all services
docker compose down -v         # Stop and remove volumes
./pull_build_run.sh           # Quick script: git pull + build frontend + start
```

### IMPORTANT: Backend 修改後測試流程
修改 backend 程式碼後，必須重新 build 並啟動才能測試：
```bash
docker compose up --build backend -d   # 重新 build 並啟動 backend
# 或
docker compose down && docker compose up --build -d  # 完整重建所有服務
```

### Frontend 修改注意
前端修改只能在 `frontend-dennis/` 目錄下進行，絕對不可以動到 `frontend/` 目錄。
```bash
docker compose up --build frontend-demo -d  # 重新 build 並啟動 Next.js frontend
```

### Backend (in /backend)
```bash
# Run tests (unit tests with mocks)
pytest
pytest tests/test_auth.py -v              # Single test file
pytest tests/test_auth.py::test_name -v   # Single test

# Live tests (against running backend)
python tests/live_booking_test.py --email employee@eop-test.com --password TestPassword123!
```

### Service URLs (when running via Docker)
- **Frontend (Next.js):** http://localhost:4173
- **Backend API:** http://localhost:8001
- **Backend Swagger:** http://localhost:8001/docs
- **pgAdmin:** http://localhost:5050 (admin@local.dev / admin)
- **Nginx Proxy:** http://localhost:80
- **PostgreSQL:** localhost:5432 (host port)
- **Redis:** localhost:6379 (host port)

## Architecture

### Docker Services

| Service | Container | Host Port → Container Port |
|---------|-----------|---------------------------|
| backend | teaching-platform-backend | 8001 → 8000 |
| frontend-demo | teaching-platform-frontend-demo | 4173 → 3000 |
| frontend | teaching-platform-frontend | (nginx only) → 5173 |
| db | teaching-platform-db | 5432 → 5432 |
| redis | teaching-platform-redis | 6379 → 6379 |
| migrations | teaching-platform-migrations | (no port) |
| pgadmin | teaching-platform-pgadmin | 5050 → 80 |
| nginx | teaching-platform-nginx | 80 → 80 |

### Service Structure
- **frontend-dennis/** - Next.js 14 with App Router, TypeScript, Tailwind, Zustand (production frontend, port 4173)
- **frontend/** - Vue 3 + Vite + Element Plus (dev frontend via nginx, **不要修改**)
- **backend/** - FastAPI + asyncpg + Redis, JWT auth via HttpOnly cookies
- **supabase/migrations/** - PostgreSQL schema (28 migration files)
- **scripts/** - Migration runner, AWS setup scripts

### Backend Organization
```
backend/app/
├── api/v1/          # Route handlers (auth, users, courses, bookings, line_*, zoom, etc.)
├── services/        # Business logic (supabase_service, auth_service, redis_service, line_*_service, zoom_service, storage_service)
├── middleware/      # Auth middleware, rate limiting, logging
├── core/            # Security (JWT), dependencies (DI), exceptions
├── models/          # Database models
└── schemas/         # Pydantic request/response schemas
```

### Frontend Organization (frontend-dennis/)
```
frontend-dennis/src/
├── app/             # Next.js App Router pages
├── components/      # React components (DashboardLayout, Sidebar)
└── lib/
    ├── api/         # API client functions (students, courses, contracts)
    └── hooks/       # Custom hooks (useAuth, useLine, useTeachers, useStudents)
```

### Key Patterns
1. **Cookie-Based Auth** - JWT in HttpOnly cookies, sessions backed by Redis
2. **Direct asyncpg** - Backend connects directly to PostgreSQL via asyncpg (NOT Supabase SDK)
3. **Entity ID Authorization** - Permission checks via entity_id (employee/teacher/student) + page_permissions table
4. **Service Layer** - Business logic in `/backend/app/services/`
5. **LINE Multi-Channel** - Separate messaging channels for students, teachers, employees
6. **Zoom Integration** - OAuth-based Zoom meeting management

### Database
- PostgreSQL 15 (Alpine), direct asyncpg connection (no Supabase SDK)
- Schema: `supabase/migrations/001_complete_schema.sql` (3197+ lines)
- 28 migration files, tracked in `_migrations` table
- Key tables: `users`, `user_profiles`, `employees`, `teachers`, `students`, `courses`, `bookings`, `student_contracts`, `teacher_contracts`, `teacher_bonus_records`, `line_bindings`, `roles`, `page_permissions`
- View: `bookings_view` (adds `is_trial_to_formal` computed field)
- Extensions: `uuid-ossp`, `btree_gist`

### Database Access for Tests
Backend container 的 DB 連線是 `db:5432`。從 host 連線測試 DB：
```bash
# 透過 docker exec (推薦)
docker exec teaching-platform-db psql -U postgres -c "SELECT ..."

# 或 host port (注意：確認 5432 沒有被其他 PostgreSQL 佔用)
psql postgresql://postgres:${POSTGRES_PASSWORD}@127.0.0.1:5432/postgres
```

### Environment Variables
所有環境變數定義在根目錄 `.env`，由 `docker-compose.yml` 注入。Backend config 在 `backend/app/config.py`。

Key variables:
- DB: `DATABASE_URL` (auto-composed from `POSTGRES_PASSWORD`, `POSTGRES_DB`)
- Redis: `REDIS_URL`, `REDIS_PASSWORD`
- Auth: `SECRET_KEY`, `COOKIE_DOMAIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE`
- LINE: `LINE_LOGIN_CHANNEL_ID`, `LINE_LOGIN_CHANNEL_SECRET`, `LINE_*_MESSAGING_TOKEN`
- Zoom: `ZOOM_OAUTH_CLIENT_ID`, `ZOOM_OAUTH_CLIENT_SECRET`, `ZOOM_ENABLED`
- AWS S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`
- App: `APP_ENV`, `FRONTEND_URL`, `SERVICE_API_KEY`

## Test Accounts

測試用帳號 (詳見 `backend/tests/secret.md`)：

| 角色 | Email | Password | Entity ID |
|------|-------|----------|-----------|
| Admin | `eopAdmin@example.com` | (pre-created) | SUPER-ADMIN |
| Employee | `employee@eop-test.com` | `TestPassword123!` | E001 |
| Teacher | `teacher@eop-test.com` | `TestPassword123!` | T001 |
| Student | `student@eop-test.com` | `TestPassword123!` | S001 |

**注意**: Employee 角色可執行 CRUD 操作 (建立/更新/刪除)，Student/Teacher 只有讀取權限。
