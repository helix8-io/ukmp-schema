# Implementation status

Per-conformance-level coverage of the **reference implementation** (the
open tooling in this repository and the WP2 reference stack). The
specification is normative at all three levels; this table tracks what
the reference tooling can do today, and is updated as WP2 lands rather
than being restated inside spec clauses.

Schema version: **v0.2** (`spec/ukmp-schema-v0.2.md`).

## Conformance levels

| Level | Name | Specification | Reference implementation |
|---|---|---|---|
| 1 | Core | Normative (§8) | ✅ Emitted and validated (`tools/validate.py`, browser playground) |
| 2 | Evidence-linked | Normative (§8) | ✅ Emitted and validated, including recycled-content arithmetic and mass-balance reconciliation |
| 3 | Verified | Normative (§6, §8) | ⏳ **Issuance (signing) is not implemented.** Validation of both securings' *structure* (JOSE-enveloped compact JWS and embedded Data Integrity proof) and conformance-level detection is implemented; KMS-held per-organisation ECDSA keys remain in the WP2 backlog. `tools/validate.py` indicates, but does not perform, cryptographic signature verification. |

## v0.2 baseline core extensions

| Extension | Schema + context | `tools/validate.py` | Exchange API |
|---|---|---|---|
| B1 multi-level identity | ✅ | ✅ Schema validation; effective identity level reported; item-level identifier and `identityLevel`/`subjectType` consistency warnings | — (no API-specific behaviour) |
| B2 succession / lifecycle | ✅ | ✅ Schema validation; predecessor-link consistency warnings. Does **not** dereference `predecessorRefs`/`successorRefs` or check that links are reciprocal across passports | 📄 Specified in `api/openapi.yaml` (D2.1: `/revisions`, `/successors`, `passport.succeeded` webhook); not implemented in a server in this repository |
| B3 access tiers | ✅ | ✅ JSON Pointer syntax/resolution, conflicting tiers, always-public fields | 📄 Specified in D2.1 (OAuth2 scopes, `withheldPaths`); **no server-side enforcement implemented**. Issuing role credentials (who holds legitimate interest) is out of scope pending the battery access-rights implementing act and prEN 18239 |
| B4 applicability status | ✅ | ✅ Pointer syntax/resolution; `required`-but-absent warnings | — |
| `feedstockSource` | ✅ | ✅ Schema enum | — |
| B5 party details / `parties[]` | ✅ | ✅ Schema validation (ISO 3166-1 alpha-2 pattern only; country codes not checked against the list) | — |
| B6–B8 declared unit, indicators, study refs | ✅ | ✅ Schema validation. Indicator codes and EN 15804 modules are *recommended* values and are not enforced; no check that per-kg and per-declared-unit footprints agree, or that module D is kept out of `netAvoidedKgCo2ePerKg` | — |
| B9 `recycledContentDetail[]` | ✅ | ✅ Per-entry fraction arithmetic (error); pointer `componentRef` resolution (warning). No check that layer entries sum to the aggregate | — |

Not done anywhere yet: selective-disclosure credentials (SD-JWT VC is a
non-normative candidate only); published `ukmp-batteries`,
`ukmp-textiles` and `ukmp-construction` profile contexts; GTIN check-digit
and GS1 CSET 82 serial validation for `gs1:sgtin`.

Independent implementations of the schema (including commercial
platforms) may support levels beyond the reference tooling; conformance
claims for those are made by their operators, not by this table.

Last updated: 2026-11-02.
