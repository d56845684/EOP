# TODOS

## Launch Blockers (fix before first customer deployment)

### Booking Race Condition
**What:** Wrap booking creation in a database transaction with `SELECT ... FOR UPDATE` row locking.
**Why:** Two concurrent booking requests for the same teacher/time slot both pass the overlap check and both insert. Double-bookings are a matter of time, not probability.
**Context:** `bookings.py` create_booking() does ~10 sequential queries then INSERT, all outside a transaction. The `generate_booking_no()` function has the same race (two simultaneous requests on the same day generate the same booking number). Only `page_permissions.py` uses transactions in the entire codebase. Fix by acquiring a connection, BEGIN, SELECT FOR UPDATE on teacher_slots, then validate + insert within the same transaction.
**Depends on:** Nothing. This is the highest priority fix.

### Global Exception Handler (API Error Leakage)
**What:** Add a FastAPI exception handler that logs internal errors but returns generic messages to clients.
**Why:** 258 endpoints send `str(e)` to the frontend. Database errors could expose table names, column names, or query fragments to users.
**Context:** Every route handler repeats `except Exception as e: raise HTTPException(500, detail=f"操作失敗: {str(e)}")`. Replace with a global handler in `main.py` that logs the full error internally and returns a sanitized message.
**Depends on:** Nothing.

### Frontend Error Boundary
**What:** Add a React error boundary wrapping page content in DashboardLayout.
**Why:** Any component crash (bad API data, null reference) causes a white screen with no recovery path. The school owner sees a blank page.
**Context:** Zero error boundaries exist. Add a class component in `frontend-dennis/src/components/ErrorBoundary.tsx` that catches render errors and shows "Something went wrong, try refreshing."
**Depends on:** Nothing.

### N+1 Query Fix + Pagination Optimization
**What:** Fix N+1 enrichment in `leave_records.py` (4 queries per record) and replace `len(all_records)` pagination pattern with `SELECT COUNT(*)` across list endpoints.
**Why:** Leave records page: 20 records = 80+ queries. List endpoints fetch all records just to count them. Both cause noticeable delays.
**Context:** `leave_records.py:44-82` enrich function makes 4 sequential queries per record. `teachers.py:37-40`, `students.py:448`, `zoom.py:310-325` all fetch full result sets for count. Fix enrichment with JOIN query, replace count with `SELECT COUNT(*) FROM ... WHERE ...`.
**Depends on:** Nothing.

### Booking Integration Tests
**What:** Write 3-5 live integration tests for the booking flow (create, status transition, delete with Zoom cascade).
**Why:** Bookings is the core product (2,579 LOC, biggest module) with zero automated tests. Any code change risks breaking booking creation with no safety net.
**Context:** Match existing `live_*.py` test patterns. Test: create booking happy path, double-booking prevention (after race condition fix), delete with Zoom meeting cancellation, leave request submission.
**Depends on:** Booking race condition fix (test the transaction-safe version).

### Ops/Infra Hardening
**What:** Five quick fixes: (1) `restart: unless-stopped` for backend + frontend-demo, (2) `DEBUG=false` for production, (3) daily `pg_dump` cron, (4) disable pgAdmin or add auth, (5) `--requirepass` for Redis.
**Why:** Without restart policy, a crashed backend stays dead. Without backups, one bad migration loses all data. Without Redis auth, anyone on the network can flush sessions. Without pgAdmin auth, full DB access is open.
**Context:** docker-compose.yml already has restart policy for db/redis/nginx but NOT for backend/frontend-demo. Redis is exposed on port 6379 with no password. pgAdmin uses default credentials (admin@local.dev / admin) with password disabled. DEBUG defaults to true, exposing Swagger docs.
**Depends on:** Nothing.

## Post-Launch

### Bookings Page Refactoring
**What:** Split `bookings/page.tsx` (3,127 lines, 75+ useState) into sub-components: BookingTable, BookingFilters, CreateBookingModal, EditBookingModal, LeaveRequestModal, BatchOperations.
**Why:** Any change to the bookings page risks breaking unrelated functionality. 3,127 lines in one component is unmaintainable.
**Context:** Current page handles CRUD, 4+ modal states, filtering, pagination, batch operations, Zoom meeting management all inline. Extract each concern into its own component with clear props interfaces.
**Depends on:** Should be done before adding new booking features.

### TLS/HTTPS for Production
**What:** Configure Let's Encrypt SSL certificates + Nginx HTTPS config.
**Why:** Auth cookies sent in cleartext without HTTPS. LINE OAuth requires HTTPS redirect URIs in production. COOKIE_SECURE should be true in production.
**Context:** Nginx currently serves HTTP on port 80 only. Need certbot or similar for auto-renewing certs. Update nginx/default.conf with SSL termination. Set COOKIE_SECURE=true, COOKIE_SAMESITE=strict in production .env.
**Depends on:** Domain name + DNS configured.

### CSRF Protection
**What:** Add CSRF tokens for state-changing operations (POST/PUT/DELETE).
**Why:** Cookie-based auth without CSRF tokens allows cross-site request forgery attacks. Currently mitigated by SameSite=Lax but not bulletproof.
**Context:** Implement double-submit cookie pattern or synchronizer token pattern. Add CSRF middleware to FastAPI. Add token to frontend API client.
**Depends on:** Not urgent for single-school deployment. Add when scaling to multiple schools or handling payments.
