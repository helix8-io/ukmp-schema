#!/usr/bin/env bash
# Mock-server smoke test for the UK Materials Passport Exchange API.
#
# Starts a Prism mock of the bundled spec (api/dist/openapi.bundled.yaml) and
# exercises a handful of operations, asserting HTTP status codes. Prism
# validates requests against the spec, so this also proves that the example
# passports in examples/ are accepted as POST /passports bodies by an
# independent (AJV-based) validator, and that an invalid passport is rejected.
#
# Why the bundle: Prism 5 does not reliably apply the external passport schema
# ($ref ../schema/material_passport.schema.json, which carries its own $id) to
# request validation — invalid passports are accepted silently. The bundle
# produced by tests/api/bundle.py inlines it with the $id neutralised.
#
# Usage: bash tests/api/mock_smoke.sh   (from anywhere; needs node/npx, curl)
# Env:   PRISM_PORT (default 4010), SPEC (default api/dist/openapi.bundled.yaml)

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

PORT="${PRISM_PORT:-4010}"
SPEC="${SPEC:-api/dist/openapi.bundled.yaml}"
BASE="http://127.0.0.1:${PORT}"
WORK="$(mktemp -d)"
LOG="$WORK/prism.log"
PASS=0
FAIL=0

if [[ ! -f "$SPEC" ]]; then
  echo "error: $SPEC not found — run: python tests/api/bundle.py" >&2
  exit 2
fi

# Run Prism in its own process group so cleanup kills npx *and* the node child.
setsid npx -y @stoplight/prism-cli@5 mock "$SPEC" --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
PRISM_PGID=$!

cleanup() {
  kill -- "-$PRISM_PGID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

for _ in $(seq 1 90); do
  if grep -q "Prism is listening" "$LOG" 2>/dev/null; then break; fi
  if ! kill -0 "$PRISM_PGID" 2>/dev/null; then
    echo "error: Prism exited during start-up" >&2; cat "$LOG" >&2; exit 2
  fi
  sleep 1
done
grep -q "Prism is listening" "$LOG" || { echo "error: Prism did not start" >&2; cat "$LOG" >&2; exit 2; }

# expect <name> <expected-status> <curl args...>
expect() {
  local name="$1" want="$2"; shift 2
  local got
  got="$(curl -sS -o "$WORK/body" -w '%{http_code}' "$@" || echo "000")"
  if [[ "$got" == "$want" ]]; then
    printf 'PASS  %-58s %s\n' "$name" "$got"; PASS=$((PASS + 1))
  else
    printf 'FAIL  %-58s got %s, want %s\n' "$name" "$got" "$want"; FAIL=$((FAIL + 1))
    head -c 600 "$WORK/body"; echo
  fi
}

AUTH=(-H 'Authorization: Bearer smoke-test-token')
LD=(-H 'Content-Type: application/ld+json')

# --- Trust material (public, no auth) -------------------------------------------
expect "GET /.well-known/ukmp/keys (no auth)" 200 "$BASE/.well-known/ukmp/keys"
grep -q '"keys"' "$WORK/body" || { echo "FAIL  JWKS body has no 'keys' member"; FAIL=$((FAIL + 1)); }
expect "GET /status/3 (no auth)" 200 "$BASE/status/3"

# --- Create ------------------------------------------------------------------------
shopt -s nullglob
examples=(examples/*.jsonld)
[[ ${#examples[@]} -gt 0 ]] || { echo "error: no examples/*.jsonld" >&2; exit 2; }
for f in "${examples[@]}"; do
  expect "POST /passports $(basename "$f")" 201 -X POST "$BASE/passports" \
    "${AUTH[@]}" "${LD[@]}" -H 'Prefer: code=201' -H "Idempotency-Key: smoke-$(basename "$f")" \
    --data-binary "@$f"
done

python3 - "$WORK/invalid.jsonld" <<'PY'
import json, sys
doc = json.load(open("examples/example_passport.jsonld", encoding="utf-8"))
doc["credentialSubject"]["recycledContent"]["totalRecycledFraction"] = 1.87
json.dump(doc, open(sys.argv[1], "w", encoding="utf-8"))
PY
expect "POST /passports schema-invalid passport -> 422" 422 -X POST "$BASE/passports" \
  "${AUTH[@]}" "${LD[@]}" -H 'Idempotency-Key: smoke-invalid-1' --data-binary "@$WORK/invalid.jsonld"
expect "POST /passports without token -> 401" 401 -X POST "$BASE/passports" \
  "${LD[@]}" -H 'Idempotency-Key: smoke-noauth-1' --data-binary @examples/example_level1_minimal.jsonld
expect "POST /passports text/plain -> 415" 415 -X POST "$BASE/passports" \
  "${AUTH[@]}" -H 'Content-Type: text/plain' -H 'Idempotency-Key: smoke-415-1' --data 'not a passport'

# --- Retrieve (content negotiation) ------------------------------------------------
KEY='urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42'
expect "GET /passports/{key} application/ld+json (anonymous)" 200 -H 'Accept: application/ld+json' "$BASE/passports/$KEY"
expect "GET /passports/{key} application/vc+jwt" 200 "${AUTH[@]}" -H 'Accept: application/vc+jwt' "$BASE/passports/$KEY"
expect "GET /passports/{key} text/html" 200 -H 'Accept: text/html' "$BASE/passports/$KEY"
expect "GET /passports?gtin=... (list)" 200 "${AUTH[@]}" "$BASE/passports?gtin=05060987654321&limit=10"

# --- Verify ------------------------------------------------------------------------
expect "POST /verify application/ld+json" 200 -X POST "$BASE/verify" \
  "${AUTH[@]}" "${LD[@]}" --data-binary @examples/example_passport.jsonld
grep -q '"achievedLevel"' "$WORK/body" || { echo "FAIL  verify body has no achievedLevel"; FAIL=$((FAIL + 1)); }
JWS='eyJhbGciOiJFUzI1NiIsInR5cCI6InZjK2p3dCJ9.eyJ0eXBlIjpbIlZlcmlmaWFibGVDcmVkZW50aWFsIl19.SUxMVVNUUkFUSVZF'
expect "POST /verify application/vc+jwt" 200 -X POST "$BASE/verify" \
  "${AUTH[@]}" -H 'Content-Type: application/vc+jwt' --data "$JWS"

# --- Lifecycle ---------------------------------------------------------------------
expect "POST /passports/{key}/status revoke" 200 -X POST "$BASE/passports/$KEY/status" \
  "${AUTH[@]}" -H 'Content-Type: application/json' -H 'If-Match: "rev-1"' \
  --data '{"action":"revoke","reason":"recall"}'
expect "POST /passports/{key}/status bad action -> 422" 422 -X POST "$BASE/passports/$KEY/status" \
  "${AUTH[@]}" -H 'Content-Type: application/json' -H 'If-Match: "rev-1"' \
  --data '{"action":"explode","reason":"recall"}'

echo
echo "smoke: ${PASS} passed, ${FAIL} failed"
[[ $FAIL -eq 0 ]]
