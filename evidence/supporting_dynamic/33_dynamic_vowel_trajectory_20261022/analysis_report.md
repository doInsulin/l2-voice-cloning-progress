# Dynamic vowel trajectory follow-up — independent analysis report

**状态（2026-10-22）：** 完成前两步的冻结数据复分析、自动轨迹 QC、speaker-level bootstrap 和预定敏感性检查。没有修改论文正文、既有冻结结果或模型；没有生成新音频。第三步的生成门槛未达到。

## 数据充分性与设计

1. **Trajectory geometry。** `../27_dynamic_vowel_analysis/dynamic_vowel_tokens.csv` 已有三模型 20/35/50/65/80% log F1/F2 和严格 QC；`natural_dynamic_vowels.csv` 提供 held-out 同人同元音自然基线。采用既有三模型共通 strict support（214 个 matched token）；要求每人四个元音齐备的汇总涉及 199 token、14 speakers。每条元音轨迹是一个二维五点对象。五个预定属性分别为五点中心、20→80% 位移向量、四段总路径长度、50% 相对端点连线的弯曲向量、以及前后路径长度不对称。表中误差先用同人同元音不同 utterance 的自然原音配对中位数归一化，再作 speaker 等权估计和 8,000 次 speaker bootstrap。**这些 NDS 是声学差异与自然跨 utterance 差异之比，不是感知保留分数；同词同语境的原音–合成音比较也不与跨 utterance 自然配对完全同分布。**
2. **Dynamic canonical reconstruction。** 最终 F5 冻结 matched error/control 有 EH→AE 39 对、IH→IY 56 对通过既有 pair QC。利用保留的 WAV、phone interval、Praat Burg 参数和 speaker ceiling 重提取五点轨迹；未重跑 MFA 或生成。全部 190 个 token 的 50% F1/F2 与冻结 midpoint **完全一致（最大绝对差 0 Hz）**。新主分析再要求每对四条轨迹（error/control × original/clone）全部通过 strict dynamic QC；整对剔除。每对的二维五点 DID 为 `(clone_error − original_error) − (clone_control − original_control)`。将其分为五点平均的整体位移和均值中心化的动态残差。speaker 是推断单位；五点不是五个独立因变量。规范方向使用原有 held-out 同人元音轴。形状使用 speaker 符号翻转的五点二维整体检验；五点均值表的区间半径是整个轨迹的 simultaneous bootstrap band。

设计、源文件 SHA-256 和预定敏感性检查见 [design_freeze.json](design_freeze.json)。代码为 [analyze.py](analyze.py)，输入与输出哈希见 [analysis_audit.json](analysis_audit.json)。

## Step 1 — 整体轨迹几何

主 support 的 speaker 等权、四元音等权结果如下。数值为原音–合成音属性差异 / 同人同元音自然原音配对差异的中位数；方括号为 95% speaker bootstrap 区间。

| 模型 | 中心位置 | onset→offset 方向向量 | 路径长度 | 曲率向量 | 前后不对称 |
|---|---:|---:|---:|---:|---:|
| F5-TTS | 0.937 [0.857, 1.018] | 0.677 [0.586, 0.770] | 1.134 [0.882, 1.440] | 0.892 [0.758, 1.019] | 0.954 [0.853, 1.066] |
| CosyVoice 2 | 0.953 [0.861, 1.048] | 0.748 [0.657, 0.843] | 1.037 [0.874, 1.224] | 0.990 [0.844, 1.131] | 0.980 [0.846, 1.113] |
| OpenVoice V2 | 1.333 [1.141, 1.531] | 0.818 [0.707, 0.934] | 1.088 [0.905, 1.280] | 1.111 [0.919, 1.359] | 0.982 [0.875, 1.090] |

方向向量差异在三个系统均低于相应自然跨 utterance 标尺，说明 midpoint 单点遗漏了一类可测的输出轨迹关系；但路径长度、曲率、时间不对称并无同样一致的低差异。不能由这些比值推出模型编码了元音动态，也不能将三个系统排名为“动态元音更好”。模型专属 strict support（F5 395、CosyVoice 390、OpenVoice 290 个四元音齐备 token；16/16/15 speakers）与三模型共通 track support（422 token、16 speakers）的方向向量比值分别为 0.721/0.817/0.866 与 0.726/0.763/0.880；整体图景未依赖主 support 的 214-token 限制。全部五个预定指标、各元音及 speaker 的结果见 [geometry_overall_results.csv](geometry_overall_results.csv)、[geometry_speaker_results.csv](geometry_speaker_results.csv)。

## Step 2 — 完整五点 matched reconstruction

| 对比与 support | 动态 QC 配对 / speakers | 五点平均规范轴 DID | 65–80% 减 20–35% DID | 二维 shape 整体检验 |
|---|---:|---:|---:|---:|
| EH→AE，strict | 35 / 11 | +0.898 [0.450, 1.503] | +0.305 [−0.081, 0.744] | RMS 0.0263 log，sign-flip p=.419 |
| EH→AE，track sensitivity | 39 / 11 | +0.902 [0.450, 1.515] | +0.305 [−0.081, 0.730] | RMS 0.0258，p=.426 |
| IH→IY，strict | 18 / 9 | +0.512 [−0.091, 1.143] | −0.026 [−0.506, 0.566] | RMS 0.0245，p=.281 |
| IH→IY，track sensitivity | 49 / 14 | +0.553 [−0.171, 1.413] | −0.394 [−1.278, 0.279] | RMS 0.0149，p=.917 |

EH→AE 的五点平均移动与冻结 midpoint 主结果的正方向相容；它的晚段高于早段的点估计不稳，二维形状整体检验也没有确立形状改变。35 对中 ≥4 对/speaker 的 26 对、4 人敏感性结果为 +0.646 [0.395, 0.898]，early–late +0.039 [−0.307, 0.326]，shape p=.627。因此当前证据**与整体平移相容，但不足以断言严格的刚性平移，亦未证实局部阶段变化**。主 support 的 EH 五点规范方向均值为 0.729、0.818、0.787、0.960、1.196；这些是同一条估计轨迹，不能按五个独立显著性检验解释。

IH→IY 的新增 strict QC 将原有 56 对缩为 18 对，主要由短/长元音时长门槛引起；其 9 人中无人达到 ≥4 对，所以该敏感性无法在 strict support 中估计。track support 保留 49 对、14 人，但 ≥4 对/speaker 子集只有 26 对、5 人，五点平均 +1.469 [0.331, 3.126]，区间宽且对筛选敏感。**仍以冻结最终 midpoint 56 对/14 人 +0.511 [−0.320, 1.358] 为论文主证据**，不得用这里较小 support 的结果替换。EH→AE 冻结 midpoint 39 对/11 人 +0.798 [0.167, 1.597] 同样不被本复分析替换。

技术 QC：EH 39 对中 strict 35、track 39；IH 56 对中 strict 18、track 49。新增失败原因集中在 duration：190 个原有 PASS token 中，严格时长范围标记出现 75 次，宽松轨迹时长范围标记 8 次（同一 token 的多标记可重叠）。声学中点重现为 0 Hz 差异。逐对轨迹、speaker 汇总、完整五点函数及 simultaneous band 见 [reconstruction_pair_results.csv](reconstruction_pair_results.csv)、[reconstruction_speaker_results.csv](reconstruction_speaker_results.csv)、[reconstruction_trajectory_summary.csv](reconstruction_trajectory_summary.csv)。

## Step 3 gate 与 thesis 纳入判断

**不启动 midpoint-fixed reference 生成。** 前两步说明动态方向可被测量，但 matched reconstruction 未形成稳定的阶段/形状效应；IH 尤其受严格动态 QC 的配对流失限制。现有观测仍不能识别主动 reference trajectory transfer，但目前没有足够明确的动态重建信号去支撑昂贵的新生成干预。若未来另有独立证据跨过该门槛，才冻结 ORIGINAL / EARLY-shift / LATE-shift 的具体操作与声学校验，再固定 target text、seed、duration、F0、midpoint、总采样点数及整体 formant center 测试输出。

**当前不值得写入主论文结论。** 可以把本目录作为探索性附录或后续工作依据；即便引用，也仅描述输出声学轨迹与技术限制。它不证明感知类别修正、内部表征或主动 reference transfer。原有 thesis claim boundaries、证据 registry 和正文保持不变。
