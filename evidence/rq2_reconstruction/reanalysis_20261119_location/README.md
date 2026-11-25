# Post hoc manual-boundary reanalysis of RQ2

Input: `F:\MSC毕业\manual_formant_audit\boundary_review.CSV` (SHA-256 `52aac95aaf6d8270e1fbc2fc638aaa03b908773a5211b98b02f4c76294f8b716`). The user reports completing visual location review for all 380 vowels in the 95 frozen QC-valid matched pairs. Only changed boundary values were entered. A blank `reviewed_start_s` or `reviewed_end_s` retains the original time for that side; the effective midpoint is the average of the two effective endpoints. The original CSV, WAV, TextGrid, pair identifiers, and frozen research outputs were not edited.

## Processing

- 116 intervals changed (EH→AE 54, IH→IY 62); 264 were unchanged. For changed intervals, F1/F2 were measured on the existing source WAV at the reviewed midpoint with Parselmouth/Praat Burg: time step 0.005 s, five formants, frozen speaker-specific ceiling, window 0.025 s, and pre-emphasis 50 Hz. Unchanged F1/F2 values were reused exactly from the frozen feature ledger. No audio generation or MFA alignment was run.
- The frozen speaker-specific log-F1/log-F2 acoustic axis was used. For each original or clone vowel, its scalar position `P` is the projection along that axis. In each error/control pair, `DID = (P_clone,error − P_original,error) − (P_clone,control − P_original,control)`. Pair effects were averaged within speaker, then across speakers equally. The 95% intervals use the original 6,000-draw speaker bootstrap and seed 20260923. The ≥4-pairs/speaker subset uses the original threshold.
- Original formant QC had retained the 95 pairs. Rechecking the corrected intervals produced 21 ceiling-sensitivity diagnostics and two `FORMANT_TRACK_UNSTABLE` diagnostics (A0104, A0118; A0118 has both flags). The location-only midpoint analysis retains all 95 pairs. A separate diagnostic exclusion of the two flagged EH pairs is saved in the sibling `reanalysis_20261119/` directory (EH 37 pairs/10 speakers, +0.792 [0.098, 1.761]). No sample was excluded according to the direction of its effect.
- The signed initial-gap sensitivity reruns the earlier speaker-equal regression with 20,000 speaker-cluster bootstrap draws, seed 20261026. The five-point follow-up reuses frozen trajectories for unchanged boundaries and re-extracts all 116 changed intervals at 20/35/50/65/80% of reviewed duration with the original dynamic QC and speaker-level inference. The static and dynamic 50% measurements agree exactly (maximum absolute difference 0 Hz).

## Results and status

| Contrast | Reviewed midpoint matched change | Original frozen result | Reviewed strict five-point mean |
|---|---:|---:|---:|
| EH→AE | +0.863 [0.196, 1.738], 39/11 | +0.798 [0.167, 1.597], 39/11 | +0.947 [0.385, 1.817], 30/10 |
| IH→IY | +0.627 [−0.323, 1.583], 56/14 | +0.511 [−0.320, 1.358], 56/14 | +0.365 [−0.479, 1.240], 16/9 |

The review occurred after the frozen result was known, so these revised estimates are **post hoc manual-boundary reanalyses**, not a new frozen confirmatory experiment. The original result files remain the archived confirmatory record. This CSV covers the F5 matched EH/IH RQ2 sample only. RQ1 preservation, RQ3 reference interventions, reverse IY→IH, rhoticity, and reference-density analyses use other samples or interventions and were not numerically rerun from this CSV.

## Files

- `unit_measurements.csv`: all effective boundaries, midpoint formants, and original/remeasured provenance.
- `pair_results.csv`, `pair_attrition.csv`, `overall_results.csv`: reviewed matched effects, 95-pair completeness, speaker-equal estimates, and ≥4-pair sensitivity.
- `initial_gap/results.csv`: reviewed starting-position sensitivity; `initial_gap_source/` stores the revised derived token ledger used by the archived analysis code.
- `reconstruction_token_trajectories.csv`, `reconstruction_pair_results.csv`, `reconstruction_overall_results.csv`, and `reconstruction_trajectory_summary.csv`: reviewed five-point analysis.
- `followup_audit.json`: hashes and dynamic support counts.
- `validation.json`: passed source/copy hashes for all 380 WAVs and source TextGrids, exact frozen-value reuse for 264 unchanged vowels, and exact DID parity for 31 unaffected pairs.

Reproduction from `F:\MSC毕业` with the existing Python 3.12 environment and bundled acoustic dependencies: run `manual_formant_audit/recompute_boundary_did.py --review manual_formant_audit/boundary_review.CSV --out <new_output_directory>`, then `manual_formant_audit/run_reviewed_followups.py --out manual_formant_audit/reanalysis_20261119_location` in a clean copy of that output. The latter script deliberately refuses to overwrite existing follow-up results.
