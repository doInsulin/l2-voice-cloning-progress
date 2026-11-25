"""Raw and natural-scale preservation profile without a cross-trait total score."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = ("f5_tts", "cosyvoice2", "openvoice_v2")
SCALARS = {
    "f0_median_hz": "prosody", "f0_range_st": "prosody", "energy_rms_dbfs": "prosody",
    "energy_range_db": "prosody", "duration_s": "rhythm", "speech_rate_wps": "rhythm",
    "articulation_rate_wps": "rhythm", "pause_fraction": "rhythm",
    "total_internal_pause_duration_s": "rhythm", "word_duration_mean_s": "rhythm",
    "word_boundary_gap_total_s": "rhythm", "word_boundary_gap_mean_s": "rhythm",
    "leading_silence_s": "rhythm", "trailing_silence_s": "rhythm",
}
PRIMARY = {"identity": "ecapa_cosine_distance", "segmental": "vowel_median_nds_log_f1_f2",
           "rhythm": "word_boundary_gap_mean_s", "prosody": "f0_contour_rmse_st"}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def value(x) -> float | None:
    try:
        result = float(x)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def contour(a: list, b: list, minimum: int) -> tuple[float | None, float | None, int]:
    left = np.asarray([np.nan if x is None else float(x) for x in a], dtype=float)
    right = np.asarray([np.nan if x is None else float(x) for x in b], dtype=float)
    if left.shape != right.shape:
        return None, None, 0
    mask = np.isfinite(left) & np.isfinite(right)
    if int(mask.sum()) < minimum:
        return None, None, int(mask.sum())
    distance = float(np.sqrt(np.mean((left[mask]-right[mask]) ** 2)))
    correlation = float(np.corrcoef(left[mask], right[mask])[0, 1]) if np.std(left[mask]) > 1e-9 and \
        np.std(right[mask]) > 1e-9 else None
    return distance, correlation, int(mask.sum())


def write(path: Path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_speaker_equal(rows: list[dict], seed: int) -> tuple[float, float, float, int]:
    by = defaultdict(list)
    for r in rows:
        by[r["speaker"]].append(r["nds"])
    means = np.asarray([np.mean(v) for v in by.values()], dtype=float)
    if not len(means):
        return math.nan, math.nan, math.nan, 0
    estimate = float(np.mean(means))
    if len(means) < 2:
        return estimate, math.nan, math.nan, len(means)
    rng = np.random.default_rng(seed)
    draws = np.asarray([np.mean(rng.choice(means, size=len(means), replace=True)) for _ in range(4000)])
    return estimate, float(np.quantile(draws, .025)), float(np.quantile(draws, .975)), len(means)


def main() -> None:
    global_rows = []
    vowel = defaultdict(list)
    rhoticity = defaultdict(list)
    for model in MODELS:
        phase = model + "_preservation"
        rows = records(HERE / "features" / f"{phase}_global.jsonl")
        if len(rows) != 160:
            raise RuntimeError(f"Global preservation incomplete: {phase}")
        global_rows.extend(rows)
        for token in records(HERE / "features" / f"{phase}_vowels.jsonl"):
            if token["status"] == "PASS":
                vowel[(model, token["target_id"])].append(token)
        for token in records(HERE / "features" / f"{phase}_rhoticity.jsonl"):
            if token["status"] == "PASS":
                rhoticity[(model, token["target_id"])].append(token)
    ecapa = {(r["model"], r["phase"], r["target_id"], r["condition"]): r for r in
             read(HERE / "features/final_ecapa_similarities.csv")}
    scalar_scales = {(r["speaker"], r["metric"]): r for r in read(HERE / "natural_variability_scales.csv")}
    contour_scales = {(r["speaker"], r["metric"]): r for r in read(HERE / "natural_contour_scales.csv")}
    pause_scales = {r["speaker"]: r for r in read(HERE / "natural_pause_placement_scales.csv")}
    raw = []
    normalized = []
    sample_qc = []

    def add(row: dict, family: str, metric: str, original, clone, raw_distance,
            natural_scale, fallback: str, normalized_override=None, unit="") -> None:
        base = {"model": row["model"], "speaker": row["speaker"], "target_id": row["target_id"],
                "trait_family": family, "metric": metric, "original": original,
                "clone": clone, "raw_distance": raw_distance, "unit": unit,
                "generation_status": row["generation_status"], "qc_status": row["status"]}
        raw.append(base)
        numerator = value(raw_distance)
        denominator = value(natural_scale)
        nds = normalized_override if normalized_override is not None else (
            numerator/denominator if numerator is not None and denominator is not None and denominator > 1e-6 else None)
        normalized.append({**base, "natural_scale": natural_scale, "fallback_reason": fallback,
                           "nds": nds, "natural_scale_definition": "held-out_original_C"})

    for row in global_rows:
        model, speaker, target_id = row["model"], row["speaker"], row["target_id"]
        tokens = vowel[(model, target_id)]
        r_tokens = rhoticity[(model, target_id)]
        sample_qc.append({"model": model, "speaker": speaker, "target_id": target_id,
                          "generation_status": row["generation_status"], "global_qc_status": row["status"],
                          "global_qc_reasons": "|".join(row["reasons"]), "valid_vowel_tokens": len(tokens),
                          "valid_rhotic_tokens": len(r_tokens)})
        if row["status"] != "PASS":
            continue
        original, clone = row["original"], row["clone"]
        for metric, family in SCALARS.items():
            a, b = value(original.get(metric)), value(clone.get(metric))
            if a is None or b is None:
                continue
            scale = scalar_scales[(speaker, metric)]
            add(row, family, metric, a, b, abs(b-a), scale["selected_scale"], scale["fallback_reason"],
                unit="Hz" if metric == "f0_median_hz" else "source_metric_units")
        for metric, column, minimum in (("f0_contour_rmse_st", "f0_contour_centered_st", 20),
                                         ("energy_contour_rmse_db", "energy_contour_relative_db", 40)):
            distance, corr, bins = contour(original[column], clone[column], minimum)
            if distance is not None:
                family = "prosody"
                scale = contour_scales[(speaker, metric)]
                add(row, family, metric, "", "", distance, scale["selected_scale"],
                    scale["fallback_reason"], unit="semitones" if metric.startswith("f0") else "dB")
                raw.append({"model": model, "speaker": speaker, "target_id": target_id,
                            "trait_family": family, "metric": metric.replace("rmse", "correlation"),
                            "original": "", "clone": "", "raw_distance": corr, "unit": "r",
                            "generation_status": row["generation_status"], "qc_status": row["status"]})
        va, vb = original["pause_placement_vector"], clone["pause_placement_vector"]
        if len(va) == len(vb) and len(va):
            distance = sum(a != b for a, b in zip(va, vb))/len(va)
            scale = pause_scales[speaker]
            add(row, "rhythm", "pause_placement_hamming", json.dumps(va), json.dumps(vb),
                distance, scale["selected_scale"], scale["fallback_reason"], unit="fraction")
        identity = ecapa[(model, "preservation", target_id, row["condition"])]
        cosine = value(identity["ecapa_cosine"])
        if cosine is not None:
            add(row, "identity", "ecapa_cosine_distance", "", "", 1-cosine,
                identity["ecapa_natural_distance"], "ORIGINAL_ORIGINAL_MEDIAN", unit="cosine_distance")
            raw.append({"model": model, "speaker": speaker, "target_id": target_id,
                        "trait_family": "identity", "metric": "ecapa_cosine_similarity",
                        "original": "", "clone": "", "raw_distance": cosine, "unit": "cosine",
                        "generation_status": row["generation_status"], "qc_status": row["status"]})
        if tokens:
            for metric, raw_key, nds_key, unit in (
                ("vowel_abs_log_f1", "delta_log_f1", "nds_log_f1", "log_ratio"),
                ("vowel_abs_log_f2", "delta_log_f2", "nds_log_f2", "log_ratio"),
                ("vowel_abs_duration", "delta_duration_s", "nds_duration", "seconds")):
                amount = float(np.median([abs(t[raw_key]) for t in tokens]))
                nds = float(np.median([t[nds_key] for t in tokens]))
                add(row, "segmental", metric, "", "", amount, "token_specific_C_vowel_scale",
                    "TOKENWISE_MAD_OR_SD", normalized_override=nds, unit=unit)
            both = [t["nds_log_f1"] for t in tokens] + [t["nds_log_f2"] for t in tokens]
            add(row, "segmental", "vowel_median_nds_log_f1_f2", "", "",
                float(np.median([abs(t["delta_log_f1"]) for t in tokens] +
                                [abs(t["delta_log_f2"]) for t in tokens])),
                "token_specific_C_vowel_scale", "TOKENWISE_MAD_OR_SD",
                normalized_override=float(np.median(both)), unit="median_abs_log_ratio")
            projected = [abs(t["delta_p"]) for t in tokens if "delta_p" in t]
            if projected:
                raw.append({"model": model, "speaker": speaker, "target_id": target_id,
                            "trait_family": "segmental", "metric": "vowel_median_abs_delta_p",
                            "original": "", "clone": "", "raw_distance": float(np.median(projected)),
                            "unit": "speaker_axis_projection", "generation_status": row["generation_status"],
                            "qc_status": row["status"]})
        if r_tokens:
            for metric, suffix, unit in (("rhotic_abs_f3_minus_f2", "f3_minus_f2_hz", "Hz"),
                                         ("rhotic_abs_log_f3_f2", "log_f3_f2_ratio", "log_ratio"),
                                         ("rhotic_abs_duration", "duration_s", "seconds")):
                amount = float(np.median([abs(t["delta_"+suffix]) for t in r_tokens]))
                nds_values = [t["nds_"+suffix] for t in r_tokens if t.get("nds_"+suffix) is not None]
                if nds_values:
                    add(row, "segmental", metric, "", "", amount, "token_specific_C_correct_R_scale",
                        "TOKENWISE_MAD_OR_SD", normalized_override=float(np.median(nds_values)), unit=unit)

    keys = defaultdict(set)
    for row in normalized:
        if value(row["nds"]) is not None:
            keys[(row["target_id"], row["metric"])].add(row["model"])
    for row in raw:
        row["three_model_common_support"] = int(len(keys[(row["target_id"], row["metric"])]) == 3)
    for row in normalized:
        row["three_model_common_support"] = int(len(keys[(row["target_id"], row["metric"])]) == 3)
    write(HERE / "preservation_raw_long.csv", raw)
    write(HERE / "preservation_normalized_long.csv", normalized)
    write(HERE / "preservation_sample_qc.csv", sample_qc)

    summaries = []
    speaker_rows = []
    for model in MODELS:
        for family, metric in PRIMARY.items():
            for support in ("common_support", "model_specific_all_valid"):
                subset = [r for r in normalized if r["model"] == model and r["trait_family"] == family
                          and r["metric"] == metric and value(r["nds"]) is not None
                          and (support != "common_support" or r["three_model_common_support"] == 1)]
                for speaker in sorted({r["speaker"] for r in subset}):
                    values = [float(r["nds"]) for r in subset if r["speaker"] == speaker]
                    speaker_rows.append({"model": model, "speaker": speaker, "trait_family": family,
                                         "primary_metric": metric, "support": support,
                                         "n_targets": len(values), "speaker_mean_nds": float(np.mean(values)),
                                         "speaker_median_nds": float(np.median(values))})
                estimate, low, high, n = bootstrap_speaker_equal(subset, 20260923)
                summaries.append({"model": model, "trait_family": family, "primary_metric": metric,
                                  "support": support, "n_speakers": n,
                                  "n_target_metric_rows": len(subset),
                                  "speaker_equal_mean_nds": estimate,
                                  "speaker_cluster_bootstrap_95ci_low": low,
                                  "speaker_cluster_bootstrap_95ci_high": high,
                                  "sample_median_nds": float(np.median([r["nds"] for r in subset])) if subset else ""})
    write(HERE / "preservation_model_trait_summary.csv", summaries)
    write(HERE / "preservation_speaker_trait_summary.csv", speaker_rows)
    print(json.dumps({"raw_rows": len(raw), "normalized_rows": len(normalized),
                      "sample_qc_rows": len(sample_qc), "common_support_primary":
                      {r["model"]+"/"+r["trait_family"]: r["n_target_metric_rows"] for r in summaries
                       if r["support"] == "common_support"}}, indent=2))


if __name__ == "__main__":
    main()
