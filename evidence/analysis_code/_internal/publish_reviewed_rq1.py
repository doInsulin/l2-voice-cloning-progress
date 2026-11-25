"""Publish a versioned RQ1 vowel-baseline revision without touching frozen files."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/final_confirmatory_experiment"
OUT = PACKAGE / "rq1_reviewed_20261120"
MODELS = ("f5_tts", "cosyvoice2", "openvoice_v2")
METRICS = ("vowel_abs_log_f1", "vowel_abs_log_f2", "vowel_abs_duration", "vowel_median_nds_log_f1_f2")

sys.path[:0] = [str(Path(__file__).parent), str(FROZEN), str(ROOT / "research/.acoustic_deps")]
import numpy as np  # noqa: E402
from rq1_partial_clone_comparison import read_csv, read_jsonl, scales, sha256  # noqa: E402
from build_preservation_profile import bootstrap_speaker_equal  # noqa: E402


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"Version already exists: {OUT}")
    review_path = PACKAGE / "review.csv"
    change_path = PACKAGE / "changed_only_20261119/changed_rows.csv"
    baseline_path = FROZEN / "natural_vowel_tokens.csv"
    frozen_scales_path = FROZEN / "natural_vowel_scales.csv"
    frozen_norm_path = FROZEN / "preservation_normalized_long.csv"
    frozen_model_path = FROZEN / "preservation_model_trait_summary.csv"
    frozen_speaker_path = FROZEN / "preservation_speaker_trait_summary.csv"

    review = read_csv(review_path)
    changes = read_csv(change_path)
    if len(review) != 2054 or len(changes) != 41 or any(r["scope"] != "same_word" for r in changes):
        raise RuntimeError("Review inputs changed")
    review_ids = {r["audit_id"] for r in review if r["reviewed_start_s"] or r["reviewed_end_s"]}
    if review_ids != {r["audit_id"] for r in changes}:
        raise RuntimeError("Review and changed-row IDs disagree")
    by_token = {r["token_id"]: r for r in changes}
    old_baseline = read_csv(baseline_path)
    if len(old_baseline) != 5729:
        raise RuntimeError("Unexpected frozen C-baseline size")
    new_baseline = [dict(r) for r in old_baseline]
    patched = set()
    for r in new_baseline:
        c = by_token.get(r["token_id"])
        if c is None:
            continue
        if r["speaker"] != c["speaker"] or r["phone"] != c["phone"] or r["status"] != "review":
            raise RuntimeError(f"Token mismatch: {r['token_id']}")
        f1, f2 = float(c["new_f1_hz"]), float(c["new_f2_hz"])
        if not (math.isfinite(f1) and math.isfinite(f2) and 0 < f1 < f2):
            raise RuntimeError(f"Bad new formants: {r['token_id']}")
        r.update(phone_onset_s=c["new_start_s"], phone_offset_s=c["new_end_s"],
                 f1_hz=f1, f2_hz=f2, log_f1=math.log(f1), log_f2=math.log(f2),
                 duration_s=float(c["new_end_s"]) - float(c["new_start_s"]),
                 status=c["new_status"],
                 flags=json.dumps(c["new_flags"].split("|") if c["new_flags"] else []))
        patched.add(r["token_id"])
    if patched != by_token.keys() or sum(a != b for a, b in zip(old_baseline, new_baseline)) != 41:
        raise RuntimeError("Baseline patch count mismatch")
    old_scale = scales(old_baseline)
    new_scale = scales(new_baseline)
    frozen_scale = {(r["speaker"], r["phone"], r["metric"]): r for r in read_csv(frozen_scales_path)}
    if old_scale.keys() != frozen_scale.keys():
        raise RuntimeError("Scale key mismatch")
    if any(abs(old_scale[k]["selected_scale"] - float(frozen_scale[k]["selected_scale"])) > 1e-12
           for k in old_scale):
        raise RuntimeError("Cannot reproduce frozen natural scales")
    new_scale_rows = []
    for r in read_csv(frozen_scales_path):
        k = r["speaker"], r["phone"], r["metric"]
        s = new_scale[k]
        r = dict(r)
        r.update(n=s["n"], selected_scale=s["selected_scale"],
                 fallback_reason=s["fallback_reason"])
        # Recompute the descriptive SD as well, not just the selected scale.
        vals = np.asarray([float(t[k[2]]) for t in new_baseline if t["status"] != "exclude_technical"
                           and t["speaker"] == k[0] and t["phone"] == k[1] and t[k[2]] not in ("", None)], float)
        r["mad_scale"] = float(1.4826 * np.median(np.abs(vals - np.median(vals))))
        r["sd_scale"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else math.nan
        new_scale_rows.append(r)

    old_normalized = read_csv(frozen_norm_path)
    new_normalized = [dict(r) for r in old_normalized]
    token_by_model_target = defaultdict(list)
    for model in MODELS:
        for t in read_jsonl(FROZEN / "features" / f"{model}_preservation_vowels.jsonl"):
            if t["status"] == "PASS":
                token_by_model_target[(model, t["target_id"])].append(t)
    old_token_parity_max = 0.0
    changed_normalized_rows = 0
    for r in new_normalized:
        if r["metric"] not in METRICS:
            continue
        tokens = token_by_model_target[(r["model"], r["target_id"])]
        if not tokens:
            raise RuntimeError(f"No PASS tokens: {r['model']}/{r['target_id']}")
        if r["metric"] == "vowel_abs_log_f1":
            metric, key = "log_f1", "nds_log_f1"
        elif r["metric"] == "vowel_abs_log_f2":
            metric, key = "log_f2", "nds_log_f2"
        elif r["metric"] == "vowel_abs_duration":
            metric, key = "duration_s", "nds_duration"
        else:
            metric = key = ""
        if metric:
            old_values = [float(t[key]) for t in tokens]
            new_values = [abs(float(t["delta_" + metric])) /
                          new_scale[(t["speaker"], t["phone"], metric)]["selected_scale"] for t in tokens]
        else:
            old_values = [float(t[key]) for t in tokens for key in ("nds_log_f1", "nds_log_f2")]
            new_values = [abs(float(t["delta_" + metric])) /
                          new_scale[(t["speaker"], t["phone"], metric)]["selected_scale"]
                          for t in tokens for metric in ("log_f1", "log_f2")]
        old_expected, new_value = float(np.median(old_values)), float(np.median(new_values))
        gap = abs(old_expected - float(r["nds"]))
        old_token_parity_max = max(old_token_parity_max, gap)
        if gap > 1e-10:
            raise RuntimeError(f"Frozen NDS mismatch: {r['model']}/{r['target_id']}/{r['metric']}")
        changed_normalized_rows += int(abs(new_value - float(r["nds"])) > 1e-12)
        r["nds"] = new_value
    if len(old_normalized) != len(new_normalized):
        raise RuntimeError("Normalized row count drift")

    old_model = read_csv(frozen_model_path)
    new_model = [dict(r) for r in old_model]
    old_speaker = read_csv(frozen_speaker_path)
    new_speaker = [dict(r) for r in old_speaker]
    model_deltas = []
    for r in new_model:
        if r["trait_family"] != "segmental":
            continue
        model, metric, support = r["model"], r["primary_metric"], r["support"]
        old_subset = [x for x in old_normalized if x["model"] == model and x["metric"] == metric
                      and (support != "common_support" or x["three_model_common_support"] == "1")]
        new_subset = [x for x in new_normalized if x["model"] == model and x["metric"] == metric
                      and (support != "common_support" or x["three_model_common_support"] == "1")]
        old_est, old_lo, old_hi, old_n = bootstrap_speaker_equal(
            [{**x, "nds": float(x["nds"])} for x in old_subset], 20260923)
        new_est, new_lo, new_hi, new_n = bootstrap_speaker_equal(
            [{**x, "nds": float(x["nds"])} for x in new_subset], 20260923)
        if (len(old_subset) != int(r["n_target_metric_rows"]) or old_n != int(r["n_speakers"])
                or abs(old_est - float(r["speaker_equal_mean_nds"])) > 1e-10
                or abs(old_lo - float(r["speaker_cluster_bootstrap_95ci_low"])) > 1e-10
                or abs(old_hi - float(r["speaker_cluster_bootstrap_95ci_high"])) > 1e-10):
            raise RuntimeError(f"Frozen summary mismatch: {model}/{support}")
        r.update(speaker_equal_mean_nds=new_est,
                 speaker_cluster_bootstrap_95ci_low=new_lo,
                 speaker_cluster_bootstrap_95ci_high=new_hi,
                 sample_median_nds=float(np.median([float(x["nds"]) for x in new_subset])))
        model_deltas.append({"model": model, "support": support, "n_targets": len(new_subset),
                             "n_speakers": new_n, "old_nds": old_est, "new_nds": new_est,
                             "delta_nds": new_est - old_est, "old_ci_low": old_lo,
                             "old_ci_high": old_hi, "new_ci_low": new_lo, "new_ci_high": new_hi})
    for r in new_speaker:
        if r["trait_family"] != "segmental":
            continue
        subset = [x for x in new_normalized if x["model"] == r["model"] and x["speaker"] == r["speaker"]
                  and x["metric"] == r["primary_metric"] and
                  (r["support"] != "common_support" or x["three_model_common_support"] == "1")]
        if len(subset) != int(r["n_targets"]):
            raise RuntimeError("Speaker support mismatch")
        values = np.asarray([float(x["nds"]) for x in subset])
        r["speaker_mean_nds"] = float(np.mean(values))
        r["speaker_median_nds"] = float(np.median(values))
    if any(a != b for a, b in zip(old_model, new_model) if a["trait_family"] != "segmental"):
        raise RuntimeError("Nonsegmental model summary changed")
    if any(a != b for a, b in zip(old_speaker, new_speaker) if a["trait_family"] != "segmental"):
        raise RuntimeError("Nonsegmental speaker summary changed")

    OUT.mkdir()
    for filename, rows in (("natural_vowel_tokens.csv", new_baseline),
                           ("natural_vowel_scales.csv", new_scale_rows),
                           ("preservation_normalized_long.csv", new_normalized),
                           ("preservation_model_trait_summary.csv", new_model),
                           ("preservation_speaker_trait_summary.csv", new_speaker),
                           ("model_delta.csv", model_deltas)):
        write_csv(OUT / filename, rows)
    audit = {"status": "REVIEWED_RQ1_REVISION_NOT_FROZEN_OVERWRITE",
             "frozen_baseline_rows": len(old_baseline), "review_flagged_rows": 2054,
             "manually_changed_rows": len(patched), "B1926": "frozen original retained",
             "normalized_rows": len(new_normalized),
             "normalized_rows_with_changed_nds": changed_normalized_rows,
             "frozen_scale_reproduced": True, "frozen_token_nds_max_gap": old_token_parity_max,
             "frozen_summary_point_and_ci_reproduced": True,
             "nonsegmental_results_unchanged": True,
             "axes_fixed": "Original frozen speaker vowel axes remain fixed; RQ2 not reanalyzed",
             "input_sha256": {p.name: sha256(p) for p in
                              (review_path, change_path, baseline_path, frozen_scales_path,
                               frozen_norm_path, frozen_model_path, frozen_speaker_path)},
             "output_sha256": {p.name: sha256(p) for p in OUT.iterdir() if p.is_file()},
             "interpretation": "Post hoc data correction of 41 C-baseline vowels using existing A original/clone measurements; no synthesis or realignment."}
    (OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model_deltas": [r for r in model_deltas if r["support"] == "common_support"],
                      "audit": audit}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
