"""Refresh the paper-facing evidence snapshot from the local source-of-record.

Run from this repository; never changes the frozen research workspace.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent
ROOT = REPO.parent
OUT = REPO / "evidence"

SOURCES = {
    "analysis_code": [
        "research/final_confirmatory_experiment/build_preservation_profile.py",
        "research/final_confirmatory_experiment/analyze_final_segmental.py",
        "research/final_confirmatory_experiment/analyze_final_f0.py",
        "research/final_confirmatory_experiment/analyze_final_timing.py",
        "research/final_confirmatory_experiment/analyze_final_sensitivity.py",
        "research/final_confirmatory_experiment/fit_final_mixed_effects.py",
        "research/final_confirmatory_experiment/generate_final_f5.py",
        "research/final_confirmatory_experiment/generate_final_cosyvoice2.py",
        "research/final_confirmatory_experiment/generate_final_openvoice.py",
        "manual_formant_audit/recompute_boundary_did.py",
        "manual_formant_audit/run_reviewed_followups.py",
        "manual_formant_audit/validate_reanalysis.py",
        "manual_formant_audit/RQ1_元音复核/_internal/publish_reviewed_rq1.py",
        "manual_formant_audit/RQ1_元音复核/_internal/recompute_reviewed_rq1_sensitivity.py",
        "manual_formant_audit/RQ1_元音复核/_internal/recompute_reviewed_dynamic_rq1.py",
        "manual_formant_audit/RQ1_元音复核/_internal/recompute_reviewed_geometry_rq1.py",
        "manual_formant_audit/RQ1_元音复核/_internal/verify_reviewed_rq1.py",
        "research/33_dynamic_vowel_trajectory_20261022/analyze.py",
    ],
    "design": [
        "research/final_confirmatory_experiment/final_design_freeze.json",
        "research/final_confirmatory_experiment/generation_design_freeze.json",
        "research/final_confirmatory_experiment/final_speaker_manifest.csv",
        "research/final_confirmatory_experiment/final_target_manifest.csv",
        "research/final_confirmatory_experiment/final_reference_manifest.csv",
        "research/final_confirmatory_experiment/final_baseline_pool_manifest.csv",
        "research/final_confirmatory_experiment/final_formant_ceilings.json",
        "research/final_confirmatory_experiment/final_confirmatory_summary.json",
        "research/final_confirmatory_experiment/final_confirmatory_experiment_report.md",
    ],
    "rq1_preservation": [
        "research/final_confirmatory_experiment/preservation_sample_qc.csv",
        "research/final_confirmatory_experiment/natural_variability_scales.csv",
        "research/final_confirmatory_experiment/natural_contour_scales.csv",
        "research/final_confirmatory_experiment/natural_vowel_axes.json",
        "research/final_confirmatory_experiment/identity_behavior_association.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/README.md",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/audit.json",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/verification.json",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/preservation_model_trait_summary.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/preservation_speaker_trait_summary.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/sensitivity_results.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/mixed_effects_results.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/identity_behavior_association.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/dynamic/dynamic_overall_results.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/dynamic/dynamic_vowel_coverage.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/dynamic/reviewed_dynamic_audit.json",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/geometry/geometry_overall_results.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/geometry/geometry_speaker_results.csv",
        "manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/geometry/audit.json",
    ],
    "rq2_reconstruction": [
        "research/final_confirmatory_experiment/segmental_pair_qc.csv",
        "research/final_confirmatory_experiment/segmental_confirmatory_results.csv",
        "manual_formant_audit/reanalysis_20261119_location/README.md",
        "manual_formant_audit/reanalysis_20261119_location/validation.json",
        "manual_formant_audit/reanalysis_20261119_location/followup_audit.json",
        "manual_formant_audit/reanalysis_20261119_location/unit_measurements.csv",
        "manual_formant_audit/reanalysis_20261119_location/pair_results.csv",
        "manual_formant_audit/reanalysis_20261119_location/overall_results.csv",
        "manual_formant_audit/reanalysis_20261119_location/pair_attrition.csv",
        "manual_formant_audit/reanalysis_20261119_location/reconstruction_overall_results.csv",
        "manual_formant_audit/reanalysis_20261119_location/reconstruction_pair_results.csv",
        "manual_formant_audit/reanalysis_20261119_location/reconstruction_trajectory_summary.csv",
        "manual_formant_audit/reanalysis_20261119_location/initial_gap/results.csv",
    ],
    "rq3_controllability": [
        "research/final_confirmatory_experiment/reference_controllability_audit.json",
        "research/final_confirmatory_experiment/reference_controllability_summary.csv",
        "research/final_confirmatory_experiment/f0_controllability_results.csv",
        "research/final_confirmatory_experiment/timing_controllability_results.csv",
        "research/final_confirmatory_experiment/timing_local_features.csv",
        "research/final_confirmatory_experiment/f0_reference_manipulation_manifest.csv",
        "research/final_confirmatory_experiment/timing_reference_manipulation_manifest.csv",
        "research/28_localized_vowel_reference_intervention/vowel_intervention_design_freeze.json",
        "research/28_localized_vowel_reference_intervention/vowel_transfer_overall_results.csv",
        "research/29_qwen3_ih_vowel_replication/design_freeze.json",
        "research/29_qwen3_ih_vowel_replication/overall_results.csv",
        "research/30_f5_ih_vowel_replication/generation_freeze.json",
        "research/30_f5_ih_vowel_replication/overall_results.csv",
        "research/31_qwen_eh_vowel_replication/design_freeze.json",
        "research/31_qwen_eh_vowel_replication/overall_results.csv",
        "research/31_qwen_eh_vowel_replication/factorial_contrasts.csv",
        "research/qwen3_external_replication_20261003/thesis_ready_results_summary.md",
        "research/qwen3_external_replication_20261003/external_replication_audit.json",
    ],
    "supporting_dynamic": [
        "research/33_dynamic_vowel_trajectory_20261022/design_freeze.json",
        "research/33_dynamic_vowel_trajectory_20261022/analysis_audit.json",
        "research/33_dynamic_vowel_trajectory_20261022/analysis_report.md",
        "research/33_dynamic_vowel_trajectory_20261022/step3_decision.json",
        "research/33_dynamic_vowel_trajectory_20261022/reconstruction_overall_results.csv",
        "research/33_dynamic_vowel_trajectory_20261022/geometry_overall_results.csv",
    ],
    "manuscript_figures": [
        *[f"thesis_manuscript/figures/{name}" for name in (
            "fig01_study_estimand_framework.svg",
            "fig02_reviewed_selective_preservation_profile.png",
            "fig03_reviewed_dynamic_vowel_preservation.png",
            "fig04_reviewed_canonical_reconstruction.png",
            "fig05_f0_reference_response.png",
            "fig06_equal_frame_timing_response.png",
            "fig07_localized_vowel_2x2.png",
            "fig08_final_synthesis_matrix.svg",
        )],
        "thesis_manuscript/appendix/figA1_selective_transfer_numeric_comparison.png",
        "thesis_manuscript/appendix/figA2_timing_measurement_spectrogram_example.png",
        "thesis_manuscript/audit/figure_provenance.md",
    ],
}


def main() -> None:
    rows = []
    for group, paths in SOURCES.items():
        for rel in paths:
            source = ROOT / rel
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = OUT / group / source.parent.name / source.name
            if destination.exists() and destination.read_bytes() != source.read_bytes():
                # Different sources may share a basename inside one group.
                raise ValueError(f"Destination collision: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            rows.append((destination.relative_to(REPO).as_posix(), rel, digest, destination.stat().st_size))
    # Keep the manual corrections while omitting machine-specific WAV/TextGrid paths.
    for label, rel in (
        ("rq1_vowel_boundaries.csv", "manual_formant_audit/RQ1_元音复核/review.csv"),
        ("rq2_vowel_boundaries.csv", "manual_formant_audit/boundary_review.CSV"),
    ):
        source = ROOT / rel
        destination = OUT / "manual_review" / label
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open(newline="", encoding="utf-8-sig") as inp, destination.open("w", newline="", encoding="utf-8") as out:
            reader = csv.DictReader(inp)
            columns = [name for name in reader.fieldnames or [] if name.lower() not in {"wav", "textgrid"}]
            writer = csv.DictWriter(out, fieldnames=columns)
            writer.writeheader()
            for row in reader:
                writer.writerow({name: row[name] for name in columns})
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        rows.append((destination.relative_to(REPO).as_posix(), rel + " (WAV/TextGrid paths omitted)", digest, destination.stat().st_size))
    with (OUT / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("repository_path", "local_source_path", "sha256", "size_bytes"))
        writer.writerows(rows)
    print(f"Copied {len(rows)} files, {sum(r[3] for r in rows):,} bytes")


if __name__ == "__main__":
    main()
