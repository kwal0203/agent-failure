#!/usr/bin/env bash
set -euo pipefail

# Build + push runtime image and update staging lock in one command.
#
# Usage:
#   ./scripts/release_runtime_image.sh
#
# Optional passthrough env vars:
#   REGISTRY=ghcr.io
#   ORG=kwal0203
#   IMAGE_REPO=agent-failure-runtime-v1
#   LAB_SLUG=agent
#   LAB_VERSION=0.1.0
#   RUNTIME_DIR=runtimes/agent
#   ARTIFACT_DIR=.artifacts
#   LOCK_FILE=deploy/k8s/staging/runtime-image.lock
#   TARGET_LABS=agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning
#   UPDATE_RUNTIME_LOCK=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "Step 1/2: Build runtime image"
./scripts/build_runtime_image.sh

echo "Step 2/2: Push runtime image and update lock"
UPDATE_RUNTIME_LOCK="${UPDATE_RUNTIME_LOCK:-1}" ./scripts/push_runtime_image.sh

echo
echo "Runtime release flow complete."
