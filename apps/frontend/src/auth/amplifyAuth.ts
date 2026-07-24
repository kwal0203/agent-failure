import { Amplify } from "aws-amplify";
import {
  confirmResetPassword,
  confirmSignUp,
  fetchAuthSession,
  getCurrentUser,
  resetPassword,
  signIn,
  signOut,
  signUp,
} from "aws-amplify/auth";
import { cognitoUserPoolsTokenProvider } from "aws-amplify/auth/cognito";
import { sessionStorage } from "aws-amplify/utils";
import { readFrontendConfig } from "../config";

let configuredResourceKey: string | null = null;

function getCognitoConfiguration(): {
  userPoolId: string;
  userPoolClientId: string;
} {
  const config = readFrontendConfig();
  const userPoolClientId = config.cognitoClientId ?? "";
  const userPoolId = config.cognitoUserPoolId ?? "";

  if (!userPoolClientId || !userPoolId) {
    throw new Error(
      "Cognito is not configured. Missing VITE_COGNITO_CLIENT_ID or VITE_COGNITO_USER_POOL_ID.",
    );
  }

  return { userPoolId, userPoolClientId };
}

export function configureAmplifyAuth(): void {
  const configuration = getCognitoConfiguration();
  const resourceKey = `${configuration.userPoolId}:${configuration.userPoolClientId}`;
  if (configuredResourceKey === resourceKey) {
    return;
  }

  Amplify.configure({
    Auth: {
      Cognito: configuration,
    },
  });
  cognitoUserPoolsTokenProvider.setKeyValueStorage(sessionStorage);
  configuredResourceKey = resourceKey;
}

export async function getAmplifySession() {
  configureAmplifyAuth();
  return fetchAuthSession();
}

export async function getAmplifyUser() {
  configureAmplifyAuth();
  return getCurrentUser();
}

export async function signInWithAmplify(username: string, password: string) {
  configureAmplifyAuth();
  return signIn({ username, password });
}

export async function signUpWithAmplify(username: string, password: string) {
  configureAmplifyAuth();
  return signUp({
    username,
    password,
    options: {
      userAttributes: {
        email: username,
      },
    },
  });
}

export async function confirmSignUpWithAmplify(
  username: string,
  confirmationCode: string,
) {
  configureAmplifyAuth();
  return confirmSignUp({ username, confirmationCode });
}

export async function requestPasswordResetWithAmplify(username: string) {
  configureAmplifyAuth();
  return resetPassword({ username });
}

export async function confirmPasswordResetWithAmplify(
  username: string,
  confirmationCode: string,
  newPassword: string,
) {
  configureAmplifyAuth();
  return confirmResetPassword({
    username,
    confirmationCode,
    newPassword,
  });
}

export async function signOutWithAmplify(): Promise<void> {
  configureAmplifyAuth();
  await signOut();
}
