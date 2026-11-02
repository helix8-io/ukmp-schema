# 1. Concepts

Ten minutes of background. Skip to [chapter 2](02-quickstart-level1-from-spreadsheet.md)
if you just want to make a passport.

## What a passport is

A **materials passport** is a small, structured data file that travels with a
batch of material (a tonne of PP pellet, a bale of sorted textiles, a battery
pack) and answers the questions the next owner asks:

- What is it made of?
- Who made it, and where has it been?
- How much of it is recycled, how was that worked out, and who stands behind
  the number?
- What is its carbon footprint?
- Which UK rules does it relate to (waste codes, End of Waste, Plastic
  Packaging Tax, packaging EPR)?

The file format is **JSON-LD**: ordinary JSON (the text format most software
already reads) with a `@context` line that ties each field name to a published
definition. You can treat it as plain JSON; the `@context` just makes sure
"recycledContent" means the same thing to every system.

In the files, the passport object is called the **credentialSubject**. When a
passport is signed (Level 3) it is wrapped inside a signed envelope and the
passport is the "subject" of that credential. Unsigned passports (Levels 1
and 2) are just the passport object on its own. This guide calls that a
"bare" passport.

## The five layers

The specification describes a passport in layers. You meet them in this order
as you adopt:

| Layer | Name | Plain-English meaning | Standard it reuses |
|---|---|---|---|
| L0 | Identity | The ID numbers: which batch, which company, which site | GS1 barcodes and IDs (GTIN, GLN), GS1 Digital Link QR codes |
| L1 | Events | The diary of what happened to the material: received, sorted, shredded, blended, despatched | GS1 EPCIS 2.0 |
| L2 | Content | The facts: composition, recycled content, carbon, regulatory codes | CEN EN 18223, CIRPASS-2, plus UK fields |
| L3 | Trust envelope | A digital signature and a revocation check | W3C Verifiable Credentials 2.0 |
| L4 | Sector profiles | Extra fields for plastics, batteries, textiles, construction | This project's extension mechanism |

Every passport needs L0 and L2. The others are what lift you to higher
conformance levels.

## Conformance levels 1 to 3

Levels let you start small and add proof later. The validator works out the
level automatically.

| Level | Name | What you add | What a buyer can rely on |
|---|---|---|---|
| 1 | Core | Identity and content. Recycled content is `self-declared`. | Your statement, in a standard format. |
| 2 | Evidence-linked | The event diary (EPCIS events) behind each claim, with weights in and out of every process step. | The recycled-content figure can be **recomputed** from your own records, and the weights must add up. |
| 3 | Verified | A digital signature and a revocation entry. | The file came from you, has not been altered, and has not been withdrawn. |

A Level 1 passport from a spreadsheet is a perfectly valid passport. Levels 2
and 3 add confidence; they do not replace Level 1 content.

## Identity levels (new in v0.2)

A passport can describe three different kinds of "thing". The optional
`identityLevel` field says which:

| identityLevel | Describes | Typical ID | Example |
|---|---|---|---|
| `productType` | A model or grade, not a physical lot | GTIN | "PP-GREY-IM grade", a construction product type |
| `batch` | One lot or batch | GTIN + lot number (`gs1:lgtin`) or your own batch ref | 975 kg of PP pellet, lot PP-2026-0150 |
| `item` | One serialised individual object | GTIN + serial (`gs1:sgtin`) | One battery pack, serial SL-2026-000481 |

Recyclers almost always work at `batch` level. If you leave `identityLevel`
out, it is read from `subjectType` (`MaterialBatch` means batch).

Item-level passports can point at their product-type passport
(`productTypeRef`) and at the things they contain or are contained in
(`aggregation.parentRefs` / `childRefs`). Turning a pack into black mass is
**not** aggregation; that is a transformation event (chapter 3).

## Revision or successor?

Passports are never edited in place. When something changes you do one of
two things:

| | Revision | Successor |
|---|---|---|
| When | You are correcting or updating facts about the **same** material | The material itself has changed role or state: prepared for reuse, repurposed, remanufactured, recycled into something new. (For batteries, becoming waste is recorded as a revision of the same passport; spec §7.2.) |
| Passport ID | Stays the same; a new revision is appended | A **new** passport with a new ID |
| Link | Revision history on the same passport | `lifecycle.predecessorRefs` on the new one, `lifecycle.successorRefs` on the old one |
| API | `POST /passports/{id}/revisions` | `POST /passports/{id}/successors` |
| Example | Lab result arrives and the contamination figure is corrected | An EV battery pack is repurposed into home storage |

For a recycler: re-weighing or correcting a batch is a **revision**. When a
batch that already has a passport (your own regrind, or a supplier's
passported flake) is consumed to make a new batch, issue the output's
passport as a **successor** with `lifecycle.status: recycled`, and point
`transitionEventID` at the transformation event that consumed it (chapter 5).
Feedstock that arrived without a passport (most bales today) is simply an
input lot in your event chain (chapter 3).

## Access tiers (new in v0.2)

Some fields are commercially sensitive (exact formulation, supplier names) or
only for regulators. The optional `accessPolicy` lets you mark them:

| Tier | Who sees it | API scope needed |
|---|---|---|
| `public` | Anyone with the passport link | `passports:read` |
| `legitimate-interest` | Trading partners, recyclers, repairers you have authorised | `passports:read:legitimate-interest` |
| `authority` | Regulators and market-surveillance bodies | `passports:read:authority` |

Fields are named with a JSON Pointer, a path such as
`/composition/substances` (always starting with `/`). When the API returns a
passport to someone without the right tier, those fields are left out and
their paths are listed as `withheldPaths`, so the reader knows something was
withheld rather than missing. Chapter 5 shows this.

Access tiers are enforced by the **API**, not by the file. If you email a
complete passport file to someone, they can read all of it.

## Field status (new in v0.2)

`fieldStatus` lets you say why a field is empty or provisional, for example
"carbon footprint not yet applicable: the EU methodology act has not been
adopted". This matters most for batteries (chapter 7). Most recyclers will
not need it.

## Words you will see

| Term | Meaning |
|---|---|
| GTIN | GS1 product number (the number under a barcode). 8 to 14 digits. |
| GLN | GS1 location/company number. 13 digits. |
| LGTIN | GTIN plus a batch/lot number. |
| SGTIN | GTIN plus a serial number (one item). |
| GS1 Digital Link | A web address built from GS1 IDs, e.g. `https://id.gs1.org/01/05060987654321/10/LOT1`. It can be printed as a QR code. |
| EPCIS | The GS1 standard for recording supply-chain events ("what, when, where, why"). |
| bizStep | The EPCIS "why" of an event: `receiving`, `inspecting`, `transforming`, `packing`, `shipping`. |
| Pre-consumer | Recycled material from manufacturing waste that never reached a user (ISO 14021). Excludes scrap you regrind and reuse in your own process. |
| Post-consumer | Recycled material from products that reached an end user and were discarded. |
| Verifiable Credential (VC) | A W3C standard for signed digital statements. A Level 3 passport is one. |
| EWC code | List of Waste / European Waste Catalogue code, e.g. `19 12 04` (plastic and rubber from mechanical treatment of waste). |
