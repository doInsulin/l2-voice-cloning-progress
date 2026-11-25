"""Prespecified normalization, support, aggregation, and QC sensitivities."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research/.acoustic_deps"))
import numpy as np
from scipy.stats import spearmanr

MODELS = ("f5_tts", "cosyvoice2", "openvoice_v2")
PRIMARY = {"identity": "ecapa_cosine_distance", "segmental": "vowel_median_nds_log_f1_f2",
           "rhythm": "word_boundary_gap_mean_s", "prosody": "f0_contour_rmse_st"}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def num(v) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else math.nan
    except (ValueError, TypeError):
        return math.nan


def speaker_equal(rows: list[dict], field: str) -> tuple[float, int]:
    by = defaultdict(list)
    for r in rows:
        number = num(r.get(field))
        if math.isfinite(number):
            by[r["speaker"]].append(number)
    return (float(np.mean([np.mean(v) for v in by.values()])), len(by)) if by else (math.nan, 0)


def main() -> None:
    normalized = read(HERE / "preservation_normalized_long.csv")
    summary = read(HERE / "preservation_model_trait_summary.csv")
    scale = {(r["speaker"], r["metric"]): r for r in read(HERE / "natural_variability_scales.csv")}
    results = []
    by_summary = {(r["model"], r["trait_family"], r["support"]): r for r in summary}
    for model in MODELS:
        for family, metric in PRIMARY.items():
            common = by_summary[(model, family, "common_support")]
            specific = by_summary[(model, family, "model_specific_all_valid")]
            results.append({"sensitivity": "common_vs_model_specific_support", "model": model,
                            "trait_family": family, "metric": metric,
                            "primary_estimate": num(common["speaker_equal_mean_nds"]),
                            "alternative_estimate": num(specific["speaker_equal_mean_nds"]),
                            "n_speakers": common["n_speakers"],
                            "n_primary_rows": common["n_target_metric_rows"],
                            "n_alternative_rows": specific["n_target_metric_rows"]})
            subset = [r for r in normalized if r["model"] == model and r["metric"] == metric
                      and r["three_model_common_support"] == "1" and math.isfinite(num(r["nds"]))]
            sample_mean = float(np.mean([num(r["nds"]) for r in subset])) if subset else math.nan
            results.append({"sensitivity": "speaker_equal_vs_sample_weighted", "model": model,
                            "trait_family": family, "metric": metric,
                            "primary_estimate": num(common["speaker_equal_mean_nds"]),
                            "alternative_estimate": sample_mean,
                            "n_speakers": common["n_speakers"],
                            "n_primary_rows": len(subset), "n_alternative_rows": len(subset)})
    for metric, family in (("f0_range_st", "prosody"), ("f0_median_hz", "prosody"),
                           ("word_boundary_gap_mean_s", "rhythm"), ("pause_fraction", "rhythm")):
        for model in MODELS:
            subset = [r for r in normalized if r["model"] == model and r["metric"] == metric
                      and r["three_model_common_support"] == "1" and math.isfinite(num(r["nds"]))]
            primary, n = speaker_equal(subset, "nds")
            alternative = []
            for row in subset:
                sd = num(scale[(row["speaker"], metric)]["speaker_sd_scale"])
                distance = num(row["raw_distance"])
                if math.isfinite(sd) and sd > 1e-6 and math.isfinite(distance):
                    alternative.append({"speaker": row["speaker"], "sd_nds": distance/sd})
            alt, n_alt = speaker_equal(alternative, "sd_nds")
            results.append({"sensitivity": "MAD_vs_speaker_SD_normalization", "model": model,
                            "trait_family": family, "metric": metric,
                            "primary_estimate": primary, "alternative_estimate": alt,
                            "n_speakers": n_alt, "n_primary_rows": len(subset),
                            "n_alternative_rows": len(alternative)})
    for family, metric in PRIMARY.items():
        group = [r for r in normalized if r["metric"] == metric and r["three_model_common_support"] == "1"
                 and math.isfinite(num(r["raw_distance"])) and math.isfinite(num(r["nds"]))]
        by = defaultdict(list)
        for row in group:
            by[(row["model"], row["speaker"])].append(row)
        raw_values = [float(np.mean([num(r["raw_distance"]) for r in group_rows])) for group_rows in by.values()]
        nds_values = [float(np.mean([num(r["nds"]) for r in group_rows])) for group_rows in by.values()]
        if len(raw_values) > 2:
            rho, pvalue = spearmanr(raw_values, nds_values)
        else:
            rho, pvalue = math.nan, math.nan
        results.append({"sensitivity": "raw_distance_vs_NDS_rank", "model": "all_three",
                        "trait_family": family, "metric": metric,
                        "primary_estimate": "", "alternative_estimate": "",
                        "rank_spearman_rho": rho, "rank_p_value": pvalue,
                        "rank_unit": "model_speaker_profile",
                        "n_speakers": len({s for _, s in by}),
                        "n_primary_rows": len(group), "n_alternative_rows": len(by)})
    # QC exclusion sensitivity only observes acoustic features that exist for the
    # generated WAV; it never promotes a failed sample to primary analysis.
    for model in MODELS:
        phase = model + "_preservation"
        global_rows = records(HERE / "features" / f"{phase}_global.jsonl")
        for metric, family in (("f0_range_st", "prosody"), ("word_boundary_gap_mean_s", "rhythm")):
            all_observed, qc = [], []
            for row in global_rows:
                if "original" not in row or "clone" not in row:
                    continue
                a, b = num(row["original"].get(metric)), num(row["clone"].get(metric))
                natural = num(scale[(row["speaker"], metric)]["selected_scale"])
                if not all(math.isfinite(x) for x in (a, b, natural)) or natural <= 1e-6:
                    continue
                observation = {"speaker": row["speaker"], "value": abs(b-a)/natural}
                all_observed.append(observation)
                if row["status"] == "PASS":
                    qc.append(observation)
            a, n = speaker_equal(qc, "value")
            b, _ = speaker_equal(all_observed, "value")
            results.append({"sensitivity": "QC_pass_vs_all_generated_observed", "model": model,
                            "trait_family": family, "metric": metric,
                            "primary_estimate": a, "alternative_estimate": b,
                            "n_speakers": n, "n_primary_rows": len(qc),
                            "n_alternative_rows": len(all_observed)})
    for row in results:
        a, b = num(row["primary_estimate"]), num(row["alternative_estimate"])
        row["alternative_minus_primary"] = b-a if math.isfinite(a) and math.isfinite(b) else ""
    path = HERE / "sensitivity_results.csv"
    columns = list(dict.fromkeys(k for r in results for k in r))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({"rows": len(results), "sensitivity_types": sorted({r["sensitivity"] for r in results})},
                     indent=2))


if __name__ == "__main__":
    main()
