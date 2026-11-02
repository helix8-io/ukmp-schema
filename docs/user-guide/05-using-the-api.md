# 5. Using the exchange API

The exchange API lets any system create, fetch, check and hand over passports,
whoever built it. It is defined in `api/openapi.yaml` (OpenAPI 3.1, WP2
deliverable D2.1). This chapter is a task-by-task walkthrough with `curl`.

> **About the examples.** The WP2 reference implementation (D2.2) is not yet
> deployed, so the responses shown here are the response examples from
> `api/openapi.yaml`, not captures from a live server. The request bodies in
> `docs/user-guide/examples/api/` were checked against the OpenAPI request
> schemas, and the passports inside them pass `tools/validate.py`.

## Before you start

Your platform provider (or your own deployment) gives you:

| Item | Example used below |
|---|---|
| API base URL | `https://passports.example.org/ukmp/v1` |
| Token URL | `https://passports.example.org/oauth2/token` |
| Client ID and secret | issued per system (for example one for your ERP) |

```bash
export UKMP_API=https://passports.example.org/ukmp/v1
export UKMP_TOKEN_URL=https://passports.example.org/oauth2/token
```

Two exceptions to the base path: the key set is at the **origin root**,
`https://passports.example.org/.well-known/ukmp/keys`, and the status lists
are at `$UKMP_API/status/{listId}`.

## Step 1: get an access token (OAuth2 client credentials)

System-to-system calls use the OAuth 2.0 **client credentials** grant: your
software swaps its client ID and secret for a short-lived bearer token.

```bash
curl -s -u "$CLIENT_ID:$CLIENT_SECRET" \
  -d grant_type=client_credentials \
  -d scope="passports:write passports:read:legitimate-interest verify exchange" \
  "$UKMP_TOKEN_URL"
```

The response is a standard OAuth2 token response containing `access_token`
and `expires_in`. Put the token in a variable:

```bash
export TOKEN=...   # the access_token value
```

Ask only for the scopes the system needs:

| Scope | Lets you |
|---|---|
| `passports:read` | Read passports, public fields only |
| `passports:read:legitimate-interest` | Read public and legitimate-interest fields |
| `passports:read:authority` | Read all fields (regulators only) |
| `passports:write` | Create passports, add revisions and successors, revoke |
| `verify` | Use `POST /verify` |
| `exchange` | Send passports to trading partners, read delivery receipts |

The read scopes stack: `authority` includes `legitimate-interest`, which
includes `read`.

## Step 2: create a passport

Send the passport file with `Content-Type: application/ld+json` and an
**Idempotency-Key** (a fresh UUID per new passport):

```bash
curl -s -i -X POST "$UKMP_API/passports" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/ld+json" \
  -H "Idempotency-Key: $(uuidgen)" \
  --data-binary @my-passports/PP-2026-0142.jsonld
```

A pre-signed Level 3 passport goes up the same way with
`Content-Type: application/vc+jwt` and the `.jwt` file as the body.

Response `201 Created`:

```
HTTP/1.1 201 Created
Location: /ukmp/v1/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42
ETag: "rev-1-sha256-..."
Content-Type: application/ld+json
```

with the passport as stored in the body. Keep two things:

- the **passport key** at the end of `Location` (the server's handle for the
  passport; you can also use the `passportId` percent-encoded as one path
  segment);
- the **ETag**, which you need to change the passport later.

### Idempotency: safe retries

Networks fail. If you are not sure a create worked, **send exactly the same
request again with the same Idempotency-Key**:

| You send | Server returns |
|---|---|
| Same key, same body | `200 OK` with the passport created the first time. Nothing is duplicated. |
| Same key, different body | `409 Conflict` |
| New key, but a `passportId` that already exists | `409 Conflict` (`duplicate-passport`). To change an existing passport, add a revision. |

Keys are kept for at least 24 hours. Store the key alongside the batch record
in your ERP so a retry after a crash reuses it.

## Step 3: retrieve a passport (tier-filtered)

Anyone can fetch a passport; what they see depends on their token.

```bash
# anonymous: public tier
curl -s "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42" \
  -H "Accept: application/ld+json" -D -

# trading partner: public + legitimate-interest
curl -s "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/ld+json"
```

Use `Accept` to choose the format:

| Accept | You get |
|---|---|
| `application/ld+json` | The JSON-LD passport (filtered to your tier) |
| `application/vc+jwt` | The issuer-signed JWS exactly as issued. Only if nothing is withheld from you; otherwise `406 Not Acceptable`. |
| `text/html` | A human-readable page, e.g. for a QR code scanned on a phone |

When fields are withheld, the response says so in two places:

```
UKMP-Withheld-Paths: /composition/substances,/processingHistory
```

and in the body:

```json
"ukmp:redaction": { "tier": "public", "withheldPaths": ["/composition/substances", "/processingHistory"] }
```

A filtered view has **no signature** (removing fields would break it), so it
verifies at most to Level 2. To check the signature, a partner needs a tier
that sees everything, then fetches `application/vc+jwt`.

Other read options:

- `?revision=1` returns a historical revision.
- `If-None-Match: <etag>` returns `304 Not Modified` if nothing changed (cheap
  polling).
- Revoked passports are still returned; check their status (Step 7).

### Finding passports

```bash
curl -s "$UKMP_API/passports?lgtin=05060987654321.B26-0803-HD" -H "Authorization: Bearer $TOKEN"
curl -s "$UKMP_API/passports?gtin=05060987654321&from=2026-10-01&to=2026-10-31&limit=50" -H "Authorization: Bearer $TOKEN"
```

Other filters: `identityLevel`, `lifecycleStatus`, `credentialStatus`.
Results come in pages: `{"items": [...], "limit": 50, "nextCursor": "..."}`.
Pass `cursor=<nextCursor>` for the next page; `nextCursor: null` means the
last page. The same URL is in the `Link: <...>; rel="next"` header.

## Step 4: verify a passport

Submit any passport (yours or a supplier's) and get a per-check report:

```bash
curl -s -X POST "$UKMP_API/verify" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/ld+json" \
  --data-binary @docs/user-guide/examples/level2_pp_pellet.jsonld
```

The report (`200 OK` even when checks fail; the report *is* the answer):

```json
{
  "reportId": "...",
  "verifiedAt": "...",
  "passportId": "https://id.gs1.org/01/05060987654338/10/PP-2026-0150",
  "securing": "none",
  "declaredLevel": 2,
  "achievedLevel": 2,
  "result": "pass",
  "checks": [
    { "check": "schema-valid", "level": 1, "result": "pass" },
    { "check": "identifiers-resolve", "level": 1, "result": "pass" },
    { "check": "recycled-fraction-arithmetic", "level": 1, "result": "pass" },
    { "check": "evidence-traceable", "level": 2, "result": "pass" },
    { "check": "genealogy-traversable", "level": 2, "result": "pass" },
    { "check": "mass-balance-reconciles", "level": 2, "result": "pass" },
    { "check": "proof-valid", "level": 3, "result": "skip" },
    { "check": "status-not-revoked", "level": 3, "result": "skip" }
  ]
}
```

(Shape per the `VerificationReport` schema; values illustrative for this
file.) `result` is `pass` when the achieved level is at least the declared
level. Options: `?resolve=false` skips network checks (identifier
resolution, keys, status) and caps the result at Level 2;
`?targetLevel=1` stops early. `tools/validate.py` runs the document-local
subset of these checks offline.

## Step 5: correct a passport (revision)

Passports are never edited. To correct one, append a revision. You need the
current ETag (from the create response or a fresh GET) in `If-Match`:

```bash
curl -s -X POST "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42/revisions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H 'If-Match: "rev-1-sha256-..."' \
  -H "Idempotency-Key: $(uuidgen)" \
  --data-binary @docs/user-guide/examples/api/revision-request.json
```

The body ([`revision-request.json`](examples/api/revision-request.json)) wraps
the **complete** new passport, with the **same `passportId`**, plus a reason:

```json
{
  "reason": "correction",
  "changeSummary": "Contamination corrected from 3.0% to 2.5% (lab report LR-2026-1027).",
  "passport": { "...": "the full corrected passport" }
}
```

`reason` is one of `correction`, `update`, `evidence-added`,
`verification-added`, `succession-link`, `other`. Moving from Level 1 to
Level 2 by adding the event chain is an `evidence-added` revision.

Response `201` with the revision record (`revision`, `supersedes`,
`createdAt`, `digest`, `etag`, `href`) and a new `ETag`. Subscribers get a
`passport.revised` webhook.

List the history:

```bash
curl -s "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42/revisions" \
  -H "Authorization: Bearer $TOKEN"
```

Newest first, paginated like other lists.

## Step 6: issue a successor (lifecycle change)

When the material becomes something new (repurposed battery, regrind
compounded into a new product), issue a **new** passport linked to the old
one:

```bash
curl -s -X POST "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42/successors" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H 'If-Match: "rev-2-sha256-..."' \
  -H "Idempotency-Key: $(uuidgen)" \
  --data-binary @docs/user-guide/examples/api/successor-request.json
```

Body ([`successor-request.json`](examples/api/successor-request.json)):

```json
{
  "lifecycleStatus": "recycled",
  "transitionEventID": "https://passports.example-sme.co.uk/events/compound-run-CR-1102",
  "effectiveAt": "2026-11-02T11:00:00Z",
  "reason": "Regrind batch PP-2026-0142 consumed in compounding run CR-1102.",
  "successor": { "...": "new passport with a NEW passportId and lifecycle.status recycled" }
}
```

The server:

- adds the old `passportId` to the successor's `lifecycle.predecessorRefs`;
- appends a revision to the old passport adding the new one to
  `lifecycle.successorRefs` (that is why `If-Match` is needed on the old one);
- does **not** revoke the old passport; it stays the record of the earlier
  life;
- sends a `passport.succeeded` webhook.

`lifecycleStatus` cannot be `original`. Sending a different subject through
`/revisions` instead is rejected with `422`.

## Step 7: revoke, suspend, reinstate

```bash
curl -s -X POST "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H 'If-Match: "rev-2-sha256-..."' \
  --data-binary @docs/user-guide/examples/api/status-revoke.json
```

`action` is `revoke` (permanent), `suspend` or `reinstate` (suspension only);
`reason` is `recall`, `withdrawal`, `issued-in-error`, `compromised-key`,
`under-investigation` or `other`. This flips the passport's bit in its status
list, so copies already sent out are flagged next time anyone verifies them.
Reinstating a revoked passport returns `409`.

Anyone can read a status list without a token:

```bash
curl -s "$UKMP_API/status/3" -H "Accept: application/ld+json"
```

## Step 8: hand a passport to a customer (exchange)

At despatch, push the passport to your customer's goods-in endpoint (their own
implementation of this API) and track the receipt:

```bash
curl -s -X POST "$UKMP_API/exchanges" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  --data-binary @docs/user-guide/examples/api/exchange-request.json
```

Body ([`exchange-request.json`](examples/api/exchange-request.json)):

```json
{
  "passport": { "passportId": "https://passports.example-sme.co.uk/passports/urn:uuid:e4e73173-c5cb-52f5-8674-0abb4a098ea9" },
  "recipient": {
    "name": "Example Converter Ltd",
    "gs1:gln": "5060888000031",
    "endpoint": "https://ukmp.example-converter.co.uk/ukmp/v1"
  },
  "despatch": {
    "sscc": "350601234500000038",
    "despatchAdviceId": "DA-2026-10-0219",
    "shippingEventID": "https://passports.example-sme.co.uk/events/despatch-DA-2026-10-0219",
    "expectedDeliveryDate": "2026-10-30"
  },
  "disclosureTier": "legitimate-interest",
  "mediaType": "application/ld+json",
  "callbackUrl": "https://erp.example-sme.co.uk/hooks/ukmp"
}
```

Response `202 Accepted` with a receipt in state `queued`. Poll
`GET $UKMP_API/exchanges/{exchangeId}` or wait for your `callbackUrl`. States
go `queued` -> `delivered` -> `acknowledged` (or `rejected` / `failed`). The
acknowledgement carries the customer's own goods-in event ID and a signed
digest of what they received, which closes the despatch-to-goods-in loop.

`disclosureTier` controls what the customer receives; it can never be higher
than your own entitlement. If your customer only needs to check the recycled
figure, `public` may be enough. If they will verify a signed passport
themselves, they need a tier that sees everything.

## Step 9: walk the event chain

```bash
curl -s "$UKMP_API/passports/urn:uuid:8f2b7c1e-4d3a-4f6b-9e2d-1a5c7b9d0e42/events?direction=upstream&depth=3&bizStep=transforming" \
  -H "Authorization: Bearer $TOKEN"
```

`direction` is `upstream` (towards feedstock), `downstream` or `both`; `depth`
(1 to 20) is how many transformations to follow across passports. Events above
your tier are left out and counted in `withheldCount`.

## Errors

All errors are `application/problem+json` (RFC 9457):

```json
{
  "type": "https://schema.materialspassport.org.uk/problems/schema-invalid",
  "title": "Passport fails schema validation",
  "status": 422,
  "detail": "2 schema violations.",
  "errors": [
    { "pointer": "/credentialSubject/recycledContent/totalRecycledFraction", "message": "1.3 is greater than the maximum of 1" },
    { "pointer": "/credentialSubject/composition", "message": "'substances' is a required property" }
  ]
}
```

Switch on `type`, not on `title` or `detail` (those are for humans).

| Status | `type` ends with | Usual cause | What to do |
|---|---|---|---|
| 400 | `invalid-parameter` | Bad query parameter or malformed request | Fix the parameter named in `errors[].pointer` (`#/query/<name>`) |
| 401 | `unauthorized` | Missing or expired token | Get a new token |
| 403 | `insufficient-scope` | Token lacks the scope | Request the scope (Step 1) |
| 404 | `not-found` | Wrong passport key | Check the key or percent-encode the `passportId` |
| 406 | `signed-view-unavailable` | Asked for `application/vc+jwt` but some fields are withheld from you | Ask for `application/ld+json`, or obtain a higher tier |
| 409 | `duplicate-passport` | `passportId` already exists on this server | Use `/revisions` to change it |
| 409 | (no dedicated type yet) | Idempotency-Key reused with a different body | Use a new key for a genuinely new request |
| 409 | `invalid-status-transition` | e.g. reinstating a revoked passport | Revocation is permanent; issue a new passport |
| 412 | `stale-etag` | Someone changed the passport since you read it | GET again, re-apply your change, retry with the new ETag |
| 415 | `unsupported-media-type` | Wrong `Content-Type` | `application/ld+json` or `application/vc+jwt` for passports; `application/json` for revision, successor, status and exchange bodies |
| 422 | `schema-invalid` | Passport fails the JSON Schema or a lifecycle rule | Run `tools/validate.py` locally; see chapter 8 |
| 428 | `if-match-required` | Write without `If-Match` | Add the current ETag |
| 429 | `rate-limited` | Too many requests | Wait `Retry-After` seconds |

Run `tools/validate.py` before you call the API; most `422`s are caught
locally first.
