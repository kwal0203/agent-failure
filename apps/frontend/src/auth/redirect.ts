export const POST_LOGIN_REDIRECT_KEY = "agent_failure_post_login_redirect";

export function resolveSafeNext(rawNext: string | null): string {
  if (!rawNext) return "/labs";
  if (!rawNext.startsWith("/")) return "/labs";
  if (rawNext.startsWith("//")) return "/labs";
  return rawNext;
}
