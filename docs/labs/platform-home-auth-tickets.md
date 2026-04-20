# Platform Home + Auth Flow Implementation Tickets

## Goal
Shift frontend from a labs-first entrypoint to a platform-style main page with authentication and protected app routes (LeetCode-like model).

## Ticket 1: Route Split + Auth Guard Scaffolding
### Scope
- Introduce public routes and protected routes.
- Add client auth state provider + guard components.

### Deliverables
- Public routes:
  - `/` (platform home)
  - `/login`
  - `/signup`
- Protected route group (requires auth):
  - `/app`
  - `/labs`
  - `/history`
  - `/trace`
  - `/sessions/:sessionId`
- Route guards:
  - unauthenticated => redirect to `/login?next=...`
  - authenticated access to `/login`/`/signup` => redirect to `/app`

### Acceptance Criteria
- Visiting `/labs` while signed out redirects to `/login`.
- Logging in redirects to `/app` (or `next`).
- Signed-in user cannot stay on `/login`.

## Ticket 2: Public Platform Home Page
### Scope
- Build `/` as a product front page, not catalog.

### Deliverables
- Hero with primary CTA (`Get Started`) and secondary CTA (`Browse Labs`).
- Platform explanation (how it works).
- Visual consistency with current app style.

### Acceptance Criteria
- `/` is fully usable without auth.
- CTA paths route correctly (`/signup`, `/login`, `/labs` guarded behavior).

## Ticket 3: Login UX (Real App Entry)
### Scope
- Implement login page flow with loading/error states.

### Deliverables
- Form: email/username + password.
- Submit action stores session auth state.
- Redirects to `next` query param when present.

### Acceptance Criteria
- Invalid input blocked client-side.
- Successful login updates global auth state and route transitions correctly.

## Ticket 4: Signup UX
### Scope
- Implement signup page with baseline validation.

### Deliverables
- Form + basic validation + success path to authenticated app.

### Acceptance Criteria
- New user can sign up and land in `/app`.

## Ticket 5: Authenticated App Home (`/app`)
### Scope
- Create dashboard-style app home.

### Deliverables
- Continue session card (if available).
- Recent sessions panel.
- Labs quick-launch panel.
- Progress summary panel.

### Acceptance Criteria
- `/app` gives clear “what to do next” flow.

## Ticket 6: Header/Auth Controls Integration
### Scope
- Connect app shell header to auth state.

### Deliverables
- Display current user identity from auth state.
- Add `Log out` action.
- Keep existing nav behavior intact.

### Acceptance Criteria
- Logout clears auth state and routes to `/`.

## Ticket 7: Session Bootstrap Auth Integration
### Scope
- Replace hardcoded auth header usage with auth-aware token source.

### Deliverables
- Shared auth token utility/context consumption in session/lab APIs.
- Remove duplicated hardcoded bearer values in page hooks/api modules.

### Acceptance Criteria
- Protected API calls include current user token consistently.

## Ticket 8: API Contract Wiring (Control Plane Auth)
### Scope
- Wire frontend auth flows to real backend auth endpoints.

### Deliverables
- `/auth/login`, `/auth/signup`, `/auth/me`, `/auth/logout` integration.
- Boot-time session restoration via `/auth/me`.

### Acceptance Criteria
- Refresh preserves authenticated state via backend contract.

## Ticket 9: Access + UX Hardening
### Scope
- Guard edge cases and polish transitions.

### Deliverables
- Loading gate during auth bootstrap.
- Friendly unauthorized/expired-session handling.
- Keyboard/a11y pass for auth forms.

### Acceptance Criteria
- No redirect loops.
- No protected content flash when signed out.

## Ticket 10: Tests + Cleanup
### Scope
- Add/adjust tests and remove obsolete routing assumptions.

### Deliverables
- Route guard tests.
- Login redirect tests.
- Public vs protected render tests.
- Remove dead labs-as-root assumptions.

### Acceptance Criteria
- App/frontend test suite passes with new route model.
