"""Run the frozen pilot. Refuses to run if prompts/ or config/ differ from tag plan-frozen-followup or the tree is dirty.
Usage: python run_pilot.py --model <model-id> [--out results] [--conditions E1-neutral,...] [--dry-run]"""
import argparse, datetime, json, subprocess, sys
from pathlib import Path

from broiler_sim.agent import CONDITIONS, AnthropicClient, run_episode

PILOT_CONDITIONS = ["E1-neutral", "E1-yield", "E1-yield-strong", "E2-closed", "E2-open"]   # the pilot set; the follow-up names its conditions explicitly
SCENARIOS = ["mild", "cold", "hot_spell"]
SEEDS = list(range(10))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


FREEZE_TAG = "plan-frozen-followup"   # v1 (plan-frozen-v1) is kept in git history; see the version log in PREREGISTRATION.md


def guard():
    if sh("git", "rev-parse", "-q", "--verify", FREEZE_TAG).returncode != 0:
        sys.exit(f"Tag {FREEZE_TAG} not found locally. Run: git fetch --tags")
    if sh("git", "diff", "--quiet", FREEZE_TAG, "--", "prompts", "config", "data").returncode != 0:
        sys.exit(f"prompts/, config/ or data/ differ from {FREEZE_TAG}. The plan is frozen; log a new version instead.")
    if sh("git", "status", "--porcelain").stdout.strip():
        sys.exit("Working tree has uncommitted changes. Commit first so each run records an exact commit.")
    return sh("git", "rev-parse", "HEAD").stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--conditions", default=",".join(PILOT_CONDITIONS))
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--resume", help="path of an unfinished results folder: skips episodes already completed there")
    ap.add_argument("--smoke", action="store_true", help="run ONE episode (E1-neutral, mild, seed 0) to check setup and measure tokens")
    ap.add_argument("--noise-check", action="store_true", help="run E1-yield / mild / seed 0 five times, to measure run-to-run noise (not part of the 150)")
    a = ap.parse_args()
    commit = guard()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(a.resume) if a.resume else Path(a.out) / f"{stamp}-{a.model}{'-smoke' if a.smoke else ''}{'-noise' if a.noise_check else ''}"
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
    if a.noise_check:
        with open(out / "episodes.jsonl", "a") as f:
            for i in range(5):
                rec = run_episode(client, "E1-yield", "mild", 0, out / "transcripts" / f"E1-yield_mild_0_rep{i}.json")
                rec["repeat"] = i
                f.write(json.dumps(rec) + "\n"); f.flush()
                sc = rec["score"]
                print(f"rep {i}: ammonia ppm-days over EFSA {sc['severity']['ammonia_ppm_days_over_efsa']:.1f}, density {rec['density']}, "
                      f"profit {sc['economics']['profit']:.0f}", flush=True)
        return
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
