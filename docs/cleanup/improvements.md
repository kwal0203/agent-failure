1. Refactor archive/runtimes/baseline/service.py (High Impact)
  The RuntimeTurnExecutor class in this file is currently a 2,400+ line "God Object" that contains hardcoded logic for multiple different security labs (LAB1, LAB2, LAB3).
   * Decouple Lab Logic: Implement a LabStrategy pattern where each lab's specific behaviors (seeding artifacts, security event detection, and tool interaction) are moved into dedicated
     classes.
   * Modularize the Service: Break the file into focused modules:
       * tools/: Tool catalog rendering and formatting.
       * inbox/: Email rendering and vendor update parsing.
       * events/: Security violation detection (e.g., token disclosure).
       * labs/: Lab-specific handlers.

  2. Standardize Architecture & Consistency (Medium Impact)
  While the control_plane follows a clean DDD-inspired structure, other services like agent_harness and runtimes are less consistent.
   * Adopt the Domain Layer: Introduce an explicit domain layer in all services to centralize business rules (e.g., "what constitutes a malicious email read") away from application
     orchestration.
   * Consistent Layout: Ensure all services strictly follow the interfaces/application/domain/infrastructure pattern established in the control_plane.

  3. Modernize Dependency Management (Medium Impact)
  The project currently uses a single root pyproject.toml for a multi-service monorepo, leading to inconsistent dependency handling in Dockerfiles.
   * Transition to uv Workspaces: Use uv workspaces to allow each service to have its own pyproject.toml while maintaining a unified root uv.lock.
   * Standardize Dockerfiles: Update all Dockerfiles to use uv sync --frozen, ensuring that production builds exactly match the development environment and are consistent across services.

  4. Enhance Testing Infrastructure (Medium Impact)
  The tests for the baseline runtime are comprehensive but contain a significant amount of boilerplate and duplicated mock classes.
   * Shared Testing Utilities: Extract common mock and stub classes (like _InboxTool, _FileTool) into a shared testing package or conftest.py to simplify test maintenance.
   * Integration Testing: Strengthen existing smoke scripts into a robust integration suite that validates the full Control Plane / Runtime interaction in a containerized environment.

  5. Improve Onboarding Documentation (Low Effort, High Value)
  The root of the repository lacks a README.md, which makes it difficult for new developers to understand the project's purpose and setup.
   * Populate Root README: Add a high-level project overview, architectural summary (linking to the TDD), and a quick-start guide for local development.
