# Implementation status

Per-conformance-level coverage of the **reference implementation** (the
open tooling in this repository and the WP2 reference stack). The
specification is normative at all three levels; this table tracks what
the reference tooling can do today, and is updated as WP2 lands rather
than being restated inside spec clauses.

| Level | Name | Specification | Reference implementation |
|---|---|---|---|
| 1 | Core | Normative (§8) | ✅ Emitted and validated (`tools/validate.py`, browser playground) |
| 2 | Evidence-linked | Normative (§8) | ✅ Emitted and validated, including recycled-content arithmetic and mass-balance reconciliation |
| 3 | Verified | Normative (§6, §8) | ⏳ Validation of both securings (JOSE-enveloped compact JWS and embedded Data Integrity proof) and conformance-level detection is implemented; **signing/issuance is not** — KMS-held per-organisation ECDSA keys are scheduled in the WP2 backlog. `tools/validate.py` indicates, but does not perform, cryptographic signature verification. |

Independent implementations of the schema (including commercial
platforms) may support levels beyond the reference tooling; conformance
claims for those are made by their operators, not by this table.

Last updated: 2026-08-14.
