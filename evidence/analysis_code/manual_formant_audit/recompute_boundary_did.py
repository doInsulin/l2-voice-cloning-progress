"""Post-review analysis: frozen formants for unchanged boundaries, Burg for edits.

Run only after boundary inspection is complete. Never writes frozen experiment files.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research/.acoustic_deps"))
import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "research" / "final_confirmatory_experiment"
METRICS = ("did_delta_p", "did_delta_log_f1", "did_delta_log_f2", "did_delta_log_duration")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, data, columns):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)


def project(f1, f2, axis):
    point = np.log([f1, f2])
    direction = np.asarray(axis["axis_vector"])
    return float(np.dot(point - axis["mu_deviation"], direction) / np.dot(direction, direction))


def remeasure(path, start, end, ceiling_info):
    """Reproduce the frozen Parselmouth Burg five-point formant check."""
    import parselmouth
    from scipy.io import wavfile
    sys.path.insert(0, str(HERE.parent / "research/07_auto_qc"))
    import f5_tts_auto_qc as qc

    sample_rate, raw = wavfile.read(str(path))
    samples = np.asarray(raw, dtype=float)
    if np.issubdtype(raw.dtype, np.integer):
        limits = np.iinfo(raw.dtype)
        samples /= float(max(abs(limits.min), limits.max))
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if not 0 <= start < end <= len(samples) / sample_rate:
        raise ValueError("corrected boundary outside WAV")
    sound = parselmouth.Sound(samples, sampling_frequency=int(sample_rate))
    spec = qc.SPEC["features"]["formant"]
    primary_ceiling = int(ceiling_info["chosen_ceiling_hz"])
    points = [start + (end - start) * p / 100 for p in spec["points_pct"]]
    trajectories = {}
    for ceiling in spec["alternate_ceiling_grid_hz"][ceiling_info["sex"]]:
        formant = sound.to_formant_burg(time_step=0.005, max_number_of_formants=5,
                                       maximum_formant=ceiling, window_length=0.025,
                                       pre_emphasis_from=50)
        trajectories[str(ceiling)] = [[float(formant.get_value_at_time(n, t)) for n in (1, 2)]
                                        for t in points]
    primary = trajectories[str(primary_ceiling)]
    alternate = {k: v for k, v in trajectories.items() if k != str(primary_ceiling)}
    check = qc.check_formants(primary, alternate)
    flags = [*check["reasons"], *check["flags"]]
    return primary[2][0], primary[2][1], "|".join(dict.fromkeys(flags))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out == FROZEN.resolve() or FROZEN.resolve() in out.parents:
        raise ValueError("Output must be a new directory outside the frozen experiment")
    review = read_csv(args.review)
    key = read_csv(HERE / "restricted/sample_index.csv")
    if len(review) != 380 or len(key) != 380:
        raise ValueError("Expected 380 review and key rows")
    by_id = {r["audit_id"]: r for r in review}
    if len(by_id) != 380 or set(by_id) != {r["audit_id"] for r in key}:
        raise ValueError("Audit IDs missing or duplicated")
    allowed = {"audit_id", "contrast", "wav", "textgrid", "word", "phone_start_s",
               "phone_end_s", "midpoint_s", "burg_ceiling_hz", "reviewed_start_s",
               "reviewed_end_s", "position_note"}
    if set(review[0]) != allowed:
        raise ValueError("Unexpected review columns")
    counts = Counter((r["contrast"], r["frozen_pair_qc"]) for r in key)
    assert counts == Counter({("EH_TO_AE", "PASS"): 156, ("IH_TO_IY", "PASS"): 224})
    features = {r["target_id"]: r for r in (json.loads(line) for line in
                (FROZEN / "features/f5_tts_segmental_tokens.jsonl")
                .read_text(encoding="utf-8").splitlines() if line.strip())}
    axes = json.loads((FROZEN / "natural_vowel_axes.json").read_text(encoding="utf-8"))["axes"]
    ceilings = json.loads((FROZEN / "final_formant_ceilings.json").read_text(encoding="utf-8"))["speakers"]
    units, slots = [], {}
    for identity in key:
        aid, condition = identity["audit_id"], identity["condition"]
        row, frozen = by_id[aid], features[identity["target_id"]]
        if row["contrast"] != identity["contrast"]:
            raise ValueError(f"{aid}: contrast changed")
        if Path(row["wav"]).resolve() != (HERE / "praat" / f"{aid}.wav").resolve():
            raise ValueError(f"{aid}: audit WAV path changed")
        if Path(row["textgrid"]).resolve() != (HERE / "praat" / f"{aid}.TextGrid").resolve():
            raise ValueError(f"{aid}: audit TextGrid path changed")
        if int(float(row["burg_ceiling_hz"])) != int(ceilings[identity["speaker"]]["chosen_ceiling_hz"]):
            raise ValueError(f"{aid}: Burg ceiling changed")
        old_start, old_end = map(float, frozen["original_interval" if condition == "ORIGINAL" else "clone_interval"]["phone"])
        if abs(float(row["phone_start_s"]) - old_start) > 1e-5 or abs(float(row["phone_end_s"]) - old_end) > 1e-5:
            raise ValueError(f"{aid}: frozen boundary columns changed")
        if abs(float(row["midpoint_s"]) - (old_start + old_end) / 2) > 1e-5:
            raise ValueError(f"{aid}: frozen midpoint column changed")
        start = float(row["reviewed_start_s"]) if row["reviewed_start_s"].strip() else old_start
        end = float(row["reviewed_end_s"]) if row["reviewed_end_s"].strip() else old_end
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise ValueError(f"{aid}: invalid reviewed boundary")
        changed = abs(start - old_start) > 1e-9 or abs(end - old_end) > 1e-9
        status, flag, f1, f2 = "FROZEN", "", None, None
        if "UNRESOLVED" in row["position_note"].upper():
            status = "UNRESOLVED"
        elif changed:
            try:
                f1, f2, flag = remeasure(Path(identity["source_wav"]), start, end, ceilings[identity["speaker"]])
                status = "REMEASURED_QC_FLAG" if flag else "REMEASURED"
            except ValueError as exc:
                status, flag = "REMEASUREMENT_FAIL", str(exc)
        else:
            auto = frozen["original_formants" if condition == "ORIGINAL" else "clone_formants"]
            f1, f2 = float(auto["midpoint_f1_hz"]), float(auto["midpoint_f2_hz"])
        if f1 is not None and not (math.isfinite(f1) and math.isfinite(f2) and 0 < f1 < f2):
            raise ValueError(f"{aid}: invalid F1/F2")
        unit = {"audit_id": aid, "pair_id": identity["pair_id"], "contrast": identity["contrast"],
                "speaker": identity["speaker"], "role": identity["role"], "condition": condition,
                "frozen_start_s": old_start, "frozen_end_s": old_end,
                "reviewed_start_s": start, "reviewed_end_s": end, "measurement_source": status,
                "f1_hz": f1 if f1 is not None else "", "f2_hz": f2 if f2 is not None else "",
                "formant_note": flag, "position_note": row["position_note"]}
        units.append(unit)
        slot = (identity["pair_id"], identity["role"], condition)
        if slot in slots:
            raise ValueError(f"Duplicate unit {slot}")
        slots[slot] = unit
    pair_ids = sorted({r["pair_id"] for r in units})
    if len(pair_ids) != 95:
        raise ValueError("Expected 95 frozen PASS pairs")
    pairs, attrition, by_speaker = [], [], defaultdict(list)
    for pair_id in pair_ids:
        members = [slots[(pair_id, role, condition)] for role in ("ERROR", "CONTROL")
                   for condition in ("ORIGINAL", "CLONE")]
        contrast, speaker = members[0]["contrast"], members[0]["speaker"]
        bad = [r for r in members if r["measurement_source"] in {"UNRESOLVED", "REMEASUREMENT_FAIL"}]
        attrition.append({"pair_id": pair_id, "contrast": contrast, "speaker": speaker,
                          "included": "NO" if bad else "YES",
                          "excluded_audit_ids": "|".join(r["audit_id"] for r in bad),
                          "reason": "|".join(r["measurement_source"] for r in bad)})
        if bad:
            continue
        axis = axes[speaker][contrast]
        def val(role, condition, metric):
            r = slots[(pair_id, role, condition)]
            if metric == "p":
                return project(r["f1_hz"], r["f2_hz"], axis)
            if metric == "duration":
                return r["reviewed_end_s"] - r["reviewed_start_s"]
            return r[metric + "_hz"]
        def delta(role, metric):
            clone, original = val(role, "CLONE", metric), val(role, "ORIGINAL", metric)
            return clone - original if metric == "p" else math.log(clone / original)
        effect = {"pair_id": pair_id, "contrast": contrast, "speaker": speaker,
                  "did_delta_p": delta("ERROR", "p") - delta("CONTROL", "p"),
                  "did_delta_log_f1": delta("ERROR", "f1") - delta("CONTROL", "f1"),
                  "did_delta_log_f2": delta("ERROR", "f2") - delta("CONTROL", "f2"),
                  "did_delta_log_duration": delta("ERROR", "duration") - delta("CONTROL", "duration")}
        pairs.append(effect)
        by_speaker[(contrast, speaker)].append(effect)
    rng = np.random.default_rng(20260923)
    overall = []
    for contrast in ("IH_TO_IY", "EH_TO_AE"):
        for metric in METRICS:
            speakers = sorted(s for c, s in by_speaker if c == contrast)
            means = []
            for speaker in speakers:
                values = np.asarray([r[metric] for r in by_speaker[(contrast, speaker)]])
                means.append(float(np.mean(values)))
                if len(values) > 1:
                    np.asarray([np.mean(rng.choice(values, size=len(values), replace=True))
                                for _ in range(4000)])
            bootstrap = np.asarray([np.mean(rng.choice(means, size=len(means), replace=True))
                                    for _ in range(6000)])
            low, high = np.quantile(bootstrap, [0.025, 0.975])
            overall.append({"level": "overall_speaker_equal", "contrast": contrast, "feature": metric,
                            "estimate": float(np.mean(means)) if means else "",
                            "ci_low_95": low, "ci_high_95": high,
                            "n_pairs": sum(len(by_speaker[(contrast, s)]) for s in speakers),
                            "n_speakers": len(speakers)})
            robust_speakers = [s for s in speakers if len(by_speaker[(contrast, s)]) >= 4]
            if len(robust_speakers) >= 2:
                stable_means = np.asarray([np.mean([r[metric] for r in by_speaker[(contrast, s)]])
                                           for s in robust_speakers])
                stable_boot = np.asarray([np.mean(rng.choice(stable_means, size=len(stable_means), replace=True))
                                          for _ in range(6000)])
                stable_low, stable_high = np.quantile(stable_boot, [0.025, 0.975])
                overall.append({"level": "overall_speaker_equal_ge4pairs_sensitivity",
                                "contrast": contrast, "feature": metric,
                                "estimate": float(np.mean(stable_means)), "ci_low_95": stable_low,
                                "ci_high_95": stable_high,
                                "n_pairs": sum(len(by_speaker[(contrast, s)]) for s in robust_speakers),
                                "n_speakers": len(robust_speakers)})
    out.mkdir(parents=True)
    write_csv(out / "unit_measurements.csv", units, list(units[0]))
    write_csv(out / "pair_attrition.csv", attrition, list(attrition[0]))
    write_csv(out / "pair_results.csv", pairs, ["pair_id", "contrast", "speaker", *METRICS])
    write_csv(out / "overall_results.csv", overall, list(overall[0]))


if __name__ == "__main__":
    main()
