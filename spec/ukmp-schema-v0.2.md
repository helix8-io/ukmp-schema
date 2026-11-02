# UK Materials Passport Schema — Specification v0.2 (Draft)

**Project:** Interoperable Materials Passport Infrastructure for UK Circular Economy (Materials 4.0 Focus)
**Project number:** 10188380 · National Materials Innovation Programme Feasibility Studies
**Work package:** WP1 — Requirements & Schema Development (deliverable **D1.2 — JSON-LD schema**, revision v0.2), incorporating the WP3 sector gap analysis
**Lead:** Helix8 Ltd · Dr John Harrison (Technical Director)
**Status:** Draft for steering review · November 2026 (M7). Supersedes v0.1 (`spec/ukmp-schema-v0.1.md`, kept for history).
**Licence (on release):** Open source, permissive (MIT/Apache 2.0), per grant commitment

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be interpreted as described in RFC 2119 / RFC 8174 when, and only when, they appear in capitals.

---

## Changes in v0.2

v0.2 is **strictly additive** over v0.1: every field, enumeration value and constraint of v0.1 is retained unchanged, no field becomes required, and every v0.1-valid passport is v0.2-valid (checked in CI against the v0.1 examples).

The WP3 sector gap analysis (batteries, textiles, construction) asked whether each sector fits the core-plus-profile mechanism of §7 or forces core changes. Its finding: no sector forced a *breaking* core change, but four sector-neutral needs recurred across sectors and belong in the core rather than in any one profile. These are the **baseline core extensions B1–B4**:

| Ext. | Name | New fields | Driven by | Section |
|---|---|---|---|---|
| **B1** | Multi-level identity | `identityLevel`, `gs1:sgtin`, `productTypeRef`, `aggregation`; `subjectType` gains `ProductType`, `Item` | Batteries (item-level, Reg (EU) 2023/1542 Art 77(3)); construction (product-type level, Reg (EU) 2024/3110) | §4.6 |
| **B2** | Passport succession / lifecycle | `lifecycle {status, predecessorRefs, successorRefs, statusChangedAt}` | Batteries (new linked passport after repurposing, Art 77(7)); reuse in all sectors | §4.7 |
| **B3** | Role-based access tiers (field level) | `accessPolicy {defaultTier, fieldTiers[]}` | Batteries (Annex XIII public / legitimate-interest tiers); textiles (JRC preparatory-study tiers) | §4.8 |
| **B4** | Per-field applicability status | `fieldStatus[] {path, status, basis, reviewBy}` | All three: carbon-footprint, recycled-content and access-rights acts not yet adopted | §4.9 |
| **B5** | Party details and multiple parties | `party.address`, `party.contactPoint`; `role` gains `importer`, `authorised-representative`, `distributor`, `economic-operator`; passport-level `parties[]` | All three: manufacturer / importer / authorised-representative identity and contact | §4.10 |
| **B6** | Declared / functional unit | `lcaSummary.declaredUnit`, `lcaSummary.carbonFootprintPerDeclaredUnit` | Batteries (kg CO₂e per kWh); construction (per declared unit, e.g. 1 m); textiles (PEF functional unit) | §4.11 |
| **B7** | Multi-indicator, per-stage LCA | `lcaSummary.indicators[] {indicator, lifecycleStage, value, unit}` | Construction (EN 15804+A2 indicators by module, incl. C and D); batteries (stage contributions); textiles (PEF categories) | §4.11 |
| **B8** | LCA study provenance | `lcaSummary.studyRefs[]`, `lcaSummary.verifierParty` | Batteries (link to public CF study); textiles (calculation parameters); construction (EPD verification) | §4.11 |
| **B9** | Scoped recycled content | passport-level `recycledContentDetail[]` = claim + `scope {material, componentRef, layer}` | Batteries (pre/post-consumer Co, Li, Ni, Pb shares, Art 8); construction (per layer of multilayer pipe) | §4.12 |

**Where B5–B9 came from.** B1–B4 were proposed from the WP3 desk research. B5–B9 were added after the WP3 **mapping tests** (`mapping/README.md`), which classified every attribute of Battery Pass v1.2 (82 in scope), a construction pilot (62, recycled plastic drainage pipe) and a textiles pilot (26, JRC proposal). With B1–B4 alone, 37 attributes — batteries 15, construction 19, textiles 3 — fell into class (d): the concept is already owned by a core class (`ukmp:Party`, `ukmp:LcaSummary`, `ukmp:RecycledContentClaim`), but the core shape could not carry it, and a profile-level duplicate would fork the core. These reduce to five distinct core changes, D1–D5, implemented here as B5–B9. All five are optional and additive. The one relaxation (`lcaSummary` now needs a per-kg **or** a per-declared-unit footprint) only admits more passports, never fewer.

Also added (sector-neutral, optional): **`recycledContent.feedstockSource`** (§4.3) — origin class of recycled feedstock, needed to separate bottle, packaging and textile feedstock.

Corrected in v0.2: the worked example `example_passport.jsonld` described mechanically recycled HDPE but declared `calculationMethod` and `chainOfCustodyModel` as `mass-balance`. It now declares `controlled-blending` / `segregated`. §4.3 adds a normative note separating step-level `ukmp:massBalanceDelta` weight reconciliation from the ISO 22095 mass-balance chain-of-custody model, and an informative note on the UK Plastic Packaging Tax changes from 1 April 2027.

Other v0.2 changes:

- Schema `$id` is `https://schema.materialspassport.org.uk/v0.2/material_passport.schema.json`. The namespace prefix stays `ukmp:`; existing terms keep their v0.1 IRIs, new terms are minted under `https://schema.materialspassport.org.uk/v0.2/`.
- **JSON-LD context fix.** In v0.1 the passport-level terms (`passportId`, `composition`, `recycledContent`, …) were defined only inside a type-scoped context keyed on the term `MaterialPassport`. Passports write `"type": "ukmp:MaterialPassport"` (a compact IRI, not that term), so the scoped context never applied and those properties were silently dropped on JSON-LD expansion. v0.2 also defines them at the top level of the context, with the **same IRIs** — the JSON form of passports is unchanged; RDF consumers now see the data they always should have.
- §7 sector profiles rewritten around the WP3 findings; §10 open issues updated.
- Exchange API (WP2 deliverable D2.1) is now specified as OpenAPI 3.1 in `api/openapi.yaml`, including the revision/successor and tier-scoped read operations that B2 and B3 rely on.

---

## 1. Purpose and scope

This document specifies the **UK Materials Passport Schema**: an open, JSON-LD data format for describing the composition, origin, processing history, recycled content, and environmental footprint of a material or product as it moves between organisations in a circular-economy supply chain.

The schema is the WP1 deliverable of project 10188380. It:

- **Extends the European DPP framework** — CEN EN 18223:2026 (DPP system interoperability) and the CIRPASS-2 D4.1 reference architecture (June 2026), informed by UNTP — with practical data fields for UK recycling and manufacturing contexts (recycled-content verification, LCA integration, UK regulatory identifiers);
- **Serialises as JSON-LD aligned with GS1 EPCIS 2.0**, so that passport events are expressed in the same vocabulary enterprise systems already use for supply-chain visibility;
- **Is designed for exchange**, not for any single platform. Any conformant system — ERP, MES, traceability platform, regulatory reporting tool — can produce, consume, and verify a passport without reference to the system that created it.

Plastics/polymers are the validation sector (WP4, with Plaswire and Border Plastics). The schema core is deliberately sector-neutral; batteries, textiles, and construction are addressed through the extension mechanism assessed in WP3 (§7).

## 2. Design principles

1. **Extend, don't replace.** Where an established standard defines a concept, we reference it (GS1 EPCIS 2.0 CBV, CEN EN 18223:2026, CIRPASS-2 D4.1, W3C VC v2.0, UN/CEFACT UNTP). New terms are introduced only for genuinely UK-specific or gap fields. v0.2 applies this to sector data models too: where a sector already has an open data model (batteries: Battery Pass), the profile imports it rather than competing with it.
2. **Layered, so adopters can start small.** A passport is useful at the data layer alone; verification and exchange layers are additive. An SME can emit Level 1 (Core) passports from a spreadsheet export; a platform can emit Level 3 (Linked & Verified) passports. Both interoperate.
3. **Events are the source of truth.** A passport is a *view* derived from a chain of EPCIS events, not a hand-assembled document. This is what makes claims auditable rather than asserted.
4. **Verification is standards-based.** The trust envelope is a W3C Verifiable Credential (Data Model v2.0). No proprietary verification protocol; any off-the-shelf VC verifier works.
5. **Sector extension by profile, not by fork.** Sector-specific fields live in named extension contexts (`ukmp-plastics`, `ukmp-batteries`, …) layered over one core. Needs shared by several sectors are promoted to the core, additively (B1–B9).
6. **Say what is not yet known.** Where an obligation depends on a legal act that has not been adopted, the passport records that explicitly (B4) instead of leaving a silent gap or inventing a value.

## 3. Layered model

| Layer | Name | Standard basis | What it carries |
|---|---|---|---|
| L0 | **Identity** | GS1 keys (GTIN, GLN, SSCC/LGTIN, SGTIN), GS1 Digital Link, EN 18219:2026 | Who/what/where identifiers at product-type, batch or item level (B1); QR resolution to the passport |
| L1 | **Events** | GS1 EPCIS 2.0 (JSON-LD binding) | Commissioning, transformation, aggregation, shipping events — the material journey |
| L2 | **Passport content** | CEN EN 18223:2026 + CIRPASS-2 D4.1 alignment, + UK extension (this spec) | Composition, recycled content, processing summary, LCA/carbon, regulatory codes, lifecycle (B2), access policy (B3), applicability status (B4) |
| L3 | **Trust envelope** | W3C Verifiable Credentials v2.0; VC-JOSE (primary) or Data Integrity proof | Issuer identity, signature, revocation status, audit-trail linkage |
| L4 | **Sector profiles** | This spec's extension mechanism | Plastics profile (normative); batteries / textiles / construction (WP3 findings, §7) |

A conformant passport MUST implement L0 + L2. L1 linkage and L3 proofs define the higher conformance levels (§8).

## 4. Core vocabulary

Namespace: `https://schema.materialspassport.org.uk/v0.1/` (prefix `ukmp:`) for v0.1 terms; terms added in v0.2 are minted under `https://schema.materialspassport.org.uk/v0.2/`. All terms are defined in the published JSON-LD `@context` (`schema/context.jsonld`). Core classes:

### 4.1 `ukmp:MaterialPassport`
The root object (carried as `credentialSubject` at Level 3).

| Field | Type | Req | Notes |
|---|---|---|---|
| `passportId` | URI | ✔ | Globally unique; resolvable via GS1 Digital Link |
| `subjectType` | enum | ✔ | `MaterialBatch` \| `Product` \| `Component` \| `ProductType` (v0.2) \| `Item` (v0.2) |
| `identityLevel` | enum | — | v0.2, B1: `productType` \| `batch` \| `item` (§4.6) |
| `gs1:gtin` / `gs1:lgtin` / `gs1:sgtin` | string | ✔* | GS1 identifier of the product type / batch / serialised item (`gs1:sgtin` added in v0.2, §4.6) (*or `alternativeId` with scheme — the EN 18219:2026 permitted schemes `gs1-digital-link`, `iec-61406`, `did` and `doi` are recommended for EU DPP registry registrability; other schemes remain valid) |
| `productTypeRef` | URI | — | v0.2, B1: passport of the product type this batch/item instantiates |
| `aggregation` | object | — | v0.2, B1: `{parentRefs[], childRefs[]}` containment links |
| `issuerParty` | `ukmp:Party` | ✔ | Organisation issuing the passport (GLN + name; optionally `otherPartyId {scheme, value}` — e.g. GLEIF LEI, Companies House number, DUNS — per EN 18219 operator-identifier schemes) |
| `issueDate` / `lastUpdated` | ISO 8601 | ✔ | |
| `composition` | `ukmp:Composition` | ✔ | §4.2 |
| `recycledContent` | `ukmp:RecycledContentClaim` | ✔ | §4.3 — the UK-extension centrepiece |
| `processingHistory` | array of EPCIS event refs | L2+ | §5 |
| `environmentalFootprint` | `ukmp:LcaSummary` | rec | §4.4 |
| `ukRegulatory` | `ukmp:UkRegulatoryData` | rec | §4.5 |
| `sectorProfile` | URI | rec | e.g. `ukmp-plastics:v0.1` |
| `lifecycle` | object | — | v0.2, B2 (§4.7) |
| `accessPolicy` | object | — | v0.2, B3 (§4.8) |
| `fieldStatus` | array | — | v0.2, B4 (§4.9) |
| `parties` | array of `ukmp:Party` | — | v0.2, B5: non-issuer parties (§4.10) |
| `recycledContentDetail` | array | — | v0.2, B9: scoped recycled-content claims (§4.12) |

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
| `feedstockSource` | enum | **v0.2, optional.** `post-consumer-packaging` \| `post-consumer-bottle` \| `post-consumer-textile` \| `post-industrial` \| `post-industrial-textile` \| `mixed` \| `other` |

`feedstockSource` records the origin class of the recycled input. It is sector-neutral and lives in the core because the same distinction matters across profiles: bottle-derived versus textile-derived recycled polyester (textiles), and packaging-derived versus industrial-scrap recyclate (plastics, construction pipe). It complements, and does not replace, the ISO 14021 pre/post-consumer split. Issuers SHOULD use `mixed` where more than one class contributes materially, and MAY detail the split in a sector profile.

**Process reconciliation is not a mass-balance chain of custody (normative, v0.2).** Two things in this specification are called "mass balance" and they MUST NOT be confused:

- `ukmp:massBalanceDelta` (§5) is **step-level weight reconciliation**: on one TransformationEvent, input mass = output mass + waste. It shows that the event chain is physically consistent. It says nothing about how recycled content is attributed to outputs.
- `chainOfCustodyModel: mass-balance` (and `calculationMethod: mass-balance`) is the **ISO 22095 (Part 2) allocation model**: recycled and non-recycled inputs are mixed, and recycled content is *allocated* to outputs by bookkeeping over a defined period and system boundary, so a given output need not physically contain the claimed share.

A claim MUST declare `chainOfCustodyModel: mass-balance` only when the claimed fraction is allocated in that sense. Where recycled input is kept physically separate up to a measured blend, and the fraction is computed from the weights in the event genealogy (as in `examples/example_passport.jsonld`: 890 kg segregated PCR + 130 kg virgin carrier ⇒ 87 %), the claim is `calculationMethod: controlled-blending` with `chainOfCustodyModel: segregated`, even though every event carries a `ukmp:massBalanceDelta`.

*Informative — UK Plastic Packaging Tax (PPT).* From 1 April 2027 HMRC permits a mass-balance approach for PPT **only for chemically recycled plastic**, and **pre-consumer plastic no longer counts** towards the 30 % recycled-content threshold (see [gov.uk: Plastic Packaging Tax — mass balance approach and removal of pre-consumer plastic](https://www.gov.uk/government/publications/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic)). For PPT purposes, `ukRegulatory.pptStatus.recycledFractionForPpt` SHOULD therefore be computed from **post-consumer** content only, and a mechanically recycled claim SHOULD NOT rely on a mass-balance chain of custody. This specification does not encode tax rules. Issuers remain responsible for applying HMRC guidance in force at the time.

### 4.4 `ukmp:LcaSummary` — LCA integration (UK extension)
Designed to carry results from any LCA tool rather than embed a methodology:
- `carbonFootprintKgCo2ePerKg` (value + `assessmentBoundary`: cradle-to-gate | gate-to-gate | cradle-to-grave)
- `methodology` (e.g. ISO 14067, PEF, GHG Protocol product standard, EN 15804+A2) + `characterisationFactors` version
- `dataQualityRating` (1–5, PEF DQR-style), `primaryDataFraction` (0–1)
- `energySource` breakdown (grid kWh, on-site renewables kWh) — populated automatically where site metering exists
- `virginBaselineKgCo2ePerKg` — the **gross** virgin cradle-to-gate burden for the equivalent material (value + mandatory `source`, optional `assessmentBoundary`). Material-specific and sourced; this specification deliberately sets **no normative default** — a baseline without LCA provenance is an asserted-not-checkable claim.
- `netAvoidedKgCo2ePerKg` — the **net** avoided figure, computed as `virginBaselineKgCo2ePerKg.value` minus this passport's own `carbonFootprintKgCo2ePerKg`. Never defaulted and never carried without the baseline it derives from.

Where a sector's carbon-footprint obligation is not yet applicable (e.g. batteries, Reg (EU) 2023/1542 Art 7, pending the methodology delegated act), the issuer records the status with `fieldStatus` (§4.9). Any value the issuer publishes voluntarily MUST NOT be presented as the regulatory declaration.

v0.2 extends `ukmp:LcaSummary` with a declared unit, multiple indicators and study provenance (B6–B8, §4.11). From v0.2 an `LcaSummary` MUST carry at least one of `carbonFootprintKgCo2ePerKg` or `carbonFootprintPerDeclaredUnit` (v0.1 required the former; every v0.1 summary still satisfies this).

### 4.5 `ukmp:UkRegulatoryData` — UK context fields
- `ewcCode` — European Waste Catalogue / List of Waste code while material is waste
- `endOfWasteStatus` — bool + basis (e.g. quality protocol / individual assessment), the point where waste becomes material
- `wasteHierarchyPosition` — preparation-for-reuse | recycling | recovery
- `recoveryCode` — R-codes (e.g. R3)
- `pptStatus` — UK Plastic Packaging Tax: `inScope` (bool), `recycledFractionForPpt` (0–1, 30 % threshold relevance), `evidenceRef`
- `eprCategory` — packaging EPR material category (UK Environment Act)
- `permits[]` — environmental permit / waste carrier registration numbers of processing sites
- `euMapping` — where the same batch is exported: ESPR delegated-act category, PPWR recyclability grade, so one passport serves both UK and EU reporting

### 4.6 Multi-level identity (B1, v0.2)

Regulated sectors disagree about *what* a passport describes: the EU battery passport is per **item** (Reg (EU) 2023/1542 Art 77(3)); the construction-products DPP is per **product type** (Reg (EU) 2024/3110); recycled-content claims and chain of custody are per **batch**. EN 18219:2026 accordingly permits identifiers at model, batch or item level. v0.2 makes the level explicit.

**`identityLevel`** — `productType` | `batch` | `item`.

- A `productType` passport describes properties invariant across all instances of a model (declared performance, type-level composition specification, type GTIN). It MUST NOT carry instance-specific measurements as if they applied to every instance.
- A `batch` passport describes one production or processing lot (the v0.1 default case).
- An `item` passport describes one serialised physical unit.
- If `identityLevel` is absent, consumers MUST interpret it from `subjectType`: `MaterialBatch` ⇒ `batch`, `ProductType` ⇒ `productType`, `Item` ⇒ `item`; `Product` and `Component` leave the level unspecified (v0.1 behaviour). If both are present they SHOULD agree; the validator warns on contradiction.

**`gs1:sgtin`** — serialised GTIN, written `<GTIN>.<serial>` (the dotted convention v0.1 already uses for `gs1:lgtin`). Schema pattern: `^[0-9]{8,14}\.[!-~]{1,20}$` — the serial is 1–20 printable ASCII characters, a superset of the GS1 AI (21) character set 82. Issuers SHOULD restrict serials to CSET 82; v0.2 does not enforce CSET 82 or the GTIN check digit. `gs1:sgtin` satisfies the core identifier requirement alongside `gs1:gtin`, `gs1:lgtin` and `alternativeId`. An item-level passport SHOULD carry `gs1:sgtin` or an `alternativeId` whose scheme serialises items (e.g. `iec-61406`, `gs1-digital-link` with AI 21); the validator warns otherwise.

**`productTypeRef`** — the `passportId` of the product-type passport that a batch or item passport instantiates. Type-level data is inherited **by reference, not copied**. A consumer MAY dereference it to obtain type-level data. Instance passports MUST NOT contradict the declared values of their product type; where an instance carries its own value for a property (e.g. a batch's measured recycled content against a type's declared minimum), the instance value applies to that instance.

**`aggregation`** — `{ parentRefs: [uri], childRefs: [uri] }`: physical **containment** between passported subjects (cell or module serials *contained in* a pack; a pack *contained in* a stationary storage system). Aggregation does not change the material. **Transformation is not aggregation:** a pack shredded to a black-mass lot, or flake extruded to pellet, MUST be expressed as an EPCIS `TransformationEvent` (§5), not as `aggregation`.

### 4.7 Passport succession and lifecycle (B2, v0.2)

**`lifecycle`** — `{ status, predecessorRefs[], successorRefs[], statusChangedAt }`.

`status`: `original` | `prepared-for-reuse` | `reused` | `repurposed` | `remanufactured` | `waste` | `recycled`. Absent `lifecycle` (or absent `status`) means `original`.

**Revision versus successor (normative).** Two different things change a passport, and they MUST NOT be conflated:

| | **Revision** | **Successor** |
|---|---|---|
| What changes | The *record* — a correction, an update, a new event, a status change of the same subject | The *subject* — it has been transformed into something placed on the market again, usually by a different responsible operator |
| `passportId` | Unchanged | New |
| History | Append-only: earlier revisions are retained and retrievable; `lastUpdated` advances | The predecessor passport is retained unchanged except for the addition of `successorRefs` |
| Links | — | Successor's `lifecycle.predecessorRefs` MUST list the predecessor(s); predecessor's `lifecycle.successorRefs` SHOULD list the successor(s) |
| Exchange API (D2.1) | `GET /passports/{id}/revisions` | `POST /passports/{id}/successors` |

Rules:

1. A transition to `prepared-for-reuse`, `repurposed` or `remanufactured` creates a **successor** passport. This mirrors Reg (EU) 2023/1542 Art 77(7), under which a repurposed, remanufactured or prepared-for-reuse battery receives a new passport linked to the original, with responsibility transferring to the operator who places it on the market.
2. A transition to `reused` (same purpose, no transformation) or to `waste` is a **revision** of the existing passport, unless a new operator places the subject on the market under its own responsibility, in which case it is a successor.
3. `recycled` is **terminal**: the passport is revised one final time to status `recycled` and accepts no further revisions except corrections. Recovered materials receive new batch passports whose provenance is the EPCIS `TransformationEvent` chain (§5); they are **not** successors of the recycled item, because succession links one subject's identity over time and recycling ends that identity. (For batteries, Art 77(8): the passport ceases to exist once the battery is recycled.)
4. A passport with `status` other than `original` SHOULD carry at least one `predecessorRefs` entry (validator warning). A passport MUST NOT list its own `passportId` as predecessor or successor — that is a revision.
5. `predecessorRefs` is authoritative; `successorRefs` is best-effort, because the predecessor may be held by another issuer who must be notified (D2.1 webhook `passport.succeeded`). A consumer that needs the full chain SHOULD walk predecessor links.
6. `statusChangedAt` SHOULD be set whenever `status` is not `original`.

### 4.8 Role-based access tiers (B3, v0.2)

Batteries (Annex XIII) and the draft textiles requirements (JRC preparatory study) both define data that is public, data restricted to persons with a **legitimate interest** (repairers, repurposers, recyclers), and data for **authorities** (market surveillance, notified bodies, the Commission). v0.2 lets a passport declare, field by field, which tier each field belongs to.

**`accessPolicy`** — `{ defaultTier, fieldTiers: [{ path, tier }] }`.

- Tiers: `public` | `legitimate-interest` | `authority`. Tiers are **cumulative**: a reader entitled to `legitimate-interest` also sees `public`; `authority` sees everything.
- `defaultTier` (default `public`) applies to every field not covered by a `fieldTiers` entry.
- `path` is an RFC 6901 **JSON Pointer** evaluated against the passport object (the `credentialSubject`) in its JSON form as issued — not against the expanded RDF graph. A pointer to an object or array covers everything beneath it.
- **Tier resolution:** a field's tier is given by the `fieldTiers` entry with the **longest** path that equals or is a token-wise prefix of the field's own pointer; if none matches, `defaultTier`. (Most specific wins, so a public summary can sit beside a restricted detail, e.g. `/composition/materialFamily` public while `/composition/substances` is `legitimate-interest`.) The same path MUST NOT be assigned two different tiers.
- The following MUST remain `public` and MUST NOT be restricted: `type`, `passportId`, `subjectType`, `identityLevel`, the identifier fields (`gs1:gtin`, `gs1:lgtin`, `gs1:sgtin`, `alternativeId`), `issuerParty`, `issueDate`, `conformanceLevel`, `lifecycle/status`, `accessPolicy` and `fieldStatus`. A reader must always be able to tell what the passport is, who stands behind it, and that something has been withheld.
- **Enforcement** is by the exchange API (D2.1), keyed to OAuth2 scopes: `passports:read` ⇒ `public` only; `passports:read:legitimate-interest` ⇒ `public` + `legitimate-interest`; `passports:read:authority` ⇒ all tiers. Fields above the caller's tier are **omitted**, and their pointers are listed in `withheldPaths` in the response. How a caller *obtains* a legitimate-interest or authority scope (credential issuance, registry roles) is out of scope here and depends on the Art 77(9) access-rights implementing act and prEN 18239.
- **Access tiers are a disclosure policy, not encryption.** A passport containing non-public fields MUST NOT be published in full at an unauthenticated URL; the public representation MUST be the tier-filtered view.
- **Interaction with signatures (Level 3).** A VC signed over the full subject cannot be served with fields removed without breaking the signature. A tier-filtered response is therefore either (a) the full signed credential, served only to callers entitled to every field in it, or (b) a separately issued credential per tier, each signed over its own content. Issuers MUST NOT present a field-stripped copy of a signed credential as if it carried the original signature.

*Non-normative:* selective-disclosure credential formats — for example SD-JWT VC — would let one signed credential disclose per-tier subsets with each disclosure verifiable. They are a **candidate** for a later version, to be aligned with EN 18239 (access rights, security, confidentiality) and EN 18246 (authentication, integrity) once those standards are published and cited. v0.2 does not make any selective-disclosure format normative.

### 4.9 Per-field applicability status (B4, v0.2)

Several obligations that a passport must eventually satisfy depend on legal acts not yet adopted — at the date of this draft, for example, the battery carbon-footprint methodology act (Reg (EU) 2023/1542 Art 7), the battery recycled-content methodology act (Art 8), the battery access-rights implementing act (Art 77(9)) and the textiles and construction-products delegated acts. A passport that simply omits such fields is indistinguishable from one that is non-compliant. B4 lets the issuer say which.

**`fieldStatus`** — array of `{ path, status, basis, reviewBy }`.

- `path`: RFC 6901 JSON Pointer, as in §4.8.
- `status`:
  - `required` — the field is mandatory for this passport under the cited basis;
  - `optional` — the field may be provided; its absence carries no meaning;
  - `conditional` — required only if a stated condition holds (the condition goes in `basis`);
  - `not-yet-applicable` — the field will become relevant but the obligation has not started (typically pending an implementing or delegated act).
- `basis`: free text naming the legal or standards basis, e.g. `"Reg (EU) 2023/1542 Art 7 — methodology act not adopted"`. It SHOULD be present for `required`, `conditional` and `not-yet-applicable`.
- `reviewBy`: date by which the issuer will re-assess the status. It SHOULD be present for `not-yet-applicable`.

Semantics:

1. Consumers MUST NOT treat the absence of a field marked `not-yet-applicable` (or `optional`, or `conditional` with its condition unmet) as a defect.
2. A field marked `not-yet-applicable` MAY be populated voluntarily (e.g. a carbon footprint computed to a draft or non-regulatory method, or per-metal recycled content ahead of the Art 8 deadline). Such a value MUST NOT be presented as the regulatory declaration; its `methodology`, `basis` or `description` SHOULD say that it is voluntary.
3. A field marked `required` that is absent is a warning in v0.2 (validator), not a schema error, because the obligation is external to this schema.
4. `fieldStatus` is the **issuer's assertion** of applicability, not a legal determination. Sector profiles MAY publish default `fieldStatus` sets that issuers copy and update.
5. Pointers may address core-schema required fields: a required core field (e.g. `recycledContent`) can still carry `conditional` status relative to an *external* obligation, as in `examples/example_battery_item_v02.jsonld`.

### 4.10 Party details and multiple parties (B5, v0.2)

Battery, textile and construction-product passports must identify, and give contact details for, economic operators other than the issuer: the manufacturer, the importer, an authorised representative.

- `ukmp:Party` gains optional **`address`** `{streetAddress, locality, region, postalCode, countryCode}`, where `countryCode` is ISO 3166-1 alpha-2 (schema pattern `^[A-Z]{2}$`), and optional **`contactPoint`** `{email, telephone, url}`.
- `role` gains `importer`, `authorised-representative`, `distributor` and `economic-operator`. `economic-operator` is the generic role, for use where the governing regulation names a responsible operator with none of the more specific roles.
- **`parties[]`** (passport level) lists parties other than the issuer. Each entry MUST carry `role`. The issuer MUST NOT be repeated in `parties[]` with the same role. Where the issuer is also, for example, the manufacturer, `issuerParty.role` says so.
- Contact details of natural persons are personal data. Issuers SHOULD use functional addresses (e.g. a compliance mailbox) and MAY tier personal contact details via `accessPolicy` (§4.8).

### 4.11 Declared unit, indicators and study provenance (B6–B8, v0.2)

v0.1 carried one number: a carbon footprint per kg. Batteries declare kg CO₂e **per kWh** of total energy over the service life. Construction EPDs declare a set of EN 15804+A2 indicators **per declared unit, per life-cycle module**. Textiles PEF uses 16 impact categories per functional unit.

- **B6 `declaredUnit`** `{quantity (> 0), unit, description}` — the declared or functional unit, e.g. `{1, "kWh"}`, `{1, "m"}`, `{1, "kg"}`. **`carbonFootprintPerDeclaredUnit`** — kg CO₂e per declared unit. It requires `declaredUnit` (schema `dependentRequired`). Both footprints MAY be present. Where both are present they MUST describe the same system and boundary, and they then differ only by the mass of the declared unit.
- **B7 `indicators[]`** — `{indicator, lifecycleStage, value, unit}`:
  - `indicator`: issuers SHOULD use EN 15804+A2 codes: `GWP-total`, `GWP-fossil`, `GWP-biogenic`, `GWP-luluc`, `ODP`, `AP`, `EP-freshwater`, `EP-marine`, `EP-terrestrial`, `POCP`, `ADP-mm`, `ADP-fossil`, `WDP`. PEF impact-category names are permitted.
  - `lifecycleStage`: EN 15804 modules `A1-A3`, `A4`, `A5`, `B1`…`B7`, `C1`…`C4`, `D`, or the battery carbon-footprint stages `raw-material`, `production`, `distribution`, `end-of-life`. If absent, the value is the total over `assessmentBoundary`.
  - Values are per `declaredUnit` when one is present, otherwise per kg. `unit` states the indicator unit (e.g. `kg CO2e`, `mol H+e`, `MJ`).
- **Module D is not `netAvoidedKgCo2ePerKg` (normative).** EN 15804 module D reports loads and benefits beyond the system boundary, under EN 15804 rules, per declared unit, reported separately and not summed into A–C. `netAvoidedKgCo2ePerKg` (§4.4) is this specification's own figure: a sourced virgin baseline minus this passport's cradle-to-gate footprint, per kg. The two are different quantities. Module D MUST be carried as an `indicators[]` entry with `lifecycleStage: "D"`, and MUST NOT be written to, derived from, or copied into `netAvoidedKgCo2ePerKg`, or the reverse.
- **B8 `studyRefs[]`** (URI references) — the LCA study, EPD, carbon-footprint study or calculation-parameter documents the figures come from. **`verifierParty`** (`ukmp:Party`) — the independent verifier of that study or EPD, mirroring `recycledContentClaim.verifierParty`. A summary with `verifierParty` SHOULD also carry `studyRefs`.

### 4.12 Scoped recycled content (B9, v0.2)

`recycledContent` is one aggregate claim. Batteries must document pre- and post-consumer recycled **cobalt, lead, lithium and nickel** shares separately (Reg (EU) 2023/1542 Art 8). A multilayer pipe has recycled content in its core layer only.

- **`recycledContentDetail[]`** (passport level): each entry has every field and rule of `ukmp:RecycledContentClaim` (§4.3) — including the fraction arithmetic, `verifierParty` when `independently-verified`, and `evidenceRefs` for `epcis-event-chain` — **plus** a mandatory **`scope`** with at least one of:
  - `material` — element symbol (`Ni`, `Co`, `Li`, `Pb`), ISO 1043 polymer code, material name or CAS number;
  - `componentRef` — a JSON Pointer into this passport (e.g. `/composition/substances/0`) or the URI of the component's own passport;
  - `layer` — layer of a multilayer product (e.g. `outer`, `core`, `inner`).
- The aggregate `recycledContent` remains required and unchanged. Fractions in a scoped entry are fractions **of the scoped material, component or layer**, not of the whole product. Where entries partition the product by mass (e.g. layers), the aggregate SHOULD equal their mass-weighted sum. For per-element entries no such sum applies.
- The validator applies the §4.3 arithmetic to every entry (an error) and warns when a pointer-form `componentRef` does not resolve.

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
| Repurposing / remanufacturing (v0.2, B2) | ObjectEvent or TransformationEvent, per the change to the subject | `repairing` / `commissioning` (CBV), recorded on the predecessor before the successor passport is issued |
| Dismantling to black mass / recyclate (v0.2) | TransformationEvent | `transforming` (never `aggregation` — §4.6) |

Two project-defined EPCIS extension fields (permitted by EPCIS 2.0):
- `ukmp:massBalanceDelta` on TransformationEvents — input/output/waste masses enabling automated, step-level weight reconciliation. This is **not** a mass-balance chain-of-custody model (§4.3 note);
- `ukmp:verificationExtension` on inspection events — instrument type, measured polymer class, contamination level (the data-capture side that the MateriAI sensing project generates; this project makes it exchangeable).

**Traversability requirement:** every TransformationEvent MUST list input and output EPCs/LGTINs, so a verifier can walk the genealogy from any output batch back to feedstock intakes. Recycled-content claims at `evidenceType: epcis-event-chain` are recomputable from this walk — that is the interoperability dividend. B1 `aggregation` mirrors, at passport level, what EPCIS `AggregationEvent`s record; where both exist they SHOULD agree.

## 6. Trust envelope — W3C Verifiable Credential (L3)

At conformance Level 3 the passport is issued as a **W3C Verifiable Credential, Data Model v2.0**:

- `@context`: `https://www.w3.org/ns/credentials/v2` + GS1 EPCIS context + `ukmp` context
- `type`: `["VerifiableCredential", "MaterialPassportCredential"]`
- `issuer`: HTTPS URL identifying the issuing organisation (optionally `did:web`); public keys published as a JWK Set at `/.well-known/ukmp/keys` per the API spec (D2.1, `api/openapi.yaml`); `verificationMethod` / JOSE `kid` reference a key in that set (e.g. `https://passports.example-recycler.co.uk/.well-known/ukmp/keys#2026-1`)
- `credentialSubject`: the `ukmp:MaterialPassport` object (§4)
- **Securing (primary): VC-JOSE enveloping proof** — the credential is secured as a compact JWS (`alg: ES256`, ECDSA P-256, header `typ: vc+jwt`) per W3C *Securing Verifiable Credentials using JOSE and COSE*. This follows the convergence of the CIRPASS-2 reference architecture (D4.1 rec 3.10) and UNTP on JOSE enveloping proofs. Exchanged as media type `application/vc+jwt` (D2.1).
- **Securing (permitted alternative): embedded Data Integrity proof**, cryptosuite `ecdsa-jcs-2019` (ECDSA P-256 over JCS/RFC 8785 canonicalised content). The same P-256 key material serves both mechanisms. Verifiers claiming Level 3 support MUST accept both securings; issuers SHOULD prefer JOSE for EU DPP registry interoperability.
- `credentialStatus`: W3C Bitstring Status List entry — enables batch recall/withdrawal without breaking previously distributed copies. Revocation is distinct from succession (§4.7): a succeeded passport is not revoked; it remains valid as the record of the subject's earlier life.
- **Tiered disclosure (v0.2):** see §4.8 for how access tiers interact with signatures. Selective-disclosure formats (e.g. SD-JWT VC) are a non-normative candidate only.
- External time-anchoring (attestation of existence) is **pluggable and out of schema scope** — the schema carries `evidenceRefs` to anchoring receipts; the anchoring provider model is specified in the WP2 API documentation.

Rationale: the EU DPP implementation direction (JRC methodology work, CIRPASS-2 pilots, W3C VC-for-GS1 draft) treats VCs as the natural expression of verifiable product data. Adopting the VC envelope now means UK passports will register cleanly with the EU DPP registry — live since 20 July 2026 under Implementing Regulation (EU) 2026/1778 — rather than needing wrapping later.

**Implementation status:** this clause is normative. Level 3 issuance (signing) is not yet available in the reference implementation; nor is server-side enforcement of §4.8 access tiers. See `IMPLEMENTATION_STATUS.md` for current coverage.

## 7. Sector extension mechanism (L4) — WP3 findings

A sector profile is: (a) a named JSON-LD context adding fields, (b) enumeration restrictions on core fields, (c) additional EPCIS bizStep mappings, and (v0.2) (d) an optional default `fieldStatus` set (§4.9) and default `accessPolicy` (§4.8) reflecting the sector's regulation. The core never changes per sector; needs found in several sectors are promoted into the core additively (B1–B9).

**WP3 headline findings (from the mapping tests, `mapping/README.md`):**

- **No sector required a *breaking* core change.** Every gap found could be closed additively.
- **B1–B4 alone were not sufficient.** The mapping tests found 37 core gaps (batteries 15, construction 19, textiles 3) in five distinct core changes, now B5–B9 (see "Changes in v0.2").
- **Two sectors failed their proceed thresholds as tested.**
  - Batteries: (a)+(b) coverage was 4.9 % against a threshold of ≥ 80 %, and there were 15 (d) items against a threshold of zero. The coverage rule assumes a profile already exists, and none does yet. The (d) items are what B5–B9 address.
  - Construction: the bespoke share was 74 % against a threshold of ≤ 20 %, driven by product-specific DoPC characteristics and the EN 15804 indicator block.
  - B5–B9 remove the (d) class. They do not by themselves meet either threshold: that needs the profiles to be written.
- **Re-run against v0.2 (2 November 2026).** The mapping tests were re-run against the v0.2 baseline (B1–B9); results are in `mapping/README.md`, "Re-run against the v0.2 baseline". All 37 (d) items re-classify as (b): zero (d) in every sector and coverage 100 %. Batteries (a)+(b) is 23.2 %, pending import of the Battery Pass profile; the construction bespoke share is 43.5 %. Both thresholds still fail until the profiles are written (§10 item 9).
- Textiles (pilot) fitted best: 88.5 % coverage.

What each profile still needs is listed below. None of the three non-plastics profiles ships a published context in v0.2.

### 7.1 `ukmp-plastics` v0.1 — normative (unchanged)
Polymer typing, form, colour, food-contact grade, additives (`schema/plastics-context.jsonld`) — validated in WP4. v0.2 adds `feedstockSource` to the core claim, which plastics passports SHOULD populate (packaging vs bottle vs post-industrial feedstock).

### 7.2 `ukmp-batteries` — import Battery Pass v1.2 as the profile
- **Do not author a competing battery data model.** DIN DKE SPEC 99100 and the Battery Pass consortium data model (v1.2.0, JSON-LD, seven attribute groups: general product information, carbon footprint, circularity, material composition, performance and durability, labels, supply-chain due diligence) already exist. The batteries profile **imports and maps Battery Pass v1.2**; the ukmp core contributes what that model does not specify: recycled-content chain-of-custody evidence (§4.3, the same mass-balance pattern as plastics recyclate), EPCIS provenance, succession (B2), tiered access (B3), applicability status (B4) and the VC trust layer.
- B1: the battery passport is **item-level** (Art 77(3)); `identityLevel: item` with `gs1:sgtin` or an EN 18219-permitted serialised `alternativeId`; modules and packs linked by `aggregation`.
- B2: repurposed, remanufactured and prepared-for-reuse batteries get a **new passport linked to the original** (Art 77(7)); waste status is a revision; the passport ceases on recycling (Art 77(8)).
- B3: Annex XIII public vs legitimate-interest (detailed composition, dismantling, safety measures, dynamic state-of-health data) map directly to tiers. The Art 77(9) access-rights implementing act defining *who* qualifies had not been adopted at the time of writing; the tier mechanism does not depend on its final content.
- B4: carbon footprint (Art 7) and recycled-content documentation (Art 8) depend on methodology acts not yet adopted — recorded as `not-yet-applicable` / `conditional`.
- B5–B9: manufacturer and importer identity and contact (`parties[]`), carbon footprint per kWh (`declaredUnit`), stage contributions (`indicators[]` with battery stages), link to the public study (`studyRefs`), per-metal pre/post-consumer shares (`recycledContentDetail[]` scoped by `material`).
- Feasibility test applied in WP3: the share of Battery Pass v1.2 attributes that map into core + profile without core changes. The attribute-level mapping lives in the repository's `mapping/` work (WP3), not in this specification.
- Worked example: `examples/example_battery_item_v02.jsonld` (illustrative values).

### 7.3 `ukmp-textiles`
- Today ~98 % of recycled polyester is bottle-derived PET (Textile Exchange, 2025), so most recycled synthetic fibre is a **plastics-recyclate stream**: same polymer, often the same certified recyclers. The plastics profile is reused for synthetic fibre composition, lightly extended (PA6/PA66, PAN, elastane).
- The bottle-versus-textile feedstock distinction is where market and regulatory attention is heading; it is now the core `feedstockSource` field (`post-consumer-bottle`, `post-consumer-textile`, `post-industrial-textile`).
- Chain of custody: align with ISO 22095 (Parts 2 and 3, mass balance and book-and-claim, published 2026); certificate references (GRS / RCS, moving to Textile Exchange MMS) are carried as `evidenceRefs` / VCs.
- B3: the JRC preparatory study's public / legitimate-interest / authority split maps onto `accessPolicy`.
- B5–B8: economic-operator identity and contact, and PEF footprint per functional unit with its calculation parameters.
- B4: the ESPR textiles delegated act is not adopted (planned 2027; application not expected before ~2029); profile fields carry `not-yet-applicable` until it is.
- Profile-specific fields still to define: fibre composition per the Textile Labelling Regulation, durability score, care information.

### 7.4 `ukmp-construction` — an overlay on EN ISO 23387
- B1: the construction-products DPP under Reg (EU) 2024/3110 (CPR) is **product-type** level; recycled-content and chain-of-custody claims are **batch** level; installed items in buildings are item level. The profile uses `identityLevel: productType` for the DPP and `productTypeRef` on batch passports.
- **Overlay, not redefinition:** declared performance characteristics (the digital declaration of performance and conformity, DoPC) are carried by referencing **EN ISO 23387 data templates** (and prEN 18357, the CEN/TC 442 digital-DoPC methodology), with EN 15804+A2 / ILCD+EPD for environmental indicators. The ukmp core supplies the upstream recyclate chain of custody those templates lack.
- B5–B9: manufacturer and authorised representative (`parties[]`), per-declared-unit EPD indicators by module including C1–C4 and D (`declaredUnit`, `indicators[]`, `studyRefs`, `verifierParty`), and recycled content per layer of a multilayer pipe (`recycledContentDetail[]` scoped by `layer`).
- First construction case: **recycled-HDPE non-pressure drainage pipe** (the proven entry point for recycled HDPE in construction products) — `examples/example_pipe_producttype_v02.jsonld` and `examples/example_pipe_batch_v02.jsonld` (illustrative values).
- B4: CPR obligations bite product family by product family once harmonised technical specifications are cited; the construction DPP delegated act had not been adopted at the time of writing.
- Open profile issues: service lives of 50–100+ years outlast the CPR retention period (10 + 15 years), so persistence and custodian hand-over need design (EN 18221); Northern Ireland manufacturers face the EU CPR DPP (Windsor Framework) while GB develops its own digital product record — the overlay must serve both.

## 8. Conformance levels

| Level | Name | Requires | Typical adopter |
|---|---|---|---|
| 1 | **Core** | L0 identity + L2 content, `verificationStatus: self-declared` | SME starting out; export from existing ERP |
| 2 | **Evidence-linked** | Level 1 + L1 EPCIS event chain traversable for every claim | Traceability platforms (reference implementation today) |
| 3 | **Verified** | Level 2 + L3 VC envelope with valid proof + status list | Platforms serving regulated/EU-exporting customers |

Levels are per-passport, machine-detectable, and printed on the human-readable passport view — adoption can be incremental without fragmenting the ecosystem. The v0.2 extensions B1–B9 are orthogonal to conformance level: they neither raise nor lower it, and are available at every level.

## 9. Worked examples

| File | Shows |
|---|---|
| `examples/example_passport.jsonld` | Level 3 VC-enveloped recycled-HDPE batch passport (v0.1; valid under v0.2) — 9 EPCIS events, 87 % post-consumer content derived from the event genealogy (controlled blending, segregated chain of custody — corrected in v0.2 from `mass-balance`, see §4.3), LCA, UK regulatory block |
| `examples/example_level1_minimal.jsonld` | Minimal Level 1 self-declared batch passport (v0.1; valid under v0.2) |
| `examples/example_battery_item_v02.jsonld` | B1 item-level identity (`gs1:sgtin`, `aggregation`); B2 repurposed successor with `predecessorRefs`; B3 legitimate-interest composition; B4 carbon footprint `not-yet-applicable` citing Reg (EU) 2023/1542 Art 7, with a voluntary per-kWh estimate (B6, B7 battery stages, B8); B5 manufacturer + importer in `parties[]`; B9 per-metal (Co, Ni, Li) recycled content, `not-yet-applicable` until 18 Aug 2028 |
| `examples/example_pipe_producttype_v02.jsonld` | B1 product-type passport for a recycled-HDPE non-pressure drainage pipe; `feedstockSource`; B4 conditional environmental indicators; B5 authorised representative; B6 declared unit 1 m; B7 EN 15804+A2 indicators A1–A3, C1–C4 and D; B8 EPD reference and verifier; B9 per-layer recycled content |
| `examples/example_pipe_batch_v02.jsonld` | Batch passport referencing the pipe type via `productTypeRef` |

All values in the v0.2 examples are **illustrative**; no example represents a real company, product or certificate. A machine-validation schema is provided in `schema/material_passport.schema.json` (JSON Schema 2020-12); `tools/validate.py` adds the semantic checks (§4.6–4.9 and §4.12 warnings, recycled-content arithmetic, mass-balance reconciliation, conformance-level detection).

## 10. Open issues for steering discussion (M7)

1. **Namespace home** — `schema.materialspassport.org.uk` proposed; needs registration decision and a neutral governance statement so the namespace outlives Helix8 stewardship (open-ecosystem commitment). v0.2 mints new terms under `/v0.2/`; whether v1.0 consolidates all terms under one versionless namespace is open.
2. **Standards tracking** — EN 18216–18223 are published; prEN 18239 (access rights, security, confidentiality) and prEN 18246 (authentication, integrity) went to formal vote in July 2026 and were not yet cited at the time of writing. §4.8 tier semantics and the non-normative selective-disclosure note must be re-diffed against them on publication, before v1.0.
3. **PPT evidence granularity** — HMRC guidance on the mass-balance approach for PPT (published August 2026, applying from April 2027) to be checked against the evidence granularity validation partners' auditors request.
4. **Digital Link resolver** — single national resolver vs. per-issuer resolvers; now also determines how item-level (`gs1:sgtin`) and product-type passports resolve from one data carrier.
5. **Level 3 key custody for SMEs** — smaller adopters won't run KMS; does the ecosystem need a hosted signing service, and is that a commercial (post-project) offering? Feeds exploitation plan.
6. **(new) Who holds legitimate interest?** — B3 defines the tiers and enforcement point; credential issuance for repairers, repurposers and recyclers waits on the battery access-rights implementing act (Art 77(9)) and prEN 18239. Decision needed on whether the project prototypes a role-credential issuer or defers it.
7. **(new) Pointer stability** — `fieldTiers` and `fieldStatus` pointers address the JSON form of the passport; profile changes that rename or restructure fields silently break them. Proposal for v1.0: profiles publish pointer-stable field lists.
8. **(new) Required core fields at item and product-type level** — `composition` and `recycledContent` remain required at every identity level (strict additivity). For a repurposed battery or a product type this is workable (declared zero / declared minimum, plus `fieldStatus`) but awkward; steering to decide whether v1.0 relaxes them per `identityLevel` (a breaking change).

9. **(new) WP3 proceed thresholds for sectors with no profile yet.** The mapping tests were re-run against v0.2 on 2 November 2026 (`mapping/README.md`, "Re-run against the v0.2 baseline"): zero (d) in all sectors and coverage 100 %, but batteries (a)+(b) is 23.2 % pending the Battery Pass profile import, and the construction bespoke share is 43.5 %. Both thresholds still fail until the profiles exist. Steering to decide whether those thresholds, as written, are the right proceed tests for sectors with no profile yet.

---

*Companion files: `schema/material_passport.schema.json`, `schema/context.jsonld`, `examples/`, `api/openapi.yaml` (D2.1), `docs/user-guide/` (D2.3), architecture pack `NMIP_Architecture.md`.*
