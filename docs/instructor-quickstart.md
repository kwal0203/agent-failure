# Instructor Quickstart

This guide helps instructors run an Agent Failure pilot from first login to first class session.

## What You Just Received

After your pilot request is approved and provisioned, you should receive:

- A login URL
- A class code for student enrollment
- Confirmation that your instructor access was assigned

If any of these are missing, contact support and include your pilot request ID.

## First 10 Minutes

1. Sign in at the provided login URL.
2. Open the lab catalog (`/labs`).
3. Confirm available lab modules are visible.
4. Confirm your class code is active.
5. Run a quick learner-path check in a separate browser profile:
   - Sign up as a test learner with the class code.
   - Confirm enrollment succeeds and learner lands in the catalog.

## Student Onboarding

Tell students to:

1. Open the login page.
2. Select `Join with class code`.
3. Enter the class code you provide.
4. Complete account setup and email confirmation.
5. Sign in and verify access to assigned labs.

## Recommended Pilot Flow (Class Session)

1. Start with the pre-lab briefing.
2. Explain objective, target data, and success criteria.
3. Have students launch the lab workspace.
4. Ask students to capture required evidence artifacts.
5. Debrief outcomes and compare successful vs failed attempts.

## Troubleshooting

### Invalid Class Code

- Re-check code formatting/case.
- Confirm code is active and linked to the intended course.

### Enrollment Token Expired / Redeemed

- Ask learner to re-enter class code in enrollment flow.
- Clear site data/session if stale state persists.

### Role or Access Mismatch

- Instructor account appears as learner:
  - Verify Cognito `instructor` group assignment.
  - Re-run instructor provisioning for that email.

## Support and Escalation

When reporting issues, include:

- Pilot request ID
- Correlation ID (if shown in admin provisioning response)
- User email
- Timestamp (with timezone)
- Screenshot of the error

Send to your internal support channel or pilot operations contact.
