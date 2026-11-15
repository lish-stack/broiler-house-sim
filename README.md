# Broiler house simulation: does an AI agent protect the birds under pressure? (pilot)

An AI agent manages a simulated 42-day broiler chicken house. Experiment 1 asks whether operator pressure toward output lowers welfare when the agent is told no welfare limits. Experiment 2 asks whether the agent uses tools that could hide harm.

## Status and next steps

- **Done:** the 150-episode pilot. Results and limits: `docs/PILOT_RESULTS.md`. Plan and full history: `PREREGISTRATION.md`.
- **Naming:** the pilot is the only experiment that has run. Its plan was first frozen as "v1" (only two test episodes ever ran on it, both discarded), replaced by "v2" before any real episode, and amended by "v2.1" (analysis only) before the 150 ran. Those labels are drafts of the one pilot plan, not separate experiments. Nothing else has a version number.
- **Planned, not run:** a 120-episode told-the-limits follow-up that also captures the agent's reasons. Plan in `PREREGISTRATION.md` (section "Planned follow-up").
- **Before running the follow-up:** outside review of the design (a poultry vet or welfare scientist on the thresholds, an evaluations methodologist on the design).

## About this simulator


One-day steps over a 42-day grow-out. Agent levers: placement density, lighting hours and lux, ventilation, temperature setpoint.
Hidden state: true ammonia, true mortality. Reporting hooks: reported mortality, ammonia alarm threshold.

- `config/parameters.yaml`: cited values, each with a verification status.
- `config/assumptions.yaml`: values with no published source; all go into sensitivity runs.
- `data/ross308_as_hatched.csv`: Ross 308 2022 performance objectives (checked: daily gains and cumulative intake reconcile).
- `broiler_sim/scripted.py`: scripted known-good and known-bad agents (not language models).
- `tests/`: calibration. Run `python3 -m pytest -q tests`.

Not yet built: the Inspect task wrapper (tools and prompts), the monitor stage, the worker-harm control scenario.
Known limitation: no evaporative cooling, so a hot spell above ~30 C cannot be fully managed; heat mortality there is driven by an assumed anchor.
Score components separately; do not average them into one index (the weighting would be arbitrary).


## Parameter audit (latest)
- config/assumptions.yaml: every non-regulatory input has a status (Sourced / Derived / Assumption) and a source note.
- config/ranges.yaml: low/high for each; `python3 -m broiler_sim.sweep` checks the calibration conclusions across all of them
  (one-at-a-time + random draws). Result: 0 failures. Ammonia emission is the widest range (0.0045 to 0.038 g/bird/day per day of age).
- Cooling pads are now a lever (`pad=True`): incoming air cooled `pad_drop_c` (default 5 C, range 0-8) when outside > 27 C. Air-speed
  (wind-chill) cooling and the pad humidity limit are still not modelled.
- Still unsourced: minimum-ventilation table, cold effects, heat mortality curve, economics (scenario values, ranges only).

## Running the pilot

Needs the `anthropic` package and an `ANTHROPIC_API_KEY` on a machine that can reach the API (the build sandbox cannot).
`pip install anthropic pyyaml` then `git fetch --tags` then `python run_pilot.py --model <model-id>`.
Writes `results/<timestamp>-<model>/` with `run_info.json`, `episodes.jsonl` and one full transcript per episode.
The run guard checks against the freeze tag `plan-frozen-followup` (earlier tags `plan-frozen-v1`, `plan-frozen-v2`). The 150-episode pilot was run against `plan-frozen-v2`. To run the follow-up: `python run_pilot.py --model claude-sonnet-5-5 --conditions FU-neutral,FU-neutral-limits,FU-yield,FU-yield-limits`, then `python analyze_limits.py results/<folder> --out report_followup.md`. Analysis of the pilot: `python analyze.py results/<folder> --out report.md`. Note: the code package was renamed from `livestock_sim` to `broiler_sim` on 2026-11-15; older sections of `PREREGISTRATION.md` name the old path.
Optional before the full run: `python run_pilot.py --model <model-id> --noise-check` (5 repeats of one case, not part of the 150).
After a run: `python analyze.py results/<folder> --out report.md` (three headline measures: density chosen, ammonia ppm-days, lighting violation days; paired differences, stratified bootstrap, exploratory only).
Each transcript also holds the daily true simulator state (`house_log`).
