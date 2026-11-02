#!/usr/bin/env python3
"""Convert a spreadsheet (CSV) of material batches into Level 1 UK Materials
Passports.

Usage:
    python tools/csv_to_passport.py <batches.csv> --base-url <https://...> [--out DIR]
                                    [--force] [--quiet]

One CSV row = one batch = one passport. Each passport is written as a bare
(non-enveloped) JSON-LD document, the same shape as
examples/example_level1_minimal.jsonld, to <DIR>/<batch_ref>.jsonld.

Start from templates/level1_batch_template.csv; a filled example is in
templates/level1_batch_example.csv. Column meanings are documented in
docs/user-guide/02-quickstart-level1-from-spreadsheet.md.

Level 1 ("Core") means: identity + passport content, with the recycled-content
claim marked verificationStatus = self-declared. Event evidence (Level 2) and
signing (Level 3) are added by other tooling.

The passport ID is taken, in order of preference, from:
  1. the passport_id column, if filled;
  2. a GS1 Digital Link URI built from gtin + lot, if both are filled;
  3. <base-url>/passports/urn:uuid:<uuid5 of issuer name + batch_ref>.
     The UUID is deterministic, so re-running the tool on the same row gives
     the same passport ID (no accidental duplicates).

Only the Python 3 standard library is used. Validate the output with:
    python tools/validate.py <DIR>/*.jsonld

Exit codes:
    0  all rows converted
    1  one or more rows had errors (no files written for those rows)
    2  usage error, or the CSV could not be read

Project 10188380 (Innovate UK, National Materials Innovation Programme),
WP2 deliverable D2.3 tooling.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path

CONTEXT_CORE = "https://schema.materialspassport.org.uk/v0.2/context.jsonld"
CONTEXT_PLASTICS = "https://schema.materialspassport.org.uk/v0.1/plastics-context.jsonld"
PLASTICS_PROFILE = "https://schema.materialspassport.org.uk/v0.1/profiles/plastics"

# Fixed namespace so passport UUIDs are reproducible across runs and machines.
UKMP_UUID_NAMESPACE = uuid.UUID("6f1c2a52-6a0e-5d3b-9f43-0b1a7e5c2d10")

MAX_SUBSTANCES = 5

ENUMS = {
    "subject_type": ["MaterialBatch", "Product", "Component", "ProductType", "Item"],
    "identity_level": ["productType", "batch", "item"],
    "issuer_role": ["producer", "collector", "sorter", "reprocessor", "compounder",
                    "converter", "manufacturer", "brand", "verifier", "other"],
    "material_family": ["polymer", "metal", "glass", "fibre", "mineral", "composite", "other"],
    "calculation_method": ["mass-balance", "batch-segregation", "controlled-blending", "declared"],
    "chain_of_custody_model": ["identity-preserved", "segregated", "mass-balance", "book-and-claim"],
    "evidence_type": ["third-party-certificate", "supplier-declaration", "epcis-event-chain"],
    "verification_status": ["self-declared"],
    "feedstock_source": ["post-consumer-packaging", "post-consumer-bottle", "post-consumer-textile",
                         "post-industrial", "post-industrial-textile", "mixed", "other"],
    "polymer_type": ["PET", "HDPE", "LDPE", "PP", "PS", "PVC", "other"],
    "form": ["bale", "flake", "pellet", "regrind"],
    "end_of_waste_basis": ["quality-protocol", "individual-assessment", "not-applicable"],
    "waste_hierarchy_position": ["preparation-for-reuse", "recycling", "recovery"],
    "lca_boundary": ["cradle-to-gate", "gate-to-gate", "cradle-to-grave"],
}

# Every column the tool understands. Unknown columns are an error (catches typos).
KNOWN_COLUMNS = [
    "batch_ref", "id_scheme", "passport_id", "gtin", "lot", "subject_type", "identity_level",
    "issuer_name", "issuer_role", "issuer_gln", "issuer_companies_house",
    "issue_date", "description", "material_family",
    "polymer_type", "form", "colour", "food_contact_grade",
] + [f"substance{_i}_{part}" for _i in range(1, MAX_SUBSTANCES + 1)
     for part in ("name", "mass_fraction", "cas", "svhc")] + [
    "pre_consumer_fraction", "post_consumer_fraction", "total_recycled_fraction",
    "calculation_method", "chain_of_custody_model", "evidence_type", "evidence_refs",
    "verification_status", "feedstock_source",
    "ewc_code", "end_of_waste_achieved", "end_of_waste_basis", "waste_hierarchy_position",
    "recovery_code", "ppt_in_scope", "ppt_recycled_fraction", "epr_category",
    "permit_ref",
    "carbon_footprint_kgco2e_per_kg", "lca_boundary", "lca_methodology",
]

REQUIRED_COLUMNS = ["batch_ref", "issuer_name", "issue_date", "material_family",
                    "substance1_name", "substance1_mass_fraction"]

TRUE_WORDS = {"true", "yes", "y", "1"}
FALSE_WORDS = {"false", "no", "n", "0"}


class RowError(Exception):
    """A problem with one cell; message names the column."""


def cell(row: dict, col: str) -> str:
    value = row.get(col)
    return value.strip() if isinstance(value, str) else ""


def parse_fraction(row: dict, col: str, required: bool = False):
    raw = cell(row, col)
    if not raw:
        if required:
            raise RowError(f"{col}: required, but empty")
        return None
    percent = raw.endswith("%")
    text = raw.rstrip("%").strip()
    try:
        value = float(text)
    except ValueError:
        raise RowError(f"{col}: '{raw}' is not a number (use 0.87 or 87%)") from None
    if percent:
        value = value / 100.0
    if not 0.0 <= value <= 1.0:
        hint = " (looks like a percentage; write 87% or 0.87)" if 1 < value <= 100 else ""
        raise RowError(f"{col}: {raw} is outside 0-1{hint}")
    return round(value, 6)


def parse_number(row: dict, col: str):
    raw = cell(row, col)
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        raise RowError(f"{col}: '{raw}' is not a number") from None
    if value < 0:
        raise RowError(f"{col}: must not be negative")
    return value


def parse_bool(row: dict, col: str):
    raw = cell(row, col).lower()
    if not raw:
        return None
    if raw in TRUE_WORDS:
        return True
    if raw in FALSE_WORDS:
        return False
    raise RowError(f"{col}: '{cell(row, col)}' is not yes/no")


def parse_enum(row: dict, col: str, default: str | None = None):
    raw = cell(row, col)
    if not raw:
        return default
    allowed = ENUMS[col]
    for option in allowed:
        if raw.lower() == option.lower():
            return option
    raise RowError(f"{col}: '{raw}' is not one of: {', '.join(allowed)}")


def parse_date(row: dict, col: str) -> str:
    raw = cell(row, col)
    if not raw:
        raise RowError(f"{col}: required, but empty")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise RowError(f"{col}: '{raw}' is not a date (use 2026-10-14 or 14/10/2026)")


def gtin14(gtin: str) -> str:
    return gtin.zfill(14)


def build_passport(row: dict, base_url: str | None) -> dict:
    batch_ref = cell(row, "batch_ref")
    if not batch_ref:
        raise RowError("batch_ref: required, but empty")
    issuer_name = cell(row, "issuer_name")
    if not issuer_name:
        raise RowError("issuer_name: required, but empty")

    gtin = cell(row, "gtin")
    lot = cell(row, "lot")
    if gtin and not re.fullmatch(r"[0-9]{8,14}", gtin):
        raise RowError(f"gtin: '{gtin}' must be 8-14 digits (no spaces). "
                       "Tip: format the column as Text in Excel so leading zeros survive")
    if lot and not gtin:
        raise RowError("lot: filled but gtin is empty (a GS1 lot needs its GTIN)")

    # ---- passport ID -------------------------------------------------------
    passport_id = cell(row, "passport_id")
    if passport_id:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", passport_id):
            raise RowError(f"passport_id: '{passport_id}' is not an absolute URI")
    elif gtin and lot:
        passport_id = f"https://id.gs1.org/01/{gtin14(gtin)}/10/{lot}"
    else:
        if not base_url:
            raise RowError("passport_id is empty and no gtin+lot given, so --base-url "
                           "is needed to mint an ID (e.g. --base-url https://passports.yourco.co.uk)")
        uid = uuid.uuid5(UKMP_UUID_NAMESPACE, f"{issuer_name}|{batch_ref}")
        passport_id = f"{base_url.rstrip('/')}/passports/urn:uuid:{uid}"

    passport: dict = {
        "@context": [CONTEXT_CORE],
        "type": "ukmp:MaterialPassport",
        "passportId": passport_id,
        "subjectType": parse_enum(row, "subject_type", "MaterialBatch"),
    }
    identity_level = parse_enum(row, "identity_level")
    implied = {"MaterialBatch": "batch", "ProductType": "productType", "Item": "item"}.get(
        passport["subjectType"])
    if identity_level and implied and identity_level != implied:
        raise RowError(f"identity_level: '{identity_level}' contradicts subject_type "
                       f"'{passport['subjectType']}' (which means '{implied}')")
    if identity_level:
        passport["identityLevel"] = identity_level

    # ---- identifiers (schema needs at least one) ---------------------------
    if gtin:
        passport["gs1:gtin"] = gtin
    if gtin and lot:
        passport["gs1:lgtin"] = f"{gtin14(gtin)}.{lot}"
    passport["alternativeId"] = {
        "scheme": cell(row, "id_scheme") or "internal-batch-ref",
        "value": batch_ref,
    }

    passport["conformanceLevel"] = 1

    # ---- issuer ------------------------------------------------------------
    issuer: dict = {"name": issuer_name}
    gln = cell(row, "issuer_gln")
    if gln:
        if not re.fullmatch(r"[0-9]{13}", gln):
            raise RowError(f"issuer_gln: '{gln}' must be exactly 13 digits")
        issuer["gs1:gln"] = gln
    ch = cell(row, "issuer_companies_house")
    if ch:
        issuer["otherPartyId"] = {"scheme": "companies-house", "value": ch}
    role = parse_enum(row, "issuer_role")
    if role:
        issuer["role"] = role
    passport["issuerParty"] = issuer

    passport["issueDate"] = parse_date(row, "issue_date")
    description = cell(row, "description")
    if description:
        passport["description"] = description

    # ---- composition -------------------------------------------------------
    family = parse_enum(row, "material_family")
    if not family:
        raise RowError("material_family: required, but empty")
    substances = []
    for i in range(1, MAX_SUBSTANCES + 1):
        name = cell(row, f"substance{i}_name")
        frac = parse_fraction(row, f"substance{i}_mass_fraction", required=bool(name))
        if not name:
            if frac is not None:
                raise RowError(f"substance{i}_mass_fraction: filled but substance{i}_name is empty")
            continue
        sub = {"name": name, "massFraction": frac}
        cas = cell(row, f"substance{i}_cas")
        if cas:
            if not re.fullmatch(r"[0-9]{2,7}-[0-9]{2}-[0-9]", cas):
                raise RowError(f"substance{i}_cas: '{cas}' is not a CAS number (e.g. 9003-07-0)")
            sub["casNumber"] = cas
        svhc = parse_bool(row, f"substance{i}_svhc")
        if svhc is not None:
            sub["svhcFlag"] = svhc
        substances.append(sub)
    if not substances:
        raise RowError("substance1_name: at least one substance is required")
    total_mass = sum(s["massFraction"] for s in substances)
    if total_mass > 1.0 + 1e-6:
        raise RowError(f"substance mass fractions add up to {total_mass:.4f}, which is more than 1")

    composition: dict = {"materialFamily": family}
    plastics = {
        "ukmp-plastics:polymerType": parse_enum(row, "polymer_type"),
        "ukmp-plastics:form": parse_enum(row, "form"),
        "ukmp-plastics:colour": cell(row, "colour") or None,
        "ukmp-plastics:foodContactGrade": parse_bool(row, "food_contact_grade"),
    }
    plastics = {k: v for k, v in plastics.items() if v is not None}
    if plastics:
        composition.update(plastics)
        passport["@context"].append(CONTEXT_PLASTICS)
        passport["sectorProfile"] = PLASTICS_PROFILE
    composition["substances"] = substances
    passport["composition"] = composition

    # ---- recycled-content claim -------------------------------------------
    pre = parse_fraction(row, "pre_consumer_fraction")
    post = parse_fraction(row, "post_consumer_fraction")
    total = parse_fraction(row, "total_recycled_fraction")
    if total is None:
        if pre is None and post is None:
            raise RowError("total_recycled_fraction: required (or give pre_ and post_consumer_fraction)")
        total = round((pre or 0.0) + (post or 0.0), 6)
        if pre is not None and post is None:
            post = 0.0
        if post is not None and pre is None:
            pre = 0.0
    if total > 1.0 + 1e-6:
        raise RowError(f"pre_consumer_fraction + post_consumer_fraction = {total}, more than 1")
    if pre is not None and post is not None and abs(pre + post - total) > 1e-6:
        raise RowError(f"total_recycled_fraction ({total}) must equal pre_consumer_fraction + "
                       f"post_consumer_fraction ({pre} + {post} = {round(pre + post, 6)})")

    evidence_type = parse_enum(row, "evidence_type", "supplier-declaration")
    if evidence_type == "epcis-event-chain":
        raise RowError("evidence_type: 'epcis-event-chain' is Level 2 - it needs the event chain, "
                       "which a spreadsheet row cannot carry. Use supplier-declaration or "
                       "third-party-certificate at Level 1 (see guide chapter 03)")
    status_raw = cell(row, "verification_status")
    if status_raw and status_raw.lower() != "self-declared":
        raise RowError(f"verification_status: '{status_raw}' is not allowed at Level 1 - "
                       "Level 1 claims are always self-declared (leave blank)")

    claim: dict = {}
    if pre is not None:
        claim["preConsumerFraction"] = pre
    if post is not None:
        claim["postConsumerFraction"] = post
    claim["totalRecycledFraction"] = total
    claim["calculationMethod"] = parse_enum(row, "calculation_method", "declared")
    coc = parse_enum(row, "chain_of_custody_model")
    if coc:
        claim["chainOfCustodyModel"] = coc
    claim["evidenceType"] = evidence_type
    refs = [r.strip() for r in cell(row, "evidence_refs").split(";") if r.strip()]
    for ref in refs:
        if " " in ref:
            raise RowError(f"evidence_refs: '{ref}' contains a space - separate several refs with ;")
    if refs:
        claim["evidenceRefs"] = refs
    claim["verificationStatus"] = "self-declared"
    feedstock = parse_enum(row, "feedstock_source")
    if feedstock:
        claim["feedstockSource"] = feedstock
    passport["recycledContent"] = claim

    # ---- environmental footprint (all-or-nothing) --------------------------
    cf = parse_number(row, "carbon_footprint_kgco2e_per_kg")
    boundary = parse_enum(row, "lca_boundary")
    method = cell(row, "lca_methodology")
    lca_given = [x is not None and x != "" for x in (cf, boundary, method)]
    if any(lca_given) and not all(lca_given):
        raise RowError("carbon_footprint_kgco2e_per_kg, lca_boundary and lca_methodology "
                       "must be filled together (or all left empty)")
    if all(lca_given):
        passport["environmentalFootprint"] = {
            "carbonFootprintKgCo2ePerKg": cf,
            "assessmentBoundary": boundary,
            "methodology": method,
        }

    # ---- UK regulatory -----------------------------------------------------
    reg: dict = {}
    ewc = cell(row, "ewc_code")
    if ewc:
        ewc_norm = re.sub(r"\s+", " ", ewc)
        if re.fullmatch(r"[0-9]{6}\*?", ewc_norm):
            ewc_norm = f"{ewc_norm[0:2]} {ewc_norm[2:4]} {ewc_norm[4:]}"
        if not re.fullmatch(r"[0-9]{2} [0-9]{2} [0-9]{2}\*?", ewc_norm):
            raise RowError(f"ewc_code: '{ewc}' should look like 19 12 04 (or 19 12 04* if hazardous)")
        reg["ewcCode"] = ewc_norm
    eow = parse_bool(row, "end_of_waste_achieved")
    eow_basis = parse_enum(row, "end_of_waste_basis")
    if eow_basis and eow is None:
        raise RowError("end_of_waste_basis: filled but end_of_waste_achieved is empty")
    if eow is not None:
        reg["endOfWasteStatus"] = {"achieved": eow}
        if eow_basis:
            reg["endOfWasteStatus"]["basis"] = eow_basis
    whp = parse_enum(row, "waste_hierarchy_position")
    if whp:
        reg["wasteHierarchyPosition"] = whp
    rcode = cell(row, "recovery_code").upper()
    if rcode:
        if not re.fullmatch(r"R[0-9]{1,2}", rcode):
            raise RowError(f"recovery_code: '{rcode}' should look like R3")
        reg["recoveryCode"] = rcode
    ppt = parse_bool(row, "ppt_in_scope")
    ppt_frac = parse_fraction(row, "ppt_recycled_fraction")
    if ppt_frac is not None and ppt is None:
        raise RowError("ppt_recycled_fraction: filled but ppt_in_scope is empty")
    if ppt is not None:
        reg["pptStatus"] = {"inScope": ppt}
        if ppt_frac is not None:
            reg["pptStatus"]["recycledFractionForPpt"] = ppt_frac
    epr = cell(row, "epr_category")
    if epr:
        reg["eprCategory"] = epr
    permit = cell(row, "permit_ref")
    if permit:
        reg["permits"] = [{"type": "environmental-permit", "ref": permit}]
    if reg:
        passport["ukRegulatory"] = reg

    return passport


def safe_filename(batch_ref: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", batch_ref).strip("._")
    return (name or "passport") + ".jsonld"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="csv_to_passport.py",
        description="Convert a CSV of batches (one row per batch) into Level 1 UK Materials "
                    "Passports (bare JSON-LD).",
        epilog="Validate the output with: python tools/validate.py <out>/*.jsonld")
    parser.add_argument("csv", help="input CSV (start from templates/level1_batch_template.csv)")
    parser.add_argument("--out", default="passports",
                        help="output directory (created if missing; default: ./passports)")
    parser.add_argument("--base-url",
                        help="your passport web address, used to mint IDs for rows without "
                             "passport_id or gtin+lot, e.g. https://passports.yourco.co.uk")
    parser.add_argument("--force", action="store_true", help="overwrite existing output files")
    parser.add_argument("--quiet", action="store_true", help="only print errors and the summary")
    args = parser.parse_args(argv[1:])

    if args.base_url and not re.match(r"^https?://[^/\s]+", args.base_url):
        print(f"error: --base-url '{args.base_url}' must start with https://", file=sys.stderr)
        return 2

    csv_path = Path(args.csv)
    try:
        # utf-8-sig strips the byte-order mark Excel adds to "CSV UTF-8" exports
        with csv_path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            header = [h.strip() for h in (reader.fieldnames or [])]
            reader.fieldnames = header
            rows = list(reader)
    except OSError as exc:
        print(f"error: cannot read {csv_path}: {exc}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"error: {csv_path} is not UTF-8. In Excel use File > Save As > "
              "'CSV UTF-8 (Comma delimited)'", file=sys.stderr)
        return 2

    if not header:
        print(f"error: {csv_path} is empty (no header row)", file=sys.stderr)
        return 2
    unknown = [h for h in header if h and h not in KNOWN_COLUMNS]
    if unknown:
        print(f"error: unknown column(s): {', '.join(unknown)}. Check spelling against "
              "templates/level1_batch_template.csv", file=sys.stderr)
        return 2
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        print(f"error: required column(s) missing from header: {', '.join(missing)}",
              file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written, failed, seen = 0, 0, {}
    for line_no, row in enumerate(rows, start=2):  # line 1 is the header
        if not any((v or "").strip() for k, v in row.items() if k):
            continue  # blank row
        if None in row:  # more cells than header columns
            print(f"[ERROR] line {line_no}: more cells than header columns "
                  "(an unquoted comma in a description?)")
            failed += 1
            continue
        batch_ref = cell(row, "batch_ref") or "(no batch_ref)"
        try:
            passport = build_passport(row, args.base_url)
        except RowError as exc:
            print(f"[ERROR] line {line_no} ({batch_ref}): {exc}")
            failed += 1
            continue
        fname = safe_filename(batch_ref)
        if fname in seen:
            print(f"[ERROR] line {line_no} ({batch_ref}): duplicate batch_ref "
                  f"(also on line {seen[fname]})")
            failed += 1
            continue
        seen[fname] = line_no
        target = out_dir / fname
        if target.exists() and not args.force:
            print(f"[ERROR] line {line_no} ({batch_ref}): {target} already exists "
                  "(use --force to overwrite)")
            failed += 1
            continue
        target.write_text(json.dumps(passport, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        written += 1
        if not args.quiet:
            print(f"[OK]    line {line_no} ({batch_ref}) -> {target}")

    print(f"\n{written} passport(s) written to {out_dir}/, {failed} row(s) with errors")
    if written == 0 and failed == 0:
        print("note: the CSV has a header but no data rows")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
