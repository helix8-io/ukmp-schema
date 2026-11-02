# UK Materials Passport — Adopter User Guide

**Deliverable:** D2.3 Integration and user guides (WP2), Innovate UK project 10188380
**Applies to:** schema v0.2 (draft), exchange API OpenAPI 3.1 (`api/openapi.yaml`, draft)
**Status:** Draft, November 2026

This guide shows you how to produce, exchange and check UK Materials
Passports. It is practical: every command in it has been run against this
repository, and the output shown is the real output.

## Who this is for

- **UK SME recyclers and reprocessors** who want to send customers a
  passport with each batch (for example, to back up a recycled-content
  claim for Plastic Packaging Tax) without buying a new system.
- **IT suppliers and in-house developers** who look after those firms' ERP,
  weighbridge, MES or traceability software and need to connect it to the
  passport format and API.
- **Buyers of recyclate** (converters, compounders, brands) who receive
  passports and want to know what they can rely on.

You do not need to know JSON-LD, EPCIS or Verifiable Credentials to start.
Chapter 1 explains the handful of terms you need, and chapter 2 gets you to a
valid passport from a spreadsheet.

## Where to start

| If you want to... | Read |
|---|---|
| Understand what a passport is and the three levels | [01 Concepts](01-concepts.md) |
| Make passports from a spreadsheet today (Level 1) | [02 Quickstart: Level 1 from a spreadsheet](02-quickstart-level1-from-spreadsheet.md) |
| Back recycled-content claims with your site's records (Level 2) | [03 Level 2: event evidence](03-level2-event-evidence.md) |
| Sign passports so anyone can check them (Level 3) | [04 Level 3: signing](04-level3-signing.md) |
| Connect software through the exchange API | [05 Using the API](05-using-the-api.md) |
| Plan an ERP / MES / LCA integration | [06 Integration patterns](06-integration-patterns.md) |
| Work outside plastics (batteries, textiles, construction) | [07 Sector profiles](07-sector-profiles.md) |
| Fix a validation error | [08 FAQ and troubleshooting](08-faq-troubleshooting.md) |

## What you need

- Python 3.9 or later.
- For validation only: `pip install -r tools/requirements.txt` (installs
  `jsonschema`). The spreadsheet converter needs nothing beyond Python itself.
- A spreadsheet program that can save CSV (Excel, LibreOffice, Google Sheets).

## Files this guide uses

| Path | What it is |
|---|---|
| `templates/level1_batch_template.csv` | Empty spreadsheet template: one row per batch |
| `templates/level1_batch_example.csv` | The same template filled in for three example batches |
| `tools/csv_to_passport.py` | Converts the spreadsheet into Level 1 passport files |
| `tools/validate.py` | Checks passport files against the schema and arithmetic rules |
| `docs/user-guide/examples/level2_pp_pellet.jsonld` | Level 2 worked example used in chapter 3 |
| `examples/` | Reference examples maintained with the schema |
| `spec/ukmp-schema-v0.2.md` | The normative specification (this guide is not normative) |
| `api/openapi.yaml` | The exchange API definition (D2.1) |

## Status and honesty notes

- The schema is a **v0.2 draft** for steering review. Field names may still
  change before v1.0 (January 2027). This guide tracks v0.2.
- **Level 3 signing is not yet implemented in the reference tooling.** The
  validator recognises signed passports but does not check signatures. See
  chapter 4 and `IMPLEMENTATION_STATUS.md`.
- Sector profiles other than plastics are **WP3 interim** material (chapter 7).
  The mapping tests were re-run against v0.2 on 2 November 2026 — see
  `mapping/README.md`: zero (d) in all sectors and coverage 100 %; batteries
  (a)+(b) 23.2 % pending the Battery Pass profile import; construction
  bespoke share 43.5 %.
- Regulatory notes (Plastic Packaging Tax, EU Battery Regulation and so on)
  are pointers, not legal or tax advice. Check current HMRC and regulator
  guidance before relying on them.

Funded by Innovate UK, National Materials Innovation Programme, project
10188380. Licence: Apache 2.0.
