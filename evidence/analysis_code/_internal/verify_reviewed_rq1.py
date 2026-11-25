"""Final integrity check for the reviewed RQ1 version and manuscript pointers."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
REVISED = PACKAGE / "rq1_reviewed_20261120"
FROZEN = ROOT / "research/final_confirmatory_experiment"
MANUSCRIPT = ROOT / "thesis_manuscript"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    audit = json.loads((REVISED / "audit.json").read_text(encoding="utf-8"))
    baseline_old = read(FROZEN / "natural_vowel_tokens.csv")
    baseline_new = read(REVISED / "natural_vowel_tokens.csv")
    changed = [a["token_id"] for a, b in zip(baseline_old, baseline_new) if a != b]
    assert len(baseline_old) == len(baseline_new) == 5729 and len(changed) == 41
    assert [r for r in baseline_old if r["token_id"] == "YKWK|arctic_a0006|9"] == [
        r for r in baseline_new if r["token_id"] == "YKWK|arctic_a0006|9"]
    for name, digest in audit["input_sha256"].items():
        source = PACKAGE / name if name in ("review.csv", "changed_rows.csv") else FROZEN / name
        if name == "changed_rows.csv":
            source = PACKAGE / "changed_only_20261119/changed_rows.csv"
        assert sha(source) == digest, (name, "input hash drift")
    dyn_audit = json.loads((REVISED / "dynamic/reviewed_dynamic_audit.json").read_text(encoding="utf-8"))
    geo_audit = json.loads((REVISED / "geometry/audit.json").read_text(encoding="utf-8"))
    assert all(dyn_audit["frozen_reproduction_exact"].values())
    assert all(geo_audit["frozen_reproduction_exact"].values())
    assert sha(REVISED / "dynamic/dynamic_vowel_tokens.csv") == sha(
        ROOT / "research/27_dynamic_vowel_analysis/dynamic_vowel_tokens.csv")
    assert len(read(REVISED / "preservation_normalized_long.csv")) == 11351
    assert len(read(REVISED / "preservation_model_trait_summary.csv")) == 24
    assert len(read(REVISED / "identity_behavior_association.csv")) == 9
    assert len(read(REVISED / "sensitivity_results.csv")) == 46
    source_registry = (MANUSCRIPT / "source_registry.md").read_text(encoding="utf-8")
    assert "rq1_reviewed_20261120" in source_registry
    for chapter in ("chapters/04_results_zh.md", "chapters/04_results_en.md", "full_thesis_draft.md"):
        text = (MANUSCRIPT / chapter).read_text(encoding="utf-8")
        assert "0.872 [0.803, 0.947]" in text
        assert "0.867 [0.801, 0.940]" in text
        assert "fig02_reviewed_selective_preservation_profile.png" in text
        assert "fig03_reviewed_dynamic_vowel_preservation.png" in text
    assert (MANUSCRIPT / "figures/fig02_reviewed_selective_preservation_profile.png").is_file()
    assert (MANUSCRIPT / "figures/fig03_reviewed_dynamic_vowel_preservation.png").is_file()
    rq2_audit = json.loads((ROOT / "manual_formant_audit/reanalysis_20261119_location/followup_audit.json").read_text(encoding="utf-8"))
    assert sha(ROOT / "manual_formant_audit/boundary_review.CSV") == rq2_audit["boundary_review_sha256"]
    result = {"status": "PASS", "frozen_c_rows": 5729, "changed_c_rows": len(changed),
              "B1926_original_retained": True, "frozen_inputs_match_recorded_hashes": True,
              "dynamic_frozen_parity": True, "geometry_frozen_parity": True,
              "thesis_current_tables_and_figures_checked": True,
              "rq2_review_input_unchanged": True,
              "current_output_sha256": {str(p.relative_to(REVISED)).replace("\\", "/"): sha(p)
                                        for p in sorted(REVISED.rglob("*")) if p.is_file() and p.name != "verification.json"}}
    (REVISED / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "current_output_sha256"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
