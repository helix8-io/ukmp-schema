"""Tests for the UK Materials Passport Exchange API description (D2.1).

Run from the repository root:

    pip install -r tests/api/requirements.txt
    pytest tests/api

What is checked:

* api/openapi.yaml (and the committed single-file bundle) is a valid
  OpenAPI 3.1 document according to openapi-spec-validator;
* every operationId (paths and webhooks) is unique, and the D2.1 operation
  set is present with summary, description, responses and examples;
* every example in the document — media-type examples, parameter and header
  examples, component examples — validates against its schema, with the
  external passport JSON Schema resolved through a ``referencing`` registry;
* every ``examples/*.jsonld`` passport validates as a request body for
  ``POST /passports`` and ``POST /verify``, and a deliberately broken passport
  does not (so the checks above are not vacuous).

These tests are deliberately independent of the passport schema version: they
validate against whatever ``schema/material_passport.schema.json`` is in the
working tree.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

import pytest
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / "api" / "openapi.yaml"
BUNDLE_PATH = REPO / "api" / "dist" / "openapi.bundled.yaml"
PASSPORT_SCHEMA_PATH = REPO / "schema" / "material_passport.schema.json"
EXAMPLE_FILES = sorted((REPO / "examples").glob("*.jsonld"))

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

# The D2.1 operation surface (design brief, api/openapi-draft.md + v0.2 additions).
EXPECTED_OPERATIONS = {
    ("post", "/passports"): "createPassport",
    ("get", "/passports"): "listPassports",
    ("get", "/passports/{passportKey}"): "getPassport",
    ("get", "/passports/{passportKey}/revisions"): "listPassportRevisions",
    ("post", "/passports/{passportKey}/revisions"): "createPassportRevision",
    ("post", "/passports/{passportKey}/successors"): "createPassportSuccessor",
    ("post", "/passports/{passportKey}/status"): "updatePassportStatus",
    ("get", "/passports/{passportKey}/events"): "listPassportEvents",
    ("post", "/verify"): "verifyPassport",
    ("post", "/exchanges"): "createExchange",
    ("get", "/exchanges/{exchangeId}"): "getExchange",
    ("get", "/.well-known/ukmp/keys"): "getIssuerKeys",
    ("get", "/status/{listId}"): "getStatusList",
}
EXPECTED_WEBHOOKS = {"passport.revised", "passport.revoked", "passport.succeeded", "exchange.received"}
EXPECTED_SCOPES = {
    "passports:read",
    "passports:read:legitimate-interest",
    "passports:read:authority",
    "passports:write",
    "verify",
    "exchange",
}


# --------------------------------------------------------------------------- helpers


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _retrieve_from_disk(uri: str) -> Resource:
    """Resolve file: URIs (relative $refs between repo files) from the working tree."""
    parts = urlsplit(uri)
    if parts.scheme != "file":
        raise NoSuchResource(ref=uri)
    path = Path(unquote(parts.path)).resolve()
    if REPO not in path.parents:
        raise NoSuchResource(ref=uri)
    if path.suffix in {".yaml", ".yml"}:
        contents = load_yaml(path)
    else:
        contents = json.loads(path.read_text(encoding="utf-8"))
    return Resource.from_contents(contents, default_specification=DRAFT202012)


def make_registry(spec: dict, spec_uri: str) -> Registry:
    passport = json.loads(PASSPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    passport_res = Resource.from_contents(passport, default_specification=DRAFT202012)
    resources = [
        (spec_uri, Resource.from_contents(spec, default_specification=DRAFT202012)),
        (PASSPORT_SCHEMA_PATH.as_uri(), passport_res),
    ]
    if passport_res.id():
        resources.append((passport_res.id(), passport_res))
    return Registry(retrieve=_retrieve_from_disk).with_resources(resources)


def escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def pointer(*tokens: Any) -> str:
    return "/" + "/".join(escape(str(t)) for t in tokens)


class SpecWalker:
    """Collects (schema-pointer, example-value, location) triples from a spec."""

    def __init__(self, spec: dict):
        self.spec = spec

    def deref(self, obj: dict, ptr: str) -> tuple[dict, str]:
        """Follow local component $refs (responses, parameters, headers, examples)."""
        seen = set()
        while isinstance(obj, dict) and "$ref" in obj and str(obj["$ref"]).startswith("#/"):
            ref = obj["$ref"]
            if ref in seen:
                raise AssertionError(f"circular $ref {ref}")
            seen.add(ref)
            node: Any = self.spec
            for tok in ref[2:].split("/"):
                node = node[tok.replace("~1", "/").replace("~0", "~")]
            obj, ptr = node, ref[1:]
        return obj, ptr

    def _examples_of(self, holder: dict, ptr: str, where: str) -> Iterator[tuple[str, Any, str]]:
        if "schema" not in holder:
            return
        schema_ptr = ptr + "/schema"
        if "example" in holder:
            yield schema_ptr, holder["example"], f"{where} example"
        for name, ex in (holder.get("examples") or {}).items():
            ex, _ = self.deref(ex, f"{ptr}/examples/{escape(name)}")
            if "value" in ex:
                yield schema_ptr, ex["value"], f"{where} examples.{name}"

    def _content(self, content: dict, ptr: str, where: str):
        for media, mt in (content or {}).items():
            yield from self._examples_of(mt, f"{ptr}/content/{escape(media)}", f"{where} [{media}]")

    def _parameters(self, params: list, ptr: str, where: str):
        for i, p in enumerate(params or []):
            p, pptr = self.deref(p, f"{ptr}/parameters/{i}")
            yield from self._examples_of(p, pptr, f"{where} param {p.get('name')}")

    def _headers(self, headers: dict, ptr: str, where: str):
        for name, h in (headers or {}).items():
            h, hptr = self.deref(h, f"{ptr}/headers/{escape(name)}")
            yield from self._examples_of(h, hptr, f"{where} header {name}")

    def _operation(self, op: dict, ptr: str, where: str):
        yield from self._parameters(op.get("parameters"), ptr, where)
        if "requestBody" in op:
            rb, rbptr = self.deref(op["requestBody"], ptr + "/requestBody")
            yield from self._content(rb.get("content"), rbptr, f"{where} requestBody")
        for code, resp in (op.get("responses") or {}).items():
            resp, rptr = self.deref(resp, f"{ptr}/responses/{code}")
            yield from self._content(resp.get("content"), rptr, f"{where} {code}")
            yield from self._headers(resp.get("headers"), rptr, f"{where} {code}")

    def operations(self) -> Iterator[tuple[str, str, str, dict, str]]:
        """Yield (kind, key, method, operation, pointer) for paths and webhooks."""
        for kind in ("paths", "webhooks"):
            for key, item in (self.spec.get(kind) or {}).items():
                for method, op in item.items():
                    if method in HTTP_METHODS:
                        yield kind, key, method, op, pointer(kind, key, method)

    def all_examples(self) -> Iterator[tuple[str, Any, str]]:
        for kind in ("paths", "webhooks"):
            for key, item in (self.spec.get(kind) or {}).items():
                yield from self._parameters(item.get("parameters"), pointer(kind, key), f"{key}")
        for _, key, method, op, ptr in self.operations():
            yield from self._operation(op, ptr, f"{method.upper()} {key}")
        comps = self.spec.get("components", {})
        for name, p in (comps.get("parameters") or {}).items():
            yield from self._examples_of(p, pointer("components", "parameters", name), f"parameter {name}")
        for name, h in (comps.get("headers") or {}).items():
            yield from self._examples_of(h, pointer("components", "headers", name), f"header {name}")
        for name, r in (comps.get("responses") or {}).items():
            yield from self._content(r.get("content"), pointer("components", "responses", name), f"response {name}")


def validator_for(spec_uri: str, schema_ptr: str, registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"{spec_uri}#{schema_ptr}"},
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def errors_of(v: Draft202012Validator, instance: Any) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(v.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))
    ]


# --------------------------------------------------------------------------- fixtures

SPECS = {"source": SPEC_PATH, "bundle": BUNDLE_PATH}


@pytest.fixture(scope="module", params=sorted(SPECS))
def spec_ctx(request):
    path = SPECS[request.param]
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO)} not present (run tests/api/bundle.py)")
    spec = load_yaml(path)
    uri = path.as_uri()
    return request.param, spec, uri, make_registry(spec, uri)


@pytest.fixture(scope="module")
def source_spec():
    return load_yaml(SPEC_PATH)


# --------------------------------------------------------------------------- tests


def test_openapi_spec_validator_passes(spec_ctx):
    _, spec, uri, _ = spec_ctx
    assert spec["openapi"] == "3.1.0"
    validate_openapi(spec, base_uri=uri)


def test_operation_ids_unique(spec_ctx):
    _, spec, _, _ = spec_ctx
    ids = [op.get("operationId") for _, _, _, op, _ in SpecWalker(spec).operations()]
    assert all(ids), "every operation (including webhooks) needs an operationId"
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"duplicate operationIds: {dupes}"


def test_expected_operation_surface(source_spec):
    found = {
        (method, key): op["operationId"]
        for kind, key, method, op, _ in SpecWalker(source_spec).operations()
        if kind == "paths"
    }
    assert found == EXPECTED_OPERATIONS
    assert set(source_spec["webhooks"]) == EXPECTED_WEBHOOKS


def test_info_block(source_spec):
    info = source_spec["info"]
    assert info["version"] == "1.0.0"
    assert info["license"]["identifier"] == "Apache-2.0"
    assert info["contact"]["email"] == "contact@helix8.io"
    for phrase in ("Conformance levels", "Why OpenAPI 3.1", "OpenAPI 3.0"):
        assert phrase in info["description"]


def test_oauth2_scopes(source_spec):
    scheme = source_spec["components"]["securitySchemes"]["oauth2"]
    assert scheme["type"] == "oauth2"
    assert set(scheme["flows"]["clientCredentials"]["scopes"]) == EXPECTED_SCOPES
    used: set[str] = set()
    for _, key, method, op, _ in SpecWalker(source_spec).operations():
        if key in source_spec.get("webhooks", {}):
            continue
        assert "security" in op, f"{method.upper()} {key}: per-operation security is required"
        for req in op["security"]:
            used.update(req.get("oauth2", []))
    assert used == EXPECTED_SCOPES, f"scopes never used by an operation: {EXPECTED_SCOPES - used}"


@pytest.mark.parametrize("key", ["/.well-known/ukmp/keys", "/status/{listId}"])
def test_trust_endpoints_are_public(source_spec, key):
    assert source_spec["paths"][key]["get"]["security"] == []


def test_every_operation_documented_with_examples(source_spec):
    walker = SpecWalker(source_spec)
    problems = []
    for _, key, method, op, _ in walker.operations():
        where = f"{method.upper()} {key}"
        for field in ("operationId", "summary", "description", "responses"):
            if not op.get(field):
                problems.append(f"{where}: missing {field}")
        if "requestBody" in op:
            rb, _ = walker.deref(op["requestBody"], "")
            for media, mt in rb["content"].items():
                if not (mt.get("example") is not None or mt.get("examples")):
                    problems.append(f"{where} requestBody [{media}]: no example")
        for code, resp in op.get("responses", {}).items():
            resp, _ = walker.deref(resp, "")
            for media, mt in (resp.get("content") or {}).items():
                if not (mt.get("example") is not None or mt.get("examples")):
                    problems.append(f"{where} {code} [{media}]: no example")
    assert not problems, "\n".join(problems)


def test_error_responses_use_problem_json(source_spec):
    for name, resp in source_spec["components"]["responses"].items():
        assert list(resp["content"]) == ["application/problem+json"], name
        assert resp["content"]["application/problem+json"]["schema"]["$ref"].endswith("/Problem")


def test_passport_schema_is_referenced_not_copied(source_spec):
    mp = source_spec["components"]["schemas"]["MaterialPassport"]
    assert mp["$ref"] == "../schema/material_passport.schema.json"


def test_all_examples_validate(spec_ctx):
    label, spec, uri, registry = spec_ctx
    collected = list(SpecWalker(spec).all_examples())
    assert len(collected) > 60, f"suspiciously few examples found ({len(collected)})"
    failures = []
    for schema_ptr, value, where in collected:
        errs = errors_of(validator_for(uri, schema_ptr, registry), value)
        if errs:
            failures.append(f"[{label}] {where}:\n    " + "\n    ".join(errs[:5]))
    assert not failures, "\n".join(failures)


def _create_body_ptr() -> str:
    return pointer("paths", "/passports", "post", "requestBody", "content", "application/ld+json", "schema")


def _verify_body_ptr() -> str:
    return pointer("paths", "/verify", "post", "requestBody", "content", "application/ld+json", "schema")


@pytest.mark.parametrize("example", EXAMPLE_FILES, ids=lambda p: p.name)
def test_repository_example_is_valid_create_and_verify_body(spec_ctx, example):
    _, _, uri, registry = spec_ctx
    doc = json.loads(example.read_text(encoding="utf-8"))
    for ptr in (_create_body_ptr(), _verify_body_ptr()):
        errs = errors_of(validator_for(uri, ptr, registry), doc)
        assert not errs, f"{example.name} rejected by {ptr}:\n" + "\n".join(errs)


def test_example_files_present():
    names = {p.name for p in EXAMPLE_FILES}
    assert {"example_passport.jsonld", "example_level1_minimal.jsonld"} <= names


def test_invalid_passports_are_rejected(spec_ctx):
    """Guards against a vacuous pass (e.g. an unresolved or ignored $ref)."""
    _, _, uri, registry = spec_ctx
    v = validator_for(uri, _create_body_ptr(), registry)
    vc = json.loads((REPO / "examples" / "example_passport.jsonld").read_text(encoding="utf-8"))
    bare = json.loads((REPO / "examples" / "example_level1_minimal.jsonld").read_text(encoding="utf-8"))
    assert not errors_of(v, vc) and not errors_of(v, bare)

    broken = copy.deepcopy(vc)
    broken["credentialSubject"]["recycledContent"]["totalRecycledFraction"] = 1.87
    assert errors_of(v, broken), "fraction > 1 must fail the passport schema"

    no_id = copy.deepcopy(bare)
    del no_id["alternativeId"]
    assert errors_of(v, no_id), "a passport with no identifier must fail"

    no_context = copy.deepcopy(bare)
    del no_context["@context"]
    assert errors_of(v, no_context), "JSON-LD bodies must carry @context"

    bad_party = copy.deepcopy(vc)
    bad_party["credentialSubject"]["issuerParty"]["gs1:gln"] = "123"
    assert errors_of(v, bad_party), "internal $defs refs of the passport schema must resolve"


def test_redacted_view_must_not_carry_proof(source_spec):
    uri = SPEC_PATH.as_uri()
    registry = make_registry(source_spec, uri)
    v = validator_for(uri, pointer("components", "schemas", "RedactedPassportView"), registry)
    view = copy.deepcopy(source_spec["components"]["examples"]["PassportRedactedPublic"]["value"])
    assert not errors_of(v, view)
    view["proof"] = {"type": "DataIntegrityProof"}
    assert errors_of(v, view)


def test_bundle_matches_source_surface(source_spec):
    if not BUNDLE_PATH.exists():
        pytest.skip("bundle not present")
    bundle = load_yaml(BUNDLE_PATH)
    src_ops = {(k, m): op["operationId"] for _, k, m, op, _ in SpecWalker(source_spec).operations()}
    bun_ops = {(k, m): op["operationId"] for _, k, m, op, _ in SpecWalker(bundle).operations()}
    assert src_ops == bun_ops, "bundle is stale — run: python tests/api/bundle.py"
    passport = json.loads(PASSPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    inlined = [
        s for s in bundle["components"]["schemas"].values()
        if isinstance(s, dict) and s.get("x-ukmp-schema-id")
    ]
    assert len(inlined) == 1 and "$id" not in inlined[0]
    assert inlined[0]["x-ukmp-schema-id"] == passport.get("$id"), (
        "bundle inlines a different passport schema version — run: python tests/api/bundle.py"
    )
