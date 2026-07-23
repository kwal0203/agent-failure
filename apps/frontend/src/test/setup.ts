import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.stubEnv("VITE_COGNITO_CLIENT_ID", "test-client-id");
vi.stubEnv("VITE_COGNITO_USER_POOL_ID", "us-east-2_testpool");
vi.stubEnv("VITE_ENROLLMENT_API_ENABLED", "false");

afterEach(() => {
  cleanup();
});
