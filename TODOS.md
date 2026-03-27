# TODOS

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
