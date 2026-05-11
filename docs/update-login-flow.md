# Updated Login + Enrollment Flow (Cognito + Backend Course Code)

## Goal
Use AWS Cognito for authentication (email/password) and backend APIs for course-code validation and enrollment, without coupling enrollment logic into Cognito.

## Current State (as implemented)
- Frontend signup collects: `classCode`, `email`, `password`.
- Frontend currently calls Cognito signup via `useAuth().signup(email, password)`.
- Frontend confirms email via `useAuth().confirmSignup(email, confirmationCode)`.
- Enrollment is not yet wired to backend.

## Proposed Architecture
- Cognito owns identity lifecycle:
  - create account
  - verify email
  - issue JWTs on login
- Backend owns academic domain logic:
  - class code validation
  - mapping users to courses
  - enrollment policy and audit

## Recommended Endpoints

### 1) Validate class code (pre-signup)
`POST /api/v1/enrollment/validate-class-code`

Request:
```json
{
  "classCode": "ABC123",
  "email": "student@example.edu"
}
```

Response (200):
```json
{
  "valid": true,
  "enrollmentToken": "eyJhbGciOi...",
  "expiresInSeconds": 600,
  "course": {
    "id": "course_01",
    "name": "CS 447 - AI Agent Security"
  }
}
```

Response (4xx):
```json
{
  "valid": false,
  "error": "Invalid or expired class code"
}
```

Notes:
- `enrollmentToken` should be backend-signed, short-lived, and one-time redeemable.
- Include claims such as: `courseId`, normalized `email`, `nonce`, `exp`.

### 2) Redeem enrollment token (post-login)
`POST /api/v1/enrollment/redeem`

Headers:
- `Authorization: Bearer <cognito access or id token>`

Request:
```json
{
  "enrollmentToken": "eyJhbGciOi..."
}
```

Response (200):
```json
{
  "enrolled": true,
  "course": {
    "id": "course_01",
    "name": "CS 447 - AI Agent Security"
  }
}
```

Response (4xx):
```json
{
  "enrolled": false,
  "error": "Token expired or already redeemed"
}
```

Backend checks:
- JWT is valid and trusted.
- `enrollmentToken` signature, expiry, and nonce are valid.
- Token not previously redeemed.
- Token email matches authenticated user email.
- Then write enrollment: `userSub -> courseId`.

## Frontend Flow (Detailed)

### Signup Page
1. User enters `classCode`, `email`, `password`.
2. Frontend calls `POST /enrollment/validate-class-code`.
3. If valid:
   - Store returned `enrollmentToken` in `sessionStorage` (or short-lived in-memory state).
   - Proceed with Cognito signup (`signup(email, password)`).
4. If invalid:
   - Show backend error and block signup.

### Confirmation Step
5. User enters confirmation code from email.
6. Frontend calls `confirmSignup(email, confirmationCode)`.
7. Redirect user to login page.

### First Login + Enrollment Redemption
8. User logs in via Cognito; frontend receives JWT-backed authenticated session.
9. If `enrollmentToken` exists in storage:
   - call `POST /enrollment/redeem` with auth header + token.
10. On success:
   - clear `enrollmentToken` from storage.
   - continue to labs/catalog.
11. On failure:
   - surface clear error (expired/used token) and offer:
     - re-enter class code
     - contact instructor

## Failure/Edge Cases to Handle
- User validates code but never completes signup: token expires naturally.
- User signs up/confirm on one device, logs in on another:
  - no local token available; provide "Enter class code" fallback after login.
- Email mismatch:
  - if code validated with one email and user logs in as another, backend must reject redeem.
- Replay attempts:
  - one-time token + nonce + redeemed flag.
- Duplicate enrollment:
  - make redeem idempotent (return success if already enrolled in same course).

## Security Requirements
- Enrollment token TTL: 5-15 minutes.
- Enrollment token must be signed by backend secret/private key.
- Store only minimal claims in token.
- Always re-check course status at redeem time (course still active, code still allowed).
- Audit log events:
  - class code validation attempts
  - redeem attempts (success/failure)

## Suggested Data Model (minimal)
- `class_codes`:
  - `code`, `course_id`, `expires_at`, `max_uses`, `uses`, `status`
- `enrollment_tokens`:
  - `jti/nonce`, `email`, `course_id`, `expires_at`, `redeemed_at`
- `enrollments`:
  - `user_sub`, `course_id`, `created_at`, `source` (class_code)

## API Contract Sketch for Current Frontend

### Frontend service functions
- `validateClassCode(classCode: string, email: string): Promise<{ enrollmentToken: string; courseName: string }>`
- `redeemEnrollmentToken(enrollmentToken: string): Promise<{ enrolled: boolean; courseId: string }>`

### Signup page state
- `classCode` (already added)
- `pendingEnrollmentToken` (new)
- `awaitingConfirmation` (already present)

Pseudo-flow:
```ts
async function onSignup() {
  const validation = await validateClassCode(classCode, email);
  sessionStorage.setItem("pending_enrollment_token", validation.enrollmentToken);
  await signup(email, password); // Cognito
  setAwaitingConfirmation(true);
}

async function onPostLogin() {
  const token = sessionStorage.getItem("pending_enrollment_token");
  if (!token) return;
  await redeemEnrollmentToken(token); // backend + bearer auth
  sessionStorage.removeItem("pending_enrollment_token");
}
```

## Where to Trigger Post-Login Redemption
Pick one:
1. Immediately after successful login in auth context/provider.
2. On app bootstrap when authenticated session is detected.
3. On catalog page mount before loading learner courses.

Recommendation: option 2 (app bootstrap) for centralization and consistency.

## Migration Plan
1. Add backend endpoints and token store.
2. Add frontend API client methods.
3. Wire signup page to call validate endpoint before Cognito signup.
4. Add post-login redeem hook.
5. Add UX states for expired/invalid tokens.
6. Add observability logs + metrics.

## Out of Scope for Phase 1
- Instructor self-serve class creation workflow.
- Multi-course selection during signup.
- SSO role provisioning.
