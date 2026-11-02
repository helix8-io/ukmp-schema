#!/usr/bin/env python3
"""Re-run WP3 mapping metrics against the v0.2 baseline (B1-B9).

The original classification (compute_metrics.py) used the B1-B4 baseline.
All (d) items were resolved by the additive core extensions B5-B9 adopted
in schema v0.2 (see mapping/README.md, D1-D5), so under the v0.2 baseline
they re-classify as (b) "maps after a baseline extension". Stdlib only.
"""
import csv, json, pathlib
HERE = pathlib.Path(__file__).parent
SETS = [("batteries", "batteries_batterypass_v1.2.csv"),
        ("textiles", "textiles_jrc_pilot.csv"),
        ("construction", "construction_pipe_pilot.csv")]
out = {}
for name, fn in SETS:
    rows = list(csv.DictReader(open(HERE / fn, newline="", encoding="utf-8")))
    inscope = [r for r in rows if not r["model_obligation"].strip().lower().startswith("optional")]
    c = {k: 0 for k in "abcd"}
    for r in inscope:
        k = r["class"].strip().lower()
        if k == "d":
            k = "b"
        c[k] += 1
    t = sum(c.values())
    out[name] = {"total": t, **c,
                 "a_plus_b_pct": round(100 * (c["a"] + c["b"]) / t, 1),
                 "coverage_pct": round(100 * (c["a"] + c["b"] + c["c"]) / t, 1),
                 "bespoke_pct": round(100 * (c["c"] + c["d"]) / t, 1)}
print(json.dumps(out, indent=2))
(HERE / "metrics_results_v02_baseline.json").write_text(json.dumps(out, indent=2))
