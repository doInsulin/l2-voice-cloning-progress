# Dynamic vowel incremental validation

Run ID: `DVIV-20261030-01`. Existing-data follow-up to local `research/27_dynamic_vowel_analysis` and `research/33_dynamic_vowel_trajectory_20261022`. No audio, weights, cache, or thesis manuscript is stored here.

Read in order: [Phase 0 audit](phase0_existing_data_audit.md), [frozen protocol](experiment_protocol.md), [literature comparison](literature_comparison.md), [final report](final_experiment_report.md), [decision](decision_gate.md). Tables: `incremental_value_results.csv`, `classification_results.csv`, `dimension_matched_negative_control.csv`, `time_resolved_did_results.csv`, `speaker_specific_preservation.csv`, `qc_attrition_tokens.csv`, `sensitivity_results.csv`, `analysis_summary.json`. Eight academic figures are in `figures/`.

Reproduce from the original local workspace (the large frozen source tables are not copied to Git):

```powershell
$env:PYTHONPATH='F:/MSC毕业/research/.acoustic_deps'
& 'C:/Users/12727/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' experiments/dynamic_vowel_incremental_validation/scripts/run.py
```

The exact local source hashes are in `analysis_summary.json` and `run_manifest.json`. The script reads frozen CSV/JSON only. It does not synthesize audio, rerun alignment, or modify frozen evidence.
