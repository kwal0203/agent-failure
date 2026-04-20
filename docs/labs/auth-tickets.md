# Auth Implementation Tickets (Production-Grade, AWS-Oriented)

## Goal
Replace frontend-local auth scaffolding with managed, production-grade authentication using AWS Cognito (OIDC), backend JWT verification, and role-aware authorization.

## Scope Assumptions
- Medium-term hosting is AWS.
- Frontend uses hosted login flow (Authorization Code + PKCE).
- Control-plane remains authorization source-of-truth for session/lab access.

---

## Ticket 1: Introduce Auth Provider Abstraction in Control Plane
### Scope
- Create a provider-agnostic auth interface so Cognito integration does not leak into business logic.

### Deliverables
- `AuthClaims` domain type (subject, email, roles/scopes, issued/expiry).
- `TokenVerifierPort` (verify/decode JWT -> AuthClaims).
- Request-level `PrincipalContext` mapping from verified claims.
- Config-driven issuer/audience/JWKS URI wiring.

### Acceptance Criteria
- Existing endpoints can receive authenticated principal from middleware without Cognito-specific code in services.

---

## Ticket 2: Add Cognito JWT Verification Middleware
### Scope
- Validate bearer token from frontend against Cognito JWKS.

### Deliverables
- JWKS fetch + cache strategy.
- JWT signature + issuer + audience + expiry checks.
- Structured 401 errors for invalid/missing tokens.
- Basic auth observability logs (invalid token reason code, no token values).

### Acceptance Criteria
- Protected endpoint rejects invalid/expired token.
- Valid Cognito token produces authenticated principal.

---

## Ticket 3: Define Role/Permission Mapping
### Scope
- Map Cognito groups/claims to internal roles used by control-plane.

### Deliverables
- Claim-to-role mapper (`learner`, `admin`, future roles).
- Fallback behavior for missing role claim.
- Test matrix for role mapping behavior.

### Acceptance Criteria
- Authorization behavior unchanged for current role semantics.
- Role mapping is deterministic and test-covered.

---

## Ticket 4: Protect API Surface + Centralize Auth Requirement
### Scope
- Ensure all session/lab mutation/query endpoints use auth middleware consistently.

### Deliverables
- Route-level auth policy inventory.
- Guard all protected routes through shared dependency/middleware.
- Explicitly mark any public endpoints.

### Acceptance Criteria
- No protected endpoint is reachable without valid token.
- Auth policy is documented and test-validated.

---

## Ticket 5: Frontend - Replace Local Auth Scaffold with Cognito OIDC Flow
### Scope
- Remove localStorage user/account hacks.
- Integrate real hosted auth flow.

### Deliverables
- OIDC client integration (Cognito hosted UI, PKCE).
- Login/logout route flow updates.
- Callback handling route.
- Auth context backed by OIDC session state.

### Acceptance Criteria
- User can sign in/out via Cognito hosted flow.
- Page refresh preserves authenticated state through OIDC session.
- Local auth scaffold removed.

---

## Ticket 6: Frontend API Client Auth Wiring
### Scope
- Ensure frontend API calls attach access token correctly.

### Deliverables
- Shared authenticated fetch wrapper.
- Attach bearer token from OIDC session.
- Graceful 401 handling (session expired -> prompt relogin).

### Acceptance Criteria
- Labs/session endpoints work when authenticated.
- Expired sessions fail cleanly and redirect to login path.

---

## Ticket 7: Backend User Profile Linking (Optional but Recommended)
### Scope
- Persist minimal local user profile linked to external identity (`sub`).

### Deliverables
- `users` table (external_subject unique, email, display_name, created_at).
- Upsert-on-first-seen flow from verified claims.
- Principal enriched with local user ID.

### Acceptance Criteria
- Backend can reference stable local user identity while auth remains externally managed.

---

## Ticket 8: Infrastructure - Cognito Setup and Environment Configuration
### Scope
- Provision and configure Cognito resources for staging.

### Deliverables
- User Pool, App Client, domain/hosted UI config.
- Callback/logout URLs for frontend envs.
- Environment variables in frontend/control-plane deployments.
- Secret/config management in AWS (SSM/Secrets Manager as appropriate).

### Acceptance Criteria
- Staging environment can complete end-to-end login and authenticated API access.

---

## Ticket 9: Security Hardening
### Scope
- Add baseline auth security controls.

### Deliverables
- CORS allowlist tightened to known frontend origins.
- Optional rate limiting on sensitive endpoints.
- Secure logging rules (no token leakage).
- Token validation failure telemetry.

### Acceptance Criteria
- Security checklist passes for staging review.
- No sensitive auth artifacts appear in logs.

---

## Ticket 10: Tests + Migration Cleanup
### Scope
- Ensure robust coverage and remove temporary auth artifacts.

### Deliverables
- Backend tests: token verification, role mapping, protected route behavior.
- Frontend tests: guarded routes, callback handling, logout flow.
- Delete local demo auth storage keys and related fallback code.
- Update docs/runbooks for local/staging auth setup.

### Acceptance Criteria
- Auth test suite passes.
- No legacy local auth path remains.

---

## Suggested Execution Order
1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4
5. Ticket 8
6. Ticket 5
7. Ticket 6
8. Ticket 7
9. Ticket 9
10. Ticket 10

## Notes
- Keep auth provider integration isolated behind interfaces so migration to Auth0/Entra later is low-friction.
- Avoid baking Cognito claim names deep into application services; do mapping at auth boundary.
