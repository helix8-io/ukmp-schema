# UK Materials Passport Exchange API (D2.1)

`openapi.yaml` is the **OpenAPI 3.1.0** specification of the exchange plane
for UK Materials Passports — Innovate UK project 10188380, WP2 deliverable
**D2.1**, API version **1.0.0**, licensed Apache-2.0.

It defines how any conformant system (ERP, MES, traceability platform,
recycler portal, regulator tooling) issues, retrieves, revises, verifies
and hands over passports across organisational boundaries. Passport
payloads are not redefined here: the spec references the published JSON
Schema `../schema/material_passport.schema.json` by `$ref`, so the API
always tracks the schema version in the same release.

| File | Purpose |
|---|---|
| `openapi.yaml` | Source specification (edit this) |
| `dist/openapi.bundled.yaml` | Generated single-file bundle with the passport schema inlined — for tools that cannot follow external `$ref`s (code generators, Prism, API gateways). Do not edit by hand. |
| `redocly.yaml` | Lint configuration (Redocly `recommended`, one documented adjustment) |
| `openapi-draft.md` | Superseded draft operations table, kept for history |

## Surface

| Operation | Method & path | Scope |
|---|---|---|
| `createPassport` | `POST /passports` | `passports:write` |
| `listPassports` | `GET /passports?gtin=&lgtin=&from=&to=&identityLevel=&lifecycleStatus=&credentialStatus=&cursor=&limit=` | `passports:read*` |
| `getPassport` | `GET /passports/{passportKey}` — `application/ld+json`, `application/vc+jwt`, `text/html` | anonymous or `passports:read*` |
| `listPassportRevisions` | `GET /passports/{passportKey}/revisions` | `passports:read*` |
| `createPassportRevision` | `POST /passports/{passportKey}/revisions` (append-only, `If-Match`) | `passports:write` |
| `createPassportSuccessor` | `POST /passports/{passportKey}/successors` | `passports:write` |
| `updatePassportStatus` | `POST /passports/{passportKey}/status` (revoke / suspend / reinstate) | `passports:write` |
| `listPassportEvents` | `GET /passports/{passportKey}/events` (EPCIS 2.0 genealogy) | `passports:read*` |
| `verifyPassport` | `POST /verify` → `VerificationReport` | `verify` |
| `createExchange` | `POST /exchanges` (push to partner, `202`) | `exchange` |
| `getExchange` | `GET /exchanges/{exchangeId}` (delivery receipt) | `exchange` |
| `getIssuerKeys` | `GET /.well-known/ukmp/keys` (JWKS, origin root) | public |
| `getStatusList` | `GET /status/{listId}` (Bitstring Status List credential) | public |

Webhooks: `passport.revised`, `passport.revoked`, `passport.succeeded`,
`exchange.received` (signed with a detached JWS in `UKMP-Webhook-Signature`).

Conventions: OAuth2 client credentials; RFC 9457 `application/problem+json`
errors; `Idempotency-Key` on creating `POST`s; `If-Match`/`ETag` optimistic
concurrency on writes to an existing passport; opaque cursor pagination with
RFC 8288 `Link` headers.

## Conformance notes

- **Levels.** The API carries passports of any conformance level (1 Core,
  2 Evidence-linked, 3 Verified). `POST /verify` reports the level a document
  *achieves*, check by check, which may be lower than the level it declares.
  A verifier claiming Level 3 support MUST accept both securings (JOSE compact
  JWS and embedded `ecdsa-jcs-2019` Data Integrity proof).
- **Revision vs successor.** Revisions update the same subject (same
  `passportId`); successors are new passports after a lifecycle transition,
  linked both ways via `lifecycle.predecessorRefs` / `successorRefs`
  (schema v0.2, B2).
- **Access tiers.** Field-level disclosure follows `accessPolicy`
  (schema v0.2, B3) and the caller's scope. Withheld members are omitted and
  listed in the `UKMP-Withheld-Paths` header and the body's `ukmp:redaction`.
  Redacted views are unsigned (`application/ld+json` only; `vc+jwt` returns
  `406`), so a redacted Level 3 passport verifies at most to Level 2.
  Selective-disclosure credentials (e.g. SD-JWT VC) are a non-normative
  candidate for signed partial disclosure.
- **Why 3.1, not 3.0.** The application named "OpenAPI 3.0". 3.1 is used
  because its schema objects are JSON Schema 2020-12, so the passport schema
  is referenced without lossy conversion, and webhooks are first-class.
- **v0.1 compatibility.** The tests validate every `examples/*.jsonld`
  (v0.1 and v0.2) as a `POST /passports` body. Filters and behaviour tied to
  v0.2 fields (`identityLevel`, `lifecycleStatus`, access tiers) define
  defaults for passports that lack those fields.

## View the documentation

```bash
npx @redocly/cli@1 preview-docs api/openapi.yaml       # live preview at http://127.0.0.1:8080
npx @redocly/cli@1 build-docs api/openapi.yaml -o api/dist/index.html   # static Redoc HTML
```

## Run the checks

From the repository root (Python ≥ 3.10, Node.js ≥ 18):

```bash
pip install -r tests/api/requirements.txt

npx @redocly/cli@1 lint api/openapi.yaml --config api/redocly.yaml   # lint
pytest tests/api                                                     # spec + example validation
python tests/api/bundle.py                                           # regenerate dist/openapi.bundled.yaml
python tests/api/bundle.py --check                                   # CI: fail if the bundle is stale
bash tests/api/mock_smoke.sh                                         # Prism mock + curl smoke test
```

Regenerate the bundle whenever `openapi.yaml` **or the passport schema**
changes; CI (`.github/workflows/api.yml`) fails on a stale bundle.

Prism note: use the bundle for mocking (`npx @stoplight/prism-cli@5 mock
api/dist/openapi.bundled.yaml`). Against the source file, Prism 5 does not
apply the external passport schema (which carries its own `$id`) to request
validation and accepts invalid passports silently; the bundler step
neutralises that `$id` (moved to `x-ukmp-schema-id`).

## Reference implementation status (D2.2)

This document is the **specification**. What the open reference tooling
does today (see also `../IMPLEMENTATION_STATUS.md`):

| Area | Status |
|---|---|
| Document-local verification checks (schema validity, recycled-fraction arithmetic, evidence traceability, mass-balance reconciliation, level detection) | ✅ Implemented in `tools/validate.py` — the basis of the `/verify` report |
| An HTTP server implementing this API | ❌ Not in this repository. The mock (`mock_smoke.sh`) returns spec examples only |
| Level 3 **issuance** (signing; KMS-held per-organisation P-256 keys) | ❌ **Not implemented** — WP2 backlog. `createPassport` with server-side signing cannot be exercised with the reference tooling |
| Level 3 cryptographic **verification** (`proof-valid`) | ⚠️ Structure of both securings is checked; signatures are not cryptographically verified yet |
| Network checks (`identifiers-resolve`, key retrieval, `status-not-revoked`, time anchoring) | ❌ Not implemented |
| Access-tier enforcement, revisions/successors store, exchanges with receipts, webhooks | ❌ Specified only |

All signatures, key coordinates and status-list bitstrings in the examples
are **illustrative**, not real cryptographic material.
