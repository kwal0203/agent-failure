import { describe, expect, it } from "vitest";
import { readFrontendConfig } from "./config";

describe("readFrontendConfig", () => {
  it("provides explicit local-development defaults", () => {
    expect(readFrontendConfig({})).toEqual({
      apiBaseUrl: "http://localhost:8000",
      cognitoClientId: null,
      cognitoUserPoolId: null,
      enrollmentApiEnabled: false,
      labCatalogSource: "stub",
      uiMode: "demo",
    });
  });

  it("normalizes typed environment values", () => {
    expect(
      readFrontendConfig({
        VITE_API_BASE_URL: "https://api.example.test/",
        VITE_COGNITO_CLIENT_ID: " client-id ",
        VITE_COGNITO_USER_POOL_ID: " pool-id ",
        VITE_ENROLLMENT_API_ENABLED: "true",
        VITE_LAB_CATALOG_SOURCE: "api",
        VITE_UI_MODE: "debug",
      }),
    ).toEqual({
      apiBaseUrl: "https://api.example.test",
      cognitoClientId: "client-id",
      cognitoUserPoolId: "pool-id",
      enrollmentApiEnabled: true,
      labCatalogSource: "api",
      uiMode: "debug",
    });
  });

  it("rejects invalid URLs and enum values", () => {
    expect(() =>
      readFrontendConfig({ VITE_API_BASE_URL: "not a URL" }),
    ).toThrow();
    expect(() =>
      readFrontendConfig({ VITE_LAB_CATALOG_SOURCE: "remote" }),
    ).toThrow();
  });
});
