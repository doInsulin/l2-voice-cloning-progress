# Adem (2026) 与本实验的关系

核对来源：[Adem, *Journal of Phonetics* 114, 101471](https://www.sciencedirect.com/science/article/pii/S0095447025000828)，DOI [10.1016/j.wocn.2025.101471](https://doi.org/10.1016/j.wocn.2025.101471)。2026-10-30 检索时可访问该出版页的索引化摘要及 Methods/Results 摘录，但网页全文打开失败，PDF 未取得。因此以下只采用可核实的公开内容；不转述未核实的表格、效应量、分类准确率或验证分折细节。

Adem 研究 Arabic-speaking adolescent learners 的 L2 English vowel **production**。可访问内容说明其在元音 20/35/50/65/80% 取 F1/F2，使用 VISC 的 vector length (VL)、trajectory length (TL)、formant velocity (FV)、angular displacement，以及 fPCA 描述跨时间变化；公开摘要报告动态减弱、速度较慢及相对静态中点的额外线索。其样本、分类标签、统计任务与本项目不相同，不能比较效应大小或准确率。

本研究借鉴五点时间标准化、二维向量与路径的测量思想，但研究对象是**同一 speaker 原声–克隆配对差异**和**matched error/control DID**。VL 对应 20→80% 位移大小，TL 对应相邻段之和；FV 需要除以持续时长，因原声与合成声时长可变、短元音测量脆弱，本轮不另立 FV 为主指标。角度在位移很小的 token 上不稳定，改用完整二维位移向量。fPCA 在当前 214-token/16-speaker 及 matched EH 35 对、IH 18 对的支持下没有充分优势，因此不强行拟合。对齐边界沿用已冻结的 source TextGrid/MFA，而非借用 Adem 的人工分段规则。归一化采用本项目的 log-Hz 和同人自然变异标尺，不照搬该文的 raw-Hz 或其他归一化方案。

Adem 的问题是 L2 学习者如何实现元音动态；本研究的问题是 zero-shot cloning 的输出在控制 midpoint、文本/元音类别和匹配正确 token 后，是否有额外动态保留或重建信息。其生产数据的分类目标不能充当本项目的克隆失真验证目标；本项目的 secondary vowel-category decoding 也只作为独立标签的辅助检验。
