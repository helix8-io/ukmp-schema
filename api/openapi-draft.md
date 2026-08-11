# UK Materials Passport Exchange API — Draft Surface

**Status:** draft operations table, extracted from the project architecture
(WP2 input). The full **OpenAPI 3.0 specification is WP2 deliverable D2.1**
and will be published in this directory when formalised.

The exchange plane is a RESTful API that any conformant system implements —
ERP, MES, traceability platform, or regulator tooling. Authentication is
OAuth2 client-credentials (system-to-system). The critical design fact:
passports cross organisational boundaries, so every operation assumes the
consumer does not run the producer's software.

## Core operations (draft)

| Operation | Method & path (draft) | Purpose |
|---|---|---|
| Create passport | `POST /passports` | Issue a passport for a batch/product |
| Retrieve passport | `GET /passports/{id}` | Fetch by ID (also the GS1 Digital Link target); content-negotiation: JSON-LD, human-readable HTML |
| List/query | `GET /passports?gtin=&from=&to=` | Batch discovery for a trading partner |
| Update / supersede | `POST /passports/{id}/revisions` | Append-only revisioning — passports are never edited in place |
| Revoke | `POST /passports/{id}/status` | Sets the status-list bit (recall/withdrawal) |
| Verify | `POST /verify` | Submit a passport document; returns a structured verification report (per-check pass/fail + overall conformance level achieved) |
| Event trace | `GET /passports/{id}/events` | EPCIS event chain for genealogy traversal |
| Exchange/hand-off | `POST /exchanges` | Push a passport to a trading partner's endpoint with delivery receipt (despatch → goods-in linkage) |
| Public keys | `GET /.well-known/ukmp/keys` | Issuer's current + historical verification keys |

## Design rules

- **Append-only revisioning** — audit safety; a passport is superseded, never
  mutated.
- **Idempotent creates** — retry safety for machine-to-machine integrations.
- **Pagination and webhook notification** — for high-volume ERP/MES
  integrations.

## Verification report (`POST /verify`)

The verifier returns a machine-readable report so "verified recycled content"
is an outcome, not a marketing phrase. Checks by conformance level:

| Check | L1 | L2 | L3 |
|---|---|---|---|
| Schema-valid against published JSON Schema | ✔ | ✔ | ✔ |
| Identifiers resolve (Digital Link, GLN) | ✔ | ✔ | ✔ |
| Every claim traceable to EPCIS events; genealogy traversable; mass-balance arithmetic reconciles | | ✔ | ✔ |
| VC proof validates against issuer's published key | | | ✔ |
| Status list: not revoked | | | ✔ |
| External time-anchor receipt validates (where configured) | | | ✔ (optional) |

`tools/validate.py` in this repository implements the document-local subset
of these checks (schema validity, fraction arithmetic, mass-balance
reconciliation, level detection); network-dependent checks (identifier
resolution, key retrieval, status lists) belong to the WP2 reference
implementation (D2.2).
