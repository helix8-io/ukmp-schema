# UK Materials Passport Schema (ukmp)

[![Schema validation](https://img.shields.io/badge/CI-pending-lightgrey)](../../actions)
[![Spec version](https://img.shields.io/badge/spec-v0.2--draft-orange)](spec/ukmp-schema-v0.2.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

An open JSON-LD data format for describing the composition, origin, processing
history, recycled content, and environmental footprint of a material as it
moves between organisations in a circular-economy supply chain.

Developed by [Helix8 Ltd](https://www.materiai.co.uk) as work package 1 of the
Innovate UK feasibility study *Interoperable Materials Passport Infrastructure
for UK Circular Economy (Materials 4.0 Focus)*, project 10188380.

**Current version: v0.2 (draft, November 2026).** v0.2 adds four additive
"baseline core extensions" found necessary by the WP3 sector analysis
(batteries, textiles, construction): **B1** multi-level identity
(product type / batch / serialised item), **B2** passport succession for
reuse and repurposing, **B3** role-based field-level access tiers, and
**B4** per-field applicability status for obligations whose legal acts are
not yet adopted — plus an optional recycled `feedstockSource`. Every v0.1
passport remains valid. See [Changes in v0.2](spec/ukmp-schema-v0.2.md#changes-in-v02)
and the [CHANGELOG](CHANGELOG.md).

Canonical repository: `https://github.com/materiAI/ukmp-schema` · Project site: [materiai.co.uk](https://www.materiai.co.uk)

**Try it in your browser:** the [interactive playground](https://materiAI.github.io/ukmp-schema/) builds a passport from editable process weights (recycled content computed from the event chain) and validates pasted passports against the same checks as `tools/validate.py` — including catching claims that don't match their evidence. Source: [`docs/index.html`](docs/index.html); enable GitHub Pages (Settings → Pages → main branch, `/docs` folder) to serve it.

## What is a materials passport?

A materials passport is a machine-readable record that travels with a batch of
material — a tonne of recycled HDPE pellet, a coil of steel, a bale of sorted
textiles — and answers, verifiably, the questions its next user must ask: What
is it made of? Where has it been? How much of it is recycled, and who stands
behind that number? What is its carbon footprint? Which regulatory regimes
(UK Plastic Packaging Tax, packaging EPR, EU DPP/ESPR) does it satisfy?

Today that information exists but is locked inside isolated systems. This
schema defines a common, vendor-neutral exchange format so a passport created
in one system can be retrieved, understood, and verified in another.

## Quickstart — validate the worked example in 3 commands

```bash
git clone <this-repo> && cd ukmp-schema-repo
pip install -r tools/requirements.txt
python tools/validate.py examples/*.jsonld
```

The validator checks each passport against the published JSON Schema, verifies
recycled-content fraction arithmetic, reconciles mass-balance deltas across
the EPCIS event chain, checks the v0.2 JSON Pointers (access tiers,
applicability status) and lifecycle/identity consistency, and reports the
detected conformance level.

## Repository layout

| Path | Contents |
|---|---|
| `spec/ukmp-schema-v0.2.md` | The specification, current draft (WP1 deliverable D1.2, incorporating WP3 findings) |
| `spec/ukmp-schema-v0.1.md` | v0.1 specification, kept for history |
| `schema/material_passport.schema.json` | JSON Schema 2020-12 validation schema |
| `schema/context.jsonld` | JSON-LD `@context` for the `ukmp:` core vocabulary |
| `schema/plastics-context.jsonld` | `ukmp-plastics:` sector profile terms |
| `examples/` | Worked examples at conformance Levels 1 and 3, including v0.2 battery (item-level, repurposed) and construction pipe (product type + batch) passports |
| `tools/validate.py` | CLI validator (used in CI) |
| `tools/csv_to_passport.py` | Converts a spreadsheet (CSV) row set into Level 1 passports |
| `templates/` | CSV templates for `tools/csv_to_passport.py` (blank + worked example) |
| `api/openapi.yaml` | Exchange API specification, **OpenAPI 3.1.0** — WP2 deliverable **D2.1** |
| `api/README.md` | How to read, bundle, lint and mock the API specification |
| `api/openapi-draft.md` | *Superseded* by `api/openapi.yaml`; earlier prose draft kept for history |
| `tests/api/` | API specification tests (bundling, structural tests, mock smoke test) |
| `mapping/` | WP3 mapping tests: Battery Pass v1.2, construction-pipe and textiles attribute mappings, metrics script and results |
| `docs/user-guide/` | Integration and user guides — WP2 deliverable **D2.3** |
| `IMPLEMENTATION_STATUS.md` | What the reference tooling implements today, per conformance level and v0.2 extension |

## Conformance levels

Adoption is incremental: a passport is useful at the data layer alone, and
verification layers are additive. Levels are per-passport and
machine-detectable (the validator reports them).

| Level | Name | Requires | Typical adopter |
|---|---|---|---|
| 1 | **Core** | Identity + passport content, `verificationStatus: self-declared` | SME starting out; export from existing ERP |
| 2 | **Evidence-linked** | Level 1 + traversable GS1 EPCIS 2.0 event chain for every claim | Traceability platforms |
| 3 | **Verified** | Level 2 + W3C Verifiable Credential envelope with valid proof + status list | Platforms serving regulated / EU-exporting customers |

## Standards alignment

The schema extends established standards rather than replacing them:

- **[CIRPASS-2](https://cirpassproject.eu/)** — Digital Product Passport data
  model; the ukmp core extends it with UK-specific fields (recycled-content
  verification, PPT/EPR, End of Waste).
- **[GS1 EPCIS 2.0](https://www.gs1.org/standards/epcis)** — processing
  history is expressed as standard EPCIS events (JSON-LD binding); GS1 keys
  (GTIN/LGTIN, GLN, SSCC) and Digital Link provide identity and discovery.
- **[W3C Verifiable Credentials v2.0](https://www.w3.org/TR/vc-data-model-2.0/)**
  — the Level 3 trust envelope, secured primarily by a VC-JOSE enveloping
  proof (ES256), with an embedded Data Integrity proof (`ecdsa-jcs-2019`)
  as a permitted alternative, and Bitstring Status List revocation. Any off-the-shelf
  VC verifier works; there is no proprietary verification protocol.
- **ISO 14021 / ISO 22095 / ISO 14067** — recycled-content definitions, chain
  of custody models, and carbon-footprint methodology references.
- **Sector models (v0.2 profiles, WP3)** — batteries import the
  [Battery Pass](https://github.com/batterypass/BatteryPassDataModel) data
  model v1.2 as the profile rather than competing with it; construction is an
  overlay on EN ISO 23387 data templates. Neither profile context is published
  yet.

## Roadmap

| Version | Target | Scope |
|---|---|---|
| v0.1 | Aug 2026 | Public draft for steering review; plastics profile normative |
| v0.2 (this release) | Nov 2026 | WP3 baseline core extensions B1–B4 + `feedstockSource` (additive); JSON-LD context fix; OpenAPI 3.1 API spec (D2.1) |
| v1.0 | Jan 2027 (project end) | Frozen schema + OpenAPI spec + reference implementation |

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Schema changes go through steering review; the governance process is described
there.

## Links

- Project & company: [www.materiai.co.uk](https://www.materiai.co.uk)
- Specification: [spec/ukmp-schema-v0.2.md](spec/ukmp-schema-v0.2.md) (v0.1: [spec/ukmp-schema-v0.1.md](spec/ukmp-schema-v0.1.md))
- API specification (D2.1): [api/openapi.yaml](api/openapi.yaml)
- User guides: [docs/user-guide/](docs/user-guide/)
- Namespace (proposed): `https://schema.materialspassport.org.uk/v0.1/` (v0.1 terms) and `https://schema.materialspassport.org.uk/v0.2/` (terms added in v0.2)

## Funding acknowledgement

Funded by Innovate UK, National Materials Innovation Programme, project
10188380.

## License

[Apache License 2.0](LICENSE) — copyright 2026 Helix8 Ltd.
