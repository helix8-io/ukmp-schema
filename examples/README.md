# Examples

Worked example passports. Every file in this directory is validated in CI by
`tools/validate.py`. The two v0.1 examples are unchanged and remain valid
under the v0.2 schema (v0.2 is strictly additive).

| File | Level | What it shows |
|---|---|---|
| `example_passport.jsonld` | 3 — Verified | A VC-enveloped passport for a 1-tonne batch of post-consumer recycled HDPE pellet: full EPCIS event chain (bale intake → sort → shred → wash → extrude → blend → bag → despatch), 87 % post-consumer content derived from the event genealogy (controlled blending of 890 kg segregated PCR with 130 kg virgin carrier; `segregated` chain of custody — step-level `ukmp:massBalanceDelta` weight reconciliation is not a mass-balance chain-of-custody claim), cradle-to-gate LCA (0.42 kg CO₂e/kg), UK regulatory block (End of Waste, PPT in scope with evidence), plastics profile fields, W3C VC envelope with Data Integrity proof structure. **The signature value is illustrative, not a real signature.** |
| `example_level1_minimal.jsonld` | 1 — Core | The smallest useful passport: a bare (non-enveloped) self-declared passport for a batch of PP regrind, identified by an internal batch reference, with composition and a `declared` recycled-content claim. No event chain, no proof — the realistic starting point for an SME exporting from a spreadsheet or ERP. |
| `example_battery_item_v02.jsonld` | 1 — Core | **v0.2.** Item-level (`identityLevel: item`, `gs1:sgtin`) successor passport for an ex-EV battery pack repurposed into stationary storage: `lifecycle.status: repurposed` with `predecessorRefs` to the original EV passport (B2), module/system `aggregation` (B1), detailed composition at the `legitimate-interest` tier (B3), and `fieldStatus` marking the carbon footprint `not-yet-applicable` under Reg (EU) 2023/1542 Art 7 (B4). The file also shows the manufacturer and importer in `parties[]` (B5); a voluntary per-kWh footprint with battery-stage indicators and a study reference (B6–B8), labelled as not the Art 7 declaration; and per-metal (Co, Ni, Li) `recycledContentDetail` (B9), marked `not-yet-applicable` until 18 Aug 2028. |
| `example_pipe_producttype_v02.jsonld` | 1 — Core | **v0.2.** Product-type passport (`identityLevel: productType`, type GTIN) for a recycled-HDPE non-pressure drainage pipe — the construction overlay case: `recycledContent.feedstockSource`, third-party-certified declared minimum recycled content, and a `conditional` status on environmental indicators under the CPR (Reg (EU) 2024/3110). The file also shows an authorised representative (B5); declared unit 1 m with EN 15804+A2 indicators for A1–A3, C1–C4 and D (D kept separate from `netAvoidedKgCo2ePerKg`), EPD reference and verifier (B6–B8); and per-layer `recycledContentDetail` for the three-layer pipe (B9). |
| `example_pipe_batch_v02.jsonld` | 1 — Core | **v0.2.** Batch passport for one lot of that pipe type, linking to it via `productTypeRef` (optional usage). |

**All v0.2 example values are illustrative.** Company names, identifiers
(the GTINs are drawn from the example GTINs used in GS1 documentation), certificates and figures are
invented for demonstration and do not describe any real organisation or product.

Validate them:

```bash
python tools/validate.py examples/*.jsonld
```

The validator reports the detected conformance level and identity level for
each file, and warns where evidence references cannot be resolved within the
document, where v0.2 JSON Pointers (`accessPolicy.fieldTiers`, `fieldStatus`)
do not resolve, or where lifecycle / identity fields are inconsistent.
