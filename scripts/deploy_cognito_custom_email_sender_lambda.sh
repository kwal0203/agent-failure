#!/usr/bin/env bash
set -euo pipefail

# Deploy/update a Cognito CustomEmailSender Lambda that relays mail through Resend.
# This script only manages Lambda packaging/deployment. Cognito trigger wiring is separate.
#
# Required env vars:
#   AWS_REGION
#   LAMBDA_FUNCTION_NAME
#   LAMBDA_ROLE_ARN
#   RESEND_API_KEY
#   MAIL_FROM                      (e.g. "Agent Failure <no-reply@auth.agentfailure.com>")
#   KMS_KEY_ARN                    (used to decrypt Cognito custom sender code)
#
# Optional env vars:
#   REPLY_TO                       (default: support@agentfailure.com)
#   LAMBDA_TIMEOUT                 (default: 15)
#   LAMBDA_MEMORY_MB               (default: 256)
#   PYTHON_BIN                     (default: python3)
#
# Example:
#   AWS_REGION=us-east-2 \
#   LAMBDA_FUNCTION_NAME=agentfailure-cognito-custom-email-sender \
#   LAMBDA_ROLE_ARN=arn:aws:iam::123456789012:role/lambda-exec-role \
#   RESEND_API_KEY=... \
#   MAIL_FROM='Agent Failure <no-reply@auth.agentfailure.com>' \
#   REPLY_TO='support@agentfailure.com' \
#   ./scripts/deploy_cognito_custom_email_sender_lambda.sh

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: Missing required env var: $name" >&2
    exit 1
  fi
}

require_var AWS_REGION
require_var LAMBDA_FUNCTION_NAME
require_var LAMBDA_ROLE_ARN
require_var RESEND_API_KEY
require_var MAIL_FROM
require_var KMS_KEY_ARN

REPLY_TO="${REPLY_TO:-support@agentfailure.com}"
LAMBDA_TIMEOUT="${LAMBDA_TIMEOUT:-15}"
LAMBDA_MEMORY_MB="${LAMBDA_MEMORY_MB:-256}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: aws CLI not found" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python binary not found: $PYTHON_BIN" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip not available for $PYTHON_BIN" >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

cat > "$WORKDIR/lambda_function.py" <<'PY'
import base64
import json
import os

import aws_encryption_sdk
from aws_encryption_sdk import CommitmentPolicy
from aws_encryption_sdk.key_providers.kms import StrictAwsKmsMasterKeyProvider
import requests

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
MAIL_FROM = os.environ["MAIL_FROM"]
REPLY_TO = os.environ.get("REPLY_TO", "")
KMS_KEY_ARN = os.environ["KMS_KEY_ARN"]
client = aws_encryption_sdk.EncryptionSDKClient(
    commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT
)


def _decrypt_code(event: dict) -> str:
    encrypted = base64.b64decode(event["request"]["code"])
    key_provider = StrictAwsKmsMasterKeyProvider(key_ids=[KMS_KEY_ARN])
    plaintext, _header = client.decrypt(
        source=encrypted,
        key_provider=key_provider,
    )
    return plaintext.decode("utf-8")


def _subject_html_text(trigger: str, code: str) -> tuple[str, str, str]:
    if trigger == "CustomEmailSender_SignUp":
        subject = "Verify your Agent Failure account"
        html = (
            "<p>Hello,</p>"
            "<p>Your Agent Failure verification code is:</p>"
            f"<p><b style='font-size:18px;letter-spacing:1px'>{code}</b></p>"
            "<p>This code expires shortly. If you did not request this, you can ignore this email.</p>"
            "<p>Agent Failure</p>"
        )
        text = (
            "Hello,\n\n"
            "Your Agent Failure verification code is:\n"
            f"{code}\n\n"
            "This code expires shortly. If you did not request this, you can ignore this email.\n\n"
            "Agent Failure\n"
        )
        return subject, html, text
    if trigger == "CustomEmailSender_ForgotPassword":
        subject = "Reset your Agent Failure password"
        html = (
            "<p>Hello,</p>"
            "<p>Your Agent Failure password reset code is:</p>"
            f"<p><b style='font-size:18px;letter-spacing:1px'>{code}</b></p>"
            "<p>If you did not request this, you can ignore this email.</p>"
            "<p>Agent Failure</p>"
        )
        text = (
            "Hello,\n\n"
            "Your Agent Failure password reset code is:\n"
            f"{code}\n\n"
            "If you did not request this, you can ignore this email.\n\n"
            "Agent Failure\n"
        )
        return subject, html, text

    subject = "Your Agent Failure security code"
    html = (
        "<p>Hello,</p>"
        "<p>Your Agent Failure code is:</p>"
        f"<p><b style='font-size:18px;letter-spacing:1px'>{code}</b></p>"
        "<p>If you did not request this, you can ignore this email.</p>"
        "<p>Agent Failure</p>"
    )
    text = (
        "Hello,\n\n"
        "Your Agent Failure code is:\n"
        f"{code}\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "Agent Failure\n"
    )
    return subject, html, text


def handler(event, context):
    trigger = event.get("triggerSource", "")
    user_email = event["request"]["userAttributes"]["email"]
    code = _decrypt_code(event)
    subject, html, text = _subject_html_text(trigger, code)

    payload = {
        "from": MAIL_FROM,
        "to": [user_email],
        "subject": subject,
        "text": text,
        "html": html,
    }
    if REPLY_TO:
        payload["reply_to"] = REPLY_TO

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=10,
    )
    resp.raise_for_status()
    return event
PY

"$PYTHON_BIN" -m pip install --quiet --target "$WORKDIR" requests aws-encryption-sdk
(
  cd "$WORKDIR"
  zip -qr function.zip .
)

set +e
aws lambda get-function \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_FUNCTION_NAME" >/dev/null 2>&1
exists=$?
set -e

if [[ "$exists" -eq 0 ]]; then
  echo "Updating existing Lambda: $LAMBDA_FUNCTION_NAME"
  aws lambda update-function-code \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://$WORKDIR/function.zip" >/dev/null

  aws lambda wait function-updated \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME"

  aws lambda update-function-configuration \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --timeout "$LAMBDA_TIMEOUT" \
    --memory-size "$LAMBDA_MEMORY_MB" \
    --environment "Variables={RESEND_API_KEY=$RESEND_API_KEY,MAIL_FROM=$MAIL_FROM,REPLY_TO=$REPLY_TO,KMS_KEY_ARN=$KMS_KEY_ARN}" >/dev/null

  aws lambda wait function-updated \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME"
else
  echo "Creating new Lambda: $LAMBDA_FUNCTION_NAME"
  aws lambda create-function \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --runtime python3.12 \
    --handler lambda_function.handler \
    --zip-file "fileb://$WORKDIR/function.zip" \
    --role "$LAMBDA_ROLE_ARN" \
    --timeout "$LAMBDA_TIMEOUT" \
    --memory-size "$LAMBDA_MEMORY_MB" \
    --environment "Variables={RESEND_API_KEY=$RESEND_API_KEY,MAIL_FROM=$MAIL_FROM,REPLY_TO=$REPLY_TO,KMS_KEY_ARN=$KMS_KEY_ARN}" >/dev/null
fi

echo "Done. Lambda deployed: $LAMBDA_FUNCTION_NAME"
echo "Next: wire Cognito User Pool CustomEmailSender trigger to this Lambda and set KMS key in Cognito."
