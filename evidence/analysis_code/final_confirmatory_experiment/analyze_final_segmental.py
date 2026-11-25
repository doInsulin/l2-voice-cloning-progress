"""Paired F5 canonical-direction DID for frozen IH→IY and EH→AE targets."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FEATURES = ("delta_p", "delta_log_f1", "delta_log_f2", "delta_log_duration")
SEED = 20260923


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = records(HERE / "features/f5_tts_segmental_tokens.jsonl")
    if len(rows) != 312:
        raise RuntimeError("Segmental technical denominator incomplete")
    pairs = defaultdict(dict)
    for row in rows:
        pairs[row["pair_id"]][row["role"]] = row
    if len(pairs) != 156 or any(set(p) != {"ERROR", "CONTROL"} for p in pairs.values()):
        raise RuntimeError("Frozen 156 error/control pairs changed")
    pair_qc = []
    results = []
    valid = defaultdict(list)
    for pair_id, records_by_role in sorted(pairs.items()):
        error, control = records_by_role["ERROR"], records_by_role["CONTROL"]
        pass_pair = error["status"] == control["status"] == "PASS"
        base = {"contrast": error["contrast"], "speaker": error["speaker"], "pair_id": pair_id,
                "error_target_id": error["target_id"], "control_target_id": control["target_id"],
                "pair_status": "PASS" if pass_pair else "FAIL",
                "error_reasons": "|".join(error["reasons"]), "control_reasons": "|".join(control["reasons"])}
        pair_qc.append(base)
        if not pass_pair:
            continue
        a, b = error["acoustic"], control["acoustic"]
        for metric in FEATURES:
            difference = a[metric] - b[metric]
            if difference is None or not math.isfinite(difference):
                raise RuntimeError(f"PASS pair with nonfinite DID: {pair_id}/{metric}")
            result = {"level": "pair", "contrast": error["contrast"], "speaker": error["speaker"],
                      "pair_id": pair_id, "feature": "did_"+metric,
                      "estimate": difference, "ci_low_95": "", "ci_high_95": "",
                      "n_pairs": 1, "n_speakers": 1,
                      "error_delta": a[metric], "control_delta": b[metric],
                      "direction": "positive_toward_canonical" if metric == "delta_p" else "log_or_raw_difference"}
            results.append(result)
            valid[(error["contrast"], error["speaker"], metric)].append(float(difference))
    write(HERE / "segmental_pair_qc.csv", pair_qc)
    rng = np.random.default_rng(SEED)
    for contrast in ("IH_TO_IY", "EH_TO_AE"):
        for metric in FEATURES:
            speakers = sorted({s for c, s, m in valid if c == contrast and m == metric})
            speaker_means = []
            for speaker in speakers:
                x = np.asarray(valid[(contrast, speaker, metric)], dtype=float)
                speaker_means.append(float(np.mean(x)))
                if len(x) > 1:
                    boot = np.asarray([np.mean(rng.choice(x, size=len(x), replace=True)) for _ in range(4000)])
                    low, high = np.quantile(boot, [.025, .975])
                else:
                    low = high = math.nan
                results.append({"level": "speaker", "contrast": contrast, "speaker": speaker,
                                "pair_id": "", "feature": "did_"+metric,
                                "estimate": float(np.mean(x)), "ci_low_95": low,
                                "ci_high_95": high, "n_pairs": len(x), "n_speakers": 1,
                                "error_delta": "", "control_delta": "",
                                "direction": "positive_toward_canonical" if metric == "delta_p" else "log_or_raw_difference"})
            if speaker_means:
                means = np.asarray(speaker_means)
                boot = np.asarray([np.mean(rng.choice(means, size=len(means), replace=True)) for _ in range(6000)])
                low, high = np.quantile(boot, [.025, .975])
                results.append({"level": "overall_speaker_equal", "contrast": contrast, "speaker": "",
                                "pair_id": "", "feature": "did_"+metric,
                                "estimate": float(np.mean(means)), "ci_low_95": low,
                                "ci_high_95": high,
                                "n_pairs": sum(len(valid[(contrast, s, metric)]) for s in speakers),
                                "n_speakers": len(speakers), "error_delta": "", "control_delta": "",
                                "direction": "positive_toward_canonical" if metric == "delta_p" else "log_or_raw_difference"})
                robust_speakers = [s for s in speakers if len(valid[(contrast, s, metric)]) >= 4]
                if len(robust_speakers) >= 2:
                    stable_means = np.asarray([np.mean(valid[(contrast, s, metric)]) for s in robust_speakers])
                    stable_boot = np.asarray([np.mean(rng.choice(stable_means, size=len(stable_means), replace=True))
                                              for _ in range(6000)])
                    stable_low, stable_high = np.quantile(stable_boot, [.025, .975])
                    results.append({"level": "overall_speaker_equal_ge4pairs_sensitivity", "contrast": contrast,
                                    "speaker": "", "pair_id": "", "feature": "did_"+metric,
                                    "estimate": float(np.mean(stable_means)), "ci_low_95": stable_low,
                                    "ci_high_95": stable_high,
                                    "n_pairs": sum(len(valid[(contrast, s, metric)]) for s in robust_speakers),
                                    "n_speakers": len(robust_speakers), "error_delta": "", "control_delta": "",
                                    "direction": "positive_toward_canonical" if metric == "delta_p" else "log_or_raw_difference"})
    write(HERE / "segmental_confirmatory_results.csv", results)
    print(json.dumps({"frozen_pairs": len(pairs), "complete_pairs": sum(r["pair_status"] == "PASS" for r in pair_qc),
                      "by_contrast": {c: {"candidate": sum(r["contrast"] == c for r in pair_qc),
                                         "complete": sum(r["contrast"] == c and r["pair_status"] == "PASS" for r in pair_qc)}
                                      for c in ("IH_TO_IY", "EH_TO_AE")}}, indent=2))


if __name__ == "__main__":
    main()
