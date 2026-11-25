"""Check provenance and numeric parity for the reviewed RQ2 reanalysis."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT / "research/final_confirmatory_experiment"
OUT = HERE / "reanalysis_20261119_location"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


review = rows(HERE / "boundary_review.CSV")
index = rows(HERE / "restricted/sample_index.csv")
units = rows(OUT / "unit_measurements.csv")
pairs = rows(OUT / "pair_results.csv")
attrition = rows(OUT / "pair_attrition.csv")
assert len(review) == len(index) == len(units) == 380
assert len(pairs) == len(attrition) == 95
assert all(r["included"] == "YES" for r in attrition)
assert len({r["audit_id"] for r in review}) == 380
u = {r["audit_id"]: r for r in units}
assert Counter(x["measurement_source"] == "FROZEN" for x in units) == {True: 264, False: 116}

for key in index:
    aid = key["audit_id"]
    assert sha(Path(key["source_wav"])) == key["source_wav_sha256"], aid
    assert sha(HERE / "praat" / (aid + ".wav")) == key["copied_wav_sha256"], aid
    assert sha(Path(key["source_textgrid"])) == key["source_textgrid_sha256"], aid
    assert float(u[aid]["reviewed_end_s"]) > float(u[aid]["reviewed_start_s"]), aid

frozen = {r["target_id"]: r for r in (json.loads(line) for line in
          (FROZEN / "features/f5_tts_segmental_tokens.jsonl")
          .read_text(encoding="utf-8").splitlines() if line.strip())}
for key in index:
    current = u[key["audit_id"]]
    if current["measurement_source"] != "FROZEN":
        continue
    auto = frozen[key["target_id"]]["original_formants" if key["condition"] == "ORIGINAL" else "clone_formants"]
    assert float(current["f1_hz"]) == float(auto["midpoint_f1_hz"])
    assert float(current["f2_hz"]) == float(auto["midpoint_f2_hz"])

changed_pairs = {r["pair_id"] for r in units if r["measurement_source"] != "FROZEN"}
old_pairs = {(r["pair_id"], r["feature"]): float(r["estimate"]) for r in
             rows(FROZEN / "segmental_confirmatory_results.csv") if r["level"] == "pair"}
untouched = [r for r in pairs if r["pair_id"] not in changed_pairs]
max_parity = max(abs(float(r["did_delta_p"]) - old_pairs[r["pair_id"], "did_delta_p"])
                 for r in untouched)
assert max_parity < 1e-10, max_parity

old_dynamic = {r["pair_id"]: r for r in
               rows(ROOT / "research/33_dynamic_vowel_trajectory_20261022/reconstruction_pair_results.csv")}
new_dynamic = {r["pair_id"]: r for r in rows(OUT / "reconstruction_pair_results.csv")}
dynamic_parity = 0.0
for pair in untouched:
    pair_id = pair["pair_id"]
    for field in ("translation_p", "early_late_p", "curvature_p"):
        old, new = old_dynamic[pair_id][field], new_dynamic[pair_id][field]
        if old and new:
            dynamic_parity = max(dynamic_parity, abs(float(old) - float(new)))
        else:
            assert old == new, (pair_id, field)
assert dynamic_parity < 1e-10, dynamic_parity

gap_results = rows(OUT / "initial_gap/results.csv")
mid_results = rows(OUT / "overall_results.csv")
for contrast in ("EH_TO_AE", "IH_TO_IY"):
    gap = next(r for r in gap_results if r["contrast"] == contrast and
               r["analysis"] == "unadjusted_speaker_equal_matched_change")
    mid = next(r for r in mid_results if r["contrast"] == contrast and
               r["feature"] == "did_delta_p" and r["level"] == "overall_speaker_equal")
    assert abs(float(gap["estimate"]) - float(mid["estimate"])) < 1e-12

summary = {"status": "PASS", "input_review_sha256": sha(HERE / "boundary_review.CSV"),
           "all_source_wav_and_textgrid_hashes_match": True,
           "all_380_copied_wav_hashes_match": True,
           "unchanged_midpoint_measurements_equal_frozen": 264,
           "changed_intervals": 116,
           "included_pairs": 95,
           "unaffected_pairs_matching_frozen": len(untouched),
           "unaffected_pair_max_abs_did_difference": max_parity,
           "unaffected_pair_max_abs_dynamic_difference": dynamic_parity,
           "initial_gap_unadjusted_estimates_match_midpoint": True,
           "formant_track_unstable_units": [r["audit_id"] for r in units if
                                              "FORMANT_TRACK_UNSTABLE" in r["formant_note"]]}
(OUT / "validation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
