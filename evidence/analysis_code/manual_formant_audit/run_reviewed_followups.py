"""Reanalyse RQ2 follow-ups from the completed human boundary review.

Inputs are immutable frozen artifacts and the new midpoint-unit ledger. Outputs
are written only in the supplied reanalysis directory. No synthesis or MFA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT / "research/final_confirmatory_experiment"
DYNAMIC = ROOT / "research/33_dynamic_vowel_trajectory_20261022"
sys.path.insert(0, str(ROOT / "research/.acoustic_deps"))
import numpy as np


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def import_source(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_initial_gap(out: Path, units: list[dict[str, str]]) -> None:
    from recompute_boundary_did import project

    axes = json.loads((FROZEN / "natural_vowel_axes.json").read_text(encoding="utf-8"))["axes"]
    index = csv_rows(HERE / "restricted/sample_index.csv")
    unit_by_id = {r["audit_id"]: r for r in units}
    by_target = {}
    for row in index:
        unit = unit_by_id[row["audit_id"]]
        p = project(float(unit["f1_hz"]), float(unit["f2_hz"]),
                    axes[row["speaker"]][row["contrast"]])
        by_target.setdefault(row["target_id"], {})[row["condition"]] = p
    source = out / "initial_gap_source"
    (source / "features").mkdir(parents=True, exist_ok=False)
    shutil.copyfile(FROZEN / "segmental_pair_qc.csv", source / "segmental_pair_qc.csv")
    frozen_records = [json.loads(line) for line in
                      (FROZEN / "features/f5_tts_segmental_tokens.jsonl")
                      .read_text(encoding="utf-8").splitlines() if line.strip()]
    with (source / "features/f5_tts_segmental_tokens.jsonl").open("w", encoding="utf-8") as stream:
        for record in frozen_records:
            if record["target_id"] in by_target:
                positions = by_target[record["target_id"]]
                record["acoustic"]["original_p"] = positions["ORIGINAL"]
                record["acoustic"]["clone_p"] = positions["CLONE"]
                record["acoustic"]["delta_p"] = positions["CLONE"] - positions["ORIGINAL"]
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    sensitivity = import_source(
        "reviewed_initial_gap", ROOT / "thesis_manuscript/audit/rq2_initial_distance_sensitivity.py")
    sensitivity.SOURCE = source
    sensitivity.OUT = out / "initial_gap"
    sensitivity.main()
    audit_path = sensitivity.OUT / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit.update(status="POST_HOC_REVIEWED_BOUNDARY_SENSITIVITY_COMPLETE",
                 acoustic_features_reextracted=True,
                 reextracted_changed_intervals=116,
                 unchanged_intervals_reused=264)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")


def run_dynamic(out: Path, units: list[dict[str, str]]) -> dict:
    analysis = import_source("reviewed_dynamic", DYNAMIC / "analyze.py")
    prior = csv_rows(DYNAMIC / "reconstruction_token_trajectories.csv")
    index = csv_rows(HERE / "restricted/sample_index.csv")
    unit_by_id = {r["audit_id"]: r for r in units}
    identity = {(r["target_id"], r["condition"]): r for r in index}
    ceilings = json.loads((FROZEN / "final_formant_ceilings.json").read_text(encoding="utf-8"))["speakers"]
    sounds = {}
    changed = 0
    max_midpoint_difference = 0.0
    results = []
    for old in prior:
        row = dict(old)
        for condition, prefix in (("ORIGINAL", "original"), ("CLONE", "clone")):
            key = identity[row["target_id"], condition]
            unit = unit_by_id[key["audit_id"]]
            if unit["measurement_source"] == "FROZEN":
                continue
            path = key["source_wav"]
            if path not in sounds:
                sounds[path] = analysis.parselmouth.Sound(path)
            sound = sounds[path]
            start, end = float(unit["reviewed_start_s"]), float(unit["reviewed_end_s"])
            ceiling = int(ceilings[row["speaker"]]["chosen_ceiling_hz"])
            sex = ceilings[row["speaker"]]["sex"]
            f1, f2, check = analysis.extract_track(
                sound, {"start": start, "end": end}, ceiling, sex, {})
            track_reasons, strict_reasons = analysis.dynamic_flags(
                f1, f2, end - start, check, 0 <= start < end <= sound.duration)
            row[prefix + "_log_f1"] = json.dumps([math.log(x) if x else None for x in f1])
            row[prefix + "_log_f2"] = json.dumps([math.log(x) if x else None for x in f2])
            row[prefix + "_duration_s"] = end - start
            row[prefix + "_track_qc"] = int(not track_reasons)
            row[prefix + "_strict_qc"] = int(not strict_reasons)
            row[prefix + "_reasons"] = "|".join(strict_reasons)
            if f1[2] is not None and f2[2] is not None:
                max_midpoint_difference = max(max_midpoint_difference,
                    abs(f1[2] - float(unit["f1_hz"])),
                    abs(f2[2] - float(unit["f2_hz"])))
            changed += 1
        row["pair_strict_qc"] = int(int(row["original_strict_qc"]) and int(row["clone_strict_qc"]))
        row["pair_track_qc"] = int(int(row["original_track_qc"]) and int(row["clone_track_qc"]))
        results.append(row)
    if changed != 116 or len(results) != 190:
        raise RuntimeError(f"Expected 116 changed units and 190 tokens, got {changed}/{len(results)}")
    if max_midpoint_difference > 0.05:
        raise RuntimeError(f"Static/dynamic midpoint mismatch: {max_midpoint_difference} Hz")
    analysis.HERE = out
    analysis.extract_segmental = lambda: (results, max_midpoint_difference)
    summary = analysis.step2()
    return {"changed_unit_trajectories": changed,
            "max_midpoint_difference_hz": max_midpoint_difference,
            "dynamic_pair_counts": summary["pair_counts"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if HERE.resolve() not in out.parents:
        raise ValueError("Output must be a reanalysis directory under manual_formant_audit")
    units = csv_rows(out / "unit_measurements.csv")
    if len(units) != 380 or Counter(r["measurement_source"] == "FROZEN" for r in units) != {True: 264, False: 116}:
        raise RuntimeError("Unexpected midpoint ledger")
    if (out / "initial_gap").exists() or (out / "reconstruction_overall_results.csv").exists():
        raise RuntimeError("Follow-up outputs already exist; preserve previous run")
    run_initial_gap(out, units)
    dynamic = run_dynamic(out, units)
    audit = {"boundary_review_sha256": sha(HERE / "boundary_review.CSV"),
             "unit_measurements_sha256": sha(out / "unit_measurements.csv"),
             "frozen_trajectory_sha256": sha(DYNAMIC / "reconstruction_token_trajectories.csv"),
             "status": "POST_HOC_MANUAL_BOUNDARY_REANALYSIS",
             **dynamic}
    (out / "followup_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
