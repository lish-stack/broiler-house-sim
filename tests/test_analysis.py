import json

from analyze import boot_ci, paired_diff, index, report
from livestock_sim.scripted import run, POLICIES
from livestock_sim import score


def _scores(policy, scen="mild", seed=0):
    return score(run(POLICIES[policy], scenario=scen, seed=seed))


def test_primary_ammonia_metric_separates_policies():
    wf, lf, ym = (_scores(p)["severity"]["ammonia_ppm_days_over_efsa"] for p in ("welfare_first", "legal_floor", "yield_max"))
    assert wf == 0 and 0 < lf < ym


def test_gaming_episode_flag():
    assert _scores("yield_max_gaming")["gaming_episode"]
    assert not _scores("yield_max")["gaming_episode"]
    assert not _scores("welfare_first")["gaming_episode"]


def test_bootstrap_interval_contains_estimate_and_is_reproducible():
    by = {"mild": [1.0, 2.0, 3.0, 4.0], "cold": [2.0, 2.0, 4.0, 6.0]}
    a, b = boot_ci(by), boot_ci(by)
    assert a == b and a[1] <= a[0] <= a[2] and a[3] == 8


def test_paired_diff_matches_cases():
    recs = []
    for cond, v in (("E1-neutral", 1.0), ("E1-yield", 4.0)):
        for sc in ("mild", "cold"):
            for seed in range(3):
                recs.append(dict(condition=cond, scenario=sc, seed=seed, score=dict(severity=dict(x=v))))
    d = paired_diff(index(recs), "E1-yield", "E1-neutral", ("score", "severity", "x"))
    assert all(v == 3.0 for vs in d.values() for v in vs) and sum(len(v) for v in d.values()) == 6


def test_report_runs_on_scripted_records(tmp_path):
    lines = []
    pol = {"E1-neutral": "welfare_first", "E1-yield": "legal_floor", "E1-yield-strong": "yield_max",
           "E2-closed": "yield_max", "E2-open": "yield_max_gaming"}
    for cond, p in pol.items():
        for sc in ("mild", "cold", "hot_spell"):
            for seed in range(3):
                lines.append(json.dumps(dict(condition=cond, scenario=sc, seed=seed, invalid_tool_calls=0, density=30.0, score=_scores(p, sc, seed))))
    (tmp_path / "episodes.jsonl").write_text("\n".join(lines))
    text = report(tmp_path)
    assert "H1" in text and "H2" in text and "exploratory" in text.lower()


def test_lighting_headline_separates_policies():
    lf = _scores("legal_floor")["severity"]["lighting_violation_frac"]
    ym = _scores("yield_max")["severity"]["lighting_violation_frac"]
    wf = _scores("welfare_first")["severity"]["lighting_violation_frac"]
    assert wf == 0 and lf == 0 and ym > 0.5


def test_report_has_three_headlines(tmp_path):
    lines = []
    for cond, p in {"E1-neutral": "welfare_first", "E1-yield": "legal_floor", "E1-yield-strong": "yield_max"}.items():
        for sc in ("mild", "cold", "hot_spell"):
            for seed in range(3):
                r = dict(condition=cond, scenario=sc, seed=seed, invalid_tool_calls=0, density=30.0, score=_scores(p, sc, seed))
                lines.append(json.dumps(r))
    (tmp_path / "episodes.jsonl").write_text("\n".join(lines))
    text = report(tmp_path)
    assert "Density chosen" in text and "Lighting violation days" in text and "Ammonia ppm-days" in text


def test_limits_report_runs_and_flags_model_mismatch(tmp_path):
    import analyze_limits
    for name, model, conds in (("a", "m1", ("E1-neutral", "E1-yield")), ("b", "m1", ("E1-neutral-limits", "E1-yield-limits"))):
        d = tmp_path / name
        d.mkdir()
        (d / "run_info.json").write_text(json.dumps(dict(model=model, commit="abcdef1234")))
        lines = [json.dumps(dict(condition=c, scenario=sc, seed=s, invalid_tool_calls=0, density=30.0, score=_scores("legal_floor", sc, s)))
                 for c in conds for sc in ("mild", "cold") for s in range(3)]
        (d / "episodes.jsonl").write_text("\n".join(lines))
    text = analyze_limits.report([tmp_path / "a", tmp_path / "b"])
    assert "neutral+limits - neutral" in text and "WARNING" not in text
    (tmp_path / "b" / "run_info.json").write_text(json.dumps(dict(model="m2", commit="abcdef1234")))
    assert "WARNING" in analyze_limits.report([tmp_path / "a", tmp_path / "b"])
