"""Recompute existing RQ1 trajectory-geometry step 1 with reviewed C baseline."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/33_dynamic_vowel_trajectory_20261022"
ORIGINAL_DYN = ROOT / "research/27_dynamic_vowel_analysis"
REVIEWED_DYN = PACKAGE / "rq1_reviewed_20261120/dynamic"
OUT = PACKAGE / "rq1_reviewed_20261120/geometry"

sys.path[:0] = [str(ROOT / "research/.acoustic_deps"), str(ORIGINAL_DYN),
                str(ROOT / "research/07_auto_qc")]
spec = importlib.util.spec_from_file_location("rq1_geometry_frozen_analysis", SOURCE / "analyze.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"Reviewed geometry output exists: {OUT}")
    original_here, original_dyn = module.HERE, module.DYN
    with tempfile.TemporaryDirectory(prefix="rq1_geo_parity_", dir=PACKAGE / "_internal") as temp_name:
        temp = Path(temp_name)
        if not temp.resolve().is_relative_to((PACKAGE / "_internal").resolve()):
            raise RuntimeError("Temporary cleanup target escaped workspace")
        try:
            module.HERE, module.DYN = temp, ORIGINAL_DYN
            frozen_result = module.step1()
        finally:
            module.HERE, module.DYN = original_here, original_dyn
        names = ("geometry_natural_scales.csv", "geometry_token_metrics.csv",
                 "geometry_speaker_results.csv", "geometry_overall_results.csv")
        parity = {name: sha(temp / name) == sha(SOURCE / name) for name in names}
        if not all(parity.values()):
            raise RuntimeError(f"Frozen geometry reproduction failed: {parity}")
    OUT.mkdir()
    try:
        module.HERE, module.DYN = OUT, REVIEWED_DYN
        new_result = module.step1()
    finally:
        module.HERE, module.DYN = original_here, original_dyn
    if new_result["common_strict_tokens"] != frozen_result["common_strict_tokens"] or \
       new_result["common_track_tokens"] != frozen_result["common_track_tokens"]:
        raise RuntimeError("Geometry support changed unexpectedly")
    audit = {"frozen_reproduction_exact": parity,
             "support": new_result,
             "rq1_geometry_only": True,
             "rq2_step2_untouched": True,
             "source_natural_dynamic_sha256": sha(REVIEWED_DYN / "natural_dynamic_vowels.csv"),
             "output_sha256": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()}}
    (OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
