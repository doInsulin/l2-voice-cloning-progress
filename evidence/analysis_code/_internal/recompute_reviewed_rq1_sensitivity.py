"""Recalculate frozen RQ1 sensitivity specifications from reviewed static NDS."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/final_confirmatory_experiment"
REVISED = PACKAGE / "rq1_reviewed_20261120"

spec = importlib.util.spec_from_file_location("rq1_reviewed_sensitivity", FROZEN / "analyze_final_sensitivity.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main() -> None:
    output = REVISED / "sensitivity_results.csv"
    if output.exists():
        raise RuntimeError(f"Output exists: {output}")
    with tempfile.TemporaryDirectory(prefix="rq1_sensitivity_", dir=PACKAGE / "_internal") as tmp:
        folder = Path(tmp)
        if not folder.resolve().is_relative_to((PACKAGE / "_internal").resolve()):
            raise RuntimeError("Temporary cleanup escaped workspace")
        for name in ("preservation_normalized_long.csv", "preservation_model_trait_summary.csv"):
            shutil.copy2(REVISED / name, folder / name)
        shutil.copy2(FROZEN / "natural_variability_scales.csv", folder / "natural_variability_scales.csv")
        (folder / "features").mkdir()
        for model in ("f5_tts", "cosyvoice2", "openvoice_v2"):
            name = f"{model}_preservation_global.jsonl"
            shutil.copy2(FROZEN / "features" / name, folder / "features" / name)
        prior = module.HERE
        try:
            module.HERE = folder
            module.main()
        finally:
            module.HERE = prior
        shutil.copy2(folder / "sensitivity_results.csv", output)


if __name__ == "__main__":
    main()
