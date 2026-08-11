# UK Materials Passport Schema (ukmp)

[![Schema validation](https://img.shields.io/badge/CI-pending-lightgrey)](../../actions)
[![Spec version](https://img.shields.io/badge/spec-v0.1--draft-orange)](spec/ukmp-schema-v0.1.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

An open JSON-LD data format for describing the composition, origin, processing
history, recycled content, and environmental footprint of a material as it
moves between organisations in a circular-economy supply chain.

Developed by [Helix8 Ltd](https://www.materiai.co.uk) as work package 1 of the
Innovate UK feasibility study *Interoperable Materials Passport Infrastructure
for UK Circular Economy (Materials 4.0 Focus)*, project 10188380.

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
python tools/validate.py examples/example_passport.jsonld
```

The validator checks the passport against the published JSON Schema, verifies
recycled-content fraction arithmetic, reconciles mass-balance deltas across
the EPCIS event chain, and reports the detected conformance level.

## Repository layout

| Path | Contents |
|---|---|
| `spec/ukmp-schema-v0.1.md` | The specification (WP1 deliverable D1.2) |
| `schema/material_passport.schema.json` | JSON Schema 2020-12 validation schema |
| `schema/context.jsonld` | JSON-LD `@context` for the `ukmp:` core vocabulary |
| `schema/plastics-context.jsonld` | `ukmp-plastics:` sector profile terms |
| `examples/` | Worked examples at conformance Levels 1 and 3 |
| `tools/validate.py` | CLI validator (used in CI) |
| `api/openapi-draft.md` | Draft of the WP2 exchange API surface |

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
  — the Level 3 trust envelope, with Data Integrity proof
  (`ecdsa-jcs-2019`) and Bitstring Status List revocation. Any off-the-shelf
  VC verifier works; there is no proprietary verification protocol.
- **ISO 14021 / ISO 22095 / ISO 14067** — recycled-content definitions, chain
  of custody models, and carbon-footprint methodology references.

## Roadmap

| Version | Target | Scope |
|---|---|---|
| v0.1 (this release) | Aug 2026 | Public draft for steering review; plastics profile normative |
| v0.2 | Post-steering, Q4 2026 | Steering feedback, CIRPASS-2 re-diff, partner validation input (WP4) |
| v1.0 | Jan 2027 (project end) | Frozen schema + OpenAPI spec + reference implementation |

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Schema changes go through steering review; the governance process is described
there.

## Links

- Project & company: [www.materiai.co.uk](https://www.materiai.co.uk)
- Specification: [spec/ukmp-schema-v0.1.md](spec/ukmp-schema-v0.1.md)
- Namespace (proposed): `https://schema.materialspassport.org.uk/v0.1/`

## Funding acknowledgement

Funded by Innovate UK, National Materials Innovation Programme, project
10188380.

## License

[Apache License 2.0](LICENSE) — copyright 2026 Helix8 Ltd.
