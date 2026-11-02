# WP3 attribute-mapping tests — UK Materials Passport v0.2 baseline

Innovate UK project 10188380 · WP3 cross-sector feasibility · run 2026-11-02
Baseline under test: UKMP v0.1 core + plastics profile + the v0.2 baseline extensions **B1–B4** (and the optional core field `recycledContent.feedstockSource`), as defined in the v0.2 design brief.

| File | What it is |
|---|---|
| `batteries_batterypass_v1.2.csv` | **Full test.** Every attribute in the Battery Pass v1.2 data model mapped to UKMP (93 rows) |
| `textiles_jrc_pilot.csv` | **Pilot.** Textile apparel DPP as *proposed* by the JRC study (May 2026). This is proposal-level, not the final delegated act |
| `construction_pipe_pilot.csv` | **Pilot.** One CPR product family, thermoplastic non-pressure drainage pipe, built from public sources only |
| `compute_metrics.py` | Stdlib script. Reads the three CSVs, prints the results and writes `metrics_results.json` |
| `_src/` | Clone of `batterypass/BatteryPassDataModel` (gitignored) |

Reproduce: `python3 mapping/compute_metrics.py`

---

## 1. Method

This is the WP3 method, applied exactly. Each **mandatory and conditional** attribute of a reference model goes into one class:

- **(a)** maps to an existing core or profile term with compatible datatype and cardinality
- **(b)** maps only after a baseline extension B1–B4
- **(c)** needs a new sector-profile term
- **(d)** needs a further core change beyond B1–B4

**Coverage** = (a+b+c)/total. **Bespoke share** = (c+d)/total.
**Thresholds:** batteries proceed if ≥ 80 % in (a)+(b) **and** zero (d). Construction proceeds if bespoke share ≤ 20 %.

Optional attributes are kept in the CSVs for completeness but are left out of the totals. The script reads the first word of `model_obligation` (`mandatory` / `conditional` / `optional`).

### Classification rules applied

These rules make the a/b/c/d boundary repeatable:

1. **(a)** needs a core or profile term that **exists today** (v0.1 core or `ukmp-plastics`). The unit must be compatible: a straight % → 0–1 rescale counts as compatible, a different reference quantity does not. Cardinality must also match. Level 2 (EPCIS) routes count as (a) only for attributes that are traceability records by nature (EN 15343).
2. **(b)** covers B1 (`identityLevel`, `gs1:sgtin`, `productTypeRef`, `aggregation`), B2 (`lifecycle`), B3 (`accessPolicy`), B4 (`fieldStatus`) and `recycledContent.feedstockSource`. An attribute whose only blocker is an access tier is (b) when it targets an existing term. If it needs a new profile term it is (c), and the B3 dependency is noted.
3. **(c)** is a new term in a sector-profile namespace (`ukmp-batteries:`, `ukmp-textiles:`, `ukmp-construction:`, or a new `ukmp-plastics:` term). It may sit at passport level or inside the designated core extension points: `composition` (declared `additionalProperties: true`, the same pattern as `ukmp-plastics:polymerType` / `additives`) and EPCIS event objects. A (c) term may reuse a core `$def` such as `ukmp:Party` without changing it.
4. **(d)** applies when the attribute's concept is **already owned by a core class**, but the core term is incompatible in unit, cardinality or structure, or the attribute needs a new property on a core `$def` outside the extension points (`party`, `recycledContentClaim`, `lcaSummary`). Expressing these in a profile would create a second, parallel definition of a core concept (for example a profile-level carbon footprint beside `environmentalFootprint`). That breaks design principle 5, "sector extension by profile, not by fork". Profiles may also only *restrict* core enums, so extending a core enum is (d).
5. Rows marked **PROMOTE** in `notes` are (c) items whose concept is horizontal: ESPR/CPR requirements that recur across sectors, such as facility identifier, manufacturing date, conformity documents, substances-of-concern location and end-of-life information. They are counted as (c), not (d), because the profile mechanism can carry them. They are listed in §4 as candidates to promote into the core.

---

## 2. Results

| Sector | Status | Total in scope | (a) | (b) | (c) | (d) | (a)+(b) | Coverage | Bespoke share | Threshold | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Batteries (Battery Pass v1.2) | full test | 82 (of 93; 11 optional excluded) | 2 | 2 | 63 | **15** | **4.9 %** | 81.7 % | 95.1 % | (a+b) ≥ 80 % **and** d = 0 | **FAIL — do not proceed** (both conditions fail) |
| Textiles (JRC proposal) | pilot | 26 | 8 | 1 | 14 | 3 | 34.6 % | 88.5 % | 65.4 % | none (pilot) | n/a |
| Construction (plastic drainage pipe) | pilot | 62 | 13 | 3 | 27 | 19 | 25.8 % | 69.4 % | **74.2 %** | bespoke ≤ 20 % | **FAIL — do not proceed** |

**Plain reading:**

- **Batteries fails the proceed test on both conditions.**
  - **(a)+(b) is 4.9 %.** UKMP has no batteries profile yet, so all 63 battery-specific performance, label, circularity and due-diligence attributes are (c). The (a)+(b) ≥ 80 % rule assumes those terms already exist. As written, it cannot be met by any sector without an existing profile.
  - **Zero-(d) fails with 15 core gaps across 5 distinct core changes.** This is the substantive finding: **B1–B4 are not sufficient for batteries.** The 15 (d) items come from three core classes: `ukmp:Party` (contact details), `ukmp:LcaSummary` (per-kg, single-indicator, no stage breakdown, no study reference) and `ukmp:RecycledContentClaim` (one claim, no material scope).
  - B1 and B2 work as intended: item identity and lifecycle status map cleanly. B3 is needed by 29 of the 82 attributes for legitimate-interest or authority access, and B4 by the carbon-footprint and recycled-content items whose delegated acts are not yet adopted.
- **Construction fails the bespoke-share test by a wide margin (74 % against ≤ 20 %).**
  - 27 (c) are product-specific essential characteristics, DoPC metadata and documents. A family-specific DoPC is bespoke by nature.
  - 19 (d) come mostly from the EN 15804+A2 multi-indicator, per-module environmental block, which the single per-kg `lcaSummary` cannot carry.
  - The test fails under every alternative reading we checked (§3).
- **Textiles (pilot) has the best fit.** 88.5 % coverage with 3 (d), and the (d) items are the same Party and LCA gaps found in the other two sectors. This rests on a summary of a proposal: see Limitations.

### (d) items — every one, with proposed resolution

| # | Sector | Aspect | Attribute | Core change | Proposed resolution (all additive; v0.1 passports stay valid) |
|---|---|---|---|---|---|
| 1 | Batteries | GeneralProductInformation | Manufacturer identifier and information | D1 | Add optional `address` (PostalAddress shape: street, postcode, locality, country ISO 3166) and `contactPoint {email, url}` to `$defs.party`. Add optional passport-level `parties[]`. Extend `role` with `importer`, `authorised-representative`, `distributor`, `operator` |
| 2 | Batteries | CarbonFootprintForBatteries | Battery carbon footprint per functional unit (kg CO₂e/kWh) | D2 | Add `lcaSummary.declaredUnit {quantity, unit, description}` and `carbonFootprintPerDeclaredUnit`. Relax `required` to anyOf(per-kg, per-declared-unit), which keeps existing per-kg passports valid |
| 3 | Batteries | CarbonFootprintForBatteries | Contribution: raw material acquisition and pre-processing | D3 | Add `lcaSummary.indicators[] {indicator, stageOrModule, value, unit}`, with indicator codes from EN 15804+A2 / PEF and stage codes from the Battery CF act or EN 15804 modules |
| 4 | Batteries | CarbonFootprintForBatteries | Contribution: main product production | D3 | as #3 |
| 5 | Batteries | CarbonFootprintForBatteries | Contribution: distribution | D3 | as #3 |
| 6 | Batteries | CarbonFootprintForBatteries | Contribution: end of life and recycling | D3 | as #3 |
| 7 | Batteries | CarbonFootprintForBatteries | Web link to public carbon footprint study | D4 | Add `lcaSummary.studyRefs[]` (URI) and optional `verifierParty`, mirroring `recycledContentClaim` |
| 8 | Batteries | Circularity | Pre-consumer recycled nickel share | D5 | Add optional core `recycledContentDetail[]`. Each item is a `recycledContentClaim` plus `scope {material (name / element / CAS), component}`. The aggregate `recycledContent` stays as it is |
| 9 | Batteries | Circularity | Pre-consumer recycled cobalt share | D5 | as #8 |
| 10 | Batteries | Circularity | Pre-consumer recycled lithium share | D5 | as #8 |
| 11 | Batteries | Circularity | Pre-consumer recycled lead share | D5 | as #8 |
| 12 | Batteries | Circularity | Post-consumer recycled nickel share | D5 | as #8 |
| 13 | Batteries | Circularity | Post-consumer recycled cobalt share | D5 | as #8 |
| 14 | Batteries | Circularity | Post-consumer recycled lithium share | D5 | as #8 |
| 15 | Batteries | Circularity | Post-consumer recycled lead share | D5 | as #8 |
| 16 | Textiles | Producer information | Manufacturer / importer / economic operators: identity and contact | D1 | as #1 |
| 17 | Textiles | Product information | Environmental footprint — absolute values (PEF, per functional unit) | D2 + D3 | as #2 and #3 (PEF 16 impact categories) |
| 18 | Textiles | Product information | Environmental footprint calculation parameters | D4 | as #7 |
| 19 | Construction | Identification & operators | Manufacturer name, trade name, postal / electronic address | D1 | as #1 |
| 20 | Construction | Identification & operators | Authorised representative (where appointed) | D1 | as #1 (`parties[]` + role `authorised-representative`) |
| 21 | Construction | Essential characteristics | Recycled content per layer (multilayer pipe) | D5 | as #8 (`scope.component = layer`) |
| 22 | Construction | Environmental | Declared / functional unit | D2 | as #2 |
| 23 | Construction | Environmental | GWP-total, modules C1–C4 | D3 | as #3 |
| 24 | Construction | Environmental | GWP-total, module D | D3 | as #3. Do **not** reuse `netAvoidedKgCo2ePerKg`, which is a different quantity |
| 25 | Construction | Environmental | GWP-fossil | D3 | as #3 |
| 26 | Construction | Environmental | GWP-biogenic | D3 | as #3 |
| 27 | Construction | Environmental | GWP-luluc | D3 | as #3 |
| 28 | Construction | Environmental | ODP | D3 | as #3 |
| 29 | Construction | Environmental | AP | D3 | as #3 |
| 30 | Construction | Environmental | EP-freshwater | D3 | as #3 |
| 31 | Construction | Environmental | EP-marine | D3 | as #3 |
| 32 | Construction | Environmental | EP-terrestrial | D3 | as #3 |
| 33 | Construction | Environmental | POCP | D3 | as #3 |
| 34 | Construction | Environmental | ADP-minerals & metals | D3 | as #3 |
| 35 | Construction | Environmental | ADP-fossil | D3 | as #3 |
| 36 | Construction | Environmental | WDP | D3 | as #3 |
| 37 | Construction | Environmental | EPD / LCA study reference and verification (AVCP 3+) | D4 | as #7 |

One optional battery attribute ("Absolute battery carbon footprint", D2) is also (d). It is excluded from the metrics because it is optional.

**The 37 (d) items reduce to five core changes:**

| Code | Core change | Batteries | Textiles | Construction | Suggested label |
|---|---|---:|---:|---:|---|
| D1 | Party contact details + non-issuer parties + role enum | 1 | 1 | 2 | B5 |
| D2 | LCA declared / functional unit | 1 | 1 | 1 | B6 (LCA generalisation) |
| D3 | LCA multi-indicator and stage / module breakdown | 4 | 1 | 14 | B6 |
| D4 | LCA study / evidence reference and verifier | 1 | 1 | 1 | B6 |
| D5 | Scoped (per-material / per-component) recycled-content claims | 8 | 0 | 1 | B7 |

D1, D2 and D4 each appear in all three sectors, and D3 is needed for any EN 15804- or PEF-based declaration. These are sector-neutral gaps in the v0.1 core, not sector-specific ones. A **v0.2.1 / v0.3 "B5–B7" additive set** would clear every (d) found here. With those in the baseline, the 37 (d) items move to (b), and batteries would meet zero-(d). Batteries would still fail the literal (a)+(b) ≥ 80 % test until a `ukmp-batteries` profile is published (see §3).

---

## 3. Sensitivity (reported only; the decisions above use the literal thresholds)

| Reading | Batteries | Construction |
|---|---|---|
| Literal method | (a+b) 4.9 % ✗; d = 15 ✗ | bespoke 74.2 % ✗ |
| "80 %" read as coverage (a+b+c) | 81.7 % ✓, but d = 15 ✗ → still fail | — |
| Exclude the 9 EN 15804 indicators expected to phase in after GWP (`[S:phase2]`) | — | total 53; bespoke 69.8 % ✗; d-only 18.9 % |
| "Bespoke" counted as (d) only | — | 30.6 % ✗ (18.9 % ✓ if phase-2 indicators also excluded) |
| B5–B7 (D1–D5 resolved) added to baseline | d = 0 ✓; (a+b) 23 % ✗ (no batteries profile) | bespoke = (c)/total = 43.5 % ✗ |
| B5–B7 + published `ukmp-batteries` profile importing Battery Pass SAMM terms (c → a) | (a+b) ≈ 100 % ✓; d = 0 ✓ → **would proceed** | — |

Observations:

- For **construction**, the ≤ 20 % bespoke-share threshold can **only** be met if product-specific essential characteristics stop counting as bespoke. One route is a generic declared-performance container: characteristic code, test standard, value, unit, class, keyed to EN ISO 23386/23387 data templates. This is the pattern the construction example passport already points at. The 27 (c) would then become a single structural term plus template references. We recommend WP3 either adopts that container or restates the construction metric. The current result should be reported as a **fail**.
- For **batteries**, the remaining blocker is the absence of the profile itself, not any lack of fit. Battery-specific terms are well-specified in the Battery Pass SAMM model (CC-BY-4.0) and can be imported by reference.

---

## 4. Promotion candidates (counted as (c), concept is horizontal)

Batteries 9, textiles 5, construction 4 (see `PROMOTE` in the CSV notes):

- unique facility identifier / manufacturing place
- manufacturing date
- product mass
- declaration of conformity / DoPC reference
- substances-of-concern location and hazard class (ESPR Art 7(5))
- critical-raw-material flag
- renewable / bio-based content
- disassembly and end-of-life information
- instructions for use and safety information
- customs commodity code

These do not block any threshold. If each profile defines them separately, the result is three slightly different versions of the same concept. Consider them for the core alongside B5–B7.

---

## 5. Limitations

1. **Batteries unit of analysis.** The 93 attributes come from the *Battery Pass Data Attribute Longlist v1.2* (`docs/1.2/2025_Battery_Passport_Data_Attributes_V1.2.xlsx`). This is the attribute definition published with the v1.2 SAMM model and aligned to DIN DKE SPEC 99100:2025-02.
   - Obligation is taken from the longlist's per-category `x` (mandatory per Battery Regulation) and `o` (voluntary, Battery Pass recommendation) flags. `mandatory` = x in all four categories (EV, LMT, industrial > 2 kWh, stationary > 2 kWh). `conditional` = x in some categories only.
   - Each row is cross-referenced to its SAMM property path. Performance uses `io.BatteryPass.Performance` **1.2.1**, the latest patch in the repo. All other aspects use 1.2.0.
   - SAMM sub-properties (e.g. address fields) are treated as part of their parent attribute and are not counted separately.
2. **Textiles is a pilot built on secondary summaries.** The SGS SafeGuardS summary of the JRC study (Textiles_DPP_20260513) and the European Commission textile DPP page were used. The JRC report itself was not read.
   - Neither source labels each item mandatory or voluntary, so items are marked "mandatory (proposed)" except where the text makes them conditional.
   - The delegated act is planned for Q4 2027. Results will move once it is adopted.
   - If it asks for recycled content per fibre, the recycled-content row becomes D5.
3. **Construction is a pilot with significant source limitations.**
   - EN ISO 23387 data templates and the EN 1401-1 / EN 13476 / EN 12666-1 / EN 15343 / EN 15804 texts are paywalled and were **not** consulted. Essential characteristics are taken from public scope descriptions of those standards, and the list must be checked against the standards and the eventual harmonised technical specification.
   - The operative text of Reg (EU) 2024/3110 could not be retrieved: the EUR-Lex fetch returned only the recitals. The national guidance pages were bot-blocked. DoPC and DPP contents come from the European Commission DG GROW presentation "The DPP in the new CPR" and secondary guides. Article and annex numbers are not cited where they could not be verified.
   - The split between GWP and the "phased" EN 15804 indicators is an assumption based on public descriptions.
   - **These pipe standards are not, to our knowledge, currently cited harmonised standards**, so the family's DoPC/DPP obligation depends on a future hTS under the CPR acquis. Every "mandatory" in this CSV is mandatory *once an hTS applies*.
4. **The classification boundary between (c) and (d) is a judgement.** Rule 4 in §1 is the explicit rule.
   - Under a looser rule ("anything a profile can technically carry is (c)"), D1–D5 would be (c), and batteries would have zero (d) but still fail (a)+(b).
   - Under a stricter rule (PROMOTE items counted as (d)), batteries would have 24 (d).
   - The literal result is a fail under all three rules.
5. **Dynamic battery data** (17 in-scope attributes updated by the battery management system) is mapped as profile value objects `{value, lastUpdate}`, with each update a B2 revision. The method treats this as structurally sound. It is **not** tested for update frequency. A signed-snapshot passport may be the wrong vehicle for near-real-time state-of-health data. This is flagged as an open architecture question, not a (d).
6. The core requires `recycledContent` (with `totalRecycledFraction`) on every passport. The Battery Regulation requires recycled content per element only, and not before 2028 (the methodology act is pending). Battery passports would carry a declared aggregate plus a B4 `conditional` status, as `examples/example_battery_item_v02.jsonld` does. This is workable but semantically weak. Consider making `recycledContent` B4-relaxable.
7. The mapping is against the v0.2 baseline as the design brief defines it. The SCHEMA agent was editing `schema/` at the same time. Field names were checked against the working-tree schema on the run date.

---

## 6. Sources

- Battery Pass consortium, *BatteryPassDataModel* (SAMM aspect models v1.2.0 / 1.2.1; Data Attribute Longlist v1.2, Jan 2025; CC-BY-4.0): https://github.com/batterypass/BatteryPassDataModel
- DIN DKE SPEC 99100:2025-02 (referenced by the longlist): https://www.dinmedia.de/en/technical-rule/din-dke-spec-99100/385692321
- Regulation (EU) 2023/1542 (Batteries), Annex XIII and Art 77, as cited in the longlist
- SGS SafeGuardS 091/26, "EU ESPR: JRC study proposes DPP content requirements for textile apparel" (Jul 2026): https://www.sgs.com/en-tr/news/2026/07/safeguards-09126-eu-espr-jrc-study-proposes-dpp-content-requirements-for-textile-apparel
- European Commission, Digital Product Passport — textile apparel: https://single-market-economy.ec.europa.eu/single-market/digital-product-passport/textile-apparel_en
- European Commission DG GROW H.1, "The DPP in the new CPR" (O. Nieto, 2025, CC BY 4.0): https://www.en.une.org/normalizacion_documentos/DPP-in-the-new-CPR---Oscar-Nieto.pdf
- Regulation (EU) 2024/3110 (CPR), EUR-Lex (recitals 51, 52, 91 consulted; operative text not retrievable in this run): https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202403110 and https://eur-lex.europa.eu/eli/reg/2024/3110/oj/eng
- Designing Buildings Wiki, "Declaration of Performance and Conformity (DoPC)": https://www.designingbuildings.co.uk/wiki/Declaration_of_Performance_and_Conformity_DoPC
- Examine China, "Construction Products Regulation (EU) 2024/3110: a practical guide": https://www.examinechina.com/construction-products-regulation-eu-2024-3110/
- Kiwa, EPD e-book (EN 15804 indicators and CPR): https://careers.kiwa.com/globalassets/germany/ecobility-experts/downloads-ecobility-experts/e-book_en_epd-1-1.pdf
- EN 1401-1 (PVC-U non-pressure drainage), EN 13476-2/-3 (structured-wall), EN 12666-1 (PE), EN 15343 (recycled-plastics traceability), EN 15804+A2, EN ISO 23386/23387: catalogue entries only (e.g. https://shop.standards.ie/en-ie/standards/en-1401-1-2009-328556_saig_cen_cen_756424). Full texts were not consulted.

Source tags used in the pilot CSV notes: `[SGS]`, `[EC]` (textiles); `[DGGROW]`, `[CPR-DoPC]`, `[ECHK]`, `[KIWA]`, `[EURLEX]`, `[EN1401]`, `[EN13476]`, `[EN15343]` (construction). `[CPR-DoPC]` marks items stated from general knowledge of the CPR DoPC that could not be checked against the operative text in this run. Treat them as needing verification.

## Re-run against the v0.2 baseline (B1–B9), 2 November 2026

All 37 (d) items were resolved by the additive core extensions B5–B9 now in schema v0.2 (D1→B5, D2→B6, D3→B7, D4→B8, D5→B9). Under the v0.2 baseline they re-classify as (b). Script: `rebaseline_v02.py` → `metrics_results_v02_baseline.json`.

| Sector | Total | a | b | c | d | (a)+(b) | Coverage | Bespoke | Threshold | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Batteries | 82 | 2 | 17 | 63 | 0 | 23.2 % | 100 % | 76.8 % | (a+b) ≥ 80 % and d = 0 | **Fail on (a+b); pass on d = 0.** The 63 (c) items are battery-specific terms to be imported from Battery Pass v1.2 as the `ukmp-batteries` profile; the (a+b) criterion cannot be met until that profile exists. |
| Textiles (pilot) | 26 | 8 | 4 | 14 | 0 | 46.2 % | 100 % | 53.8 % | none | n/a |
| Construction (pilot) | 62 | 13 | 22 | 27 | 0 | 56.5 % | 100 % | 43.5 % | bespoke ≤ 20 % | **Fail.** The 27 (c) items are pipe-specific declared-performance values. |

**Reading.** With v0.2 no sector needs a core change beyond B1–B9, and every in-scope attribute is expressible (coverage 100 %). The remaining gap is sector-profile work, not core design: batteries need the Battery Pass import, construction needs a declared-performance container referencing EN ISO 23387 templates. The batteries (a+b) criterion should be restated for the final WP3 report as "(a)+(b)+(c-imported-from-an-open-reference-model) ≥ 80 % and d = 0", since importing an existing open model is the recommended route.
