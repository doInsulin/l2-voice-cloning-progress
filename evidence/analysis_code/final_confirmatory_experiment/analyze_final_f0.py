"""Frozen three-condition F5 reference-F0 response, target paired."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CONDITIONS = ("F0_COMPRESSED", "ORIGINAL", "F0_EXPANDED")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def contour_rmse(left: list, right: list, minimum: int) -> float | None:
    a = np.asarray([np.nan if x is None else float(x) for x in left], dtype=float)
    b = np.asarray([np.nan if x is None else float(x) for x in right], dtype=float)
    if a.shape != b.shape:
        return None
    mask = np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean((a[mask] - b[mask]) ** 2))) if mask.sum() >= minimum else None


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        columns = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    features = records(HERE / "features/f5_tts_f0_global.jsonl")
    if len(features) != 288:
        raise RuntimeError("F0 global feature denominator incomplete")
    feature = {(r["target_id"], r["condition"]): r for r in features}
    reference = {(r["speaker"], r["condition"]): r for r in read(HERE / "f0_reference_manipulation_manifest.csv")}
    scales = {(r["speaker"], r["metric"]): float(r["selected_scale"])
              for r in read(HERE / "natural_variability_scales.csv") if r["selected_scale"]}
    ecapa_path = HERE / "features/final_ecapa_similarities.csv"
    identity = {(r["target_id"], r["condition"]): r for r in read(ecapa_path)
                if r["model"] == "f5_tts" and r["phase"] == "f0"} if ecapa_path.exists() else {}
    groups = defaultdict(dict)
    for r in features:
        groups[(r["speaker"], r["target_id"])][r["condition"]] = r
    if len(groups) != 96:
        raise RuntimeError("Expected 96 frozen F0 targets")
    output = []
    for (speaker, target_id), three in sorted(groups.items()):
        rec = {"speaker": speaker, "target_id": target_id, "n_conditions": len(three),
               "technical_status": "FAIL", "reasons": ""}
        if set(three) != set(CONDITIONS):
            rec["reasons"] = "MISSING_CONDITION"
        elif any(three[c]["status"] != "PASS" for c in CONDITIONS):
            rec["reasons"] = "|".join(f"{c}:{','.join(three[c]['reasons'])}" for c in CONDITIONS
                                      if three[c]["status"] != "PASS")
        else:
            measured = {c: float(three[c]["clone"]["f0_range_st"]) for c in CONDITIONS}
            ref = {c: float(reference[(speaker, c)]["f0_range_st"]) for c in CONDITIONS}
            natural = scales[(speaker, "f0_range_st")]
            raw_output = measured["F0_EXPANDED"] - measured["F0_COMPRESSED"]
            raw_ref = ref["F0_EXPANDED"] - ref["F0_COMPRESSED"]
            rec.update(technical_status="PASS", natural_f0_range_scale_st=natural,
                       reference_range_compressed_st=ref["F0_COMPRESSED"],
                       reference_range_original_st=ref["ORIGINAL"],
                       reference_range_expanded_st=ref["F0_EXPANDED"],
                       output_range_compressed_st=measured["F0_COMPRESSED"],
                       output_range_original_st=measured["ORIGINAL"],
                       output_range_expanded_st=measured["F0_EXPANDED"],
                       delta_reference_expanded_minus_compressed_st=raw_ref,
                       delta_output_expanded_minus_compressed_st=raw_output,
                       delta_reference_natural_units=raw_ref/natural,
                       delta_output_natural_units=raw_output/natural,
                       raw_transfer_gain=raw_output/raw_ref if abs(raw_ref) > 1e-6 else "",
                       rci_f0=raw_output/raw_ref if abs(raw_ref) > 1e-6 else "",
                       output_monotonic=int(measured["F0_COMPRESSED"] < measured["ORIGINAL"] < measured["F0_EXPANDED"]),
                       output_expanded_minus_original_st=measured["F0_EXPANDED"]-measured["ORIGINAL"],
                       output_original_minus_compressed_st=measured["ORIGINAL"]-measured["F0_COMPRESSED"],
                       output_median_expanded_minus_compressed_hz=float(three["F0_EXPANDED"]["clone"]["f0_median_hz"])-
                                                               float(three["F0_COMPRESSED"]["clone"]["f0_median_hz"]),
                       output_f0_contour_expanded_compressed_rmse_st=contour_rmse(
                           three["F0_EXPANDED"]["clone"]["f0_contour_centered_st"],
                           three["F0_COMPRESSED"]["clone"]["f0_contour_centered_st"], 20),
                       output_energy_contour_expanded_compressed_rmse_db=contour_rmse(
                           three["F0_EXPANDED"]["clone"]["energy_contour_relative_db"],
                           three["F0_COMPRESSED"]["clone"]["energy_contour_relative_db"], 40),
                       output_duration_expanded_minus_compressed_s=float(three["F0_EXPANDED"]["clone"]["duration_s"])-
                                                                   float(three["F0_COMPRESSED"]["clone"]["duration_s"]))
            if (target_id, "F0_EXPANDED") in identity and (target_id, "F0_COMPRESSED") in identity:
                rec["ecapa_cosine_expanded_minus_compressed"] = (
                    float(identity[(target_id, "F0_EXPANDED")]["ecapa_cosine"]) -
                    float(identity[(target_id, "F0_COMPRESSED")]["ecapa_cosine"]))
        output.append(rec)
    write(HERE / "f0_controllability_results.csv", output)
    print(json.dumps({"targets": len(output), "pass": sum(r["technical_status"] == "PASS" for r in output),
                      "fail": sum(r["technical_status"] == "FAIL" for r in output)}, indent=2))


if __name__ == "__main__":
    main()
