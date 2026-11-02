# 2. Quickstart: Level 1 passports from a spreadsheet

Goal: turn a spreadsheet of batches into valid Level 1 passports in about
15 minutes, with no new software beyond Python.

The flow is:

```
templates/level1_batch_template.csv   (you fill one row per batch)
        |
        v
tools/csv_to_passport.py              (one .jsonld passport per row)
        |
        v
tools/validate.py                     (PASS / FAIL with reasons)
```

## Step 0: get the tools

```bash
git clone https://github.com/helix8-io/ukmp-schema.git
cd ukmp-schema
pip install -r tools/requirements.txt     # only needed for validate.py
```

The converter uses only the Python standard library. The validator needs the
`jsonschema` package.

## Step 1: fill in the template

Open `templates/level1_batch_template.csv` in Excel, LibreOffice or Google
Sheets. It has a header row only. Add **one row per batch**. You can leave
any optional column blank; you cannot rename or add columns (the converter
rejects unknown column names to catch typos).

A filled example with three batches is in `templates/level1_batch_example.csv`.
Open that alongside the template the first time.

**Excel tips**

- Format the `gtin` and `issuer_gln` columns as **Text** before typing, or
  Excel turns `05060987654321` into `5.06099E+12` and drops the leading zero.
- Save with **File > Save As > CSV UTF-8 (Comma delimited)**. Plain "CSV"
  in some Excel versions uses a Windows character set and breaks characters
  like `£` and `é`.
- Commas inside a description are fine; Excel quotes them for you.

### Required columns

| Column | What to put | Example |
|---|---|---|
| `batch_ref` | Your own batch or lot reference. Must be unique in the file. Becomes the output file name. | `PP-2026-0142` |
| `issuer_name` | Your registered company name | `Example SME Reprocessing Ltd` |
| `issue_date` | Date the passport is issued. `2026-10-14` or `14/10/2026`. | `2026-10-14` |
| `material_family` | `polymer`, `metal`, `glass`, `fibre`, `mineral`, `composite` or `other` | `polymer` |
| `substance1_name`, `substance1_mass_fraction` | The main material and its share by mass. Fractions are `0` to `1`, or write a percentage with `%`. | `Polypropylene`, `0.97` |
| Recycled content | Either `total_recycled_fraction`, or `pre_consumer_fraction` and/or `post_consumer_fraction` (the total is then added up for you). If you give all three, the total must equal pre + post. | `0.05`, `0.95` |

### Identity columns (optional, but read this)

Every passport needs a unique web-style ID (`passportId`). The converter picks
one in this order:

1. `passport_id`, if you fill it in (any absolute URI).
2. A GS1 Digital Link built from `gtin` + `lot`, if you have GS1 numbers:
   `https://id.gs1.org/01/<gtin>/10/<lot>`.
3. Otherwise it makes one from `--base-url` plus a UUID derived from your
   company name and `batch_ref`. Re-running on the same row gives the **same**
   ID, so you will not create duplicates by running the tool twice.

| Column | Meaning |
|---|---|
| `id_scheme` | Name of your batch-reference scheme. Default `internal-batch-ref`. |
| `gtin`, `lot` | GS1 trade item number (8 to 14 digits) and lot number, if you have them |
| `subject_type` | Default `MaterialBatch`. Also `Product`, `Component`, `ProductType`, `Item`. |
| `identity_level` | Optional: `batch`, `productType` or `item` (chapter 1) |
| `issuer_role` | `reprocessor`, `sorter`, `collector`, `compounder`, `converter`, `producer`, `manufacturer`, `brand`, `verifier`, `other` |
| `issuer_gln` | Your GS1 GLN (13 digits), if you have one |
| `issuer_companies_house` | Your Companies House number, e.g. `NI123456` |

### Content columns (optional)

| Column(s) | Meaning |
|---|---|
| `description` | Free text: quantity, grade, colour |
| `polymer_type`, `form`, `colour`, `food_contact_grade` | Plastics profile. `PET`, `HDPE`, `LDPE`, `PP`, `PS`, `PVC`, `other`; `bale`, `flake`, `pellet`, `regrind`; free-text colour; yes/no. Filling any of these adds the plastics profile to the passport. |
| `substance2_...` to `substance5_...` | Up to five substances, each with `_name`, `_mass_fraction`, `_cas` (CAS number, e.g. `9003-07-0`) and `_svhc` (yes/no: REACH substance of very high concern). Fractions must not add up to more than 1. |
| `calculation_method` | How the recycled figure was worked out: `declared` (default), `batch-segregation`, `controlled-blending`, `mass-balance` |
| `chain_of_custody_model` | `identity-preserved`, `segregated`, `mass-balance`, `book-and-claim` (ISO 22095) |
| `evidence_type` | `supplier-declaration` (default) or `third-party-certificate`. (`epcis-event-chain` is Level 2, see chapter 3.) |
| `evidence_refs` | Links to the declaration or certificate. Separate several with `;` |
| `feedstock_source` | Where the recycled input came from: `post-consumer-packaging`, `post-consumer-bottle`, `post-consumer-textile`, `post-industrial`, `post-industrial-textile`, `mixed`, `other` |
| `verification_status` | Leave blank. Level 1 is always `self-declared`; anything else is rejected. |
| `ewc_code` | List of Waste code while the material is still waste: `19 12 04` or `191204` |
| `end_of_waste_achieved`, `end_of_waste_basis` | yes/no; `quality-protocol`, `individual-assessment`, `not-applicable` |
| `waste_hierarchy_position`, `recovery_code` | `recycling` / `recovery` / `preparation-for-reuse`; R-code such as `R3` |
| `ppt_in_scope`, `ppt_recycled_fraction` | Plastic Packaging Tax relevance (see chapter 3 before filling this in) |
| `epr_category`, `permit_ref` | Packaging EPR material category; your environmental permit number |
| `carbon_footprint_kgco2e_per_kg`, `lca_boundary`, `lca_methodology` | Fill all three or none. `cradle-to-gate` / `gate-to-gate` / `cradle-to-grave`; e.g. `ISO 14067`. |

## Step 2: convert

From the repository folder:

```
$ python tools/csv_to_passport.py templates/level1_batch_example.csv --base-url https://passports.example-sme.co.uk --out my-passports
[OK]    line 2 (PP-2026-0142) -> my-passports/PP-2026-0142.jsonld
[OK]    line 3 (HD-2026-0311) -> my-passports/HD-2026-0311.jsonld
[OK]    line 4 (PET-2026-0077) -> my-passports/PET-2026-0077.jsonld

3 passport(s) written to my-passports/, 0 row(s) with errors
```

Replace `https://passports.example-sme.co.uk` with the web address where you
will publish passports (your own domain, or the address your platform
provider gives you). It does not need to be live yet, but it should be an
address you control, because the passport ID is permanent.

Options:

| Option | Meaning |
|---|---|
| `--out DIR` | Where to write files (default `./passports`) |
| `--base-url URL` | Used to mint passport IDs for rows without `passport_id` or `gtin`+`lot` |
| `--force` | Overwrite files that already exist. Without it the tool refuses, so you cannot overwrite an issued passport by accident. |
| `--quiet` | Only print errors and the summary |

Exit code `0` means every row converted; `1` means some rows had errors (good
rows are still written); `2` means the file could not be read at all.

## Step 3: validate

```
$ python tools/validate.py my-passports/*.jsonld
[PASS]  my-passports/HD-2026-0311.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
[PASS]  my-passports/PET-2026-0077.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)
[PASS]  my-passports/PP-2026-0142.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: batch (from subjectType)

3/3 file(s) valid
```

Exit code `0` means all valid. You can put this command in a scheduled job
or CI pipeline.

## What you get

Here is the PET row from the example spreadsheet as a passport
(`my-passports/PET-2026-0077.jsonld`):

```json
{
  "@context": [
    "https://schema.materialspassport.org.uk/v0.2/context.jsonld",
    "https://schema.materialspassport.org.uk/v0.1/plastics-context.jsonld"
  ],
  "type": "ukmp:MaterialPassport",
  "passportId": "https://passports.example-sme.co.uk/passports/urn:uuid:45ec88ca-0a9a-525f-bee5-eb2497f9186d",
  "subjectType": "MaterialBatch",
  "alternativeId": {
    "scheme": "internal-batch-ref",
    "value": "PET-2026-0077"
  },
  "conformanceLevel": 1,
  "issuerParty": {
    "name": "Example SME Reprocessing Ltd",
    "role": "reprocessor"
  },
  "issueDate": "2026-10-16",
  "description": "Clear PET flake, post-industrial thermoform skeleton, EuCertPlast-certified site",
  "sectorProfile": "https://schema.materialspassport.org.uk/v0.1/profiles/plastics",
  "composition": {
    "materialFamily": "polymer",
    "ukmp-plastics:polymerType": "PET",
    "ukmp-plastics:form": "flake",
    "ukmp-plastics:colour": "clear",
    "substances": [
      {
        "name": "Polyethylene terephthalate",
        "massFraction": 0.99,
        "casNumber": "25038-59-9"
      },
      {
        "name": "Residual contamination (non-target polymer)",
        "massFraction": 0.01
      }
    ]
  },
  "recycledContent": {
    "preConsumerFraction": 1.0,
    "postConsumerFraction": 0.0,
    "totalRecycledFraction": 1.0,
    "calculationMethod": "batch-segregation",
    "chainOfCustodyModel": "segregated",
    "evidenceType": "third-party-certificate",
    "evidenceRefs": [
      "https://certificates.example-cert-body.eu/EUCP-UK-0000-ILLUSTRATIVE"
    ],
    "verificationStatus": "self-declared",
    "feedstockSource": "post-industrial"
  }
}
```

Note that this batch is 100 % **pre-consumer**. It is still a 100 % recycled
batch under ISO 14021, but from 1 April 2027 pre-consumer plastic no longer
counts towards the Plastic Packaging Tax 30 % threshold. Chapter 3 explains.

The example rows show the three common cases:

| Row | Shows |
|---|---|
| `PP-2026-0142` | No GS1 numbers: ID minted from `--base-url`; Companies House number; supplier declaration; End of Waste by individual assessment; `191204` normalised to `19 12 04` |
| `HD-2026-0311` | GS1 GTIN + lot: ID is a GS1 Digital Link; UK date `15/10/2026` and percentages (`98.5%`) accepted; carbon footprint; PPT fields |
| `PET-2026-0077` | Third-party certificate as evidence; pre-consumer feedstock |

## When a row is wrong

The converter checks each row and tells you the line number, the column and
what to do. Rows with errors are not written; the others are. This is real
output from a copy of the example file with six deliberate mistakes:

```
$ python tools/csv_to_passport.py batches_with_mistakes.csv --base-url https://passports.example-sme.co.uk --out passports
[ERROR] line 2 (PP-2026-0142): post_consumer_fraction: 95 is outside 0-1 (looks like a percentage; write 87% or 0.87)
[ERROR] line 3 (HD-2026-0311): gtin: '5.06099E+12' must be 8-14 digits (no spaces). Tip: format the column as Text in Excel so leading zeros survive
[ERROR] line 4 (PET-2026-0077): evidence_type: 'epcis-event-chain' is Level 2 - it needs the event chain, which a spreadsheet row cannot carry. Use supplier-declaration or third-party-certificate at Level 1 (see guide chapter 03)
[ERROR] line 5 (PP-2026-0143): issue_date: '14-10-2026' is not a date (use 2026-10-14 or 14/10/2026)
[ERROR] line 6 (PP-2026-0144): total_recycled_fraction (0.9) must equal pre_consumer_fraction + post_consumer_fraction (0.05 + 0.95 = 1.0)
[ERROR] line 7 (PP-2026-0145): carbon_footprint_kgco2e_per_kg, lca_boundary and lca_methodology must be filled together (or all left empty)

0 passport(s) written to passports/, 6 row(s) with errors
```

A misspelt column header stops the whole run (exit code 2):

```
$ python tools/csv_to_passport.py typo_header.csv --out passports
error: unknown column(s): postconsumer_fraction. Check spelling against templates/level1_batch_template.csv
```

Forgetting `--base-url` when a row has neither `passport_id` nor `gtin`+`lot`:

```
[ERROR] line 2 (PP-2026-0142): passport_id is empty and no gtin+lot given, so --base-url is needed to mint an ID (e.g. --base-url https://passports.yourco.co.uk)
```

Running a second time into the same folder:

```
[ERROR] line 2 (PP-2026-0142): my-passports/PP-2026-0142.jsonld already exists (use --force to overwrite)
```

If you changed facts about a batch whose passport you have already sent to a
customer, do not just overwrite it: issue a **revision** (chapter 5) so the
customer can see what changed.

## Next steps

- Publish the files at their `passportId` addresses, or load them into a
  platform that implements the exchange API (chapter 5).
- Print the passport ID as a QR code on the bag label or delivery note.
- When you are ready to back the recycled-content figure with your
  weighbridge and process records, move to Level 2 (chapter 3).
