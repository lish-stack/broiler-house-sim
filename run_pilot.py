"""Run the frozen pilot. Refuses to run if prompts/ or config/ differ from tag plan-frozen-v1 or the tree is dirty.
Usage: python run_pilot.py --model <model-id> [--out results] [--conditions E1-neutral,...] [--dry-run]"""
import argparse, datetime, json, subprocess, sys
from pathlib import Path

from livestock_sim.agent import CONDITIONS, AnthropicClient, run_episode

SCENARIOS = ["mild", "cold", "hot_spell"]
SEEDS = list(range(10))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def guard():
    if sh("git", "rev-parse", "-q", "--verify", "plan-frozen-v1").returncode != 0:
        sys.exit("Tag plan-frozen-v1 not found locally. Run: git fetch --tags")
    if sh("git", "diff", "--quiet", "plan-frozen-v1", "--", "prompts", "config", "data").returncode != 0:
        sys.exit("prompts/, config/ or data/ differ from plan-frozen-v1. The plan is frozen; log a new version instead.")
    if sh("git", "status", "--porcelain").stdout.strip():
        sys.exit("Working tree has uncommitted changes. Commit first so each run records an exact commit.")
    return sh("git", "rev-parse", "HEAD").stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--resume", help="path of an unfinished results folder: skips episodes already completed there")
    ap.add_argument("--smoke", action="store_true", help="run ONE episode (E1-neutral, mild, seed 0) to check setup and measure tokens")
    a = ap.parse_args()
    commit = guard()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(a.resume) if a.resume else Path(a.out) / f"{stamp}-{a.model}{'-smoke' if a.smoke else ''}"
    client = AnthropicClient(a.model, temperature=a.temperature)
    done = set()
    if a.resume:
        prev = json.loads((out / "run_info.json").read_text())
        if prev["model"] != a.model or prev["commit"] != commit:
            sys.exit("--resume needs the same model and the same commit as the original run.")
        for line in (out / "episodes.jsonl").read_text().splitlines():
            r = json.loads(line)
            if "infrastructure_failure" not in r:
                done.add((r["condition"], r["scenario"], r["seed"]))
    else:
        out.mkdir(parents=True)
    if not a.resume: (out / "run_info.json").write_text(json.dumps(dict(model=a.model, commit=commit, temperature=a.temperature,
                                                       conditions=a.conditions.split(","), scenarios=SCENARIOS, seeds=SEEDS), indent=1))
    conds, scens, seeds = (["E1-neutral"], ["mild"], [0]) if a.smoke else (a.conditions.split(","), SCENARIOS, SEEDS)
    with open(out / "episodes.jsonl", "a") as f:
        for cond in conds:
            for sc in scens:
                for seed in seeds:
                    if (cond, sc, seed) in done:
                        continue
                    try:
                        rec = run_episode(client, cond, sc, seed, out / "transcripts" / f"{cond}_{sc}_{seed}.json")
                    except Exception as ex:   # infrastructure failure: logged, never silently dropped
                        rec = dict(condition=cond, scenario=sc, seed=seed, infrastructure_failure=repr(ex))
                    f.write(json.dumps(rec) + "\n"); f.flush()
                    print(cond, sc, seed, "FAILED" if "infrastructure_failure" in rec else "ok", flush=True)


if __name__ == "__main__":
    main()
