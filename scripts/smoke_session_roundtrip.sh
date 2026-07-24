#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-runtime-pool}"
API_BASE="${API_BASE:-http://127.0.0.1:18080}"
LAB_ID="${LAB_ID:-44444444-4444-4444-4444-444444444444}"
LAB_DIFFICULTY="${LAB_DIFFICULTY:-medium}"
AUTH_HEADER="${AUTH_HEADER:-Bearer local:learner@example.com:learner}"
PROVISION_TIMEOUT="${PROVISION_TIMEOUT:-90}"
CLEANUP_TIMEOUT="${CLEANUP_TIMEOUT:-120}"
POLL_SECONDS="${POLL_SECONDS:-2}"

PODS="${1:-1}"
TIMES="${2:-1}"

if ! [[ "$PODS" =~ ^[0-9]+$ ]] || (( PODS < 1 )); then
  echo "Usage: $0 [pods>=1] [times>=1]"
  exit 2
fi
if ! [[ "$TIMES" =~ ^[0-9]+$ ]] || (( TIMES < 1 )); then
  echo "Usage: $0 [pods>=1] [times>=1]"
  exit 2
fi

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need kubectl
need curl
need python3

CP_POD="$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=control-plane -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "$CP_POD" ]]; then
  echo "No control-plane pod found in namespace $NS"
  exit 2
fi

echo "Namespace: $NS"
echo "API_BASE: $API_BASE"
echo "Tip: use API_BASE=http://127.0.0.1:30080 for staging NodePort checks."
echo "LAB_ID: $LAB_ID"
echo "Control-plane pod: $CP_POD"
echo "pods=$PODS times=$TIMES"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

run_one() {
  local round="$1"
  local idx="$2"
  local out="$3"
  local sid="" state="" runtime_id="" pod_name="" now_ts=0 start_ts=0

  local idem="smoke-r${round}-i${idx}-$(date +%s)-$RANDOM"
  local body_file
  body_file="$(mktemp)"

  local create_code
  create_code=$(
    curl -sS -o "$body_file" -w "%{http_code}" \
      -X POST "$API_BASE/api/v1/sessions" \
      -H "Authorization: $AUTH_HEADER" \
      -H "Idempotency-Key: $idem" \
      -H "Content-Type: application/json" \
      --data "{\"lab_id\":\"$LAB_ID\",\"lab_difficulty\":\"$LAB_DIFFICULTY\"}"
  )
  if [[ "$create_code" != "202" ]]; then
    printf "result=FAIL stage=create http=%s\n" "$create_code" >"$out"
    rm -f "$body_file"
    return
  fi

  sid="$(python3 - <<PY
import json
with open("$body_file", "r", encoding="utf-8") as f:
    data = json.load(f)
print(data["session"]["id"])
PY
)"
  rm -f "$body_file"

  start_ts=$(date +%s)
  while true; do
    row="$(kubectl -n "$NS" exec "$CP_POD" -c control-plane -- uv run python -c "from sqlalchemy import text; from apps.control_plane.src.infrastructure.persistence.db import SessionFactory as S; db=S(); r=db.execute(text(\"select state,coalesce(runtime_id,'') from sessions where id=:sid\"), {'sid':'$sid'}).fetchone(); print((r[0] if r else '') + '|' + (r[1] if r else ''))")"
    state="${row%%|*}"
    runtime_id="${row#*|}"
    if [[ "$state" == "ACTIVE" && -n "$runtime_id" ]] && kubectl -n "$NS" get pod "$runtime_id" >/dev/null 2>&1; then
      break
    fi
    now_ts=$(date +%s)
    if (( now_ts - start_ts > PROVISION_TIMEOUT )); then
      printf "result=FAIL stage=provision sid=%s state=%s runtime_id=%s\n" "$sid" "$state" "$runtime_id" >"$out"
      return
    fi
    sleep "$POLL_SECONDS"
  done

  local stop_code
  stop_code=$(
    curl -sS -o /dev/null -w "%{http_code}" \
      -X POST "$API_BASE/api/v1/sessions/$sid/stop" \
      -H "Authorization: $AUTH_HEADER" \
      -H "Content-Type: application/json"
  )
  if [[ "$stop_code" != "202" ]]; then
    printf "result=FAIL stage=stop sid=%s http=%s runtime_id=%s\n" "$sid" "$stop_code" "$runtime_id" >"$out"
    return
  fi

  start_ts=$(date +%s)
  while true; do
    row="$(kubectl -n "$NS" exec "$CP_POD" -c control-plane -- uv run python -c "from sqlalchemy import text; from apps.control_plane.src.infrastructure.persistence.db import SessionFactory as S; db=S(); r=db.execute(text(\"select state,coalesce(runtime_id,'') from sessions where id=:sid\"), {'sid':'$sid'}).fetchone(); print((r[0] if r else '') + '|' + (r[1] if r else ''))")"
    state="${row%%|*}"
    runtime_id="${row#*|}"
    pod_name="$runtime_id"
    if [[ -z "$pod_name" ]]; then
      pod_name="session-${sid%%-*}"
    fi
    if [[ "$state" =~ ^(CANCELLED|FAILED|COMPLETED|EXPIRED)$ ]] && ! kubectl -n "$NS" get pod "$pod_name" >/dev/null 2>&1; then
      printf "result=OK sid=%s final_state=%s runtime_id=%s\n" "$sid" "$state" "$runtime_id" >"$out"
      return
    fi
    now_ts=$(date +%s)
    if (( now_ts - start_ts > CLEANUP_TIMEOUT )); then
      local exists=0
      kubectl -n "$NS" get pod "$pod_name" >/dev/null 2>&1 && exists=1
      printf "result=FAIL stage=cleanup sid=%s state=%s runtime_id=%s pod=%s pod_exists=%s\n" "$sid" "$state" "$runtime_id" "$pod_name" "$exists" >"$out"
      return
    fi
    sleep "$POLL_SECONDS"
  done
}

ok_total=0
fail_total=0
create_fail=0
provision_fail=0
stop_fail=0
cleanup_fail=0

for round in $(seq 1 "$TIMES"); do
  echo ""
  echo "Round $round/$TIMES"
  pids=()
  outs=()
  for idx in $(seq 1 "$PODS"); do
    out="$TMP_DIR/r${round}_i${idx}.txt"
    outs+=("$out")
    run_one "$round" "$idx" "$out" &
    pids+=("$!")
  done

  for p in "${pids[@]}"; do
    wait "$p"
  done

  round_ok=0
  round_fail=0
  for out in "${outs[@]}"; do
    line="$(cat "$out")"
    if [[ "$line" == result=OK* ]]; then
      ((round_ok+=1))
      ((ok_total+=1))
      echo "[OK]   $line"
    else
      ((round_fail+=1))
      ((fail_total+=1))
      echo "[FAIL] $line"
      case "$line" in
        *"stage=create"*) ((create_fail+=1)) ;;
        *"stage=provision"*) ((provision_fail+=1)) ;;
        *"stage=stop"*) ((stop_fail+=1)) ;;
        *"stage=cleanup"*) ((cleanup_fail+=1)) ;;
      esac
    fi
  done
  echo "Round summary: ok=$round_ok fail=$round_fail total=$PODS"
done

total=$((PODS * TIMES))
echo ""
echo "Final summary: ok=$ok_total fail=$fail_total total=$total"
echo "Failures by stage: create=$create_fail provision=$provision_fail stop=$stop_fail cleanup=$cleanup_fail"

if (( fail_total > 0 )); then
  exit 1
fi
