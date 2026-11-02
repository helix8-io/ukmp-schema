# 8. FAQ and troubleshooting

## Reading validator output

```
[PASS]  file (bare passport)          <- valid; "bare", "VC-enveloped" or "JOSE-enveloped (JWS)"
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
        ! some warning                <- "!" = warning: valid, but check it
[FAIL]  file (bare passport)
        - schema: path: message       <- "-" = error: must fix
```

Exit codes: `0` all valid, `1` at least one file failed, `2` a file could not
be read or is not JSON/JWS.

Error prefixes:

| Prefix | Meaning |
|---|---|
| `schema:` | The JSON Schema rejected it. The path (e.g. `recycledContent/postConsumerFraction`) says where. `(root)` means the top level of the passport. |
| `recycled-content:` | Pre + post consumer fractions do not add up to the total |
| `mass-balance:` | An event's `inputKg` is not `outputKg + wasteKg` (±0.5 kg) |
| `evidence:` (warning) | An `evidenceRef` does not match an event in the file |
| `conformance:` (warning) | Declared `conformanceLevel` differs from what was detected |
| `identity:`, `lifecycle:`, `pointer:` (warnings) | v0.2 consistency checks |
| `jose:` / `proof:` (warning) | A signature is present but was not checked (see chapter 4) |

Every example below is real output from `tools/validate.py` on a deliberately
broken copy of a passport from chapter 2 (file names shortened).

## Errors (FAIL) and how to fix them

### A required section is missing

```
[FAIL]  01-missing-composition.jsonld (bare passport)
        - schema: (root): 'composition' is a required property
```

Every passport needs `type`, `passportId`, `subjectType`, `issuerParty`,
`issueDate`, `composition` and `recycledContent`. If your batch has no
recycled content, still include the block with `totalRecycledFraction: 0`.

### Percentage instead of a fraction

```
[FAIL]  02-percent-not-fraction.jsonld (bare passport)
        - schema: recycledContent/postConsumerFraction: 95 is greater than the maximum of 1
        - recycled-content: totalRecycledFraction (1.0) != preConsumerFraction + postConsumerFraction (0.05 + 95 = 95.05)
```

All fractions are between 0 and 1: write `0.95`, not `95`. (The CSV converter
accepts `95%` and converts it.)

### Pre + post does not equal total

```
[FAIL]  03-total-mismatch.jsonld (bare passport)
        - recycled-content: totalRecycledFraction (0.9) != preConsumerFraction + postConsumerFraction (0.05 + 0.95 = 1.0)
```

`totalRecycledFraction` must equal `preConsumerFraction + postConsumerFraction`
when both are given. Usually a rounding or copy error. If you only know the
total, leave both pre and post out.

### Event-chain evidence without references

```
[FAIL]  04-epcis-no-refs.jsonld (bare passport)
        - schema: recycledContent: 'evidenceRefs' is a required property
        ! evidence: evidenceType is 'epcis-event-chain' but processingHistory carries no events — chain not traversable from this document alone
```

`evidenceType: epcis-event-chain` needs `evidenceRefs` listing event IDs, and
the events themselves in `processingHistory` (or retrievable through the
API). At Level 1 use `supplier-declaration` or `third-party-certificate`.

### "Independently verified" without a verifier

```
[FAIL]  05-verified-no-verifier.jsonld (bare passport)
        - schema: recycledContent: 'verifierParty' is a required property
```

Add `verifierParty` (`name`, and `gs1:gln` or `otherPartyId` if available),
or use `self-declared` / `evidence-linked`.

### No identifier

```
[FAIL]  06-no-identifier.jsonld (bare passport)
        - schema: (root): no identifier — one of gs1:gtin | gs1:lgtin | gs1:sgtin | alternativeId is required
```

Add at least one: a GS1 GTIN, LGTIN (GTIN + lot), SGTIN (GTIN + serial), or
`alternativeId: {"scheme": "internal-batch-ref", "value": "PP-2026-0142"}`.

### Wrong EWC code format

```
[FAIL]  07-ewc-format.jsonld (bare passport)
        - schema: ukRegulatory/ewcCode: '191204' does not match '^[0-9]{2} [0-9]{2} [0-9]{2}\\*?$'
```

Write the code with spaces: `19 12 04`, and add `*` for hazardous entries
(`19 12 11*`). The CSV converter adds the spaces for you.

### UK date format

```
[FAIL]  08-uk-date.jsonld (bare passport)
        - schema: issueDate: '14/10/2026' is not a 'date'
```

Dates in the passport are ISO 8601: `2026-10-14`. Date-times need a time
zone: `2026-10-14T09:30:00Z` or `2026-10-14T10:30:00+01:00`.

### Value not in the allowed list

```
[FAIL]  09-bad-enum.jsonld (bare passport)
        - schema: subjectType: 'Batch' is not one of ['MaterialBatch', 'Product', 'Component', 'ProductType', 'Item']
```

Fixed-choice fields are case-sensitive and must match exactly. The error
lists the allowed values.

### Mass balance does not reconcile

```
[FAIL]  11-mass-balance.jsonld (VC-enveloped)
        - mass-balance: event urn:uuid:e4-transform-shred-2026-07-30: inputKg (1240) != outputKg + wasteKg (1196 + 64 = 1260)
```

On every TransformationEvent, `inputKg` must equal `outputKg + wasteKg`
within 0.5 kg. Check for a mistyped weight, or losses (moisture, fines, purge)
that were not counted in `wasteKg`. Do not change the input weight to make
it balance; it should match the goods-in or previous step's output.

### Access-tier path is not a JSON Pointer

```
[FAIL]  13-access-pointer.jsonld (bare passport)
        - schema: accessPolicy/fieldTiers/0/path: 'composition/substances' does not match '^(/([^~/]|~[01])*)*$'
        ! pointer: accessPolicy.fieldTiers[0].path 'composition/substances' is not a valid RFC 6901 JSON Pointer
```

Paths in `accessPolicy` and `fieldStatus` start with `/`:
`/composition/substances`. Escape a `/` inside a field name as `~1` and `~` as
`~0`.

### File is not valid JSON (exit code 2)

```
[ERROR] 14-trailing-comma.jsonld: neither JSON nor a compact JWS
```

The file has a JSON syntax error: often a trailing comma, a missing quote,
or "smart quotes" pasted from a word processor. Open it in an editor with
JSON checking, or run `python -m json.tool file.jsonld` to see the line.

## Warnings (PASS with "!")

The passport is valid, but something deserves a look.

### Declared level differs from detected level

```
[PASS]  10-declared-level-mismatch.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
        ! conformance: declared conformanceLevel 2 != detected 1
```

You claimed Level 2 but the file has no event chain or is still
`self-declared`. Either add the evidence (chapter 3) or declare `1`. A
receiving system trusts the detected level, not the declared one.

### Evidence reference not found

```
[PASS]  12-dangling-evidence-ref.jsonld (VC-enveloped)
        detected conformance level: 3 (Verified)
        identity level: batch (from subjectType)
        ! evidence: evidenceRef urn:uuid:e7-missing not found in processingHistory.epcisEvents
        ! proof: signature present but NOT cryptographically verified by this tool (Level 3 proof verification is a WP2 reference-implementation capability)
```

A claim points at an event that is not in the file. Fine if the event is
served by the API (`GET /passports/{key}/events`); otherwise a verifier cannot
follow the chain. Usually a typo in the event ID.

Note that the validator still reports Level 3 here because the file is
enveloped and has a proof block. It does not check signatures (chapter 4), so
treat "Level 3" from `validate.py` as "structurally Level 3".

### Successor without a predecessor

```
[PASS]  15-successor-no-predecessor.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
        lifecycle status: recycled
        ! lifecycle: status 'recycled' but no predecessorRefs — a successor passport should link to the passport(s) it succeeds
```

A `lifecycle.status` other than `original` means this passport succeeds
another. Add `lifecycle.predecessorRefs` (the API does this for you when you
use `POST .../successors`). If you were correcting the same batch, you wanted a
revision, not a successor.

### Identity level contradicts subject type

```
[PASS]  16-identity-contradiction.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: item (declared)
        ! identity: identityLevel 'item' contradicts subjectType 'MaterialBatch' (implies 'batch')
```

Make them agree: `MaterialBatch` with `batch`, `Item` with `item`,
`ProductType` with `productType`. (The CSV converter rejects this combination
outright.)

### Access tier applies to nothing

```
[PASS]  17-pointer-unresolved.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
        ! pointer: accessPolicy.fieldTiers[0].path /composition/substance does not resolve in this passport (tier 'legitimate-interest' applies to nothing)
```

Usually a typo (`substance` instead of `substances`). Take this one
seriously: the field you meant to protect is **public**.

### Field marked required but absent

```
[PASS]  18-required-field-absent.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
        ! pointer: fieldStatus[0].path /environmentalFootprint is marked 'required' but is absent
```

Either fill the field or change its `fieldStatus` to `conditional` or
`not-yet-applicable` with a `basis`.

## Converter (csv_to_passport.py) problems

| Message | Fix |
|---|---|
| `unknown column(s): ...` | Header typo. Copy the header row from `templates/level1_batch_template.csv`. |
| `required column(s) missing from header` | You deleted a required column. Restore it, even if some cells are blank. |
| `... is outside 0-1 (looks like a percentage ...)` | Write `95%` or `0.95`. |
| `gtin: '5.06099E+12' must be 8-14 digits` | Excel turned the GTIN into a number. Format the column as Text and retype. |
| `is not UTF-8` | Save as "CSV UTF-8 (Comma delimited)". |
| `more cells than header columns` | An unquoted comma in a cell. Re-save from the spreadsheet program instead of editing the CSV in a text editor. |
| `passport_id is empty and no gtin+lot given, so --base-url is needed` | Add `--base-url https://passports.yourco.co.uk`, or fill `passport_id`, or `gtin` and `lot`. |
| `already exists (use --force to overwrite)` | The passport was generated before. If it has been sent to anyone, issue a revision instead of overwriting. |
| `evidence_type: 'epcis-event-chain' is Level 2` | A spreadsheet row cannot carry an event chain. See chapter 3. |
| `verification_status: ... is not allowed at Level 1` | Leave the column blank. |
| `identity_level: 'item' contradicts subject_type` | Make them agree, or leave `identity_level` blank. |

## FAQ

**Do I need GS1 numbers?**
No. An `alternativeId` with your own batch reference is enough for a valid
passport. GS1 GTINs and GLNs help when your customers' systems already use
them and when you want a GS1 Digital Link QR code. For EU DPP registry
registration, EN 18219 recommends specific identifier schemes
(`gs1-digital-link`, `iec-61406`, `did`, `doi`).

**Is a Level 1 passport worth sending?**
Yes. It puts your declaration in a format the customer's system can read
without retyping, and it is the base that Levels 2 and 3 build on.

**Can I edit a passport after I have sent it?**
No. Append a revision (chapter 5, Step 5). The original stays on record, which
is what makes the passport auditable.

**Does `validate.py` passing mean my recycled-content claim is true?**
No. It means the passport is well-formed and its arithmetic is consistent. At
Level 2 the claim can be recomputed from your events; whether those events
reflect reality is what audits and certification check.

**Does `validate.py` check signatures?**
No (chapter 4). It reports the structure of Level 3 and warns that the
signature was not checked.

**Who can see my supplier names and formulation?**
Anyone you give the full file to. Through the API, only callers with the tier
you assign in `accessPolicy` (chapter 1). Put commercially sensitive fields
at `legitimate-interest`.

**Pre-consumer or post-consumer?**
ISO 14021: post-consumer means a product that reached an end user;
pre-consumer means manufacturing waste, excluding scrap reused in the same
process that produced it. Record them separately. For Plastic Packaging Tax,
pre-consumer stops counting from 1 April 2027 (chapter 3).

**My batch mixes several feedstocks. What is `feedstockSource`?**
Use `mixed`, and give the pre/post split in the fractions.

**What schema version am I on?**
v0.2 (draft). v0.1 passports remain valid. The `@context` line shows which
vocabulary version a file uses.
