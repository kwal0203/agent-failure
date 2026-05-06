#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-runtime-pool}"

POD="$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=control-plane -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${POD}" ]]; then
  echo "No control-plane pod found in namespace: $NS"
  exit 1
fi

echo "Namespace: $NS"
echo "Control-plane pod: $POD"

kubectl -n "$NS" exec "$POD" -c control-plane -- uv run python -c "
from sqlalchemy import text
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory as S

db = S()
with db.begin():
    rows = db.execute(
        text(\"update sessions set state='CANCELLED' where state='ACTIVE' returning id\")
    ).fetchall()
print('cancelled=', len(rows))
"

kubectl -n "$NS" exec "$POD" -c control-plane -- uv run python -c "
from sqlalchemy import text
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory as S

db = S()
rows = db.execute(
    text(\"select state,count(*) from sessions group by state order by state\")
).fetchall()
print(rows)
"
