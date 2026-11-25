# Thesis experiment evidence

This repository contains the **current, paper-facing experiment snapshot** for *L2 English Speech Traits in Zero-Shot Voice Cloning*. It replaces the October 2026 lab-meeting package and the earlier incremental dynamic-vowel validation package. Those older files are not part of the current branch; Git history still records earlier commits.

The original WAV/TextGrid corpus, generated audio, model weights, and the immutable local `research/` source-of-record are **not uploaded**. This repository is a compact review package of design locks, QC, result tables, audit records, and manuscript figures. `evidence/MANIFEST.csv` records every copied file's local source and SHA-256 hash.

## Use in the thesis

| Evidence group | What it supports | Status |
|---|---|---|
| `evidence/analysis_code/` | Selected generation and analysis implementation | Snapshot of the final experiment code; requires the original local inputs and environment to rerun |
| `evidence/design/` | Fixed speakers, targets, references, measurement settings, and final experiment design | Frozen design and source-of-record summary |
| `evidence/rq1_preservation/` | Three-system preservation profile and reviewed vowel/dynamic-trajectory estimates | The manually reviewed C-baseline revision supplies current vowel-related manuscript estimates; frozen QC and natural scales remain provenance |
| `evidence/rq2_reconstruction/` | EH→AE and IH→IY matched acoustic reconstruction | Manual-boundary reanalysis is the current manuscript estimate; frozen confirmatory tables are labeled comparators, not substitutes |
| `evidence/rq3_controllability/` | F0, equal-frame local timing, localized-vowel interventions, and Qwen replication | Frozen primary and explicitly supporting/replication estimates |
| `evidence/supporting_dynamic/` | Five-point trajectory and geometry follow-up | Supporting analysis only; the proposed midpoint-fixed generation was not run |
| `evidence/manual_review/` | Human vowel-boundary corrections | Audited CSVs with local WAV/TextGrid paths omitted |
| `evidence/manuscript_figures/` | Figures used in the current bilingual thesis draft | Working figure copies, with numeric provenance in its `audit/figure_provenance.md` |

Read `evidence/design/final_confirmatory_experiment/final_confirmatory_experiment_report.md` and the audit/README files in each group before interpreting numbers. The dimensions, support counts, and confidence intervals are not interchangeable across experiments. No result here establishes human perceived identity, pronunciation correction, or an internal model mechanism.

## Rebuild and verify

On the original Windows project workspace, run `python build_thesis_evidence.py` from this repository. It reads the local frozen and reviewed files without changing them, refreshes the snapshot, and writes `evidence/MANIFEST.csv`. To verify a snapshot independently, compute each file's SHA-256 and compare it with the manifest. Raw speech and generation are not needed for that integrity check.
