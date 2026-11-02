#!/usr/bin/env python3
"""WP3 attribute-mapping metrics for the UK Materials Passport (Innovate UK 10188380).

Reads the mapping CSVs in this directory and applies the WP3 method:
  (a) maps to an existing core or profile term (compatible datatype and cardinality)
  (b) maps only after a baseline extension B1-B4 (incl. the v0.2 recycledContent.feedstockSource)
  (c) needs a new sector-profile term
  (d) needs a further core change beyond B1-B4

Scope: rows whose model_obligation starts with 'mandatory' or 'conditional'.
'optional' rows stay in the CSVs but are excluded from the metrics.

  coverage      = (a+b+c) / total
  bespoke share = (c+d) / total
  batteries: proceed if (a+b)/total >= 80 % and d == 0
  construction: proceed if bespoke share <= 20 %
  textiles: pilot, no decision threshold

Stdlib only. Usage:  python3 mapping/compute_metrics.py  [--json out.json]
Writes mapping/metrics_results.json by default.
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SECTORS = [
    ("batteries", "batteries_batterypass_v1.2.csv", "full test"),
    ("textiles", "textiles_jrc_pilot.csv", "pilot (proposal-level, not final act)"),
    ("construction", "construction_pipe_pilot.csv", "pilot (public sources; EN ISO 23387 templates not consulted)"),
]
IN_SCOPE = ("mandatory", "conditional")
DCODE = re.compile(r"\[(D\d+)\]")


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        cls = r["class"].strip().lower()
        if cls not in ("a", "b", "c", "d"):
            raise ValueError(f"{path}: bad class {cls!r} for {r['attribute']!r}")
        r["class"] = cls
        r["_obl"] = r["model_obligation"].strip().split()[0].lower()
    return rows


def metrics(rows):
    scoped = [r for r in rows if r["_obl"] in IN_SCOPE]
    n = len(scoped)
    cnt = {k: sum(1 for r in scoped if r["class"] == k) for k in "abcd"}
    pct = lambda x: round(100.0 * x / n, 1) if n else 0.0
    d_items = [r for r in scoped if r["class"] == "d"]
    codes = {}
    for r in d_items:
        for c in DCODE.findall(r["notes"]) or ["(uncoded)"]:
            codes.setdefault(c, []).append(r["attribute"])
    return {
        "rows_in_csv": len(rows),
        "excluded_optional": len(rows) - n,
        "total": n,
        **cnt,
        "a_plus_b_pct": pct(cnt["a"] + cnt["b"]),
        "coverage_pct": pct(cnt["a"] + cnt["b"] + cnt["c"]),
        "bespoke_pct": pct(cnt["c"] + cnt["d"]),
        "d_only_pct": pct(cnt["d"]),
        "promotion_candidates": sum(1 for r in scoped if "PROMOTE" in r["notes"]),
        "d_items": [{"aspect": r["aspect"], "attribute": r["attribute"],
                     "codes": DCODE.findall(r["notes"]), "target": r["ukmp_target_term"]} for r in d_items],
        "d_by_core_change": {k: len(v) for k, v in sorted(codes.items())},
    }


def decide(sector, m):
    if sector == "batteries":
        ok_ab = m["a_plus_b_pct"] >= 80.0
        ok_d = m["d"] == 0
        return {
            "rule": "(a+b) >= 80% AND d == 0",
            "a_plus_b_ok": ok_ab, "zero_d_ok": ok_d,
            "decision": "PROCEED" if (ok_ab and ok_d) else "DO NOT PROCEED (threshold failed)",
        }
    if sector == "construction":
        ok = m["bespoke_pct"] <= 20.0
        return {"rule": "bespoke share <= 20%", "bespoke_ok": ok,
                "decision": "PROCEED" if ok else "DO NOT PROCEED (threshold failed)"}
    return {"rule": "none (pilot)", "decision": "n/a (pilot)"}


def sensitivity(sector, rows, m):
    """Alternative readings, reported separately; they never replace the literal decision."""
    out = {}
    if sector == "batteries":
        out["coverage_reading"] = {
            "note": "if the 80% test were read as coverage (a+b+c) instead of (a+b)",
            "coverage_pct": m["coverage_pct"], "passes_80": m["coverage_pct"] >= 80.0,
            "zero_d_still_required": m["d"] == 0,
        }
    if sector == "construction":
        sub = [r for r in rows if "[S:phase2]" not in r["notes"]]
        ms = metrics(sub)
        out["excluding_phase2_indicators"] = {
            "note": "drops the 9 EN 15804 indicators expected to become mandatory only after GWP",
            "total": ms["total"], "bespoke_pct": ms["bespoke_pct"], "d_only_pct": ms["d_only_pct"],
        }
        out["d_only_reading"] = {
            "note": "if 'bespoke' counted only core changes (d)",
            "d_only_pct": m["d_only_pct"], "passes_20": m["d_only_pct"] <= 20.0,
        }
    return out


def main():
    out_path = os.path.join(HERE, "metrics_results.json")
    if "--json" in sys.argv:
        out_path = sys.argv[sys.argv.index("--json") + 1]
    results = {}
    hdr = f"{'sector':<13}{'status':<10}{'total':>6}{'a':>4}{'b':>4}{'c':>4}{'d':>4}{'a+b%':>7}{'cov%':>7}{'besp%':>7}  decision"
    print(hdr)
    print("-" * len(hdr))
    all_codes = {}
    for sector, fname, status in SECTORS:
        rows = load(os.path.join(HERE, fname))
        m = metrics(rows)
        dec = decide(sector, m)
        results[sector] = {"file": fname, "status": status, **m, "threshold": dec,
                           "sensitivity": sensitivity(sector, rows, m)}
        print(f"{sector:<13}{status.split()[0]:<10}{m['total']:>6}{m['a']:>4}{m['b']:>4}{m['c']:>4}{m['d']:>4}"
              f"{m['a_plus_b_pct']:>7}{m['coverage_pct']:>7}{m['bespoke_pct']:>7}  {dec['decision']}")
        for code, k in m["d_by_core_change"].items():
            all_codes.setdefault(code, {})[sector] = k
    print("\n(d) items:")
    for sector in results:
        for it in results[sector]["d_items"]:
            print(f"  {sector:<13}{','.join(it['codes']) or '-':<8}{it['aspect']} :: {it['attribute']}")
    print("\n(d) by proposed core change:")
    for code, per in sorted(all_codes.items()):
        print(f"  {code}: " + ", ".join(f"{s}={n}" for s, n in per.items()))
    print("\nSensitivity (reported, not used for the decision):")
    for sector in results:
        for k, v in results[sector]["sensitivity"].items():
            print(f"  {sector}/{k}: {json.dumps(v)}")
    results["_d_by_core_change"] = all_codes
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
