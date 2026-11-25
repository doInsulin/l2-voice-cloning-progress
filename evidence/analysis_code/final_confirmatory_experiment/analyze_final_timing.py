"""Plan A equal-frame local-pause F5 response and timing RCI."""
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
import parselmouth
sys.path.insert(0, str(ROOT / "research/07_auto_qc"))
import f5_tts_auto_qc as q
from extract_natural_baselines import internal_pauses

CONDITIONS = ("PAUSE_COMPRESSED", "ORIGINAL", "PAUSE_EXPANDED")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def one(row: dict, target: dict, mfa_dir: Path, global_rec: dict,
        reference: dict, boundary_scale: dict, identity: dict) -> dict:
    output = {"target_id": row["target_id"], "speaker": row["speaker"], "condition": row["condition"],
              "target_boundary_right_word": target["target_boundary_right_word"],
              "target_boundary_word_index_0based": target["target_boundary_word_index_0based"],
              "reference_primary_pause_s": int(reference["primary_new_frames"])/int(reference["sample_rate"]),
              "reference_compensating_pause_s": int(reference["compensating_new_frames"])/int(reference["sample_rate"]),
              "technical_status": "FAIL", "reasons": ""}
    if global_rec["status"] != "PASS":
        output["reasons"] = "GLOBAL_QC:" + "|".join(global_rec["reasons"])
        return output
    if reference["raw_total_frames_exact"] != "1":
        output["reasons"] = "REFERENCE_TOTAL_FRAMES_DIFFER"
        return output
    grid = mfa_dir / row["speaker"] / f"{row['target_id']}__{row['condition']}.TextGrid"
    try:
        words = q.parse_mfa_textgrid(grid)
        index = int(target["target_boundary_word_index_0based"])
        if not 1 <= index < len(words):
            raise ValueError("Target boundary index outside clone words")
        right = words[index]
        if q.normalize_words(right["label"]) != q.normalize_words(target["target_boundary_right_word"]):
            raise ValueError("MFA target right word differs from frozen target")
        left = words[index - 1]
        gaps = [max(0.0, words[j]["start"] - words[j-1]["end"]) for j in range(1, len(words))]
        target_gap = gaps[index-1]
        other_gaps = [g for j, g in enumerate(gaps) if j != index-1]
        snd = parselmouth.Sound(row["output_wav"])
        audio = snd.values.mean(axis=0)
        silence = internal_pauses(audio, int(snd.sampling_frequency))
        local_pause = sum(max(0.0, min(b, right["start"]) - max(a, left["end"])) for a, b in silence)
        other_median = float(np.median(other_gaps)) if other_gaps else 0.0
        pause_vector = [int(g >= .08) for g in gaps]
        output.update(technical_status="PASS", left_word=left["label"], right_word=right["label"],
                      target_boundary_gap_s=target_gap, target_boundary_acoustic_pause_s=local_pause,
                      target_boundary_pause_present_80ms=int(local_pause >= .08),
                      target_minus_non_target_gap_s=target_gap-other_median,
                      non_target_gap_median_s=other_median,
                      non_target_gap_mean_s=float(np.mean(other_gaps)) if other_gaps else 0.0,
                      pause_placement_vector=json.dumps(pause_vector),
                      all_gap_total_s=float(sum(gaps)),
                      reference_primary_pause_natural_units=output["reference_primary_pause_s"]/
                                                            boundary_scale[(row["speaker"], "local_word_gap_s")],
                      output_gap_natural_units=target_gap/boundary_scale[(row["speaker"], "local_word_gap_s")],
                      output_acoustic_pause_natural_units=local_pause/
                          boundary_scale[(row["speaker"], "local_acoustic_pause_s")],
                      f0_range_st=global_rec["clone"]["f0_range_st"],
                      energy_range_db=global_rec["clone"]["energy_range_db"],
                      articulation_rate_wps=global_rec["clone"]["articulation_rate_wps"],
                      pause_fraction=global_rec["clone"]["pause_fraction"],
                      total_utterance_duration_s=global_rec["clone"]["duration_s"])
        key = (row["target_id"], row["condition"])
        if key in identity and identity[key]["ecapa_cosine"]:
            output["ecapa_cosine_original_clone"] = float(identity[key]["ecapa_cosine"])
    except Exception as exc:
        output["reasons"] = f"{type(exc).__name__}: {exc}"
    return output


def main() -> None:
    phase = "f5_tts_timing"
    generation = read(HERE / "generation_execution" / f"{phase}.csv")
    if len(generation) != 216 or any(r["status"] == "PENDING" for r in generation):
        raise RuntimeError("Timing generation denominator incomplete")
    global_rows = records(HERE / "features" / f"{phase}_global.jsonl")
    if len(global_rows) != len(generation):
        raise RuntimeError("Timing global features incomplete")
    global_by_key = {(r["target_id"], r["condition"]): r for r in global_rows}
    targets = {r["target_id"]: r for r in read(HERE / "timing_target_manifest.csv")}
    refs = {(r["speaker"], r["condition"]): r for r in read(HERE / "timing_reference_manipulation_manifest.csv")}
    scales = {(r["speaker"], r["metric"]): float(r["selected_scale"])
              for r in read(HERE / "natural_boundary_scales.csv") if r["selected_scale"]}
    identity_path = HERE / "features/final_ecapa_similarities.csv"
    identity = {(r["target_id"], r["condition"]): r for r in read(identity_path)
                if r["model"] == "f5_tts" and r["phase"] == "timing"} if identity_path.exists() else {}
    if len(scales) != 32:
        raise RuntimeError("Natural boundary scale missing")
    mfa = json.loads((HERE / "mfa" / f"{phase}_report.json").read_text(encoding="utf-8"))
    if mfa["status"] != "PASS":
        raise RuntimeError("Timing MFA incomplete")
    aligned = [one(row, targets[row["target_id"]], Path(mfa["output_dir"]),
                   global_by_key[(row["target_id"], row["condition"])],
                   refs[(row["speaker"], row["condition"])], scales, identity) for row in generation]
    write(HERE / "timing_local_features.csv", aligned)
    by = defaultdict(dict)
    for row in aligned:
        by[(row["speaker"], row["target_id"])][row["condition"]] = row
    if len(by) != 72:
        raise RuntimeError("Expected 72 timing targets")
    results = []
    for (speaker, target_id), three in sorted(by.items()):
        rec = {"speaker": speaker, "target_id": target_id,
               "technical_status": "FAIL", "reasons": ""}
        if set(three) != set(CONDITIONS):
            rec["reasons"] = "MISSING_CONDITION"
        elif any(three[c]["technical_status"] != "PASS" for c in CONDITIONS):
            rec["reasons"] = "|".join(f"{c}:{three[c]['reasons']}" for c in CONDITIONS
                                      if three[c]["technical_status"] != "PASS")
        else:
            compressed, original, expanded = (three[c] for c in CONDITIONS)
            d_ref = expanded["reference_primary_pause_s"] - compressed["reference_primary_pause_s"]
            d_gap = expanded["target_boundary_gap_s"] - compressed["target_boundary_gap_s"]
            d_pause = expanded["target_boundary_acoustic_pause_s"] - compressed["target_boundary_acoustic_pause_s"]
            d_specific = (expanded["target_minus_non_target_gap_s"]-
                          compressed["target_minus_non_target_gap_s"])
            gap_scale = scales[(speaker, "local_word_gap_s")]
            pause_scale = scales[(speaker, "local_acoustic_pause_s")]
            rec.update(technical_status="PASS", reference_change_s=d_ref,
                       output_target_gap_change_s=d_gap,
                       output_acoustic_pause_change_s=d_pause,
                       reference_change_gap_natural_units=d_ref/gap_scale,
                       output_gap_change_natural_units=d_gap/gap_scale,
                       reference_change_pause_natural_units=d_ref/pause_scale,
                       output_pause_change_natural_units=d_pause/pause_scale,
                       rci_local_gap=d_gap/d_ref if abs(d_ref) > 1e-6 else "",
                       rci_local_acoustic_pause=d_pause/d_ref if abs(d_ref) > 1e-6 else "",
                       rci_target_minus_nontarget_gap=d_specific/d_ref if abs(d_ref) > 1e-6 else "",
                       local_gap_monotonic=int(compressed["target_boundary_gap_s"] < original["target_boundary_gap_s"] < expanded["target_boundary_gap_s"]),
                       local_pause_monotonic=int(compressed["target_boundary_acoustic_pause_s"] < original["target_boundary_acoustic_pause_s"] < expanded["target_boundary_acoustic_pause_s"]),
                       target_minus_nontarget_gap_change_s=d_specific,
                       target_pause_placement_compressed=compressed["target_boundary_pause_present_80ms"],
                       target_pause_placement_original=original["target_boundary_pause_present_80ms"],
                       target_pause_placement_expanded=expanded["target_boundary_pause_present_80ms"],
                       f0_range_change_st=expanded["f0_range_st"]-compressed["f0_range_st"],
                       energy_range_change_db=expanded["energy_range_db"]-compressed["energy_range_db"],
                       articulation_rate_change_wps=expanded["articulation_rate_wps"]-
                                                     compressed["articulation_rate_wps"],
                       pause_fraction_change=expanded["pause_fraction"]-compressed["pause_fraction"],
                       total_utterance_duration_change_s=expanded["total_utterance_duration_s"]-
                                                         compressed["total_utterance_duration_s"])
            if "ecapa_cosine_original_clone" in compressed and "ecapa_cosine_original_clone" in expanded:
                rec["ecapa_cosine_expanded_minus_compressed"] = (
                    expanded["ecapa_cosine_original_clone"]-compressed["ecapa_cosine_original_clone"])
        results.append(rec)
    write(HERE / "timing_controllability_results.csv", results)
    print(json.dumps({"conditions": len(aligned), "targets": len(results),
                      "pass": sum(r["technical_status"] == "PASS" for r in results),
                      "fail": sum(r["technical_status"] == "FAIL" for r in results)}, indent=2))


if __name__ == "__main__":
    main()
