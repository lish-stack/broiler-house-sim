"""Analysis for the v3 told-the-limits run (fixed before the run; see the v3 section in PREREGISTRATION.md).

Usage: python analyze_limits.py results/<v2-pilot-folder> results/<v3-folder> [--out report_v3.md]

Pools the episodes from the folders and compares, on matched scenario/seed cases:
  E1-neutral-limits vs E1-neutral, E1-yield-limits vs E1-yield, and E1-yield-limits vs E1-neutral-limits.
Exploratory only; same bootstrap and intervals as analyze.py. Checks that all folders used the same model.
"""
import argparse, json, statistics as st
from pathlib import Path

from analyze import HEADLINES, load, index, paired_diff, boot_ci, fmt

COMPS = [("E1-neutral-limits", "E1-neutral"), ("E1-yield-limits", "E1-yield"), ("E1-yield-limits", "E1-neutral-limits")]
COMPONENTS = [("legal darkness (fraction of days)", ("score", "legal", "darkness")),
              ("legal lux (fraction of days)", ("score", "legal", "lux")),
              ("legal ammonia (fraction of days)", ("score", "legal", "ammonia")),
              ("true mortality (%)", ("score", "economics", "true_mortality_pct")),
              ("profit", ("score", "economics", "profit"))]
CONDS = ["E1-neutral", "E1-neutral-limits", "E1-yield", "E1-yield-limits"]


def report(folders):
    recs, models, commits = [], set(), set()
    for f in folders:
        ok, failed = load(f)
        info = json.loads((Path(f) / "run_info.json").read_text())
        models.add(info["model"]); commits.add(info["commit"])
        recs += [r for r in ok if r["condition"] in CONDS]
    idx = index(recs)
    out = ["# v3 told-the-limits results (exploratory, not confirmed)", "",
           f"Folders: {', '.join(map(str, folders))}. Models: {', '.join(sorted(models))}. Commits: {', '.join(sorted(c[:7] for c in commits))}."]
    if len(models) > 1:
        out += ["", "**WARNING: the folders used different models. The comparison is not valid.**"]
    out += ["", "Intervals: 95% stratified bootstrap over scenario/seed cases (3 weather scenarios).", "",
            "## Per-condition means", "",
            "| Condition | n | Density | Ammonia ppm-days over 15 | Lighting violation frac | Legal darkness | Legal lux | Profit |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in CONDS:
        rs = [r for (cc, _, _), r in idx.items() if cc == c]
        if rs:
            m = lambda f: st.mean(f(r) for r in rs)
            out.append(f"| {c} | {len(rs)} | {m(lambda r: r['density']):.1f} | {m(lambda r: r['score']['severity']['ammonia_ppm_days_over_efsa']):.1f} | "
                       f"{m(lambda r: r['score']['severity']['lighting_violation_frac']):.2f} | {m(lambda r: r['score']['legal']['darkness']):.2f} | "
                       f"{m(lambda r: r['score']['legal']['lux']):.2f} | {m(lambda r: r['score']['economics']['profit']):.0f} |")
    out += ["", "## Headline measures: effect of telling the limits", "",
            "| Measure | neutral+limits - neutral | yield+limits - yield | yield+limits - neutral+limits |", "| --- | --- | --- | --- |"]
    for name, path, dg in HEADLINES:
        out.append(f"| {name} | " + " | ".join(fmt(boot_ci(paired_diff(idx, a, b, path)), dg) for a, b in COMPS) + " |")
    out += ["", "## Components (pre-registered as secondary in v3)", "",
            "| Measure | neutral+limits - neutral | yield+limits - yield | yield+limits - neutral+limits |", "| --- | --- | --- | --- |"]
    for name, path in COMPONENTS:
        out.append(f"| {name} | " + " | ".join(fmt(boot_ci(paired_diff(idx, a, b, path))) for a, b in COMPS) + " |")
    out += ["", "Reading rule (fixed in v3): see PREREGISTRATION.md. Nothing here is a confirmed finding."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    text = report(a.folders)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
