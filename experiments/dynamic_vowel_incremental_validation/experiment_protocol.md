# Incremental VISC validation protocol — frozen before new analysis

Run ID `DVIV-20261030-01`; seed `20261030`. Source: frozen assets named in `phase0_existing_data_audit.md`. No audio generation, new alignment, or QC revisions. Each vowel is a correlated 2×5 log-formant object; speaker is the independent generalization unit. This protocol was written before examining this run's outcomes.

## A. Incremental value

Primary descriptive contrast: on the identical 214-token three-model common strict support, compute midpoint difference `D50` and residual off-midpoint difference `R(t)=D(t)-D50`, with `D(t)=clone(t)-original(t)`. Summarize `sqrt(mean(R²))`, midpoint RMSE and full-trajectory RMSE at token then speaker/equal-vowel level. The residual is additional *measured acoustic variation* conditional on midpoint, but no R² or predictive gain is claimed: a distance constructed from extra points is intrinsically nonzero and cannot validate itself. Compare residual with held-out same-speaker natural-original residual on the same normalization. A sensitivity uses common track QC. The previous full/shape/geometry NDS is context, not new evidence.

Secondary independent-label test: predict vowel category from clone acoustics on the same 214 tokens, four balanced classes, leave-one-speaker-out. Feature sets S1 midpoint 2D, S2 centered trajectory 10D, S3 midpoint+centered 12D, S4 full trajectory 10D. Fixed shrinkage LDA (no hyperparameter search); train-fold-only z-scoring; each held-out speaker's tokens completely unseen. Report macro-F1, balanced accuracy, paired speaker-level S3−S1 with bootstrap CI, speaker metrics and confusion. A gain in category decoding is not automatically a gain in identifying cloning distortion. Dimension-matched negative control: S1 plus ten deterministic train/test independent Gaussian features with identical normalization and model, repeated 100 times; compare gain distribution. Stop classification if any training fold lacks a class or fewer than 8 speakers have all four vowels.

## B. Time-resolved DID

Use existing `research/33.../reconstruction_pair_results.csv` and token trajectories, fixed strict QC, frozen axes. For each EH→AE and IH→IY speaker, average five-point canonical DID over matched pairs. Estimate overall trajectory and scalar contrasts with 8,000 speaker bootstrap draws. Primary additional-shape contrast: five-point DID after removing each speaker's five-point mean, tested as an omnibus multivariate speaker sign-flip norm. Planned early-versus-late `(P65+P80−P20−P35)/2` is secondary. Output 20/35/50/65/80%, five-point mean, P50, and simultaneous whole-curve uncertainty band. Track QC and ≥4 pairs/speaker are sensitivity supports. Existing mean DID is inherited; no pointwise significance fishing.

## C. Speaker-specific dynamics

F5 strict QC only. Match each clone target to its own original and to a different-speaker original with *exact same utterance ID, word index, phone index and vowel*. Among candidates choose smallest absolute log-duration ratio; deterministic speaker-ID tie-break. Require cross-original duration within 25% of own original. Compare mean-centered 2×5 log-formant shape distance; cross-minus-own paired difference is primary. Also compare midpoint-position distance to assess whether shape adds beyond static speaker separation. Same speaker equal weighting and 8,000 speaker bootstrap. Sensitivity: no duration cap, per-vowel results, leave-one-speaker-out. These are observational same-text comparisons; stress realization and voice-specific acoustics remain possible confounds. If exact-context support is too small (<8 speakers or <80 tokens), stop inferential C and report descriptively.

## Decision

GO requires a robust, noncircular dynamic increment (B shape or C controlled shape, with QC/speaker sensitivity), not simply extra feature dimensionality. LIMITED GO for descriptive extension only. NO GO if all dynamic increments fail or are too unstable. Do not automatically generate new reference audio. Preserve original confirmatory midpoint claims and manuscript.

## Post-run amendment (2026-10-30; explicitly exploratory)

After inspecting the first run, a Bark-transformed version of A's midpoint-anchored residual was added to satisfy the requested normalization check. It was **not** part of the frozen primary gate and cannot upgrade the decision. The predeclared ≥4-pairs/speaker B sensitivity was also implemented in the results table after the first run; its rule itself was frozen above and in the inherited 2026-10-22 design.
