let currentAccessToken = "";

export function setCurrentAccessToken(token: string): void {
  currentAccessToken = token;
}

export function getCurrentAccessToken(): string {
  return currentAccessToken;
}

export function getCurrentAuthHeader(): string {
  if (!currentAccessToken) {
    throw new Error("No active access token. User must be authenticated.");
  }
  return `Bearer ${currentAccessToken}`;
}
