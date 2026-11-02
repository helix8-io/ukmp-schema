#!/usr/bin/env python3
"""Bundle api/openapi.yaml into a single self-contained file.

    python tests/api/bundle.py            # write api/dist/openapi.bundled.yaml
    python tests/api/bundle.py --check    # fail if the committed bundle is stale

Runs ``npx @redocly/cli@1 bundle`` (which inlines the external passport JSON
Schema and hoists its ``$defs`` into ``components/schemas``), then
post-processes the result:

* The inlined passport schema keeps its ``$id``/``$schema`` from the source
  file. Under JSON Schema 2020-12 an embedded ``$id`` changes the base URI, so
  the bundler's rewritten ``#/components/schemas/...`` references inside that
  subschema would resolve against the passport schema's URL instead of this
  document and break strict resolvers (Prism/AJV, jsonschema). The ``$id`` is
  therefore moved to the annotation ``x-ukmp-schema-id`` and ``$schema`` is
  dropped (the OpenAPI 3.1 default dialect, JSON Schema 2020-12, applies).
* The bundler copies the schema's ``$defs`` into ``components/schemas`` and
  repoints references there, leaving the original ``$defs`` block as an
  unreferenced duplicate; it is removed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "api" / "openapi.yaml"
CONFIG = REPO / "api" / "redocly.yaml"
OUT = REPO / "api" / "dist" / "openapi.bundled.yaml"

HEADER = (
    "# GENERATED FILE - do not edit by hand.\n"
    "# Single-file bundle of api/openapi.yaml with the passport JSON Schema inlined.\n"
    "# Regenerate with: python tests/api/bundle.py\n"
)


def strip_embedded_ids(doc: dict) -> int:
    count = 0
    for schema in (doc.get("components", {}).get("schemas") or {}).values():
        if isinstance(schema, dict) and "$id" in schema:
            schema["x-ukmp-schema-id"] = schema.pop("$id")
            schema.pop("$schema", None)
            # The bundler hoists every $defs entry into components/schemas and
            # rewrites references to point there; the original $defs block is
            # left behind as an unreferenced duplicate.
            schema.pop("$defs", None)
            count += 1
    return count


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):  # noqa: D401 - PyYAML hook
        return True


def build() -> str:
    npx = shutil.which("npx")
    if not npx:
        sys.exit("error: npx not found (install Node.js >= 18)")
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "bundled.yaml"
        subprocess.run(
            [npx, "-y", "@redocly/cli@1", "bundle", str(SRC), "--config", str(CONFIG), "-o", str(raw)],
            check=True,
            cwd=REPO,
        )
        doc = yaml.safe_load(raw.read_text(encoding="utf-8"))
    if strip_embedded_ids(doc) == 0:
        sys.exit("error: expected the inlined passport schema to carry $id; bundler output changed?")
    return HEADER + yaml.dump(
        doc, Dumper=_NoAliasDumper, sort_keys=False, allow_unicode=True, width=120
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed bundle differs")
    args = ap.parse_args()
    text = build()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(REPO)} is stale; run: python tests/api/bundle.py", file=sys.stderr)
            return 1
        print(f"{OUT.relative_to(REPO)} is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
