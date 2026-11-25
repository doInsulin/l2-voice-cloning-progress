"""Recalculate existing RQ1 dynamic-vowel preservation with 41 reviewed C intervals.

Reuses frozen A original/clone trajectories. Writes only to the reviewed RQ1
version directory. Checks that an isolated old-input run reproduces frozen
dynamic outputs before applying the reviewed boundaries.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/27_dynamic_vowel_analysis"
FINAL = ROOT / "research/final_confirmatory_experiment"
OUT = PACKAGE / "rq1_reviewed_20261120/dynamic"

sys.path[:0] = [str(FROZEN), str(ROOT / "research/02_acoustic_validation"),
                str(ROOT / "research/.acoustic_deps")]
import parselmouth  # noqa: E402
from ih_iy_acoustic_extract import formant_values, get_formant  # noqa: E402
import analyze_dynamic_vowels as analysis  # noqa: E402


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_in(folder: Path) -> None:
    prior = analysis.HERE
    try:
        analysis.HERE = folder
        analysis.main()
    finally:
        analysis.HERE = prior


def valid(x: float) -> bool:
    return math.isfinite(x) and x > 0


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"Dynamic reviewed output already exists: {OUT}")
    changed = read(PACKAGE / "changed_only_20261119/changed_rows.csv")
    if len(changed) != 41 or any(r["scope"] != "same_word" for r in changed):
        raise RuntimeError("Expected 41 reviewed same-word intervals")
    old_audit = json.loads((FROZEN / "dynamic_vowel_extraction_audit.json").read_text(encoding="utf-8"))
    if sha(FROZEN / "dynamic_vowel_tokens.csv") != old_audit["output_sha256"]["dynamic_vowel_tokens.csv"] or \
       sha(FROZEN / "natural_dynamic_vowels.csv") != old_audit["output_sha256"]["natural_dynamic_vowels.csv"]:
        raise RuntimeError("Frozen dynamic inputs have drifted")
    # Temp path is created by tempfile within the workspace root, and is never
    # a user or frozen directory. TemporaryDirectory resolves and checks it.
    with tempfile.TemporaryDirectory(prefix="rq1_dyn_parity_", dir=PACKAGE / "_internal") as temp_name:
        temp = Path(temp_name)
        if not temp.resolve().is_relative_to((PACKAGE / "_internal").resolve()):
            raise RuntimeError("Temporary cleanup target escaped the workspace")
        for name in ("dynamic_vowel_tokens.csv", "natural_dynamic_vowels.csv",
                     "dynamic_vowel_extraction_audit.json"):
            shutil.copy2(FROZEN / name, temp / name)
        run_in(temp)
        frozen_result_audit = json.loads((FROZEN / "dynamic_vowel_analysis_audit.json").read_text(encoding="utf-8"))
        parity = {name: sha(temp / name) == digest for name, digest in frozen_result_audit["outputs"].items()}
        if not all(parity.values()):
            raise RuntimeError(f"Could not reproduce frozen dynamic outputs: {parity}")
    original = read(FROZEN / "natural_dynamic_vowels.csv")
    revised = [dict(r) for r in original]
    baseline = {r["token_id"]: r for r in read(PACKAGE / "rq1_reviewed_20261120/natural_vowel_tokens.csv")}
    by_token = {r["token_id"]: r for r in changed}
    cache = {}
    patched = set()
    for row in revised:
        c = by_token.get(row["token_id"])
        if c is None:
            continue
        b = baseline[row["token_id"]]
        if row["speaker"] != c["speaker"] or row["phone"] != c["phone"] or \
           abs(float(b["phone_onset_s"]) - float(c["new_start_s"])) > 1e-9 or \
           abs(float(b["phone_offset_s"]) - float(c["new_end_s"])) > 1e-9:
            raise RuntimeError(f"Boundary mismatch: {row['token_id']}")
        wav = row["original_wav"]
        ceiling = int(row["formant_ceiling_hz"])
        if (wav, ceiling) not in cache:
            sound = parselmouth.Sound(wav)
            cache[(wav, ceiling)] = get_formant(sound, ceiling)
        formant = cache[(wav, ceiling)]
        interval = {"phone_onset": c["new_start_s"], "phone_offset": c["new_end_s"]}
        values = formant_values(formant, interval)
        f1 = [values[f"f1_{p}"] if valid(values[f"f1_{p}"]) else None for p in (20, 35, 50, 65, 80)]
        f2 = [values[f"f2_{p}"] if valid(values[f"f2_{p}"]) else None for p in (20, 35, 50, 65, 80)]
        if abs(f1[2] - float(c["new_f1_hz"])) > 1e-6 or abs(f2[2] - float(c["new_f2_hz"])) > 1e-6:
            raise RuntimeError(f"New dynamic midpoint does not match reviewed static: {row['token_id']}")
        duration = float(c["new_end_s"]) - float(c["new_start_s"])
        reasons = []
        if b["status"] == "exclude_technical":
            reasons.append("FROZEN_NATURAL_MIDPOINT_EXCLUSION")
        if any(x is None for x in f1 + f2):
            reasons.append("MISSING_TRAJECTORY_FORMANT")
        if f1[2] is not None and f2[2] is not None and not \
           (150 <= f1[2] <= 1300 and 500 <= f2[2] <= 4000 and f2[2] > f1[2] + 150):
            reasons.append("FORMANT_IMPLAUSIBLE")
        for sequence, limit in ((f1, 350), (f2, 700)):
            for left, right in zip(sequence[:-1], sequence[1:]):
                if left is not None and right is not None and \
                   (abs(left - right) > limit or max(left, right) / min(left, right) > 1.7):
                    reasons.append("FORMANT_TRACK_UNSTABLE")
        if not 0.04 <= duration <= 0.40:
            reasons.append("PHONE_DURATION_IMPLAUSIBLE")
        strict = [*reasons]
        if not 0.06 <= duration <= 0.35:
            strict.append("DYNAMIC_DURATION_OUT_OF_RANGE")
        row.update(duration_s=duration, f1_hz=json.dumps(f1), f2_hz=json.dumps(f2),
                   log_f1=json.dumps([math.log(x) if x else None for x in f1]),
                   log_f2=json.dumps([math.log(x) if x else None for x in f2]),
                   track_qc_pass=int(not reasons), track_qc_reasons="|".join(sorted(set(reasons))),
                   strict_dynamic_qc_pass=int(not strict),
                   strict_dynamic_qc_reasons="|".join(sorted(set(strict))),
                   frozen_status=b["status"], frozen_flags=b["flags"])
        patched.add(row["token_id"])
    if patched != by_token.keys() or len(revised) != len(original):
        raise RuntimeError("Dynamic baseline patch count mismatch")
    OUT.mkdir()
    shutil.copy2(FROZEN / "dynamic_vowel_tokens.csv", OUT / "dynamic_vowel_tokens.csv")
    write(OUT / "natural_dynamic_vowels.csv", revised)
    new_audit = dict(old_audit)
    new_audit["status"] = "REVIEWED_C_BASELINE_REEXTRACTION"
    new_audit["output_sha256"] = {"dynamic_vowel_tokens.csv": sha(OUT / "dynamic_vowel_tokens.csv"),
                                  "natural_dynamic_vowels.csv": sha(OUT / "natural_dynamic_vowels.csv")}
    new_audit["reviewed_boundary_changes"] = len(patched)
    (OUT / "dynamic_vowel_extraction_audit.json").write_text(
        json.dumps(new_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_in(OUT)
    audit = {"frozen_reproduction_exact": parity,
             "changed_natural_dynamic_tokens": len(patched),
             "new_natural_dynamic_sha256": sha(OUT / "natural_dynamic_vowels.csv"),
             "dynamic_token_input_unchanged": True,
             "no_new_synthesis_or_alignment": True}
    (OUT / "reviewed_dynamic_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
