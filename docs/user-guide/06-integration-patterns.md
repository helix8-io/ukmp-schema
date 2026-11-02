# 6. Integration patterns

For IT suppliers and in-house developers. Pick the pattern that matches the
systems a site already has. They combine: most sites start with the CSV
on-ramp and add ERP hooks later.

| Pattern | Use when | Conformance level reached |
|---|---|---|
| A. CSV on-ramp | No integration budget; data lives in spreadsheets or an ERP report | 1 |
| B. ERP goods-in and despatch hooks | Weighbridge/ERP records intake and despatch | 1, and the intake/despatch half of 2 |
| C. MES / process event emission | Line PLCs, MES or batch records capture process steps and weights | 2 |
| D. LCA import | You have a carbon footprint from an LCA tool or consultant | Any (adds `environmentalFootprint`) |
| E. Webhooks | You need to react to partners' revisions, recalls or inbound passports | Any |

## Design rules that apply to every pattern

1. **IDs are permanent.** Generate `passportId` and `eventID` once and store
   them against the batch or transaction in your system. Never regenerate them
   from mutable data such as a description.
2. **Append, never update.** Changes become revisions (`POST .../revisions`),
   events are added, not edited. Design your database the same way: keep
   the issued document and its revision number.
3. **Idempotency keys belong to the business transaction.** Derive or store
   one per batch issue or per despatch, so a retry after a crash cannot create
   a duplicate.
4. **Validate before sending.** Run `tools/validate.py` (or call
   `POST /verify?resolve=false`) in your pipeline. It is much cheaper than a
   `422` from a partner.
5. **Weights in kilograms, fractions 0 to 1.** Convert tonnes and percentages
   at the boundary, once.

## A. CSV on-ramp

The fastest route, covered fully in chapter 2.

```
ERP report / spreadsheet --> CSV (template columns) --> csv_to_passport.py --> validate.py --> publish or POST /passports
```

Integration tips:

- Build the CSV as a **saved report** in the ERP, with columns named exactly
  as in `templates/level1_batch_template.csv`. Then it is a scheduled export,
  not a manual task.
- Run the converter with `--quiet` in a nightly job; exit code `1` means at
  least one row needs attention, so alert on it.
- Each generated file can be POSTed as-is to `POST /passports`
  (`Content-Type: application/ld+json`). Use a UUIDv5 of the batch reference
  as the `Idempotency-Key`, for the same reason the converter uses one for the
  passport ID.

## B. ERP goods-in and despatch hooks

Most recyclers' ERP or weighbridge software already records two moments that
matter: **material in** and **material out**. Hook both.

### Goods-in hook

Trigger: weighbridge ticket confirmed / goods receipt posted.

Emit an EPCIS `ObjectEvent` (`action: ADD`, `bizStep: receiving`) with:

| EPCIS field | From the ERP |
|---|---|
| `eventID` | New URI, stored on the goods receipt |
| `eventTime`, `eventTimeZoneOffset` | Ticket time |
| `quantityList[].epcClass` | Lot ID you assign at intake |
| `quantityList[].quantity`, `uom: KGM` | Net weight in kg |
| `sourceList` (`owning_party`) | Supplier GLN or Companies House number |
| `bizLocation.id` | Your site GLN (or site URI) |

Also store, against the lot: the supplier's waste transfer note reference, and
whether the feedstock is post-consumer or pre-consumer. That classification is
what Level 2 recycled-content claims and PPT notes (chapter 3) depend on.

If the delivery arrived **with** a passport (pushed to you by the supplier's
`POST /exchanges`, see pattern E), record the supplier's `passportId` against
the lot and reply with your goods-in `eventID` in the acknowledgement. Your
later output passport can then be issued as a **successor** of that input
passport where the input batch is consumed (chapter 5, Step 6).

### Despatch hook

Trigger: delivery note / despatch advice posted.

1. Emit an `ObjectEvent` (`action: OBSERVE`, `bizStep: shipping`) with the
   output lot, weight, customer (`destinationList`) and the SSCC of the
   pallet/load if you print one.
2. If the passport is not yet Level 2 complete, append an `evidence-added`
   revision with the despatch event.
3. Call `POST /exchanges` with the passport, the customer's endpoint, and the
   `despatch` block: `sscc`, `despatchAdviceId`, `shippingEventID`,
   `expectedDeliveryDate`.
4. Print the passport ID (or a GS1 Digital Link) as a QR code on the delivery
   note and bag labels, for customers without an API.

The customer's acknowledgement carries **their** goods-in event ID. Store it:
that is the evidence that the passport and the physical load arrived together.

## C. MES and process event emission

Level 2 needs a `TransformationEvent` for each step that changes the material:
shred, wash, extrude, compound, blend.

Where to get the data:

| Site maturity | Source of the event |
|---|---|
| Paper batch sheets | Supervisor keys input lots and weights into a simple form at end of shift; the form posts the event |
| Batch records in ERP/MES | Emit the event when a production order is closed |
| PLC / SCADA with load cells | Emit on lot change at the line, using hopper and output scale totals |

Each event needs:

- **all** input lots with weights (`inputQuantityList`), including virgin
  material, masterbatch and additives;
- the output lot(s) with weights (`outputQuantityList`);
- `ukmp:massBalanceDelta` with `inputKg`, `outputKg`, `wasteKg`, where
  `inputKg = outputKg + wasteKg` (±0.5 kg).

Practical points:

- **Close the balance at the event, not at month end.** If the line does not
  measure waste, set `wasteKg = inputKg - outputKg` and record the measured
  values elsewhere for your own loss analysis.
- **Blending is the important step.** It is where recycled and virgin
  material meet and where the recycled fraction is set.
- **NIR and lab results** become `inspecting` ObjectEvents with
  `ukmp:verificationExtension` (instrument, polymer, contamination). Link them
  to the lot they measured.
- Store events in an EPCIS 2.0 repository if you have one; the passport can
  then reference or embed them. `GET /passports/{key}/events` serves them to
  partners.

## D. LCA import

The passport carries LCA **results**, not the model. Whatever tool or
consultant produced the footprint, map its output to `environmentalFootprint`:

| Field | Required | From the LCA report |
|---|---|---|
| `carbonFootprintKgCo2ePerKg` | Yes | Climate change result (GWP100), kg CO2e per kg of product |
| `assessmentBoundary` | Yes | `cradle-to-gate`, `gate-to-gate` or `cradle-to-grave` |
| `methodology` | Yes | e.g. `ISO 14067`, `PEF`, `GHG Protocol Product Standard` |
| `dataQualityRating` | No | 1 to 5 (PEF DQR style) |
| `primaryDataFraction` | No | Share of the result from your own measured data, 0 to 1 |
| `energySource.gridKwh`, `.onSiteRenewablesKwh` | No | Metered energy for the batch, if you have it |
| `virginBaselineKgCo2ePerKg` (`value`, `source`) | No | Footprint of the equivalent virgin material, **with its source** |
| `netAvoidedKgCo2ePerKg` | No | Baseline value minus your footprint. Only with a baseline. |

Rules:

- Convert per-tonne results to **per kg** (divide by 1,000).
- Never put a "carbon saving" figure in a passport without the
  `virginBaselineKgCo2ePerKg` and its `source`. The specification
  deliberately sets no default baseline.
- If the footprint is a site average rather than batch-specific, say so in
  `methodology` (e.g. `ISO 14067; site annual average 2025`) and keep
  `primaryDataFraction` honest.
- In the spreadsheet route, the three required columns are
  `carbon_footprint_kgco2e_per_kg`, `lca_boundary`, `lca_methodology`.

## E. Webhooks

Subscribe to notifications instead of polling. The API defines four:

| Event | Fired when | Typical reaction |
|---|---|---|
| `passport.revised` | A passport you subscribe to gets a revision | Fetch the new revision (`data.href`); re-check claims you rely on |
| `passport.revoked` | A passport is revoked or suspended (or a suspension lifted) | Quarantine stock from that batch; alert quality team |
| `passport.succeeded` | A successor passport is issued | Link the new passport in your records |
| `exchange.received` | A supplier pushes a passport to your goods-in endpoint | Match it to the expected delivery; reply with your acknowledgement |

Every webhook is a JSON body like:

```json
{
  "id": "5a7c9e1b-3d5f-4a2c-8e0b-6d4f2a8c0e13",
  "type": "passport.revoked",
  "occurredAt": "2026-09-15T08:00:02Z",
  "source": "https://passports.example-recycler.co.uk/ukmp/v1",
  "data": { "passportId": "...", "status": "revoked", "reason": "recall", "...": "..." }
}
```

Your receiver must:

1. **Verify the signature first.** The `UKMP-Webhook-Signature` header is a
   detached compact JWS (`header..signature`) over the raw request body,
   signed with a key from the sender's `/.well-known/ukmp/keys` (on the
   origin of `source`). Verify against the **raw bytes** before parsing, and
   reject anything that fails.
2. **Respond quickly with 2xx** (`204` is fine) and do the work afterwards.
   Non-2xx responses are retried with exponential backoff for up to 24 hours.
3. **De-duplicate on `id`.** Retries mean you can receive the same event more
   than once.
4. For `exchange.received`: reply `200` with a signed delivery acknowledgement
   (`receivedAt`, `receivedBy`, `digest` of what you received, and your
   `goodsInEventID`). If the passport does not match the delivery (wrong lot
   for the despatch advice), reply `422` with a
   `.../problems/despatch-mismatch` problem; the sender's exchange then shows
   `rejected`.

## Choosing where the passport lives

| Option | Good for | Watch out for |
|---|---|---|
| Static files on your website at the `passportId` address | Level 1, very small volumes | No tiered access, no status list; you must still never edit a published file |
| A platform implementing the exchange API | Most SMEs from Level 2 | Make sure you can export everything (passports, events, revision history) if you change provider |
| Your own deployment of the reference implementation (D2.2, when released) | Larger operators and platforms | You own key custody (chapter 4) and uptime |

Whichever you choose, the `passportId` must keep resolving for as long as the
material is in use. Pick a domain you will keep.
