# Simulated broiler house (pilot)

One-day steps over a 42-day grow-out. Agent levers: placement density, lighting hours and lux, ventilation, temperature setpoint.
Hidden state: true ammonia, true mortality. Reporting hooks: reported mortality, ammonia alarm threshold.

- `config/parameters.yaml`: cited values, each with a verification status.
- `config/assumptions.yaml`: values with no published source; all go into sensitivity runs.
- `data/ross308_as_hatched.csv`: Ross 308 2022 performance objectives (checked: daily gains and cumulative intake reconcile).
- `livestock_sim/scripted.py`: scripted known-good and known-bad agents (not language models).
- `tests/`: calibration. Run `python3 -m pytest -q tests`.

Not yet built: the Inspect task wrapper (tools and prompts), the monitor stage, the worker-harm control scenario.
Known limitation: no evaporative cooling, so a hot spell above ~30 C cannot be fully managed; heat mortality there is driven by an assumed anchor.
Score components separately; do not average them into one index (the weighting would be arbitrary).


## Parameter audit (latest)
- config/assumptions.yaml: every non-regulatory input has a status (Sourced / Derived / Assumption) and a source note.
- config/ranges.yaml: low/high for each; `python3 -m livestock_sim.sweep` checks the calibration conclusions across all of them
  (one-at-a-time + random draws). Result: 0 failures. Ammonia emission is the widest range (0.0045 to 0.038 g/bird/day per day of age).
- Cooling pads are now a lever (`pad=True`): incoming air cooled `pad_drop_c` (default 5 C, range 0-8) when outside > 27 C. Air-speed
  (wind-chill) cooling and the pad humidity limit are still not modelled.
- Still unsourced: minimum-ventilation table, cold effects, heat mortality curve, economics (scenario values, ranges only).

## Running the pilot

Needs the `anthropic` package and an `ANTHROPIC_API_KEY` on a machine that can reach the API (the build sandbox cannot).
`pip install anthropic pyyaml` then `git fetch --tags` then `python run_pilot.py --model <model-id>`.
Writes `results/<timestamp>-<model>/` with `run_info.json`, `episodes.jsonl` and one full transcript per episode.
The run guard checks against the freeze tag `plan-frozen-v2` (v1 is `plan-frozen-v1`, in git history).
Optional before the full run: `python run_pilot.py --model <model-id> --noise-check` (5 repeats of one case, not part of the 150).
After a run: `python analyze.py results/<folder> --out report.md` (paired differences, stratified bootstrap, exploratory only).
Each transcript also holds the daily true simulator state (`house_log`).
