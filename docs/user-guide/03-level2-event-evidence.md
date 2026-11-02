# 3. Level 2: event evidence

At Level 1 your recycled-content figure is a statement. At Level 2 it is a
**calculation anyone can repeat** from the records you already keep: goods-in
weights, process logs and despatch notes.

You do this by adding an event diary, `processingHistory.epcisEvents`, using
the GS1 **EPCIS 2.0** event format. EPCIS is the standard many ERP, WMS and
traceability systems already use for "what happened, when, where and why".

The worked example for this chapter is
[`examples/level2_pp_pellet.jsonld`](examples/level2_pp_pellet.jsonld): 975 kg
of grey PP pellet made from post-consumer bales, bought-in post-industrial
trim, and a little virgin masterbatch.

## The four events every recycler needs

| Your process step | EPCIS event type | `bizStep` | What it must carry |
|---|---|---|---|
| Goods-in (weighbridge) | `ObjectEvent`, `action: ADD` | `receiving` | Weight (`quantityList`), lot ID, supplier (`sourceList`) |
| Sorting / NIR check / lab test | `ObjectEvent`, `action: OBSERVE` | `inspecting` | Optional `ukmp:verificationExtension` (instrument, polymer, contamination) |
| Shred, wash, extrude, **blend** | `TransformationEvent` | `transforming` | Input lots and weights, output lot and weight, and `ukmp:massBalanceDelta` |
| Despatch | `ObjectEvent`, `action: OBSERVE` | `shipping` | Output lot, weight, customer (`destinationList`) |

Packing into bags or octabins can be an `AggregationEvent` (`bizStep: packing`)
if you track bag or pallet IDs (SSCCs).

### Intake

```json
{
  "eventID": "https://passports.example-sme.co.uk/events/intake-pc-bales",
  "type": "ObjectEvent", "action": "ADD", "bizStep": "receiving",
  "eventTime": "2026-10-20T08:10:00Z", "eventTimeZoneOffset": "+01:00",
  "quantityList": [{ "epcClass": "https://id.gs1.org/01/05060987654000/10/IN-2026-0981", "quantity": 1000, "uom": "KGM" }],
  "sourceList": [{ "type": "owning_party", "source": "urn:epc:id:sgln:5060555.00001.0" }],
  "bizLocation": { "id": "urn:epc:id:sgln:5060123.45678.0" }
}
```

`uom: KGM` is the UN/ECE code for kilograms. The `epcClass` is the lot you
assign at goods-in. If you do not have GS1 numbers, any stable URI for the lot
works (for example `https://passports.example-sme.co.uk/lots/IN-2026-0981`).
The intake lot is what makes the feedstock **post-consumer** or
**pre-consumer**: record the supplier and keep the waste transfer note or
supplier declaration the classification is based on.

### Sort / inspect

```json
{
  "eventID": "https://passports.example-sme.co.uk/events/nir-sort",
  "type": "ObjectEvent", "action": "OBSERVE", "bizStep": "inspecting",
  "eventTime": "2026-10-21T09:00:00Z", "eventTimeZoneOffset": "+01:00",
  "quantityList": [{ "epcClass": "https://id.gs1.org/01/05060987654000/10/IN-2026-0981", "quantity": 1000, "uom": "KGM" }],
  "ukmp:verificationExtension": { "instrument": "NIR", "measuredPolymerClass": "PP", "contaminationLevel": 0.038 }
}
```

### Transform, with the mass-balance delta

Each processing step that changes the material is a `TransformationEvent`. It
lists what went in and what came out, and carries `ukmp:massBalanceDelta`:

```json
{
  "eventID": "https://passports.example-sme.co.uk/events/extrude-blend",
  "type": "TransformationEvent", "bizStep": "transforming",
  "eventTime": "2026-10-22T13:20:00Z", "eventTimeZoneOffset": "+01:00",
  "inputQuantityList": [
    { "epcClass": "https://id.gs1.org/01/05060987654000/10/FL-2026-0150", "quantity": 905, "uom": "KGM" },
    { "epcClass": "https://id.gs1.org/01/05060987654000/10/IN-2026-0982", "quantity": 50, "uom": "KGM" },
    { "epcClass": "https://id.gs1.org/01/05060987654000/10/VIRGIN-PP-MB-2210", "quantity": 45, "uom": "KGM" }
  ],
  "outputQuantityList": [{ "epcClass": "https://id.gs1.org/01/05060987654338/10/PP-2026-0150", "quantity": 975, "uom": "KGM" }],
  "ukmp:massBalanceDelta": { "inputKg": 1000, "outputKg": 975, "wasteKg": 25 }
}
```

Rules:

- `inputKg` must equal `outputKg + wasteKg`. The validator allows 0.5 kg for
  weighbridge rounding. Anything else fails (see chapter 8).
- `wasteKg` is everything that left the step other than product: fines, wash
  sludge, labels, moisture loss, purge. If you do not know the split, put the
  whole difference in `wasteKg`, so that the books balance.
- **Every input and output lot must be listed.** This is what lets a verifier
  walk from your output back to the intake lots ("traversability"). A
  transformation with no inputs breaks the chain.

### Despatch

```json
{
  "eventID": "https://passports.example-sme.co.uk/events/despatch",
  "type": "ObjectEvent", "action": "OBSERVE", "bizStep": "shipping",
  "eventTime": "2026-10-23T07:45:00Z", "eventTimeZoneOffset": "+01:00",
  "quantityList": [{ "epcClass": "https://id.gs1.org/01/05060987654338/10/PP-2026-0150", "quantity": 975, "uom": "KGM" }],
  "destinationList": [{ "type": "owning_party", "destination": "urn:epc:id:sgln:5060888.00003.0" }]
}
```

The customer's goods-in system can match this event to its own receiving event
(chapter 6, "ERP goods-in and despatch hooks").

## Turning events into a recycled-content claim

The claim block changes in three ways from Level 1:

```json
"recycledContent": {
  "preConsumerFraction": 0.05,
  "postConsumerFraction": 0.905,
  "totalRecycledFraction": 0.955,
  "calculationMethod": "controlled-blending",
  "chainOfCustodyModel": "segregated",
  "evidenceType": "epcis-event-chain",
  "evidenceRefs": [
    "https://passports.example-sme.co.uk/events/intake-pc-bales",
    "https://passports.example-sme.co.uk/events/intake-pi-scrap",
    "https://passports.example-sme.co.uk/events/shred-wash",
    "https://passports.example-sme.co.uk/events/extrude-blend"
  ],
  "verificationStatus": "evidence-linked",
  "feedstockSource": "mixed"
}
```

1. `evidenceType` becomes `epcis-event-chain`.
2. `evidenceRefs` lists the `eventID`s the figure is derived from.
3. `verificationStatus` becomes `evidence-linked`.

### Recomputing the figure

A buyer, auditor or the validator can now redo the sum:

| Step | Event | Recycled post-consumer kg | Recycled pre-consumer kg | Virgin kg | Total kg |
|---|---|---|---|---|---|
| Intake | `intake-pc-bales` | 1,000 | | | 1,000 |
| Intake | `intake-pi-scrap` | | 50 | | 50 |
| Shred + wash (1,000 in, 905 out, 95 waste) | `shred-wash` | 905 | | | 905 |
| Extrude + blend (input) | `extrude-blend` | 905 | 50 | 45 | 1,000 |
| **Share of blend input** | | **0.905** | **0.050** | 0.045 | 1.000 |

Process losses in the extruder (25 kg) are assumed to be spread evenly across
the blend, so the 975 kg output has the same shares as the 1,000 kg input:
post-consumer 0.905, pre-consumer 0.05, total 0.955. That matches the claim.
If the claim said 0.98, a verifier redoing this sum would catch it.

Validate the example:

```
$ python tools/validate.py docs/user-guide/examples/level2_pp_pellet.jsonld
[PASS]  docs/user-guide/examples/level2_pp_pellet.jsonld (bare passport)
        detected conformance level: 2 (Evidence-linked)
        identity level: batch (declared)

1/1 file(s) valid
```

What `tools/validate.py` checks today (document-local checks):

- schema validity, including `evidenceRefs` being present for
  `epcis-event-chain` claims;
- `totalRecycledFraction` = `preConsumerFraction` + `postConsumerFraction`;
- every `ukmp:massBalanceDelta` balances (`inputKg = outputKg + wasteKg`,
  ±0.5 kg);
- every `evidenceRef` matches an event in the file (a warning if not).

It does **not yet** walk the input/output lots to recompute the fraction
automatically; that genealogy walk is part of the WP2 reference
implementation behind `POST /verify` (chapter 5). The table above is the
calculation it performs.

## "Mass balance": two different things

The word is used for two unrelated ideas. Keep them apart:

| | `ukmp:massBalanceDelta` | `calculationMethod: mass-balance` / `chainOfCustodyModel: mass-balance` |
|---|---|---|
| What it is | Weight reconciliation on one process step: in = out + waste | A chain-of-custody **allocation** model (ISO 22095): recycled and virgin are mixed and recycled content is assigned on paper, not necessarily physically present in the batch |
| Who uses it | Everyone at Level 2 | Mainly chemical recycling and certified book-keeping schemes |

A mechanical recycler who physically blends recycled and virgin material and
reports the real proportions is doing **controlled blending** with a
**segregated** recycled stream, as in the example above. Use
`calculationMethod: controlled-blending` (or `batch-segregation` when there
is no virgin input). Every TransformationEvent should still carry a
`ukmp:massBalanceDelta`.

## Plastic Packaging Tax (PPT) notes

Recyclers do not usually pay PPT themselves, but your customers (converters
and packaging importers) need your figure to decide whether their packaging
reaches the **30 % recycled plastic** threshold. Points to get right:

1. **Pre-consumer versus post-consumer.** Record them separately, never just
   a total. HMRC has announced that **from 1 April 2027 pre-consumer plastic
   no longer counts towards the 30 % threshold** (Finance Act 2021 s.49
   amended). Until then, pre-consumer plastic counts if it is genuinely
   recycled and not your own process scrap reused in the same process. In
   the example, the PPT-relevant figure is 0.955 up to 31 March 2027 but only
   **0.905** from 1 April 2027. The example passport carries 0.905 in
   `ukRegulatory.pptStatus.recycledFractionForPpt` to be safe after that date.
2. **`feedstockSource`** (new in v0.2) says where the recycled input came from
   (`post-consumer-packaging`, `post-consumer-bottle`, `post-industrial`,
   `mixed`, and so on). It helps a customer see at a glance whether the
   material is post-consumer. Use `mixed` when a batch combines sources, as
   in the example, and rely on the pre/post fractions for the split.
3. **Mass-balance for PPT applies to chemically recycled plastic only.** From
   1 April 2027 HMRC accepts a certified mass-balance approach for
   **chemically recycled** plastic, where the supply chain is covered by a
   certification scheme meeting HMRC's minimum requirements. **Mechanically
   recycled plastic is outside that route**: a PPT claim for mechanical
   recyclate must rest on recycled plastic physically present in the
   component. So for mechanical recyclate used for PPT, avoid
   `calculationMethod: mass-balance` and `chainOfCustodyModel: mass-balance`;
   use `controlled-blending`, `batch-segregation` or `segregated`, backed by
   the event chain.
4. **Evidence granularity.** HMRC expects the customer to hold evidence. A
   Level 2 passport lets them point at specific events (`pptStatus.evidenceRef`
   names the blend event in the example). Validation partners are still
   confirming with their auditors what granularity is enough (spec open
   issue 3).

This is a summary of published HMRC policy as at November 2026, not tax
advice. Check the current HMRC guidance:
[Plastic Packaging Tax: mass balance approach and removal of pre-consumer plastic](https://www.gov.uk/government/publications/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic).

## End of Waste

If material stops being waste at a known step, record it:
`ukRegulatory.endOfWasteStatus.atEvent` names the event (the extrude-blend
event in the example). Before that point the material carries an EWC code;
after it, it is product.

## Checklist: Level 1 to Level 2

- [ ] Every intake, transform and despatch step produces an event with an
      `eventID` that never changes once issued.
- [ ] Every TransformationEvent lists all input and output lots and has a
      `ukmp:massBalanceDelta` that balances.
- [ ] Pre- and post-consumer feedstock are identifiable from the intake
      events (supplier, waste transfer note).
- [ ] `recycledContent` uses `evidenceType: epcis-event-chain`,
      `verificationStatus: evidence-linked`, and lists the events in
      `evidenceRefs`.
- [ ] `python tools/validate.py` reports `detected conformance level: 2`.
