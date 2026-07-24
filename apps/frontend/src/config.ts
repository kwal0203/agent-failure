import { z } from "zod";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const frontendEnvironmentSchema = z
  .object({
    VITE_API_BASE_URL: z.string().trim().optional(),
    VITE_COGNITO_CLIENT_ID: z.string().trim().optional(),
    VITE_COGNITO_USER_POOL_ID: z.string().trim().optional(),
    VITE_ENROLLMENT_API_ENABLED: z
      .enum(["true", "false"])
      .optional()
      .default("false"),
    VITE_LAB_CATALOG_SOURCE: z
      .enum(["api", "empty", "stub"])
      .optional()
      .default("stub"),
    VITE_UI_MODE: z.enum(["demo", "debug"]).optional().default("demo"),
  })
  .superRefine((environment, context) => {
    if (
      environment.VITE_API_BASE_URL &&
      !URL.canParse(environment.VITE_API_BASE_URL)
    ) {
      context.addIssue({
        code: "custom",
        path: ["VITE_API_BASE_URL"],
        message: "must be an absolute URL",
      });
    }
  });

export type FrontendConfig = {
  apiBaseUrl: string;
  cognitoClientId: string | null;
  cognitoUserPoolId: string | null;
  enrollmentApiEnabled: boolean;
  labCatalogSource: "api" | "empty" | "stub";
  uiMode: "demo" | "debug";
};

export function readFrontendConfig(
  environment: Record<string, string | boolean | undefined> = import.meta.env,
): FrontendConfig {
  const parsed = frontendEnvironmentSchema.parse(environment);
  const apiBaseUrl =
    parsed.VITE_API_BASE_URL?.replace(/\/+$/, "") || DEFAULT_API_BASE_URL;

  return {
    apiBaseUrl,
    cognitoClientId: parsed.VITE_COGNITO_CLIENT_ID || null,
    cognitoUserPoolId: parsed.VITE_COGNITO_USER_POOL_ID || null,
    enrollmentApiEnabled: parsed.VITE_ENROLLMENT_API_ENABLED === "true",
    labCatalogSource: parsed.VITE_LAB_CATALOG_SOURCE,
    uiMode: parsed.VITE_UI_MODE,
  };
}

export function getApiBaseUrl(): string {
  return readFrontendConfig().apiBaseUrl;
}
