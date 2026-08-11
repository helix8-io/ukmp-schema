# Examples

Worked example passports at different conformance levels. Every file in this
directory is validated in CI by `tools/validate.py`.

| File | Level | What it shows |
|---|---|---|
| `example_passport.jsonld` | 3 — Verified | A VC-enveloped passport for a 1-tonne batch of post-consumer recycled HDPE pellet: full EPCIS event chain (bale intake → sort → shred → wash → extrude → blend → bag → despatch), mass-balance-derived 87 % post-consumer content, cradle-to-gate LCA (0.42 kg CO₂e/kg), UK regulatory block (End of Waste, PPT in scope with evidence), plastics profile fields, W3C VC envelope with Data Integrity proof structure. **The signature value is illustrative, not a real signature.** |
| `example_level1_minimal.jsonld` | 1 — Core | The smallest useful passport: a bare (non-enveloped) self-declared passport for a batch of PP regrind, identified by an internal batch reference, with composition and a `declared` recycled-content claim. No event chain, no proof — the realistic starting point for an SME exporting from a spreadsheet or ERP. |

Validate them:

```bash
python tools/validate.py examples/example_passport.jsonld examples/example_level1_minimal.jsonld
```

The validator reports the detected conformance level for each file and warns
where evidence references cannot be resolved within the document.
