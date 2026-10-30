# Dynamic Vowel Preservation and Reconstruction：增量验证实验报告

Run ID `DVIV-20261030-01`，2026-10-30。所有新分析为 existing-data reanalysis；此前五点 NDS、matched DID 与 thesis 冻结结论保持原样。图表和完整精度数值见本目录 CSV/JSON。

## 1. Research motivation

此前五点轨迹分析已经证明元音内部的声学变化可以测量，也确认 F5 EH→AE 的五点**平均**规范方向位移。新问题是：这些动态信息在控制 midpoint 和相同文本/元音类别之后，是否真正增加了解释能力。更多采样点或更多图表本身不是新增证据。

## 2. Relation to Adem (2026)

[Adem (2026)](https://www.sciencedirect.com/science/article/pii/S0095447025000828) 研究 Arabic-speaking adolescents 的 L2 English vowel production，使用 VISC、VL/TL/FV、角度、fPCA 及动态分类的思路。我们借鉴五点二维时间测量，但研究 zero-shot clone 对**同一原声**的保留及 error/control 配对重建；其分类目标与效应量不能移植。网页索引化 Methods/Results 摘录可见，全文页面及 PDF 未能取得；本报告不采用未核实的数值。方法适配与未照搬项详见 [literature_comparison.md](literature_comparison.md)。

## 3. Existing frozen evidence

三模型共同严格 QC 214 vowel tokens；旧的四元音等权汇总为 199 tokens/14 speakers。旧结果已有完整轨迹、中心、形状、位移向量、路径、曲率等 NDS；方向向量 NDS 较低，其他动态属性并无一致优势。旧五点平均 matched DID：EH→AE +0.898 [0.450, 1.503]，35 对/11 人；IH→IY +0.512 [−0.091, 1.143]，18 对/9 人。冻结 midpoint 主结果分别为 EH +0.798 [0.167, 1.597]（39 对/11 人）和 IH +0.511 [−0.320, 1.358]（56 对/14 人）。以上均是继承证据，不是本轮发现。[Phase 0 audit](phase0_existing_data_audit.md)列明来源与 QC。

## 4. New hypotheses

RQ-D1：若动态增加实质信息，同一 token support 上的 midpoint-plus-dynamic 特征应在独立标签、speaker-disjoint 检验中稳定优于 midpoint；构造出的残差本身不能算预测成功。RQ-D2：若 EH 重建具有时间结构，去除五点平均位移后的配对 DID 应呈稳定的共同形状。RQ-D3：若保留 speaker-specific dynamics，严格相同句子/phone 匹配后，同人 shape 距离应稳定小于异人，并不能仅靠中点位置差异解释。

## 5. Data and QC

使用 frozen five-point log F1/F2、同人自然原声、F5 matched pair 表、held-out-C 规范轴。A 使用同一 214-token × 3-model strict support；类别分布 AE 55、EH 54、IY 53、IH 52，16 speakers。B 保持原冻结 pair PASS，再用前次冻结 strict 五点 QC：EH 35/39 对，IH 18/56 对。C 使用 F5 strict 395 tokens/16 speakers，exact utterance/word/phone 跨人候选 144 tokens；时长差 ≤25% 后只有 70 tokens/16 speakers。五点有效性、短元音、alternate-ceiling 与 boundaries 沿用原 QC；matched track QC sensitivity 为 EH 39、IH 49 对。新增分析没有更改分段、formant 规则或样本阈值。五点是 token 内相关测量；bootstrap 以 speaker 为单位。

## 6. Experiment A: Incremental information

同一原声–克隆对定义 `D(t)=clone−original`，midpoint 为 `D50`，动态残差 `R(t)=D(t)−D50`。这是控制 midpoint 后可观测的差异，不是独立预测目标；因此**不**把残差非零或 full distance 更大解读为增量 R²。speaker 等权的 residual log-formant RMSE：F5 0.072 [0.066, 0.078]，CosyVoice 2 0.078 [0.072, 0.084]，OpenVoice V2 0.081 [0.073, 0.089]；相对同人跨 utterance 自然残差的比值分别为 0.760 [0.699, 0.820]、0.830 [0.765, 0.905]、0.862 [0.775, 0.955]。这些数值描述 midpoint 未捕获的测量变化，但同文本 clone–original 与跨句自然基线并非同一分布。

独立标签辅助检验用 clone 的元音类别：16-speaker leave-one-speaker-out，训练折内 z-score，固定 shrinkage LDA。静态 S1 的 pooled balanced accuracy 0.700、macro-F1 0.699；去中心 shape S2 为 0.426/0.414；静态+shape S3 为 0.715/0.713；full 10D S4 为 0.691/0.690。S3−S1 pooled 差 +0.015，但**speaker 等权配对差 −0.010 [−0.074, 0.048]**。100 次 S1+10 个独立噪声维度的负对照平均差 −0.043，2.5–97.5% 分位数 [−0.084, −0.005]。维度增加可损害解码；本次 S3 小幅 pooled 优势不稳定。更重要的是类别解码也不是 clone distortion 的独立标签，不能用它声称重建解释力增加。common-track 422-token sensitivity 的 raw residual RMSE 为 0.068/0.071/0.076（F5/CosyVoice/OpenVoice）；与 strict 方向一致。**事后探索性** Bark 变换的残差 RMSE 为 0.369 [0.333, 0.410]、0.402 [0.363, 0.443]、0.428 [0.386, 0.473] Bark；它只检查单位变换下残差仍可测，不参与决策门槛。

## 7. Experiment B: Time-resolved reconstruction

使用冻结 speaker-specific canonical axis 和 matched error/control；每对先形成完整五点 DID，再在 speaker 内平均，最后跨 speaker 推断。严格 EH 五点 DID 约为 20% +0.729、35% +0.818、50% +0.787、65% +0.960、80% +1.196，五点平均 +0.898 [约 0.445, 1.497]（重新抽样 seed，仍与旧结果相容），中点 +0.787 [0.150, 1.594]。预定晚段减早段 +0.305 [−0.083, 0.750]；去平均的 canonical projection 轨迹整体 sign-flip **p=.173**。旧二维 shape omnibus p=.419，其定义不同，两者均未建立稳健形状效应。EH track support 39 对/11 人的时间形状 p=.183。

严格 IH 五点平均 +0.512 [−0.090, 1.143]（18 对/9 人），中点 +0.348 [−0.262, 0.921]；晚段减早段 −0.026 [−0.505, 0.560]，整体形状 p=.636。track support 49 对/14 人的形状 p=.532。预定 ≥4 对/speaker 敏感性：EH strict 26 对/4 人五点平均 +0.646 [0.395, 0.898]、晚减早 +0.039 [−0.307, 0.326]；IH strict 无满足门槛的 speaker，无法估计。IH track 的 ≥4 对子集为 26 对/5 人，平均 +1.469 [0.331, 3.111]，支持对选择明显敏感。五点同步 95% speaker-bootstrap bands 与每点估计在 [time_resolved_did_results.csv](time_resolved_did_results.csv)；五点绝不能当五次独立复现。**No stable additional time-localized reconstruction effect established.** IH 的不确定性不等于不存在重建。

## 8. Experiment C: Speaker-specific preservation

exact same utterance ID、word index、phone index 和元音类别下，clone–own-original 与 clone–other-speaker-original 作配对；异人候选按原音时长最接近选取。144 个候选 token 中只有 70 个满足预定 25% 时长门槛，低于协议的 80-token 推断门槛，故**仅描述，不给推断性 CI 或 p 值**。在 70 token/16 speakers 中，异人减同人的去中心 shape 距离为 +0.0043 log RMSE；midpoint 距离差为 +0.0755。去掉时长门槛为 144 token/16 speakers，shape 差 +0.0062，midpoint 差 +0.0791，但时长混杂更大。其模式提示可见的静态 speaker 分离较强，动态独特性证据很弱。实际重音、词内语速和共发音仍可能不同；不能称为 speaker-specific dynamics 已保留。

## 9. Robustness and limitations

所有条件保持同 token/同 speaker 支持；标准化只用训练 speaker。类别任务类别大致平衡，但每 speaker 的 token 数不同，因此 pooled +0.015 与 speaker 等权 −0.010 不一致。B 的 IH strict QC 丢失 38/56 对，短/长元音时长限制可能改变外推群体；旧 midpoint 56 对结论不能被替代。C 的 70-token 门槛触发预先停止推断。既有自然 NDS 的跨 utterance 基线与同文本原声–克隆对的语言环境不完全等价。图表中的轨迹 CI 为整体函数的 simultaneous band；没有逐点寻找显著性。无新音频、模型或轴重新拟合。

## 10. What we learned beyond the previous experiment

本轮真正新增了三项**检验结果**：一是 speaker-disjoint、训练折标准化的静态/动态类别解码未显示稳健增益；二是 canonical-direction **去平均**五点 DID 没有稳定共同时间形状；三是 exact-context 跨人对照的可行支持低于预定推断门槛，且描述性 shape 差很小。这些结果约束了“低动态 NDS=个体动态被保留”的解释。没有新增稳健的正向动态机制证据；旧五点平均 DID 与几何 NDS 不因本轮重算而变成新发现。

## 11. What remains unestablished

动态 shape 是否有独立于 midpoint 的克隆失真预测力；EH 是否存在局部时间重建；IH 是否有较弱/异质的动态重建；speaker-specific VISC 的保留；主动 reference trajectory transfer；感知元音类别或模型内部表征，均未确立。

## 12. Decision gate

**NO GO**：没有满足“稳健、非循环、且不由维度/QC/少数 speaker 主导”的预定动态增量标准。停止无目的动态指标扩张；保留 negative/null findings。详见 [decision_gate.md](decision_gate.md)。

## 13. Implications for master's thesis

冻结 EH/IH midpoint matched DID 仍是主结论；上一轮动态轨迹复分析可作为探索性测量扩展。本轮更适合在限制或附录中简述“未验证到新增动态解释力”，不提升为核心确认性发现，不改论文正文、证据 registry 或既有图表来源。

## 14. Next recommended action

不进入 midpoint-fixed reference intervention，也不新增模型或批量生成。保存代码、表、QC 及图供导师审阅；若以后有独立证据显示稳定的 midpoint-independent shape 效应，再冻结干预 protocol。供之后整合进 Notion 的简短摘要：**同 token 的 midpoint 外残差可测，但 speaker-disjoint 解码无稳健增益；EH/IH matched DID 未证实额外时间形状；严格同文本跨人对照样本不足。当前 NO GO，冻结 midpoint 结论不变。**
