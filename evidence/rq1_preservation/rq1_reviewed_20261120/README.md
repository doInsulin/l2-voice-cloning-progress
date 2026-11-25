# RQ1 人工边界修订版（2026-11-20）

本目录是论文当前 RQ1 元音相关数值的来源。原始冻结文件仍在 `F:\MSC毕业\research\final_confirmatory_experiment\`、`research\27_dynamic_vowel_analysis\` 和 `research\33_dynamic_vowel_trajectory_20261022\`，均未覆盖。

- C 组原声基线：`natural_vowel_tokens.csv` 共 5,729 行；自动标为 `review` 的 2,054 行中，人工实际更改 41 行边界。B1926 经用户决定保留原值。修订边界来自 `..\review.csv`，新中点的 F1/F2 由相同 WAV、speaker ceiling 和原 Burg 参数重提。
- 静态 RQ1：`natural_vowel_scales.csv`、`preservation_normalized_long.csv`、`preservation_model_trait_summary.csv`、`preservation_speaker_trait_summary.csv`。`model_delta.csv` 给出冻结与修订版前后差异。三模型的原声及克隆测量、技术 QC、target support 不变。
- 动态 RQ1：`dynamic\` 重提 41 条 C 组原声的 20/35/50/65/80% 轨迹，并复用冻结的三模型原声/克隆轨迹；`geometry\` 更新相关自然尺度与支持性几何 NDS。
- 下游统计：`identity_behavior_association.csv`、`mixed_effects_results.csv`、`sensitivity_results.csv` 已从修订版数据重新计算。
- 校验：`audit.json`、`dynamic\reviewed_dynamic_audit.json`、`geometry\audit.json`。修订前的冻结静态分数及置信区间、动态和几何输出均先被精确复现。

这是一项**事后人工边界测量修订**，没有重新生成克隆或运行 MFA，也没有改变 RQ2 的冻结声学轴和已审核的 matched DID。论文当前 RQ2 五点结果来自另一目录：`F:\MSC毕业\manual_formant_audit\reanalysis_20261119_location\`。
