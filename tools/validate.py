#!/usr/bin/env python3
"""UK Materials Passport validator (ukmp v0.1).

Usage:
    python tools/validate.py <passport.jsonld> [<passport.jsonld> ...]

Validates each file against the published JSON Schema
(schema/material_passport.schema.json), then runs the semantic checks a
Level 2 verifier performs:

  * recycled-content arithmetic: totalRecycledFraction must equal
    preConsumerFraction + postConsumerFraction (when both are present);
  * mass-balance reconciliation: for every EPCIS TransformationEvent
    carrying ukmp:massBalanceDelta, inputKg must equal
    outputKg + wasteKg;
  * epcis-event-chain evidence: every evidenceRef of an
    'epcis-event-chain' claim should resolve to an event in
    processingHistory (warning if the event list is absent or a ref is
    unmatched).

Both VC-enveloped passports (W3C Verifiable Credential with the passport
as credentialSubject) and bare passports are accepted. The detected
conformance level (1 Core / 2 Evidence-linked / 3 Verified) is reported.

Exit codes (CI-friendly):
    0  all files valid
    1  one or more files failed validation
    2  usage error, unreadable file, or malformed JSON

Project 10188380 — National Materials Innovation Programme feasibility
study. WP1 deliverable support tooling.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "error: the 'jsonschema' package is required. "
        "Install with: pip install -r tools/requirements.txt\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "material_passport.schema.json"

TOLERANCE_FRACTION = 1e-6   # recycled-content fraction arithmetic
TOLERANCE_KG = 0.5          # mass-balance reconciliation (weighbridge rounding)


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def is_vc_envelope(doc: dict) -> bool:
    """True if the document is a W3C VC wrapping the passport."""
    doc_type = doc.get("type", [])
    if isinstance(doc_type, str):
        doc_type = [doc_type]
    return "credentialSubject" in doc and (
        "VerifiableCredential" in doc_type or "MaterialPassportCredential" in doc_type
    )


def extract_passport(doc: dict) -> tuple[dict, bool]:
    """Return (passport_object, enveloped) for a VC-enveloped or bare passport."""
    if is_vc_envelope(doc):
        subject = doc["credentialSubject"]
        if isinstance(subject, list):  # VC data model allows an array of subjects
            subject = subject[0] if subject else {}
        return subject, True
    return doc, False


def decode_jws(text: str):
    """Decode a JOSE-enveloped credential (compact JWS, spec §6 primary
    securing) WITHOUT verifying the signature. Returns (header, payload)
    dicts or None if the text is not a well-formed compact JWS."""
    import base64

    parts = text.strip().split(".")
    if len(parts) != 3 or not all(parts[:2]):
        return None

    def b64url_json(segment: str):
        padded = segment + "=" * (-len(segment) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))

    try:
        header = b64url_json(parts[0])
        payload = b64url_json(parts[1])
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    return header, payload


def check_schema(passport: dict, validator: Draft202012Validator) -> list[str]:
    errors = []
    for err in sorted(validator.iter_errors(passport), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema: {loc}: {err.message}")
    return errors


def check_recycled_content(passport: dict) -> list[str]:
    errors = []
    claim = passport.get("recycledContent")
    if not isinstance(claim, dict):
        return errors
    pre = claim.get("preConsumerFraction")
    post = claim.get("postConsumerFraction")
    total = claim.get("totalRecycledFraction")
    if isinstance(total, (int, float)) and isinstance(pre, (int, float)) and isinstance(post, (int, float)):
        if not math.isclose(pre + post, total, abs_tol=TOLERANCE_FRACTION):
            errors.append(
                f"recycled-content: totalRecycledFraction ({total}) != "
                f"preConsumerFraction + postConsumerFraction ({pre} + {post} = {pre + post})"
            )
    return errors


def check_mass_balance(passport: dict) -> list[str]:
    errors = []
    history = passport.get("processingHistory")
    if not isinstance(history, dict):
        return errors
    for event in history.get("epcisEvents", []):
        if not isinstance(event, dict):
            continue
        delta = event.get("ukmp:massBalanceDelta")
        if not isinstance(delta, dict):
            continue
        event_id = event.get("eventID", "(no eventID)")
        input_kg = delta.get("inputKg")
        output_kg = delta.get("outputKg")
        waste_kg = delta.get("wasteKg", 0)
        if isinstance(input_kg, (int, float)) and isinstance(output_kg, (int, float)) \
                and isinstance(waste_kg, (int, float)):
            if not math.isclose(input_kg, output_kg + waste_kg, abs_tol=TOLERANCE_KG):
                errors.append(
                    f"mass-balance: event {event_id}: inputKg ({input_kg}) != "
                    f"outputKg + wasteKg ({output_kg} + {waste_kg} = {output_kg + waste_kg})"
                )
    return errors


def check_evidence_chain(passport: dict) -> list[str]:
    """Warnings (not errors): epcis-event-chain evidenceRefs should match events."""
    warnings = []
    claim = passport.get("recycledContent")
    if not isinstance(claim, dict) or claim.get("evidenceType") != "epcis-event-chain":
        return warnings
    history = passport.get("processingHistory")
    events = history.get("epcisEvents", []) if isinstance(history, dict) else []
    event_ids = {e.get("eventID") for e in events if isinstance(e, dict)}
    if not event_ids:
        warnings.append(
            "evidence: evidenceType is 'epcis-event-chain' but processingHistory "
            "carries no events — chain not traversable from this document alone"
        )
        return warnings
    for ref in claim.get("evidenceRefs", []):
        if ref not in event_ids:
            warnings.append(f"evidence: evidenceRef {ref} not found in processingHistory.epcisEvents")
    return warnings


def detect_conformance_level(passport: dict, enveloped: bool, doc: dict,
                             jose_secured: bool = False) -> int:
    """Detect the conformance level per spec §8 (machine-detectable).
    A credential is secured either by a JOSE envelope (primary) or an
    embedded Data Integrity proof (permitted alternative)."""
    level = 1
    history = passport.get("processingHistory")
    has_events = isinstance(history, dict) and bool(history.get("epcisEvents"))
    claim = passport.get("recycledContent", {})
    status = claim.get("verificationStatus") if isinstance(claim, dict) else None
    if has_events and status in ("evidence-linked", "independently-verified"):
        level = 2
    secured = jose_secured or (enveloped and isinstance(doc.get("proof"), dict))
    if enveloped and secured and level >= 2:
        level = 3
    return level


def validate_file(path: Path, validator: Draft202012Validator) -> bool:
    jose_secured = False
    try:
        doc = load_json(path)
    except json.JSONDecodeError:
        # Not JSON — a JOSE-enveloped credential (compact JWS)?
        try:
            decoded = decode_jws(path.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"[ERROR] {path}: cannot read: {exc}")
            sys.exit(2)
        if decoded is None:
            print(f"[ERROR] {path}: neither JSON nor a compact JWS")
            sys.exit(2)
        _, doc = decoded
        jose_secured = True
    except OSError as exc:
        print(f"[ERROR] {path}: cannot read/parse: {exc}")
        sys.exit(2)

    if not isinstance(doc, dict):
        print(f"[FAIL]  {path}: top-level JSON value must be an object")
        return False

    passport, enveloped = extract_passport(doc)

    errors = []
    errors += check_schema(passport, validator)
    errors += check_recycled_content(passport)
    errors += check_mass_balance(passport)
    warnings = check_evidence_chain(passport)

    if jose_secured:
        envelope_note = "JOSE-enveloped (JWS)"
    elif enveloped:
        envelope_note = "VC-enveloped"
    else:
        envelope_note = "bare passport"
    if errors:
        print(f"[FAIL]  {path} ({envelope_note})")
        for err in errors:
            print(f"        - {err}")
    else:
        level = detect_conformance_level(passport, enveloped, doc,
                                         jose_secured=jose_secured)
        declared = passport.get("conformanceLevel")
        level_names = {1: "Core", 2: "Evidence-linked", 3: "Verified"}
        print(f"[PASS]  {path} ({envelope_note})")
        print(f"        detected conformance level: {level} ({level_names[level]})")
        if declared is not None and declared != level:
            warnings.append(
                f"conformance: declared conformanceLevel {declared} != detected {level}"
            )
        if jose_secured:
            warnings.append(
                "jose: JWS signature present but NOT cryptographically verified by this "
                "tool (Level 3 signature verification is a WP2 reference-implementation "
                "capability)"
            )
        if enveloped and isinstance(doc.get("proof"), dict):
            warnings.append(
                "proof: signature present but NOT cryptographically verified by this tool "
                "(Level 3 proof verification is a WP2 reference-implementation capability)"
            )
    for warn in warnings:
        print(f"        ! {warn}")
    return not errors


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2

    try:
        schema = load_json(SCHEMA_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: cannot load schema {SCHEMA_PATH}: {exc}\n")
        return 2
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    results = [validate_file(Path(arg), validator) for arg in argv[1:]]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} file(s) valid")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
