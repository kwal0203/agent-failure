import { getAmplifySession } from "./amplifyAuth";

export async function getCurrentAccessToken(): Promise<string> {
  const session = await getAmplifySession();
  const accessToken = session.tokens?.accessToken?.toString();
  if (!accessToken) {
    throw new Error("No active access token. User must be authenticated.");
  }
  return accessToken;
}

export async function getCurrentAuthHeader(): Promise<string> {
  return `Bearer ${await getCurrentAccessToken()}`;
}
