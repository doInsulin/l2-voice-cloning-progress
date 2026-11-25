# Figure provenance audit

`F:\MSC毕业\research\` remains read-only and is the source-of-record. The files under `thesis_manuscript/figures/` are publication-working copies only. Every number in a caption or interpretation must still be checked against the listed frozen result file before final typesetting.

| Manuscript figure | Working file | Frozen figure or design source | Numeric source-of-record | Audit status |
|---|---|---|---|---|
| Fig. 1 | `figures/fig01_study_estimand_framework.svg` | Manuscript diagram based on `thesis_blueprint.md` and `final_design_freeze.json` | `final_confirmatory_experiment/final_design_freeze.json`; analysis-specific freezes listed in `source_registry.md` | No new result; design counts only |
| Fig. 2 | `figures/fig02_reviewed_selective_preservation_profile.png` | Reviewed RQ1 matrix rendered from the frozen plotting specification | `manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/preservation_model_trait_summary.csv` | Post hoc C-baseline revision; frozen figure retained separately |
| Fig. 3 | `figures/fig03_reviewed_dynamic_vowel_preservation.png` | Reviewed RQ1 dynamic reanalysis plot | `manual_formant_audit/RQ1_元音复核/rq1_reviewed_20261120/dynamic/dynamic_overall_results.csv`; `dynamic_vowel_coverage.csv` | Post hoc C-baseline revision; frozen figure retained separately |
| Fig. 4 | `figures/fig04_reviewed_canonical_reconstruction.png` | `manual_formant_audit/make_reviewed_figure.py` | `manual_formant_audit/reanalysis_20261119_location/pair_results.csv`; `overall_results.csv` | Post hoc boundary-reviewed result; original `fig04_canonical_reconstruction.png` retained |
| Fig. 5 | `figures/fig05_f0_reference_response.png` | `research/final_confirmatory_experiment/figures/f0_reference_response.png` | `research/final_confirmatory_experiment/f0_controllability_results.csv`; `reference_controllability_summary.csv` | Frozen result figure copied unchanged |
| Fig. 6 | `figures/fig06_equal_frame_timing_response.png` | `research/final_confirmatory_experiment/figures/timing_reference_response.png` | `research/final_confirmatory_experiment/timing_controllability_results.csv`; `timing_local_features.csv` | Frozen result figure copied unchanged; caption repairs the cross-text interpretation |
| Fig. 7 | `figures/fig07_localized_vowel_2x2.png` | `research/31_qwen_eh_vowel_replication/figures/four_cell_transfer.png` | `research/28_localized_vowel_reference_intervention/vowel_transfer_overall_results.csv`; `research/29_qwen3_ih_vowel_replication/overall_results.csv`; `research/30_f5_ih_vowel_replication/overall_results.csv`; `research/31_qwen_eh_vowel_replication/overall_results.csv`; `factorial_contrasts.csv` | Frozen synthesis figure copied unchanged |
| Fig. 8 | `figures/fig08_final_synthesis_matrix.svg` | Manuscript synthesis from verified Fig. 5–7 results | The frozen files listed for Fig. 5–7 plus `research/qwen3_external_replication_20261003/thesis_ready_results_summary.md` | No new analysis; categorical synthesis only |

## Appendix figure copies

| Appendix figure | Working file | Frozen source | Use boundary |
|---|---|---|---|
| Fig. A1 | `appendix/figA1_selective_transfer_numeric_comparison.png` | `research/28_localized_vowel_reference_intervention/figures/selective_transfer_summary.png` | Numeric comparison only; not a universal feature hierarchy |
| Fig. A2 | `appendix/figA2_timing_measurement_spectrogram_example.png` | `research/timing_structure_followup_20261003/measurement_check/spectrogram_sample_01.png` | Illustrates detector sensitivity; not a primary timing outcome |

## Claim checks applied

- ECAPA is labelled as an independent identity proxy, never a human identity judgement.
- NDS panels remain metric-specific and are not averaged into an overall score.
- Figure 4 is acoustic reconstruction under canonical-text synthesis, not pronunciation correction.
- Figure 6 concerns a predefined local timing proxy in the target utterance and assumes no one-to-one reference/target boundary correspondence.
- Figure 7 uses “differed across the tested systems” or “model-associated,” not a pure model effect.
- Figure 8 reports magnitude, consistency, and generalizability separately and does not encode a feature-capability ranking.
