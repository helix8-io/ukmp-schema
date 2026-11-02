# 7. Sector profiles

The passport has one **core** (identity, composition, recycled content,
events, carbon, UK regulatory fields) and optional **sector profiles** that add
fields for one industry. The core never changes per sector; a profile adds a
JSON-LD context, narrows some core choices, and maps sector process steps to
EPCIS business steps.

| Profile | Status in v0.2 | Context file |
|---|---|---|
| Plastics (`ukmp-plastics`) | **Normative.** Validated with partners in WP4. | `schema/plastics-context.jsonld` |
| Batteries (`ukmp-batteries`) | **WP3 interim.** Imports Battery Pass v1.2. Mapping tests re-run on v0.2 (`mapping/README.md`). | Not yet published |
| Textiles (`ukmp-textiles`) | **WP3 interim.** Reuses plastics profile for synthetic fibre. Mapping tests re-run on v0.2 (`mapping/README.md`). | Not yet published |
| Construction (`ukmp-construction`) | **WP3 interim.** Overlay on EN ISO 23387 data templates. Mapping tests re-run on v0.2 (`mapping/README.md`). | Not yet published |

> **WP3 interim** means: the approach is decided and worked examples exist,
> but the attribute-by-attribute mapping tests have not been completed and no
> profile context is published. Do not build production integrations against
> the non-plastics profiles yet; do use the core fields, which are stable for
> v0.2.

The WP3 finding behind v0.2: none of the three sectors needed a breaking
change to the core, but all of them needed four sector-neutral additions,
which are now in the core for everyone: identity levels (B1), succession
(B2), access tiers (B3) and field status (B4). See chapter 1.

## Plastics (normative)

What the profile adds, inside `composition`:

| Field | Values | CSV column |
|---|---|---|
| `ukmp-plastics:polymerType` | `PET`, `HDPE`, `LDPE`, `PP`, `PS`, `PVC`, `other` (ISO 1043) | `polymer_type` |
| `ukmp-plastics:form` | `bale`, `flake`, `pellet`, `regrind` | `form` |
| `ukmp-plastics:colour` | free text | `colour` |
| `ukmp-plastics:foodContactGrade` | true / false | `food_contact_grade` |
| `ukmp-plastics:foodContactAssessmentRef` | link to the food-contact assessment | (not in CSV) |
| `ukmp-plastics:additives` | list of `{name, casNumber, massFraction}` | (use `substanceN_` columns) |

To use it, add the plastics context to `@context` and set
`sectorProfile: https://schema.materialspassport.org.uk/v0.1/profiles/plastics`.
`csv_to_passport.py` does both automatically when any plastics column is
filled.

Plastics passports **should** also fill the core `recycledContent.feedstockSource`
(`post-consumer-packaging`, `post-consumer-bottle`, `post-industrial`,
`mixed`, ...). PPT notes are in chapter 3.

Worked examples: chapter 2 (Level 1 from CSV), chapter 3 (Level 2,
`docs/user-guide/examples/level2_pp_pellet.jsonld`),
`examples/example_passport.jsonld` (Level 3).

## Batteries (WP3 interim): import Battery Pass v1.2

The project does **not** define its own battery data model. The Battery Pass
consortium data model v1.2 (aligned with DIN DKE SPEC 99100) already covers
the EU Battery Regulation (EU) 2023/1542 passport content in seven groups:
general product information, carbon footprint, circularity, material
composition, performance and durability, labels, supply-chain due diligence.
The batteries profile **imports and maps** that model.

What the UK passport core adds on top of Battery Pass:

- recycled-content chain-of-custody evidence (the same claim structure and
  event chain as plastics);
- EPCIS provenance events;
- succession when a battery is repurposed or remanufactured (B2);
- field-level access tiers matching the Regulation's public / legitimate
  interest split (B3);
- field status for obligations whose EU methodology acts are not yet adopted
  (B4);
- the Verifiable Credential trust layer.

How the core fields are used for batteries:

| Need | Core field |
|---|---|
| One passport per battery (Art 77(3)) | `identityLevel: item`, `subjectType: Item`, `gs1:sgtin` (GTIN + serial) or a serialised `alternativeId` |
| Battery model | `productTypeRef` pointing to a product-type passport |
| Modules within a pack, pack within a storage system | `aggregation.childRefs` / `parentRefs` |
| Repurposed / remanufactured battery gets a new passport (Art 77(7)) | Successor passport (`lifecycle.status: repurposed`, `predecessorRefs`), via `POST .../successors` |
| Battery becomes waste | A **revision** of the same passport |
| Detailed composition, dismantling info: legitimate interest only | `accessPolicy.fieldTiers` |
| Carbon footprint not yet applicable (Art 7 methodology act not adopted) | `fieldStatus` entry with `status: not-yet-applicable`, `basis`, `reviewBy` |

Mapping status: the attribute-level mapping of Battery Pass v1.2 to the core
(`mapping/batteries_batterypass_v1.2.csv`) was re-run against v0.2 on
2 November 2026 — see `mapping/README.md`, "Re-run against the v0.2
baseline": zero (d) in all sectors and coverage 100 %; batteries (a)+(b)
23.2 % pending the Battery Pass profile import; construction bespoke share
43.5 %. Until the `ukmp-batteries` profile is published, keep
battery-specific attributes in their Battery Pass form and use the UK core
for the fields in the table above.

Worked example: `examples/example_battery_item_v02.jsonld` (illustrative:
a repurposed ex-EV pack). Validate it:

```
$ python tools/validate.py examples/example_battery_item_v02.jsonld
[PASS]  examples/example_battery_item_v02.jsonld (bare passport)
        detected conformance level: 1 (Core)
        identity level: item (declared)
        lifecycle status: repurposed

1/1 file(s) valid
```

## Textiles (WP3 interim)

- Most recycled polyester today is made from **PET bottles**, so recycled
  synthetic fibre is largely a plastics-recyclate stream. The textiles
  profile reuses the plastics profile for synthetic fibre composition, with
  extra polymer types to be added (PA6/PA66, PAN, elastane).
- The bottle-versus-textile distinction is attracting market and regulatory
  attention. Record it in the core `feedstockSource`:
  `post-consumer-bottle`, `post-consumer-textile`,
  `post-industrial-textile`.
- Certificates such as GRS / RCS go in `recycledContent.evidenceRefs` (with
  `evidenceType: third-party-certificate`), or as separate Verifiable
  Credentials.
- The EU ESPR textiles delegated act is not adopted. Profile fields will carry
  `fieldStatus: not-yet-applicable` until it is.
- Still to define: fibre composition per the Textile Labelling Regulation,
  durability score, care information.

## Construction (WP3 interim): overlay on EN ISO 23387

- The EU construction-products passport (Construction Products Regulation
  (EU) 2024/3110) is at **product-type** level; recycled-content claims are at
  **batch** level. Use a `productType` passport for the product and batch
  passports that point to it with `productTypeRef`.
- **Overlay, not redefinition:** declared performance (the digital declaration
  of performance and conformity) is carried by referencing **EN ISO 23387 data
  templates**, with EN 15804+A2 EPDs for environmental indicators. The UK core
  supplies what those templates lack: the upstream recyclate chain of custody.
- First case studied: **recycled-HDPE non-pressure drainage pipe**.
  Examples: `examples/example_pipe_producttype_v02.jsonld` and
  `examples/example_pipe_batch_v02.jsonld` (illustrative values).
- Northern Ireland manufacturers may face the EU CPR passport (Windsor
  Framework) while GB develops its own approach; the overlay is designed to
  serve both.
- Open issue: building service lives (50 to 100+ years) outlast regulatory
  retention periods, so long-term custody of passports needs design.

## Using a profile that is not published yet

If you need batteries, textiles or construction passports now:

1. Fill the **core** fields fully; they are stable for v0.2.
2. Put sector attributes in their established form (Battery Pass JSON-LD, EN
   ISO 23387 template reference) and link to them, rather than inventing
   `ukmp-` field names.
3. Use `fieldStatus` to say which obligations are not yet applicable and why.
4. Expect to revise the passports (an `update` revision) when the profile
   context is published.
