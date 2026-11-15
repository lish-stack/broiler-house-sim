"""Analysis for the planned told-the-limits follow-up (see "Planned follow-up" in PREREGISTRATION.md).

Usage: python analyze_limits.py results/<follow-up-folder> [--out report_followup.md]

All four arms (FU-neutral, FU-neutral-limits, FU-yield, FU-yield-limits) come from one run. Compares, on matched scenario/seed cases:
  told minus untold at each instruction level, and yield minus neutral within the told arms and within the untold arms.
Exploratory only; same bootstrap and intervals as analyze.py. If several folders are given they are pooled, and the script
warns if they used different models.
"""
import argparse, json, statistics as st
from pathlib import Path

from analyze import HEADLINES, load, index, paired_diff, boot_ci, fmt

COMPS = [("FU-neutral-limits", "FU-neutral"), ("FU-yield-limits", "FU-yield"),
         ("FU-yield-limits", "FU-neutral-limits"), ("FU-yield", "FU-neutral")]
COLS = ["neutral+limits - neutral", "yield+limits - yield", "yield+limits - neutral+limits", "yield - neutral (untold)"]
COMPONENTS = [("legal darkness (fraction of days)", ("score", "legal", "darkness")),
              ("legal lux (fraction of days)", ("score", "legal", "lux")),
              ("legal ammonia (fraction of days)", ("score", "legal", "ammonia")),
              ("true mortality (%)", ("score", "economics", "true_mortality_pct")),
              ("profit", ("score", "economics", "profit"))]
CONDS = ["FU-neutral", "FU-neutral-limits", "FU-yield", "FU-yield-limits"]


def report(folders):
    recs, models, commits = [], set(), set()
    for f in folders:
        ok, failed = load(f)
        info = json.loads((Path(f) / "run_info.json").read_text())
        models.add(info["model"]); commits.add(info["commit"])
        recs += [r for r in ok if r["condition"] in CONDS]
    idx = index(recs)
    out = ["# Told-the-limits follow-up results (exploratory, not confirmed)", "",
           f"Folders: {', '.join(map(str, folders))}. Models: {', '.join(sorted(models))}. Commits: {', '.join(sorted(c[:7] for c in commits))}."]
    if len(models) > 1:
        out += ["", "**WARNING: the folders used different models. The comparison is not valid.**"]
    out += ["", "Intervals: 95% stratified bootstrap over scenario/seed cases (3 weather scenarios).", "",
            "## Per-condition means", "",
            "| Condition | n | Density | Ammonia ppm-days over 15 | Lighting violation frac | Legal darkness | Legal lux | Profit | Calls missing a reason |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in CONDS:
        rs = [r for (cc, _, _), r in idx.items() if cc == c]
        if rs:
            m = lambda f: st.mean(f(r) for r in rs)
            out.append(f"| {c} | {len(rs)} | {m(lambda r: r['density']):.1f} | {m(lambda r: r['score']['severity']['ammonia_ppm_days_over_efsa']):.1f} | "
                       f"{m(lambda r: r['score']['severity']['lighting_violation_frac']):.2f} | {m(lambda r: r['score']['legal']['darkness']):.2f} | "
                       f"{m(lambda r: r['score']['legal']['lux']):.2f} | {m(lambda r: r['score']['economics']['profit']):.0f} | {sum(r.get('missing_reason_calls', 0) for r in rs)} |")
    out += ["", "## Headline measures: effect of telling the limits", "",
            "| Measure | " + " | ".join(COLS) + " |", "| --- | --- | --- | --- | --- |"]
    for name, path, dg in HEADLINES:
        out.append(f"| {name} | " + " | ".join(fmt(boot_ci(paired_diff(idx, a, b, path)), dg) for a, b in COMPS) + " |")
    out += ["", "## Components (pre-registered as secondary)", "",
            "| Measure | " + " | ".join(COLS) + " |", "| --- | --- | --- | --- | --- |"]
    for name, path in COMPONENTS:
        out.append(f"| {name} | " + " | ".join(fmt(boot_ci(paired_diff(idx, a, b, path))) for a, b in COMPS) + " |")
    out += ["", "Reading rule (fixed before the run): see PREREGISTRATION.md. Nothing here is a confirmed finding."]
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
