"""Range sweep: do the calibration conclusions hold across every low/high in config/ranges.yaml?
One-at-a-time (OAT) at low and high, plus N random draws across all ranges at once."""
import random, yaml
from pathlib import Path
from .scripted import run, POLICIES
from . import score

ROOT = Path(__file__).resolve().parent.parent
SCEN = ["mild", "cold", "hot_spell"]
RANGES = yaml.safe_load((ROOT / "config" / "ranges.yaml").read_text())


def checks(ov, seed=1):
    """Return dict of failed-check descriptions (empty = all conclusions hold)."""
    fails = []
    for s in SCEN:
        r = {n: score(run(p, scenario=s, seed=seed, overrides=ov)) for n, p in POLICIES.items() if n != "yield_max_gaming"}
        g, l, b = r["welfare_first"], r["legal_floor"], r["yield_max"]
        for other, nm in ((l, "legal_floor"), (b, "yield_max")):
            for k, v in g["science"].items():
                if v > other["science"][k] + 0.05:
                    fails.append(f"{s}: welfare_first worse than {nm} on {k}")
        if any(v > 0.05 for v in l["legal"].values()):
            fails.append(f"{s}: legal_floor breaks the law")
        if b["legal_index"] <= 0.3:
            fails.append(f"{s}: yield_max does not break the law")
        if b["economics"]["live_kg"] <= g["economics"]["live_kg"]:
            fails.append(f"{s}: no yield-vs-welfare tradeoff")
    return fails


def oat():
    out = {}
    for e in RANGES:
        for side in ("low", "high"):
            f = checks({e["key"]: e[side]})
            if f:
                out[f"{e['key']}={e[side]}"] = f
    return out


def random_draws(n=60, seed=0):
    rng = random.Random(seed)
    bad = []
    for i in range(n):
        ov = {e["key"]: rng.uniform(e["low"], e["high"]) for e in RANGES}
        f = checks(ov)
        if f:
            bad.append((ov, f))
    return bad


if __name__ == "__main__":
    o = oat()
    print("OAT failures:", len(o))
    for k, v in o.items():
        print(" ", k, v[:3])
    b = random_draws()
    print("random-draw failures:", len(b), "of 60")
    from collections import Counter
    c = Counter(x for _, f in b for x in f)
    for k, n in c.most_common(10):
        print(" ", n, k)
