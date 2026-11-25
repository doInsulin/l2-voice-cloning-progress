# Final Confirmatory Experiment：speaker traits 的自然保留与 reference 可控性

本报告仅解释已冻结的三模型 preservation benchmark、F5-TTS 两项 reference intervention，以及两个预定元音对比。数值来自本目录的逐条 CSV/JSONL；`final_confirmatory_summary.json` 是交付 gate。这里的“identity”指独立 ECAPA-TDNN 输出表征，不等于人工判断的说话人身份；相关性与声学响应也不证明模型内部如何编码。

## 设计、隔离和分析单位

本地 L2-ARCTIC 的 16 位 speaker 全部进入最终样本。固定 seed 为 `20260923`。A target、B reference、C held-out original baseline 的源 utterance 互斥，三模型 preservation 使用相同的 160 条 target 文本（每位 speaker 10 条）和相同的 speaker reference。C 有 1280 条 original utterance（每人 80 条），只用于估计说话人自然变异，不使用 clone 结果。冻结清单及哈希见 `final_design_freeze.json`、`generation_design_freeze.json`；输入分区的两项生成前文本/配对 seed 技术修订另有独立审计文件。

F5-TTS、CosyVoice 2、OpenVoice V2 均使用本地锁定的权重与推理环境，分别生成 160/160 条且无生成失败。ASR 与 MFA 对全部各 160 条完成；严格全局 QC 的 PASS 为 F5 157/160、CosyVoice 159/160、OpenVoice 160/160。三模型各有 160 行原始与 clone 的结果，不因失败行改变分母。声学主指标的三模型共同支持分别为 identity 156 条/16 人、segmental 144 条/16 人、rhythm 156 条/16 人、prosody 110 条/15 人。所有原始指标与 QC 原因保留在 `preservation_raw_long.csv`、`preservation_normalized_long.csv`、`preservation_sample_qc.csv`。

Preservation 的统一单位是 **Normalized Distortion Score (NDS)**：scalar 为 original–clone 绝对差除以 C 中该 speaker 的 `1.4826×MAD`；MAD 不可估时按生成前写定规则使用 SD 或 pooled fallback。轮廓和 ECAPA 使用 C 中同 speaker original–original 距离基准。NDS 越小，越接近 held-out original 的自然变异范围。各 family 的一个预定展示主指标分别是 ECAPA cosine distance、目标句四元音 F1/F2 的 tokenwise 标准化距离中位数、平均词间 gap、中心化 F0 轮廓 RMSE。这些主指标不代表 family 的全部构成，也不应合成“最佳模型”总分。C 中 224 个 scalar 尺度有 8 个不可估，26 个采用 speaker SD；相应指标缺测保留，不填造数值。局部 boundary 的 32 个尺度全部可估，但 28 个需要预先规定的 SD fallback，故其 NDS 幅度须看敏感性。

## 三模型自然保留：共同支持

下表为 speaker 等权平均 NDS；括号是 speaker cluster bootstrap 95% 区间。跨 family 仅用于描述本表选定指标，不能解释为统一心理量尺。

| Model | Identity：ECAPA | Segmental：vowel F1/F2 | Rhythm：word gap | Prosody：F0 contour |
|---|---:|---:|---:|---:|
| F5-TTS | 1.185 [1.093, 1.293] | 0.873 [0.804, 0.948] | 1.349 [1.167, 1.528] | 1.031 [0.930, 1.129] |
| CosyVoice 2 | 1.082 [1.017, 1.150] | 0.866 [0.763, 0.973] | 2.957 [1.972, 4.084] | 1.063 [0.960, 1.166] |
| OpenVoice V2 | 2.630 [2.494, 2.781] | 1.350 [1.066, 1.675] | 1.255 [1.066, 1.443] | 0.874 [0.778, 0.965] |

原始尺度也需并读。在共同支持上，speaker 等权的 ECAPA cosine distance 为 F5 0.392、CosyVoice 0.358、OpenVoice 0.853（相应 cosine 约 0.608、0.642、0.147）；元音 F1/F2 中位绝对 log 差为 0.101、0.099、0.150；平均词间 gap 的绝对差为 0.032、0.046、0.031 秒；F0 轮廓 RMSE 为 3.779、3.875、3.167 semitones。OpenVoice 的独立 ECAPA 身份代理明显低于另外两模型，也显著低于早期用 OpenVoice 自身 tone-color encoder 得到的印象；这是**表征与新样本条件下的分歧**，不能说人工一定无法辨认 OpenVoice 的说话人。

在这些预定指标上，F5/CosyVoice 的元音空间偏移相对自然尺度较小，CosyVoice 的词间 gap 失真最大；OpenVoice 的 ECAPA 失真最大而 F0 轮廓失真较低。因此没有一个模型在所有 trait 都占优。三模型的差异也与架构有关联，但输出行为不允许反推内部 conditioning 表征。配套 `mixed_effects_results.csv` 在 101 个全指标共同 target、15 位 speaker、1212 行上使用 `log1p(NDS)`，模型×trait 固定效应与 speaker/target 交叉随机截距；相对 F5 的条件 Wald 区间显示：CosyVoice 的 rhythm 为 +0.390 [0.295, 0.485]，OpenVoice 的 identity 为 +0.548 [0.453, 0.643]、segmental 为 +0.130 [0.035, 0.225]。其余所列模型差异较小或区间跨零。Wald 区间未包含方差分量不确定性，speaker-cluster 汇总应作为主要泛化依据。

ECAPA 身份 NDS 与 behavioral NDS 的 speaker-level Spearman 相关在三模型×三 family 共 9 个比较中均较弱或不稳定，ρ 介于 −0.10 与 +0.33，全部 speaker bootstrap 区间跨零（每格 15–16 人）。高 speaker embedding 相似度不能保证元音、停顿或 F0 的同等保留；当前证据支持**输出层面的选择性保留/解耦**，不支持宣称这几类 trait 在模型内部统计独立。

## F5 reference-F0 controllability

对 16 位 speaker 各固定 6 个 target，共 96 组。每人同一 enrollment reference 的 F0 log range 乘以预先验证的 0.65、1.00、1.35；三条件保持文本、reference 时长、RMS、目标文本、checkpoint、推理参数和 seed。48 个 reference 操纵通过预生成声学与 identity QC。288/288 生成成功，ASR/MFA 全部执行；严格全局 QC 为 286/288，**95/96** 个三条件 target 完整，失败组留在分母中。

展开减压缩的 reference F0 range 中位变化为 4.127 semitones；生成变化中位 2.532、均值 2.941 semitones。95 组中 91 组按 compressed→original→expanded 严格单调；16 位 speaker 的平均响应全部为正。按 speaker 等权的 **RCI_F0 = 0.727 [0.662, 0.794]**，同目标三点斜率为 0.726 [0.664, 0.792]；各 speaker RCI 约 0.52–0.98。F0 median 平均只增加约 1.82 Hz，符合主要操纵 range 而非中心音高。两端 ECAPA cosine 对 original–clone 相似度的均值差 +0.014、合并均值约 0.58–0.60，说明没有观察到大幅身份代理崩塌，但这种相似度仍不能替代听感验证。

这在扩大到 16 位 speaker 后复现了 F5 对 reference F0 range 的传递。F5 自然 preservation 的 F0 轮廓 NDS 仍约 1.03；故自然重现精度和可通过刻意操纵来控制的程度不是同一性质。

## 等总帧 timing intervention 与 RCI

采用预先优先的 **Plan A**：12 位 speaker 各有两处可靠自然内部 silence；调整 primary pause 并在另一处补偿，使三条件的原始及 F5 预处理 reference 总 frames 完全相同。非停顿 speech PCM 未改，reference F0、RMS、文本、seed 和生成设置通过技术检查。另 4 位 speaker 因无合格双停顿或 WAV QC 未进入 timing intervention，并未制造停顿或替换 speaker。12 人各固定 6 个 target，共 72 组三条件、216/216 条成功；ASR/MFA/全局 QC 全部 PASS，72/72 组可分析。

reference primary pause 展开减压缩的中位差为 0.270 秒。speaker 等权 **local word-gap RCI = 0.211 [0.039, 0.422]**；直接 acoustic-pause RCI = **0.067 [0.014, 0.128]**；target 减非 target gap RCI = 0.213 [0.041, 0.423]。同目标三点局部 gap 斜率 0.211 [0.038, 0.424]。对 12 位共同 speaker，RCI_F0−RCI_local_gap = **0.543 [0.359, 0.707]**。两端生成总时长差的中位数和均值均为零，只用作 duration-budget 控制核验，不用作 timing 传递的核心证据。ECAPA 两端平均差 +0.002。

局部 timing 的响应远不如 F0 稳定：72 组只有 28 组 local gap 展开减压缩为正、4 组严格三点单调；直接 acoustic pause 有 **56/72 组变化为零**，正变化仅 13 组，严格单调也仅 4 组。多数 speaker 的 acoustic-pause RCI 为零或近零，局部 gap 的正均值由部分 speaker/target 驱动。词边界 gap 还受 MFA 边界划分影响，不能与检测到的声学静音等同。最稳妥的表述是：**在等帧、局部双停顿设计下，reference timing 控制弱且高度异质；不能据此说模型没有 timing representation。**

## Segmental confirmatory 与既有边界证据

没有新增 phonetic contrast。F5 对预定 IH→IY 的 106 个 matched error/control pairs、EH→AE 的 50 pairs 各生成两条（合计 312/312），沿用固定 speaker-specific vowel axis、Praat/formant 与原 QC，不看结果挑样本。由于 original formant、clone track、时长或目标音素技术失败，完整对数为 **IH 56/106（14 人）**、**EH 39/50（11 人）**。projection 在生成前校正为“正数＝向该 contrast 的 canonical endpoint”，修订与源标注 phone parser 的实现修正分别记录在 `pre_analysis_axis_direction_correction.json` 和 `pre_analysis_source_phone_parser_correction.json`；旧方向符号不能直接与本次数值对读。

| Contrast | Speaker 等权 matched DID ΔP | 95% speaker bootstrap CI | 有效 pairs / speaker | ≥4 pairs/speaker 敏感性 |
|---|---:|---:|---:|---:|
| IH→IY | +0.511 | [−0.320, 1.358] | 56 / 14 | +0.105 [−1.002, 1.232]，45 对/9 人 |
| EH→AE | +0.798 | [0.167, 1.597] | 39 / 11 | +0.591 [0.343, 0.839]，30 对/4 人 |

EH→AE 的正向效应较一致（11 人中 10 人点估计为正），并伴随 ΔlogF1 DID −0.151 [−0.298, −0.014]、ΔlogF2 +0.123 [0.023, 0.242]；vowel duration DID −0.054 [−0.297, 0.192] 无确定方向。IH→IY 的 speaker 异质性明显（14 人中 9 人正向），ΔP 与单独 F1/F2/duration 的总体区间均跨零；不能把旧样本上的明显 IH finding 直接推广成 16 人稳定效应。IH 完整对损失主要含 41 次 original formant invalid、13 次 clone track unstable 等重叠原因；EH 主要含 9 次 track unstable、7 次 original formant invalid。失败按冻结技术阈值处理，没有按效应方向排除。

既有 IY→IH 28 对/8 人和 rhoticity 42 对/6 人的区间跨零，仍作为 boundary/null evidence；本 Goal 未扩大这两类样本。既有 reference-density 实验的 44 个共同完整 pairs、8 位 speaker 中，ERROR_RICH−PHONE_FREE 的 error ΔP 为 +0.282 [−0.146, 0.749]，4 人正/4 人负。该操纵不同于 F0/timing，故仅作为辅助证据，**不计算可比 RCI**。

## 敏感性与解释范围

共同支持改为各模型全部有效支持，12 个 model×family 单元的 speaker 等权 NDS 最大变化约 0.047；改为 sample-weighted 最大约 0.042；把可测的 QC 失败行仅作敏感性观察，最大约 0.023，不把它们重新纳入主分析。MAD 与 speaker SD 标准化会显著改变某些数值幅度，例如 word-gap NDS 从 F5 1.349/Cosy 2.957/OpenVoice 1.255 变为约 0.753/1.350/0.739；Cosy 的该指标仍最高，但“约 3 个自然尺度”的量化措辞依赖预定尺度。raw 与 NDS 的 model×speaker rank 相关依次约 identity 0.92、segmental 0.76、rhythm 0.14、prosody 0.39；尤其 rhythm 的绝对比较对单位和个体自然尺度敏感。全部敏感性行见 `sensitivity_results.csv`。

本实验支持在论文中**区分 preservation 与 controllability**：F5 的 F0 自然轮廓不是无偏复制，却能被 reference range 稳定推动；等帧后局部 timing 的主动传递远弱于 F0。Segmental canonicalization 主要在 EH→AE 显示较稳健方向，IH→IY 扩展样本异质且区间跨零，不能宣称一切发音习惯都被 canonical text 统一纠正。未来论文写作可讨论这一选择性模式，但不能凭输出相关和操纵响应直接证明模型内部 speaker/timbre/prosody 表征的解耦机制。

## 论文结论边界

1. **Thesis-ready findings：** 16 人三模型的 trait profile 与自然尺度表明保留呈维度选择性；F5 reference F0 range 的正向传递在 95 个完整 target、16 人复现；等帧实验中 F0 RCI 明显大于局部 timing RCI；EH→AE 的 matched DID 向 canonical EH 的声学方向为正。
2. **Findings requiring cautious wording：** ECAPA 是独立 ASV proxy 而非人工 identity 真值；OpenVoice 的 ECAPA 与其自身 tone-color encoder 不一致；Cosy word-gap NDS 的幅度受 MAD/SD 影响；mixed model 的 Wald 区间与 101-target 全指标支持不能替代 speaker 层泛化；EH 有若干每人仅 1–3 对。
3. **Null / boundary findings：** IH→IY 本次扩展 DID 区间跨零；既有 IY→IH、rhoticity、reference-density 结果不排除零；多数等帧 timing target 的直接声学停顿未发生改变，不能据此推论完全无 timing 编码。
4. **Remaining limitations：** 只有 16 位 L2-ARCTIC speaker，timing 仅 12 位；ASR/MFA、F0 tracking、formant 与静音检测会产生条件相关测量误差；NDS 的跨 family 可比性受不同距离构造约束；缺少新的人耳 identity/timing 感知验证。本实验阶段到此停止，不自动新增音素、模型、操纵或人工任务。
