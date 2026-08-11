# UK Materials Passport Schema — Specification v0.1 (Draft)

**Project:** Interoperable Materials Passport Infrastructure for UK Circular Economy (Materials 4.0 Focus)
**Project number:** 10188380 · National Materials Innovation Programme Feasibility Studies
**Work package:** WP1 — Requirements & Schema Development (deliverable **D1.2 — JSON-LD schema v0.1**; supports D1.3 gap analysis)
**Lead:** Helix8 Ltd · Dr John Harrison (Technical Director)
**Status:** Draft for steering review · August 2026 (M4)
**Licence (on release):** Open source, permissive (MIT/Apache 2.0), per grant commitment

---

## 1. Purpose and scope

This document specifies the **UK Materials Passport Schema**: an open, JSON-LD data format for describing the composition, origin, processing history, recycled content, and environmental footprint of a material as it moves between organisations in a circular-economy supply chain.

The schema is the WP1 deliverable of project 10188380. It:

- **Extends the EU CIRPASS-2 framework** with practical data fields for UK recycling and manufacturing contexts (recycled-content verification, LCA integration, UK regulatory identifiers);
- **Serialises as JSON-LD aligned with GS1 EPCIS 2.0**, so that passport events are expressed in the same vocabulary enterprise systems already use for supply-chain visibility;
- **Is designed for exchange**, not for any single platform. Any conformant system — ERP, MES, traceability platform, regulatory reporting tool — can produce, consume, and verify a passport without reference to the system that created it.

Plastics/polymers are the validation sector (WP4, with Plaswire and Border Plastics). The schema core is deliberately sector-neutral; batteries, textiles, and construction are addressed through the extension mechanism assessed in WP3.

## 2. Design principles

1. **Extend, don't replace.** Where an established standard defines a concept, we reference it (GS1 EPCIS 2.0 CBV, CIRPASS-2 DPP data model, W3C VC v2.0, UN/CEFACT). New terms are introduced only for genuinely UK-specific or gap fields.
2. **Layered, so adopters can start small.** A passport is useful at the data layer alone; verification and exchange layers are additive. An SME can emit Level 1 (Core) passports from a spreadsheet export; a platform can emit Level 3 (Linked & Verified) passports. Both interoperate.
3. **Events are the source of truth.** A passport is a *view* derived from a chain of EPCIS events, not a hand-assembled document. This is what makes claims auditable rather than asserted.
4. **Verification is standards-based.** The trust envelope is a W3C Verifiable Credential (Data Model v2.0). No proprietary verification protocol; any off-the-shelf VC verifier works.
5. **Sector extension by profile, not by fork.** Sector-specific fields live in named extension contexts (`ukmp-plastics`, `ukmp-batteries`, …) layered over one core.

## 3. Layered model

| Layer | Name | Standard basis | What it carries |
|---|---|---|---|
| L0 | **Identity** | GS1 keys (GTIN, GLN, SSCC/LGTIN), GS1 Digital Link | Who/what/where identifiers; QR resolution to the passport |
| L1 | **Events** | GS1 EPCIS 2.0 (JSON-LD binding) | Commissioning, transformation, aggregation, shipping events — the material journey |
| L2 | **Passport content** | CIRPASS-2 DPP data model + UK extension (this spec) | Composition, recycled content, processing summary, LCA/carbon, regulatory codes |
| L3 | **Trust envelope** | W3C Verifiable Credentials v2.0, Data Integrity proof | Issuer identity, signature, revocation status, audit-trail linkage |
| L4 | **Sector profiles** | This spec's extension mechanism | Plastics profile (normative here); batteries/textiles/construction (WP3 assessment) |

A conformant passport MUST implement L0 + L2. L1 linkage and L3 proofs define the higher conformance levels (§8).

## 4. Core vocabulary

Namespace: `https://schema.materialspassport.org.uk/v0.1/` (prefix `ukmp:`). Terms are defined in a published JSON-LD `@context`. Core classes:

### 4.1 `ukmp:MaterialPassport`
The root object (carried as `credentialSubject` at Level 3).

| Field | Type | Req | Notes |
|---|---|---|---|
| `passportId` | URI | ✔ | Globally unique; resolvable via GS1 Digital Link |
| `subjectType` | enum | ✔ | `MaterialBatch` \| `Product` \| `Component` |
| `gs1:gtin` / `gs1:lgtin` | string | ✔* | GS1 identifier of the batch/product (*or `alternativeId` with scheme) |
| `issuerParty` | `ukmp:Party` | ✔ | Organisation issuing the passport (GLN + name) |
| `issueDate` / `lastUpdated` | ISO 8601 | ✔ | |
| `composition` | `ukmp:Composition` | ✔ | §4.2 |
| `recycledContent` | `ukmp:RecycledContentClaim` | ✔ | §4.3 — the UK-extension centrepiece |
| `processingHistory` | array of EPCIS event refs | L2+ | §5 |
| `environmentalFootprint` | `ukmp:LcaSummary` | rec | §4.4 |
| `ukRegulatory` | `ukmp:UkRegulatoryData` | rec | §4.5 |
| `sectorProfile` | URI | rec | e.g. `ukmp-plastics:v0.1` |

### 4.2 `ukmp:Composition`
- `materialFamily` (enum: polymer, metal, glass, fibre, mineral, composite, other)
- `substances[]` — each: `name`, CAS or EC number where applicable, `massFraction` (0–1), `svhcFlag` (REACH substances of very high concern)
- Plastics profile adds: `polymerType` (PET, HDPE, LDPE, PP, PS, PVC, other — ISO 1043 codes), `colour`, `form` (bale, flake, pellet, regrind), `additives[]`, `foodContactGrade` (bool + assessment ref)

### 4.3 `ukmp:RecycledContentClaim` — recycled-content verification (UK extension)
CIRPASS-2 carries a recycled-content percentage; UK practice (and PPT liability) requires knowing **how the number was derived and who stands behind it**. This structure is the project's main extension:

| Field | Type | Notes |
|---|---|---|
| `preConsumerFraction` | 0–1 | ISO 14021 definitions |
| `postConsumerFraction` | 0–1 | " |
| `totalRecycledFraction` | 0–1 | MUST equal sum of the above |
| `calculationMethod` | enum | `mass-balance` \| `batch-segregation` \| `controlled-blending` \| `declared` |
| `chainOfCustodyModel` | enum | per ISO 22095: `identity-preserved`, `segregated`, `mass-balance`, `book-and-claim` |
| `evidenceType` | enum | `epcis-event-chain` \| `third-party-certificate` \| `supplier-declaration` |
| `evidenceRefs[]` | URIs | EPCIS event IDs, certificate URIs (e.g. EuCertPlast, RecyClass), or declaration docs |
| `verificationStatus` | enum | `self-declared` \| `evidence-linked` \| `independently-verified` |
| `verifierParty` | `ukmp:Party` | Required when `independently-verified` |

### 4.4 `ukmp:LcaSummary` — LCA integration (UK extension)
Designed to carry results from any LCA tool rather than embed a methodology:
- `carbonFootprintKgCo2ePerKg` (value + `assessmentBoundary`: cradle-to-gate | gate-to-gate | cradle-to-grave)
- `methodology` (e.g. ISO 14067, PEF, GHG Protocol product standard) + `characterisationFactors` version
- `dataQualityRating` (1–5, PEF DQR-style), `primaryDataFraction` (0–1)
- `energySource` breakdown (grid kWh, on-site renewables kWh) — populated automatically where site metering exists
- `virginDisplacementFactor` — kg CO₂e avoided per kg vs. virgin equivalent, with source (default UK value 1.7 kg CO₂e/kg for polymers, per project impact model; overridable with tenant-specific LCA)

### 4.5 `ukmp:UkRegulatoryData` — UK context fields
- `ewcCode` — European Waste Catalogue / List of Waste code while material is waste
- `endOfWasteStatus` — bool + basis (e.g. quality protocol / individual assessment), the point where waste becomes material
- `wasteHierarchyPosition` — preparation-for-reuse | recycling | recovery
- `recoveryCode` — R-codes (e.g. R3)
- `pptStatus` — UK Plastic Packaging Tax: `inScope` (bool), `recycledFractionForPpt` (0–1, 30 % threshold relevance), `evidenceRef`
- `eprCategory` — packaging EPR material category (UK Environment Act)
- `permits[]` — environmental permit / waste carrier registration numbers of processing sites
- `euMapping` — where the same batch is exported: ESPR delegated-act category, PPWR recyclability grade, so one passport serves both UK and EU reporting

## 5. GS1 EPCIS 2.0 alignment (L1)

Processing history is expressed as standard EPCIS 2.0 events (JSON-LD binding), so existing EPCIS repositories and enterprise visibility systems can store and query passport events with no schema changes.

| Material journey step | EPCIS event type | CBV `bizStep` |
|---|---|---|
| Goods-in / intake of feedstock | ObjectEvent (ADD) | `receiving` |
| Sorting / grading | ObjectEvent (OBSERVE) | `inspecting` |
| Shredding, granulation, washing, extrusion | TransformationEvent | `transforming` |
| Blending batches | TransformationEvent (multi-input) | `transforming` |
| Bagging / packing outputs | AggregationEvent | `packing` |
| Despatch to customer | ObjectEvent (OBSERVE) | `shipping` |
| QC sampling / lab verification | ObjectEvent (OBSERVE) | `inspecting` + `ukmp:verificationExtension` |

Two project-defined EPCIS extension fields (permitted by EPCIS 2.0):
- `ukmp:massBalanceDelta` on TransformationEvents — input/output/waste masses enabling automated mass-balance reconciliation for §4.3;
- `ukmp:verificationExtension` on inspection events — instrument type, measured polymer class, contamination level (the data-capture side that the MateriAI sensing project generates; this project makes it exchangeable).

**Traversability requirement:** every TransformationEvent MUST list input and output EPCs/LGTINs, so a verifier can walk the genealogy from any output batch back to feedstock intakes. Recycled-content claims at `evidenceType: epcis-event-chain` are recomputable from this walk — that is the interoperability dividend.

## 6. Trust envelope — W3C Verifiable Credential (L3)

At conformance Level 3 the passport is issued as a **W3C Verifiable Credential, Data Model v2.0**:

- `@context`: `https://www.w3.org/ns/credentials/v2` + GS1 EPCIS context + `ukmp` context
- `type`: `["VerifiableCredential", "MaterialPassportCredential"]`
- `issuer`: HTTPS URL identifying the issuing organisation (optionally `did:web`); public keys published at `/.well-known/` per the API spec (WP2)
- `credentialSubject`: the `ukmp:MaterialPassport` object (§4)
- `proof`: Data Integrity proof, cryptosuite `ecdsa-jcs-2019` (ECDSA P-256 over JCS/RFC 8785 canonicalised content)
- `credentialStatus`: W3C Bitstring Status List entry — enables batch recall/withdrawal without breaking previously distributed copies
- External time-anchoring (attestation of existence) is **pluggable and out of schema scope** — the schema carries `evidenceRefs` to anchoring receipts; the anchoring provider model is specified in the WP2 API documentation.

Rationale: the EU DPP implementation direction (JRC methodology work, CIRPASS-2 pilots, W3C VC-for-GS1 draft) treats VCs as the natural expression of verifiable product data. Adopting the VC envelope now means UK passports will register cleanly with the planned EU DPP registry rather than needing wrapping later.

**Honest status note for steering:** the reference implementation currently issues Level 1–2 passports (`verificationStatus: self-declared` / `evidence-linked`). Level 3 signing (KMS-held per-organisation ECDSA keys) is specified, scheduled in the WP2 reference-implementation backlog, and is a documented gap, not a claimed capability.

## 7. Sector extension mechanism (L4 / WP3 input)

A sector profile is: (a) a named JSON-LD context adding fields, (b) enumeration restrictions on core fields, (c) additional EPCIS bizStep mappings. The core never changes per sector.

- **`ukmp-plastics` v0.1** (normative in this release): polymer typing, food-contact, PPT fields — validated in WP4.
- **`ukmp-batteries`** (WP3 assessment): would add EU Battery Regulation fields (battery chemistry, state-of-health, carbon-footprint class). Battery passports are already regulated — strong candidate for the first extension.
- **`ukmp-textiles`** (WP3): fibre composition, ESPR textiles delegated act (expected first mandated DPP category, 2027).
- **`ukmp-construction`** (WP3): material banks / BAMB alignment, declarations of performance.

WP3's gap analysis will report whether each sector fits this mechanism or forces core changes — a core change requirement would itself be a key feasibility finding.

## 8. Conformance levels

| Level | Name | Requires | Typical adopter |
|---|---|---|---|
| 1 | **Core** | L0 identity + L2 content, `verificationStatus: self-declared` | SME starting out; export from existing ERP |
| 2 | **Evidence-linked** | Level 1 + L1 EPCIS event chain traversable for every claim | Traceability platforms (reference implementation today) |
| 3 | **Verified** | Level 2 + L3 VC envelope with valid proof + status list | Platforms serving regulated/EU-exporting customers |

Levels are per-passport, machine-detectable, and printed on the human-readable passport view — adoption can be incremental without fragmenting the ecosystem.

## 9. Worked example

See `example_passport.jsonld` (companion file): a Level 3 passport for a 1-tonne batch of post-consumer recycled HDPE pellet, from bale intake through sort, shred, wash, extrude, blend, bag, despatch — 9 EPCIS events, mass-balance-derived 87 % post-consumer content, cradle-to-gate 0.42 kg CO₂e/kg, PPT-in-scope with evidence, VC envelope shown with proof block structure (signature values illustrative).
A machine-validation schema is provided in `material_passport.schema.json` (JSON Schema 2020-12).

## 10. Open issues for steering discussion (M4)

1. **Namespace home** — `schema.materialspassport.org.uk` proposed; needs registration decision and a neutral governance statement so the namespace outlives Helix8 stewardship (open-ecosystem commitment).
2. **CIRPASS-2 tracking** — alignment checkpoint due this month (M4, per risk register): re-diff against latest CIRPASS-2 data-model draft before schema freeze at M5.
3. **PPT evidence granularity** — HMRC guidance accepts mass-balance for PPT in constrained cases; validation partners to confirm the evidence granularity their auditors actually request (WP1 workshop follow-up).
4. **Digital Link resolver** — single national resolver vs. per-issuer resolvers; affects the API spec (WP2) more than the schema, decision needed by M5.
5. **Level 3 key custody for SMEs** — smaller adopters won't run KMS; does the ecosystem need a hosted signing service, and is that a commercial (post-project) offering? Feeds exploitation plan.

---

*Companion files: `example_passport.jsonld`, `material_passport.schema.json`, architecture pack `NMIP_Architecture.md`, diagrams 01–03.*
