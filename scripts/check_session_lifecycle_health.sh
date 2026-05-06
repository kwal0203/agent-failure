#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-runtime-pool}"
LIMIT="${1:-10}"

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 [limit]"
  exit 2
fi

CP_POD=$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=control-plane -o jsonpath='{.items[0].metadata.name}')
if [[ -z "$CP_POD" ]]; then
  echo "No control-plane pod found in namespace $NS"
  exit 2
fi

echo "Namespace: $NS"
echo "Control-plane pod: $CP_POD"
echo "Checking latest $LIMIT sessions..."

ROWS=$(kubectl -n "$NS" exec "$CP_POD" -c control-plane -- uv run python -c "import json; from sqlalchemy import text; from apps.control_plane.src.infrastructure.persistence.db import SessionFactory as S; db=S(); rows=db.execute(text('select id::text,state,coalesce(runtime_id,\'\') as runtime_id,created_at::text from sessions order by created_at desc limit :n'), {'n': $LIMIT}).fetchall(); print(json.dumps([{'id':r[0],'state':r[1],'runtime_id':r[2],'created_at':r[3]} for r in rows]))")

if [[ -z "$ROWS" || "$ROWS" == "[]" ]]; then
  echo "No sessions found."
  exit 0
fi

FAIL=0
PASS=0

# iterate with python for robust json parsing
python3 - <<PY
import json, subprocess, sys
ns = "$NS"
rows = json.loads('''$ROWS''')
fail = 0
passed = 0

terminal = {"CANCELLED", "FAILED", "COMPLETED", "EXPIRED"}
for s in rows:
    sid = s["id"]
    state = s["state"]
    runtime_id = (s.get("runtime_id") or "").strip()
    sid8 = sid.split("-")[0]
    expected_pod = runtime_id if runtime_id else f"session-{sid8}"

    get_cmd = ["kubectl", "-n", ns, "get", "pod", expected_pod, "-o", "jsonpath={.status.phase}"]
    r = subprocess.run(get_cmd, capture_output=True, text=True)
    pod_exists = (r.returncode == 0)
    pod_phase = r.stdout.strip() if pod_exists else "<missing>"

    problems = []
    if state == "ACTIVE":
        if not runtime_id:
            problems.append("ACTIVE has empty runtime_id")
        if not pod_exists:
            problems.append(f"ACTIVE expected pod '{expected_pod}' missing")
    elif state in terminal:
        if pod_exists:
            problems.append(f"terminal state but pod still exists ({expected_pod}, phase={pod_phase})")

    if problems:
        fail += 1
        print(f"[FAIL] {sid} state={state} runtime_id='{runtime_id}' pod={expected_pod} phase={pod_phase}")
        for p in problems:
            print(f"       - {p}")
    else:
        passed += 1
        print(f"[OK]   {sid} state={state} runtime_id='{runtime_id}' pod={expected_pod} phase={pod_phase}")

print(f"\nSummary: ok={passed} fail={fail} total={len(rows)}")
if fail:
    sys.exit(1)
PY
