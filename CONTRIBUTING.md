# Contributing to Agent Failure

Thank you for helping improve Agent Failure. Bug reports, documentation fixes, tests, and focused code changes are welcome.

## Before you start

- Search existing issues and pull requests before opening a duplicate.
- Open an issue before undertaking a large feature or architectural change.
- Do not use a public issue to report a vulnerability. Follow [SECURITY.md](./SECURITY.md).
- Follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Development setup

You need Python 3.12 or later, Node.js 22.22 or later, `uv`, Docker, and npm.

```bash
docker compose up -d db
cp .env.example .env
uv sync --frozen --group dev
uv run alembic upgrade head
cd apps/frontend && npm ci
```

Use test credentials and local services only. Never commit API keys, tokens, production data, or other secrets.

## Quality checks

Run the checks relevant to your change. Before requesting review for a code change, the complete suite should pass:

```bash
uv run ruff check .
uv run mypy .
uv run pyright
uv run pytest -m "not integration"
uv run pytest -m "integration"
```

```bash
cd apps/frontend
npm run api:check
npm run biome:check
npm run typecheck
npm run lint
npm test
npm run build
```

The frontend REST client and response types are generated from FastAPI's
OpenAPI document. Run `npm run api:generate` after changing an HTTP route or
schema, and commit the resulting `src/api/generated.ts` update.

PostgreSQL must be available for integration tests. The root test configuration prevents database-backed tests from silently using a non-test database.

## Pull requests

- Keep each pull request focused on one problem.
- Explain the motivation and user-visible behavior, not only the implementation.
- Add or update tests for changed behavior.
- Update documentation and example configuration when interfaces change.
- Keep generated lockfiles in sync with dependency changes.
- Call out migrations, compatibility breaks, or security implications explicitly.

Maintainers may ask for changes or decline work that does not fit the project's scope.

## Contribution licensing

This project does not currently require a contributor license agreement. Under section 5 of the Apache License 2.0, intentionally submitted contributions are provided under the project's Apache-2.0 terms unless you explicitly state otherwise.

By submitting a contribution, you represent that you have the right to do so and that it does not knowingly include confidential, proprietary, or unlawfully copied material.
