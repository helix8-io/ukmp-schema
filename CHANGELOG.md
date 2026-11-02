# Changelog

All notable changes to the UK Materials Passport Schema are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/) applied to the
schema namespace.

## [Unreleased]

## [0.2.0] — 2026-11-02

Schema v0.2: the WP3 baseline core extensions. **Strictly additive** — no
v0.1 field, enumeration value or constraint is removed or tightened, no
field becomes required, and both v0.1 examples validate unchanged.

This release also carries the post-0.1.0 alignment changes previously
listed under Unreleased (see *Changed*). One of them —
`virginDisplacementFactor` replaced by `virginBaselineKgCo2ePerKg` +
`netAvoidedKgCo2ePerKg` — is a semantic rename rather than an addition:
the retired term still resolves in the JSON-LD context and passports
carrying it still validate (`lcaSummary` is open), but it is no longer
specified.

### Added

- **B1 — multi-level identity.** Optional `identityLevel`
  (`productType` | `batch` | `item`; inferred from `subjectType` when
  absent); `subjectType` gains `ProductType` and `Item`; `gs1:sgtin`
  (serialised GTIN, `<GTIN>.<serial>`, pattern
  `^[0-9]{8,14}\.[!-~]{1,20}$`) now satisfies the identifier `anyOf`;
  `productTypeRef` (instance → product-type passport); `aggregation
  {parentRefs, childRefs}` for physical containment (transformation stays
  an EPCIS TransformationEvent).
- **B2 — passport succession / lifecycle.** Optional `lifecycle {status,
  predecessorRefs, successorRefs, statusChangedAt}`, status enum
  `original` | `prepared-for-reuse` | `reused` | `repurposed` |
  `remanufactured` | `waste` | `recycled`. Spec §4.7 defines the
  normative revision (same subject, same passportId, append-only) versus
  successor (new passport for a changed subject, linked both ways)
  distinction, and which transitions produce which.
- **B3 — role-based field-level access tiers.** Optional `accessPolicy
  {defaultTier, fieldTiers[{path, tier}]}` with cumulative tiers `public` ⊂
  `legitimate-interest` ⊂ `authority`; JSON Pointer paths; longest-match
  tier resolution; identity/issuer/policy fields must stay public; API
  enforcement by OAuth2 scope with `withheldPaths`. Interaction with
  Level 3 signatures specified. Selective-disclosure formats (e.g. SD-JWT
  VC) named as a non-normative candidate only.
- **B4 — per-field applicability status.** Optional `fieldStatus[{path,
  status, basis, reviewBy}]`, status `required` | `optional` |
  `conditional` | `not-yet-applicable`, for obligations whose
  implementing/methodology acts are not yet adopted.
- **B5 — party details** (WP3 mapping D1): `party.address` (ISO 3166-1
  alpha-2 `countryCode`), `party.contactPoint {email, telephone, url}`;
  `role` gains `importer`, `authorised-representative`, `distributor`,
  `economic-operator`; passport-level `parties[]`.
- **B6 — declared unit** (D2): `lcaSummary.declaredUnit {quantity, unit,
  description}` and `carbonFootprintPerDeclaredUnit` (requires
  `declaredUnit`). `lcaSummary` now requires `carbonFootprintKgCo2ePerKg`
  **or** `carbonFootprintPerDeclaredUnit` (anyOf). This is a relaxation, so
  every v0.1 summary remains valid.
- **B7 — multi-indicator LCA** (D3): `lcaSummary.indicators[] {indicator,
  lifecycleStage, value, unit}` (EN 15804+A2 codes and modules recommended;
  battery stages permitted). Normative: module D MUST NOT reuse
  `netAvoidedKgCo2ePerKg`.
- **B8 — LCA provenance** (D4): `lcaSummary.studyRefs[]`,
  `lcaSummary.verifierParty`.
- **B9 — scoped recycled content** (D5): passport-level
  `recycledContentDetail[]` (recycled-content claim + `scope {material,
  componentRef, layer}`), e.g. per-metal battery shares, per-layer pipe
  content.
- B5–B9 came from the WP3 mapping tests (`mapping/README.md`). With B1–B4
  alone there were 37 class-(d) core gaps (batteries 15, construction 19,
  textiles 3).
- `recycledContent.feedstockSource` (optional, sector-neutral):
  `post-consumer-packaging` | `post-consumer-bottle` |
  `post-consumer-textile` | `post-industrial` | `post-industrial-textile` |
  `mixed` | `other`.
- `$defs` with descriptions for all new objects (`identityLevel`,
  `aggregation`, `lifecycle`, `accessTier`, `jsonPointer`, `accessPolicy`,
  `fieldStatusEntry`).
- JSON-LD context terms for all new fields, minted under
  `https://schema.materialspassport.org.uk/v0.2/`; `status`, `path` and
  `basis` are property-scoped so they do not collide with v0.1 terms.
- Specification `spec/ukmp-schema-v0.2.md` ("Changes in v0.2", §4.6–4.9
  normative clauses, §7 sector profiles rewritten from the WP3 findings:
  batteries import Battery Pass v1.2 as the profile; textiles reuse the
  plastics profile plus `feedstockSource`; construction is an overlay on
  EN ISO 23387 data templates). v0.1 spec kept for history.
- Examples: `example_battery_item_v02.jsonld` (item-level repurposed
  successor, LI-tier composition, Art 7 carbon footprint
  not-yet-applicable), `example_pipe_producttype_v02.jsonld`
  (construction product-type passport, recycled-HDPE non-pressure
  drainage pipe) and `example_pipe_batch_v02.jsonld` (batch using
  `productTypeRef`). All values illustrative.
- `tools/validate.py` v0.2 checks (warnings only, exit codes unchanged):
  JSON Pointer syntax and resolution for `accessPolicy.fieldTiers` and
  `fieldStatus`; `required`-but-absent fields; conflicting tiers; always-public fields restricted;
  lifecycle consistency (non-`original` status without
  `predecessorRefs`, `original` with predecessors, self-reference);
  item-level passports without `gs1:sgtin`/`alternativeId`;
  recycled-content arithmetic on every `recycledContentDetail` entry
  (error) and resolution of pointer-form `scope.componentRef` (warning);
  `identityLevel`/`subjectType` contradiction. Reports the effective
  identity level and lifecycle status. Root identifier `anyOf` failures
  now print a one-line message instead of the whole passport.
- `IMPLEMENTATION_STATUS.md` — per-conformance-level reference
  implementation coverage table (post-0.1.0; updated for v0.2).

### Fixed

- **`examples/example_passport.jsonld`: wrong chain-of-custody model.**
  The example describes mechanically recycled HDPE, but it declared
  `calculationMethod` / `chainOfCustodyModel` `mass-balance` while marking
  PPT in scope. It now declares `controlled-blending` / `segregated`. The
  87 % figure is still derived from the event genealogy, and step-level
  `ukmp:massBalanceDelta` is retained. Spec §4.3 adds a normative note
  separating weight reconciliation from the ISO 22095 mass-balance model,
  and an informative note on UK PPT from 1 Apr 2027: mass balance applies
  only to chemically recycled plastic, and pre-consumer content stops
  counting. `recycledFractionForPpt` (0.87) was already post-consumer only.
- `examples/example_passport.jsonld` `proof.verificationMethod` now points
  at the D2.1 key endpoint `/.well-known/ukmp/keys#2026-1`. Spec §6 names
  the endpoint.

- **JSON-LD context: passport-level terms were dropped on expansion.**
  `passportId`, `composition`, `recycledContent` and the other
  passport-level terms were defined only in a context scoped to the type
  term `MaterialPassport`, but passports declare
  `"type": "ukmp:MaterialPassport"` (a compact IRI), so the scoped context
  never applied. They are now also defined at the top level with the same
  IRIs. The JSON form of passports is unaffected.

### Changed

- Schema `$id` →
  `https://schema.materialspassport.org.uk/v0.2/material_passport.schema.json`.

- **`ukmp:LcaSummary`: `virginDisplacementFactor` replaced by two explicit
  fields.** The retired name implied a dimensionless substitution ratio
  while its definition carried kg CO₂e — a units-and-semantics collision
  between a gross virgin baseline and a net avoided figure.
  `virginBaselineKgCo2ePerKg` (gross virgin cradle-to-gate burden;
  polymer-specific, mandatory `source`, optional `assessmentBoundary`)
  and `netAvoidedKgCo2ePerKg` (computed as baseline minus the passport's
  own `carbonFootprintKgCo2ePerKg`; never defaulted) replace it. No
  normative default value is set; the 1.7 kg CO₂e/kg figure in the
  example passport is illustrative, with its WRAP-derived provenance
  stated. A dimensionless `substitutionFactor` (0–1) is reserved for a
  future revision.
- Spec §6 status note reworded as a standing convention; per-level
  reference-implementation coverage moved to `IMPLEMENTATION_STATUS.md`
  at the repository root.

- **§6 securing mechanisms: VC-JOSE enveloping proof (ES256/P-256) is now
  the primary securing**, with the embedded Data Integrity
  `ecdsa-jcs-2019` proof retained as a permitted alternative. Follows
  the CIRPASS-2 D4.1 / UNTP convergence on JOSE (M4 alignment
  checkpoint); the same P-256 key material serves both, so the change
  is cost-free before Level 3 issuance ships. Verifiers claiming
  Level 3 MUST accept both.
- `tools/validate.py` accepts JOSE-enveloped credentials (compact JWS):
  the payload is decoded and validated; the signature is indicated,
  not verified (unchanged honesty note).

- Alignment cheap acts (M4 note §3.1–3.3): `alternativeId.scheme`
  documents the EN 18219:2026 permitted schemes (`gs1-digital-link`,
  `iec-61406`, `did`, `doi`) as recommended, non-exclusive values;
  `ukmp:Party` gains optional `otherPartyId {scheme, value}` (LEI,
  Companies House, DUNS) alongside `gs1:gln`; stale "CIRPASS-2 DPP
  data model" references re-worded to CEN EN 18223:2026 + CIRPASS-2
  D4.1, and the §6 rationale now cites the live EU DPP registry
  (Implementing Regulation (EU) 2026/1778). Open issue 2 marked
  completed with the next re-diff trigger.

## [0.1.0] — 2026-08-11

Initial public draft, released for project steering review (M4).

### Added

- Specification v0.1 (`spec/ukmp-schema-v0.1.md`) — WP1 deliverable D1.2:
  layered model (L0 identity → L4 sector profiles), core vocabulary
  (`ukmp:MaterialPassport`, `ukmp:Composition`, `ukmp:RecycledContentClaim`,
  `ukmp:LcaSummary`, `ukmp:UkRegulatoryData`), GS1 EPCIS 2.0 event alignment,
  W3C Verifiable Credential trust envelope, conformance levels 1–3.
- JSON Schema 2020-12 validation schema
  (`schema/material_passport.schema.json`).
- JSON-LD core context (`schema/context.jsonld`) for the `ukmp:` namespace
  `https://schema.materialspassport.org.uk/v0.1/`.
- Plastics sector profile context (`schema/plastics-context.jsonld`) —
  polymer typing, form, colour, food-contact grade, additives. Normative in
  this release; validated in WP4.
- Worked examples: Level 3 VC-enveloped recycled-HDPE batch passport
  (`examples/example_passport.jsonld`) and minimal Level 1 self-declared
  passport (`examples/example_level1_minimal.jsonld`).
- CLI validator (`tools/validate.py`): JSON Schema validation,
  recycled-content fraction arithmetic, mass-balance reconciliation,
  conformance-level detection; CI workflow running it against all examples.
- Draft of the WP2 exchange API surface (`api/openapi-draft.md`).

### Known limitations

- The validator does not verify Level 3 cryptographic proofs (WP2 reference
  implementation scope); it flags unverified signatures explicitly.
- Namespace `schema.materialspassport.org.uk` is proposed, not yet registered
  (spec §10, open issue 1) — the published `@context` files in `schema/` are
  the normative copies until the namespace resolves.
- Battery, textile, and construction profiles are WP3 assessment scope, not
  included here.
