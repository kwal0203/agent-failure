export const POST_LOGIN_REDIRECT_KEY = "agent_failure_post_login_redirect";

export function resolveSafeNext(rawNext: string | null): string {
  if (!rawNext) return "/app";
  if (!rawNext.startsWith("/")) return "/app";
  if (rawNext.startsWith("//")) return "/app";
  return rawNext;
}
