# Changelog

All notable changes to the UK Materials Passport Schema are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/) applied to the
schema namespace.

## [Unreleased]

### Changed

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

### Added

- `IMPLEMENTATION_STATUS.md` — per-conformance-level reference
  implementation coverage table.

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
