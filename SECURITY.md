# Security Policy

Agent Failure contains deliberately vulnerable lab scenarios. Please distinguish an intended, sandboxed lesson behavior from a vulnerability that escapes the lab boundary, affects the platform, exposes data or credentials, or compromises another user's environment.

## Supported versions

The project is currently maintained on the `main` branch and has no supported release series. Security fixes are made on `main`. After versioned releases begin, this section will list their support status.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue, discussion, pull request, or social-media post.

Use GitHub's private vulnerability reporting form:

https://github.com/kwal0203/agent-failure/security/advisories/new

Include:

- the affected component and revision;
- the impact and conditions required to reproduce it;
- minimal reproduction steps or a proof of concept;
- any known mitigations; and
- whether the issue is already public or under active exploitation.

Do not access other people's data, degrade shared services, use real credentials, or perform destructive testing.

The maintainer will make a best effort to acknowledge a complete report within seven days, keep the reporter informed during triage, and coordinate disclosure after a fix or mitigation is available. These are targets, not a guarantee of a fix within a particular period.

If private vulnerability reporting is unavailable, contact the maintainer through the contact information on the [@kwal0203 GitHub profile](https://github.com/kwal0203) without including sensitive details in a public message.

## Scope

Examples of in-scope security issues include:

- authentication or authorization bypasses;
- cross-tenant or unintended data access;
- command execution or sandbox escape;
- credential disclosure;
- unsafe defaults that expose a deployed instance; and
- dependency vulnerabilities with a demonstrated impact on this project.

The documented behavior of an intentionally vulnerable lab is not a platform vulnerability when it remains confined to its designated local or sandbox environment. Reports showing that a lab can cross that boundary are in scope.
