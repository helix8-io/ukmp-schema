#!/usr/bin/env python3
"""UK Materials Passport validator (ukmp v0.2; accepts v0.1 passports).

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

v0.2 baseline core extension checks (warnings, never errors, so every
v0.1 passport keeps its v0.1 result):

  * JSON Pointers in accessPolicy.fieldTiers[].path and
    fieldStatus[].path must be syntactically valid RFC 6901 pointers
    (also enforced by the schema) and should resolve within the passport.
    An unresolved fieldTiers path, or an unresolved fieldStatus path whose
    status is 'required', is warned. Absence is expected (not warned) for
    'optional', 'conditional' and 'not-yet-applicable' fields, and a
    voluntarily populated 'not-yet-applicable' field is allowed. Conflicting tiers on one path,
    and identity / issuer / policy fields that resolve to a non-public
    tier (spec §4.8, longest-matching-path rule), are warned;
  * lifecycle consistency: lifecycle.status other than 'original' should
    carry predecessorRefs (a successor passport links to what it
    succeeds); 'original' with predecessorRefs, or a passport listing
    itself as predecessor/successor, is flagged;
  * identity level: an item-level passport (identityLevel 'item', or
    subjectType 'Item' when identityLevel is absent) is expected to carry
    gs1:sgtin or alternativeId; an identityLevel contradicting
    subjectType is flagged;
  * recycledContentDetail (B9): each scoped claim gets the same
    recycled-content arithmetic check as the aggregate claim (an error);
    a scope.componentRef written as a JSON Pointer should resolve (warning).

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
import re
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
        message = err.message
        if err.validator == "anyOf" and not err.absolute_path:
            # The root anyOf is the identifier rule; don't dump the whole passport.
            options = [", ".join(alt.get("required", [])) for alt in err.validator_value]
            message = "no identifier — one of " + " | ".join(options) + " is required"
        errors.append(f"schema: {loc}: {message}")
    return errors


def _claim_arithmetic(claim: dict, label: str) -> list[str]:
    pre = claim.get("preConsumerFraction")
    post = claim.get("postConsumerFraction")
    total = claim.get("totalRecycledFraction")
    if isinstance(total, (int, float)) and isinstance(pre, (int, float)) and isinstance(post, (int, float)):
        if not math.isclose(pre + post, total, abs_tol=TOLERANCE_FRACTION):
            return [
                f"recycled-content: {label}totalRecycledFraction ({total}) != "
                f"preConsumerFraction + postConsumerFraction ({pre} + {post} = {pre + post})"
            ]
    return []


def check_recycled_content(passport: dict) -> list[str]:
    errors = []
    claim = passport.get("recycledContent")
    if isinstance(claim, dict):
        errors += _claim_arithmetic(claim, "")
    # v0.2 B9: the same arithmetic applies to every scoped claim.
    details = passport.get("recycledContentDetail")
    if isinstance(details, list):
        for i, detail in enumerate(details):
            if isinstance(detail, dict):
                errors += _claim_arithmetic(detail, f"recycledContentDetail[{i}]: ")
    return errors


def check_recycled_content_scope(passport: dict) -> list[str]:
    """v0.2 B9: componentRef given as a JSON Pointer should resolve."""
    warnings = []
    details = passport.get("recycledContentDetail")
    if not isinstance(details, list):
        return warnings
    for i, detail in enumerate(details):
        scope = detail.get("scope") if isinstance(detail, dict) else None
        ref = scope.get("componentRef") if isinstance(scope, dict) else None
        if isinstance(ref, str) and ref.startswith("/"):
            if not is_valid_json_pointer(ref):
                warnings.append(f"pointer: recycledContentDetail[{i}].scope.componentRef {ref!r} "
                                f"is not a valid RFC 6901 JSON Pointer")
            elif not resolve_json_pointer(passport, ref):
                warnings.append(f"pointer: recycledContentDetail[{i}].scope.componentRef {ref} "
                                f"does not resolve in this passport")
    return warnings


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


POINTER_TOKEN_ESCAPE = re.compile(r"~(?![01])")


def is_valid_json_pointer(ptr) -> bool:
    """RFC 6901 syntax: '' or a sequence of '/'-prefixed reference tokens
    in which '~' only appears as the escapes '~0' or '~1'."""
    if not isinstance(ptr, str):
        return False
    if ptr == "":
        return True
    return ptr.startswith("/") and not POINTER_TOKEN_ESCAPE.search(ptr)


def resolve_json_pointer(doc, ptr: str) -> bool:
    """True if the (syntactically valid) pointer resolves within doc."""
    if ptr == "":
        return True
    node = doc
    for raw in ptr[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False
            node = node[token]
        elif isinstance(node, list):
            if not (token.isdigit() and (token == "0" or not token.startswith("0"))):
                return False
            idx = int(token)
            if idx >= len(node):
                return False
            node = node[idx]
        else:
            return False
    return True


ALWAYS_PUBLIC_POINTERS = (
    "/type", "/passportId", "/subjectType", "/identityLevel", "/gs1:gtin", "/gs1:lgtin",
    "/gs1:sgtin", "/alternativeId", "/issuerParty", "/issueDate", "/conformanceLevel",
    "/lifecycle/status", "/accessPolicy", "/fieldStatus",
)


def _pointer_covers(prefix: str, ptr: str) -> bool:
    """True if JSON Pointer `prefix` equals `ptr` or is a token-wise ancestor of it."""
    return prefix == "" or ptr == prefix or ptr.startswith(prefix + "/")


def effective_tier(policy: dict, ptr: str) -> str:
    """Spec §4.8 tier resolution: longest covering fieldTiers path wins,
    otherwise defaultTier (default 'public')."""
    best_len, tier = -1, policy.get("defaultTier", "public")
    for entry in policy.get("fieldTiers", []) or []:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if is_valid_json_pointer(path) and _pointer_covers(path, ptr) and len(path) > best_len:
            best_len, tier = len(path), entry.get("tier", tier)
    return tier


def check_field_pointers(passport: dict) -> list[str]:
    """v0.2 B3/B4: accessPolicy.fieldTiers and fieldStatus JSON Pointers."""
    warnings = []
    policy = passport.get("accessPolicy")
    if isinstance(policy, dict):
        seen: dict[str, str] = {}
        for i, entry in enumerate(policy.get("fieldTiers", []) or []):
            if not isinstance(entry, dict):
                continue
            path, tier = entry.get("path"), entry.get("tier")
            where = f"accessPolicy.fieldTiers[{i}]"
            if not is_valid_json_pointer(path):
                warnings.append(f"pointer: {where}.path {path!r} is not a valid RFC 6901 JSON Pointer")
                continue
            if not resolve_json_pointer(passport, path):
                warnings.append(f"pointer: {where}.path {path} does not resolve in this passport "
                                f"(tier '{tier}' applies to nothing)")
            if path in seen and seen[path] != tier:
                warnings.append(f"pointer: {where}.path {path} assigned conflicting tiers "
                                f"'{seen[path]}' and '{tier}'")
            seen.setdefault(path, tier)
        # Spec §4.8: identity, issuer and policy fields must stay public.
        for ptr in ALWAYS_PUBLIC_POINTERS:
            if resolve_json_pointer(passport, ptr):
                tier = effective_tier(policy, ptr)
                if tier != "public":
                    warnings.append(f"access: {ptr} resolves to tier '{tier}' but MUST remain "
                                    f"public (spec §4.8)")
    statuses = passport.get("fieldStatus")
    if isinstance(statuses, list):
        for i, entry in enumerate(statuses):
            if not isinstance(entry, dict):
                continue
            path, status = entry.get("path"), entry.get("status")
            where = f"fieldStatus[{i}]"
            if not is_valid_json_pointer(path):
                warnings.append(f"pointer: {where}.path {path!r} is not a valid RFC 6901 JSON Pointer")
                continue
            present = resolve_json_pointer(passport, path)
            if not present and status == "required":
                warnings.append(f"pointer: {where}.path {path} is marked 'required' but is absent")
    return warnings


LIFECYCLE_ORIGINAL = "original"


def check_lifecycle(passport: dict) -> list[str]:
    """v0.2 B2: successor passports should link to their predecessors."""
    warnings = []
    lifecycle = passport.get("lifecycle")
    if not isinstance(lifecycle, dict):
        return warnings
    status = lifecycle.get("status", LIFECYCLE_ORIGINAL)
    preds = lifecycle.get("predecessorRefs") or []
    succs = lifecycle.get("successorRefs") or []
    if status != LIFECYCLE_ORIGINAL and not preds:
        warnings.append(f"lifecycle: status '{status}' but no predecessorRefs — a successor passport "
                        f"should link to the passport(s) it succeeds")
    if status == LIFECYCLE_ORIGINAL and preds:
        warnings.append("lifecycle: status 'original' but predecessorRefs present — an original "
                        "passport has no predecessor (corrections are revisions, not successors)")
    own_id = passport.get("passportId")
    if own_id and (own_id in preds or own_id in succs):
        warnings.append("lifecycle: passport lists its own passportId as predecessor/successor "
                        "(use a revision, not a successor, for the same subject)")
    return warnings


SUBJECT_TYPE_LEVEL = {"MaterialBatch": "batch", "ProductType": "productType", "Item": "item"}


def effective_identity_level(passport: dict):
    """identityLevel if declared, else interpreted from subjectType (spec §4.6)."""
    level = passport.get("identityLevel")
    if level:
        return level, "declared"
    inferred = SUBJECT_TYPE_LEVEL.get(passport.get("subjectType"))
    return (inferred, "from subjectType") if inferred else (None, None)


def check_identity(passport: dict) -> list[str]:
    """v0.2 B1: item-level passports carry a serialised identifier."""
    warnings = []
    level, _ = effective_identity_level(passport)
    declared = passport.get("identityLevel")
    implied = SUBJECT_TYPE_LEVEL.get(passport.get("subjectType"))
    if declared and implied and declared != implied:
        warnings.append(f"identity: identityLevel '{declared}' contradicts subjectType "
                        f"'{passport.get('subjectType')}' (implies '{implied}')")
    if level == "item" and "gs1:sgtin" not in passport and "alternativeId" not in passport:
        warnings.append("identity: item-level passport without gs1:sgtin or alternativeId — "
                        "a serialised item identifier is expected")
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
    warnings += check_identity(passport)
    warnings += check_lifecycle(passport)
    warnings += check_field_pointers(passport)
    warnings += check_recycled_content_scope(passport)

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
        id_level, id_source = effective_identity_level(passport)
        if id_level:
            print(f"        identity level: {id_level} ({id_source})")
        lifecycle = passport.get("lifecycle")
        if isinstance(lifecycle, dict):
            print(f"        lifecycle status: {lifecycle.get('status', LIFECYCLE_ORIGINAL)}")
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
