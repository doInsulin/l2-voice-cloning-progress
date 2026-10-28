# October 2026 lab meeting: result provenance

Open [`../../docs/lab_meeting_progress_2026_10.html`](../../docs/lab_meeting_progress_2026_10.html) after downloading it. The Chinese HTML is self-contained: all 28 original experiment PNGs are embedded as data URIs, so the page does not depend on relative image loading. The separate byte-for-byte PNG copies in `figures/source/` remain independently downloadable. The report is a meeting presentation about experimental work, not a thesis draft.

## Research sequence and evidential status

| Stage | Question and design | Result files | Status |
| --- | --- | --- | --- |
| Early feasibility | Can three systems generate paired L2 speaker outputs with usable QC? | Original local `research/13_multimodel_analysis/multimodel_acoustic_benchmark_report_20260918.md` | Superseded for preservation counts and inference. Early common support 36/80, below its prespecified gate. |
| Natural preservation | How do ECAPA identity distance, vowel F1/F2, MFA word gaps, and F0 contour compare with same-speaker held-out natural variability? | `source_results/preservation_model_trait_summary.csv`, `preservation_sample_qc.csv` | Frozen final confirmation; each trait has its own common support and NDS scale. |
| Matched segmental reconstruction | Do error vowels move toward a canonical acoustic endpoint more than correct controls? | `source_results/segmental_confirmatory_results.csv` | Frozen final EH→AE positive; IH→IY final interval crosses zero. Earlier IY→IH/rhoticity are exploratory boundaries. |
| Expert audibility | Do selected acoustic changes have an audible counterpart? | `source_results/expert_audibility_results.json` | Supporting, informed, 18-item descriptive task; not blind phoneme classification. |
| F0 intervention | Does an imposed reference voiced-F0 range change pass to the clone for fixed target text? | `source_results/reference_controllability_summary.csv`, `f0_controllability_results.csv` | Frozen final confirmation, 95 complete triplets / 16 speakers. |
| Equal-frame timing intervention | Does redistributing local reference timing, while keeping reference frame count constant, change the cloned local boundary? | `source_results/reference_controllability_summary.csv`, `timing_controllability_results.csv` | Frozen final confirmation, 72 triplets / 12 eligible speakers. |
| External Qwen check | Does F0 versus local timing response recur under audio+text or speaker-vector input? | `source_results/qwen_f0_summary.json`, `qwen_timing_summary.csv` | Independent October extension; not pooled into the final F5 estimate. |
| Local vowel intervention | Does manipulating a reference vowel formant trajectory cause output trajectory change? | `source_results/vowel_transfer_overall_results.csv`, `f5_ih_overall_results.csv`, `qwen_eh_overall_results.csv`, `qwen_ih_overall_results.csv`, `qwen_factorial_contrasts.csv` | Exploratory October 2×2 extension. Its slope is a different estimand from matched canonical-axis DID. |
| Later sensitivity | Is the midpoint EH result consistent with five-point trajectory analysis; how detector-dependent is timing? | `source_results/dynamic_reconstruction_overall_results.csv`, `timing_reaudit_summary.md` | Exploratory reanalysis. Does not replace frozen main estimates. |
| Blind listening | Are the 2×2 local vowel shifts perceptible to listeners? | `source_results/perceptual_materials_report.md` | Materials prepared and checked; no human responses, no effect estimate. |

The original result files are copied byte-for-byte into `source_results/`; `source_results/SHA256SUMS.csv` records the package snapshot hashes. They are small final tables and reports, not raw audio. The local experiment code and larger manifests remain in the original `F:/MSC毕业/research/` workspace. The report builder operates entirely on the packaged snapshots; it does not require that local workspace.

## Rebuild

From the project root, run:

```sh
python reports/lab_meeting_2026_10/build_report.py
```

This standard-library script regenerates `experiment_summary.csv`, `experiment_summary.json`, `confirmatory_results.csv`, `model_qc_summary.csv`, seven supplementary SVGs, `figure_registry.csv`, and the Chinese `docs/lab_meeting_progress_2026_10.html`. `render_chinese_report.py` assembles the report from the packaged source PNGs and verified result tables. The SVGs are generated directly from the named packaged result files but are not substituted for the 28 original experimental figures. No external fonts, scripts, chart servers, or network requests are used.

`experiment_summary.csv` and `.json` contain the same 35 records and required fields: experiment, trait, model, speakers, n, metric, estimate, CI bounds, interpretation, status, and source file. Here `n` means targets, matched pairs, or speakers according to the metric; read `interpretation` and `speakers` with it. `confirmatory_results.csv` contains the frozen F5 intervention and segmental rows, including the IH boundary. `model_qc_summary.csv` derives generation and QC denominators from final gate and sample-QC files.

## Figure provenance

`figure_registry.csv` lists all 28 original PNGs, their original `research/` paths, SHA-256 hashes, Chinese titles, reading guides, and claim boundaries. Ten are displayed at full width in the main scientific story; the other 18 are displayed in the final figure atlas. All 28 appear in the HTML and can also be downloaded individually from `figures/source/`. They are unchanged copies of completed experiment figures. The original axes remain in English for provenance; the surrounding report text and figure explanations are in Chinese.

The seven supplementary SVGs below are still generated for optional reuse. The Chinese report uses the original experiment PNGs for its evidence narrative.

| Figure | Script | Source snapshots | Scientific question |
| --- | --- | --- | --- |
| `figures/qc_and_support.svg` | `build_report.py` | final summary, preservation sample QC | How much valid final data remains after QC? |
| `figures/trait_profile.svg` | `build_report.py` | preservation model-trait summary | Are natural distortions trait-dependent? |
| `figures/segmental_did.svg` | `build_report.py` | final segmental results | Which vowel directions have supported canonical-axis movement? |
| `figures/f0_response.svg` | `build_report.py` | final F0 target triplets, RCI summary | How strongly does output F0 range respond to reference change? |
| `figures/rci_contrast.svg` | `build_report.py` | final RCI summary | Is equal-frame local timing response smaller than F0 response? |
| `figures/local_vowel_transfer.svg` | `build_report.py` | four local-vowel overall tables | Does local vowel controllability depend on the tested model and contrast? |
| `figures/selective_preservation.svg` | `build_report.py` | synthesis of the preceding verified results | How do the measured output patterns fit together? |

The Chinese figure captions state the metric, sample where relevant, how to read the plot, and a scientific boundary. The original PNGs preserve the source analysis color schemes; their estimates and uncertainty come from the named frozen analyses. The seven supplementary SVGs use grayscale plus teal and ochre.

## Version reconciliation and claim limits

1. **Early vs final three-model QC.** The early 8-speaker feasibility run reported F5/Cosy/OpenVoice QC PASS 140/134/133 of 160 and own paired counts 60/57/54 of 80, with only 36/80 three-model common pairs. The later frozen confirmatory design reports generation success 160/160 for each and global QC PASS **157/159/160**; metric-specific common supports are 156 identity, 144 vowel, 156 word gap, and 110 F0-contour targets (15 speakers for F0). The report uses the later final design because the earlier common-support gate failed and the final sample/target design superseded it.
2. **EH→AE versions.** The older 31-pair / 6-speaker DID +0.897 [0.455, 1.369] is superseded by the frozen final 39-pair / 11-speaker +0.798 [0.167, 1.597]. The October five-point +0.898 [0.450, 1.503] is a different strict-QC reanalysis on 35 pairs, not a new primary DID.
3. **IH→IY versions.** An earlier 8-speaker result used a different sign convention and was stronger. The expanded frozen final 56-pair / 14-speaker +0.511 [−0.320, 1.358] controls the main conclusion; its interval crosses zero.
4. **Timing detector versions.** The frozen F5 low-energy detector yields acoustic-pause RCI 0.067 and 56/72 zero end contrasts. The October threshold re-audit finds −35 dBFS RCI 0.287 [0.128, 0.462] and 10/72 zero contrasts. These are different operational definitions. The report retains the frozen result as primary and flags detector sensitivity; it does not equate either with a manually verified linguistic pause. The MFA word-gap RCI 0.211 was reproduced in the re-audit.
5. **Duration-changing pause pilots.** The early global/local pause studies changed reference length, which also changed F5's frame budget. Their total-duration effects cannot establish learned rhythm transfer. The equal-frame timing experiment is primary.
6. **Natural preservation vs active control.** NDS is a natural-original to clone distortion divided by a same-speaker natural scale; lower is less distortion within each family. RCI is output expanded-minus-compressed response divided by reference change under an intervention. Matched DID is error-minus-control canonical-axis displacement. These quantities are not interchangeable or a common model score.
7. **Identity and perceptual bounds.** ECAPA is an automated speaker-verification proxy, not human identity truth. The informed expert task is limited and predates the final EH sample. The October blind listening materials have no responses. Acoustic movement cannot be called perceptual correction.
8. **Mechanism.** “Reference cues plus target text and model prior” is a plausible interpretive model, not an experimentally identified internal computation. Report claims stay at the level of measured outputs.

The later Qwen external replication and local-vowel studies add independent, exploratory breadth. They do not overwrite the September final confirmatory estimates; the 2×2 local-vowel evidence also limits the simple claim that all segmental deviations are reconstructed rather than transferred.
