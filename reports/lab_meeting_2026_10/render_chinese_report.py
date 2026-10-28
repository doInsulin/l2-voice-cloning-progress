"""Render the Chinese, image-rich offline meeting report from verified result tables.

All 28 original experiment PNGs are packaged byte-for-byte in figures/source/ and
embedded as data URIs so the report stays complete when opened as a single file.
"""
from __future__ import annotations

import base64
import csv
import hashlib
from html import escape
from pathlib import Path


# group prefix, original research folder, Chinese section name
GROUPS = {
    "final": ("final_confirmatory_experiment/figures", "最终确认实验"),
    "dynamic": ("27_dynamic_vowel_analysis/figures", "动态元音观察"),
    "vowel_f5_eh": ("28_localized_vowel_reference_intervention/figures", "F5 局部 EH 干预"),
    "vowel_qwen_ih": ("29_qwen3_ih_vowel_replication/figures", "Qwen 局部 IH 复验"),
    "vowel_f5_ih": ("30_f5_ih_vowel_replication/figures", "F5 局部 IH 复验"),
    "vowel_qwen_eh": ("31_qwen_eh_vowel_replication/figures", "Qwen 局部 EH 复验"),
    "qwen_external": ("qwen3_external_replication_20261003/figures", "Qwen 外部复验"),
    "timing_spectrogram": ("timing_structure_followup_20261003/measurement_check", "时间测量核查"),
    "timing_reaudit": ("timing_structure_followup_20261003/measurement_reaudit", "时间检测器复核"),
    "timing_structure": ("timing_structure_followup_20261003/structure_analysis", "时间结构匹配扩展"),
}


# title, explanation, scientific boundary. These captions interpret original
# figures without changing their pixels or their underlying estimates.
CAPTIONS = {
    "final__model_trait_preservation_matrix.png": ("三模型 × 四类特征：保留不是单一分数", "颜色和数字是每位说话人等权的自然变异归一化失真 NDS；每一列有自己的测量定义，数值越低表示该指标的声学距离越小。", "不可跨列求平均，也不能据此评出总体最优模型。"),
    "final__speaker_trait_heatmap.png": ("说话人层面的特征差异", "每一行是一位说话人；同一模型内，不同特征的失真并不总是同步。", "颜色为自动测量的 NDS，不是人耳相似度。"),
    "final__speaker_level_effects.png": ("元音重建：个体方向并不整齐一致", "左侧 IH→IY、右侧 EH→AE 是说话人层的 matched DID；零线右侧表示相对正确词对照更接近规范元音的声学方向。", "EH 总体方向受支持；IH 最终区间跨零。单个说话人的宽区间需结合配对数。"),
    "final__f0_reference_response.png": ("F0 干预：每位说话人都随参考变化", "横轴为参考语音的 F0 范围，纵轴为合成输出的 F0 范围；连线连接同一说话人的三档条件。", "这说明全局 F0 范围可控，不表示每一句的完整 F0 曲线被复制。"),
    "final__timing_reference_response.png": ("等帧时间干预：目标内部词间隔变化弱且不齐", "横轴为参考中的局部停顿，纵轴为合成目标的词间 gap；多数说话人的三档连线接近平坦或不单调。", "MFA gap 是边界代理，不等同于人工标注的语言学停顿。"),
    "final__preservation_vs_controllability.png": ("为什么必须区分保留与可控性", "横轴是自然原声—克隆的 NDS，纵轴是主动改变参考后的 RCI；F0 与词间隔落在不同位置。", "两个坐标是不同估计量，不构成一个共同能力排名。"),
    "dynamic__dynamic_nds_summary.png": ("元音动态轨迹：中点之外还有可测信息", "比较完整 F1/F2 轨迹、去中心后的形状、中点以及时长的 NDS，使用三模型共同严格支持集。", "声学轨迹对应不代表听者能辨认音类，也不代表模型内有独立轨迹编码。"),
    "dynamic__f5_speaker_dynamic_heatmap.png": ("F5 动态元音：说话人差异", "逐说话人显示动态元音指标，帮助检查总体结果是否由少数人主导。", "各元音和说话人的有效 token 数不同。"),
    "dynamic__trajectory_delta_by_vowel.png": ("四类元音的轨迹差异", "EH、AE、IH、IY 的轨迹差异分开呈现，显示不能把所有元音压成一个中点指标。", "属于观察性声学描述，不是 reference intervention。"),
    "vowel_f5_eh__selective_transfer_summary.png": ("F5 三类参考干预：F0、局部元音、词间隔", "比较 F0-range RCI、EH 局部元音斜率和局部词间隔 RCI，点和误差线给出说话人层估计及 95% 区间。", "局部元音斜率与 RCI 的操作定义不同，只作并列观察，不作统一能力刻度。"),
    "vowel_f5_eh__vowel_reference_response.png": ("F5 局部 EH 干预：参考变化传入目标元音", "每条线连接一位说话人三档局部元音参考；合成元音的 EH 轴得分随参考上升。", "48/48 目标三元组单调，斜率 0.261；这是特定模型和元音的部分声学传递。"),
    "vowel_f5_eh__vowel_speaker_slopes.png": ("F5 局部 EH：逐说话人斜率", "检查 12 位说话人的局部 EH 传递方向与不确定性。", "不能从这个干预反推自然说话中所有 EH 都会被忠实保留。"),
    "vowel_qwen_ih__ih_pointwise_f1_f2_slopes.png": ("Qwen 局部 IH：五点 F1/F2 响应", "沿元音内部五个时间点检查局部参考操纵是否传递到合成元音。", "区间和目标敏感性未给出稳定正向轨迹斜率。"),
    "vowel_qwen_ih__ih_reference_response.png": ("Qwen 局部 IH：参考—输出关系不稳定", "逐说话人三档参考与合成 IH 轴得分的关系。", "总体斜率 −0.010，区间跨零；不能把它说成已证明完全无传递。"),
    "vowel_qwen_ih__ih_speaker_slopes.png": ("Qwen 局部 IH：说话人异质性", "逐说话人斜率和区间说明总体接近零背后存在差异。", "仅 11 人、每人三个目标；估计不精确。"),
    "vowel_qwen_ih__qwen_ih_vs_f5_eh.png": ("早期跨模型跨元音对比", "并列当时 F5 EH 与 Qwen IH 的局部元音斜率，提示需要补齐四格设计。", "这里模型和元音同时改变，不能当作纯模型效应；后续四格图优先。"),
    "vowel_f5_ih__f5_ih_pointwise_f1_f2.png": ("F5 局部 IH：五点声学响应", "元音内部不同位置的 F1/F2 响应，检查传递是否只发生在中点。", "F0 range 出现小幅探索性串扰，不能宣称完全无其他特征变化。"),
    "vowel_f5_ih__f5_ih_reference_response.png": ("F5 局部 IH：同参考三档有正向响应", "11 位说话人、33 个目标三元组的局部 IH 参考—输出关系。", "斜率 0.170 [0.132, 0.220]，弱于 EH；仍限于该参考和目标集。"),
    "vowel_f5_ih__three_cell_transfer.png": ("三格阶段比较：补齐 Qwen EH 前", "F5 EH、F5 IH、Qwen IH 的局部斜率并列。", "这是研究过程图；完整四格结果应以随后四格图为准。"),
    "vowel_qwen_eh__four_cell_transfer.png": ("完整四格：局部元音传递具有条件差异", "F5/Qwen × EH/IH 四个单元的五点轨迹斜率和说话人 bootstrap 区间。", "F5 两格稳定正向，Qwen 两格不稳定；平均模型关联差为探索性，不能证明内部机制。"),
    "vowel_qwen_eh__qwen_eh_pointwise_f1_f2.png": ("Qwen 局部 EH：五点 F1/F2 响应", "逐时间点查看为何总体 EH 斜率未稳定高于零。", "Qwen 这一格有文本 QC 异常；排除后总体判断仍未改变。"),
    "qwen_external__preservation_common_support.png": ("Qwen 两种输入方式与原三模型的共同支持", "五条件放到相同目标支持集上比较四类自然保留指标。", "两种 Qwen 接口同时改变可用信息与条件路径，不能解释成单因素架构因果效应。"),
    "qwen_external__reference_controllability.png": ("Qwen 外部复验：F0 强、局部时间弱", "F5 与 Qwen 音频+文本、仅向量两种方式的 F0、局部词间隔和低能段 RCI 及区间。", "Qwen 局部时间有小的正向或跨零估计；不能写成完全不可控。"),
    "timing_spectrogram__spectrogram_sample_01.png": ("时间边界实例 1：频谱图", "展示人工核查时低能段和词边界如何对应。", "示意测量定义，不是总体效应。"),
    "timing_spectrogram__spectrogram_sample_02.png": ("时间边界实例 2：频谱图", "第二个目标的声学边界实例。", "示意测量定义，不是总体效应。"),
    "timing_spectrogram__spectrogram_sample_03.png": ("时间边界实例 3：频谱图", "第三个目标的声学边界实例。", "示意测量定义，不是总体效应。"),
    "timing_reaudit__full_boundary_diagnostics.png": ("时间检测器复核：阈值改变会改变零响应计数", "比较不同低能阈值与冻结检测器对同一批音频的测量，解释为何 56/72 零变化不能被过度解释。", "这是后续敏感性分析，不替换冻结 word-gap RCI。"),
    "timing_structure__structure_match_gap_rci.png": ("结构匹配扩展：未发现稳定增强", "匹配与不匹配目标的局部 gap 响应并列。", "目标文本也不同，区间跨零；不能把差值解释为纯结构匹配效应。"),
}

MAIN = [
    "final__model_trait_preservation_matrix.png",
    "dynamic__dynamic_nds_summary.png",
    "final__speaker_level_effects.png",
    "final__f0_reference_response.png",
    "final__timing_reference_response.png",
    "final__preservation_vs_controllability.png",
    "qwen_external__reference_controllability.png",
    "vowel_f5_eh__vowel_reference_response.png",
    "vowel_qwen_eh__four_cell_transfer.png",
    "timing_reaudit__full_boundary_diagnostics.png",
]


def render(root: Path, here: Path, summary: list[dict]):
    source = here / "figures" / "source"
    files = sorted(p.name for p in source.glob("*.png"))
    if set(files) != set(CAPTIONS):
        raise ValueError(f"Figure registry mismatch: missing {set(CAPTIONS)-set(files)}, extra {set(files)-set(CAPTIONS)}")
    image_data = {}
    registry = []
    for name in files:
        group, original = name.split("__", 1)
        folder, stage = GROUPS[group]
        raw = (source / name).read_bytes()
        image_data[name] = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        title, explanation, boundary = CAPTIONS[name]
        registry.append({"file": "figures/source/" + name, "stage": stage,
                         "original_path": "research/" + folder + "/" + original,
                         "sha256": hashlib.sha256(raw).hexdigest(), "placement": "main" if name in MAIN else "atlas",
                         "title_zh": title, "reading_zh": explanation, "boundary_zh": boundary})
    with (here / "figure_registry.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(registry[0])); writer.writeheader(); writer.writerows(registry)

    def fig(name, compact=False):
        title, explanation, boundary = CAPTIONS[name]
        klass = "figure compact" if compact else "figure"
        return (f'<figure class="{klass}" id="fig-{escape(name[:-4])}">'
                f'<div class="figure-head"><span class="fig-badge">原实验图</span><strong>{escape(title)}</strong></div>'
                f'<img src="{image_data[name]}" alt="{escape(title)}" loading="lazy">'
                f'<figcaption><b>怎么看：</b>{escape(explanation)}<br><b>边界：</b>{escape(boundary)}'
                f'<br><a href="../reports/lab_meeting_2026_10/figures/source/{escape(name)}">下载原图</a></figcaption></figure>')

    def metric(experiment, trait, model=None):
        matches = [r for r in summary if r["experiment"] == experiment and r["trait"] == trait and
                   (model is None or r["model"] == model)]
        if len(matches) != 1:
            raise ValueError((experiment, trait, model, len(matches)))
        return matches[0]

    def val(r, sign=False):
        x = r["estimate"]
        return f"{x:+.3f}" if sign else f"{x:.3f}"

    def interval(r):
        return f"[{r['ci_lower']:.3f}, {r['ci_upper']:.3f}]"

    f0 = metric("Final reference intervention", "estimated voiced-F0 range")
    gap = metric("Final reference intervention", "MFA local word-boundary gap")
    pause = metric("Final reference intervention", "RMS-detected low-energy interval")
    eh = metric("Final matched segmental reconstruction", "EH→AE")
    ih = metric("Final matched segmental reconstruction", "IH→IY")
    f5eh = metric("October local-vowel reference intervention", "EH–AE local vowel", "F5-TTS")
    f5ih = metric("October local-vowel reference intervention", "IH–IY local vowel", "F5-TTS")
    qeh = metric("October local-vowel reference intervention", "EH–AE local vowel", "Qwen3-TTS 0.6B")
    qih = metric("October local-vowel reference intervention", "IH–IY local vowel", "Qwen3-TTS 0.6B")

    css = r"""
    :root{--ink:#202124;--sub:#5d6469;--line:#d7dbdd;--pale:#f5f7f7;--teal:#147d78;--ochre:#a3691b}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:#fff;font:18px/1.6 "Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif}
    nav{position:sticky;top:0;z-index:20;display:flex;gap:22px;align-items:center;overflow:auto;white-space:nowrap;background:#fff;border-bottom:1px solid var(--line);padding:11px 3.5vw;font-size:14px}nav strong{margin-right:auto}nav a{color:var(--sub);text-decoration:none}
    main{max-width:1320px;margin:auto}section{padding:72px 5vw 78px;border-bottom:1px solid var(--line);scroll-margin-top:40px}section.hero{min-height:670px;display:flex;flex-direction:column;justify-content:center}
    h1{font-size:clamp(42px,5.3vw,72px);line-height:1.16;letter-spacing:-.03em;margin:20px 0 24px;max-width:1100px}h2{font-size:clamp(31px,3.4vw,47px);line-height:1.25;margin:6px 0 22px}h3{font-size:23px;margin:16px 0 7px}p{max-width:1040px;margin:10px 0 18px}.eyebrow{font-size:14px;letter-spacing:.08em;color:var(--teal);font-weight:700}.lead{font-size:26px;line-height:1.5;max-width:1050px}.muted,.small{color:var(--sub)}.small{font-size:15px}
    .takeaway{border-left:5px solid var(--teal);background:#f0f7f6;padding:18px 24px;font-size:24px;line-height:1.5;margin:28px 0}.warning{border-left-color:var(--ochre);background:#fbf8f3}.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}.metric{padding:20px 23px;background:var(--pale);border-top:3px solid var(--ink)}.metric em{display:block;font-style:normal;font-size:39px;font-weight:700;line-height:1.15}.metric span{font-size:15px;color:var(--sub)}
    .flow{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:24px 0}.flow span{background:var(--pale);border:1px solid var(--line);padding:13px 17px}.flow b{color:var(--teal)}.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px}.box{background:var(--pale);padding:20px 24px;border-top:3px solid var(--ink)}.box.teal{border-color:var(--teal)}.box.ochre{border-color:var(--ochre)}
    .figure{border:1px solid var(--line);margin:32px 0;background:#fff}.figure-head{display:flex;gap:14px;align-items:center;padding:17px 20px;border-bottom:1px solid var(--line);font-size:20px}.fig-badge{font-size:12px;color:var(--teal);border:1px solid var(--teal);padding:2px 7px;white-space:nowrap}.figure img{display:block;width:100%;height:auto;max-height:680px;object-fit:contain;padding:12px}.figure figcaption{padding:15px 21px 20px;background:var(--pale);font-size:15px;color:#464d51;line-height:1.65}.figure figcaption b{color:var(--ink)}a{color:#075c57;text-underline-offset:3px}
    .atlas{display:grid;grid-template-columns:1fr 1fr;gap:18px}.atlas .figure{margin:0}.atlas .figure-head{font-size:16px}.atlas .figure img{max-height:420px}.atlas .figure figcaption{font-size:13px}.atlas-group{padding:27px 0;border-top:1px solid var(--line)}.atlas-group h3{margin-bottom:15px}
    .bar-row{display:grid;grid-template-columns:190px 1fr 180px;gap:13px;align-items:center;margin:12px 0}.bar-track{height:31px;background:#e8ebeb}.bar-fill{height:31px;background:var(--teal)}.bar-row:nth-child(3) .bar-fill{background:#a3691b}.bar-row:nth-child(4) .bar-fill{background:#73787d}.bar-value{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
    table{width:100%;border-collapse:collapse;margin:24px 0;font-size:16px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:var(--pale);border-top:2px solid var(--ink)}.num{white-space:nowrap;font-variant-numeric:tabular-nums}.question{border-top:1px solid var(--line);padding:19px 0}.question strong{display:block;font-size:21px}ul{padding-left:26px}li{margin:7px 0}.source{font-size:14px;color:var(--sub)}footer{padding:25px 5vw;max-width:1320px;margin:auto;color:var(--sub);font-size:13px}
    @media(max-width:850px){section{padding:56px 5vw}.cols,.metric-grid,.atlas{grid-template-columns:1fr}.lead{font-size:22px}.bar-row{grid-template-columns:120px 1fr 100px}nav{font-size:12px}}
    @media print{nav{display:none}section{page-break-after:always;padding:20px 15px}body{font-size:14px}h1{font-size:40px}h2{font-size:29px}.figure img{max-height:440px}.atlas .figure img{max-height:260px}}
    """

    parts = [f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>零样本声音克隆中的二语英语语音特征｜组会实验进展</title><style>{css}</style></head><body>']
    parts.append('<nav><strong>组会实验进展 · 2026 年 10 月 28 日</strong><a href="#question">研究问题</a><a href="#data">数据</a><a href="#preservation">自然保留</a><a href="#segmental">元音</a><a href="#f0">F0 干预</a><a href="#timing">时间干预</a><a href="#confirmatory">确认实验</a><a href="#extension">后续扩展</a><a href="#atlas">完整图集</a><a href="#supervisor">请教导师</a></nav><main>')

    parts.append('''<section class="hero" id="top"><div class="eyebrow">硕士研究组会｜实验进展汇报</div><h1>零样本声音克隆中的二语英语语音特征：保留与重建</h1><p class="lead">L2 English Speech Traits in Zero-Shot Voice Cloning: Preservation and Reconstruction</p><p>2026 年 10 月 28 日</p><div class="takeaway">我们已经从“会不会复制二语口音？”推进到一个更具体的问题：<b>哪些说话人特征会随参考语音进入新句子，哪些会在生成时被重建？</b></div><p class="small">本页按“研究问题 → 实验设计 → 已完成实验 → 观察结果 → 结论边界 → 请教导师”顺序讲述。页面下方附有 28 张原实验图。</p></section>''')

    parts.append('''<section id="question"><div class="eyebrow">01｜从上次组会到这次组会</div><h2>研究问题已经变成可检验的实验问题</h2><div class="cols"><div class="box"><h3>上次</h3><p>提出方向：zero-shot voice cloning 会不会复制二语说话人的发音、语调和节奏？当时缺少系统实验结果。</p></div><div class="box teal"><h3>这次</h3><p>已有三模型自然保留分析、匹配元音对照、F0 与局部时间干预、最终确认实验，以及 10 月的独立复验。</p></div></div><div class="flow"><span>真实 L2 参考语音</span><b>+</b><span>新的目标文本</span><b>→</b><span>克隆系统</span><b>→</b><span>输出的身份代理、元音、F0、时间结构</span></div><p class="lead">重点不是“哪个模型最好”，而是 <b>不同语音维度是否被选择性保留</b>。</p></section>''')

    parts.append('''<section id="design"><div class="eyebrow">02｜实验路线</div><h2>从观察相关到主动操纵参考语音</h2><div class="flow"><span>16 位 L2 说话人</span><b>→</b><span>固定参考与目标句</span><b>→</b><span>F5 / CosyVoice 2 / OpenVoice V2</span><b>→</b><span>Whisper、MFA、声学 QC</span><b>→</b><span>配对测量</span><b>→</b><span>参考干预</span></div><div class="cols"><div class="box"><h3>自然保留：NDS</h3><p>比较原声与克隆的声学距离，并除以同人自然变异尺度。它回答“生成结果像不像原声的某个指标”。</p></div><div class="box"><h3>主动可控：RCI</h3><p>在固定目标句下，只改变参考特征，测量输出端点变化占参考变化的比例。它回答“这个参考线索能推动输出多少”。</p></div></div><p>另用正确词对照的匹配差分 DID 衡量偏误元音是否朝规范方向移动。<b>三个估计量不互换，也不合成总分。</b></p><p class="source">方法来源：<a href="../reports/lab_meeting_2026_10/source_results/final_confirmatory_summary.json">最终实验完成审计</a>；全部文件和图的来源见<a href="../reports/lab_meeting_2026_10/README.md">数据说明</a>。</p></section>''')

    parts.append('''<section id="data"><div class="eyebrow">03｜样本与质控</div><h2>最终三模型数据规模已超过早期可行性阶段</h2><div class="metric-grid"><div class="metric"><em>157 / 160</em><span>F5-TTS 最终全局 QC 通过</span></div><div class="metric"><em>159 / 160</em><span>CosyVoice 2 最终全局 QC 通过</span></div><div class="metric"><em>160 / 160</em><span>OpenVoice V2 最终全局 QC 通过</span></div></div><p>16 位说话人，每模型 160 个固定目标；每种指标另按自身可用性限定共同支持：身份 156、元音 144、词间隔 156、F0 轮廓 110 个目标（F0 涉及 15 位说话人）。早期 8 人实验的三模型共同配对只有 36/80，属于已被最终实验取代的可行性阶段。</p><div class="takeaway">先看“哪些样本真正可测”，再解释模型输出；不能把生成成功数直接当成每项分析的分母。</div><p class="source">下载：<a href="../reports/lab_meeting_2026_10/model_qc_summary.csv">模型 QC 表</a>、<a href="../reports/lab_meeting_2026_10/source_results/preservation_sample_qc.csv">逐条 QC</a>。</p></section>''')

    parts.append('<section id="preservation"><div class="eyebrow">04｜自然保留：三模型</div><h2>同一个“说话人”，不同特征保留程度并不一致</h2><p class="takeaway">身份代理、元音、词间隔、F0 轮廓形成不同的失真图谱；不能把一个 ECAPA 分数当作所有说话行为的忠实度。</p>')
    parts.append(fig("final__model_trait_preservation_matrix.png"))
    parts.append('<p>这张矩阵是总览。接下来把元音从“一个中点”延伸到五点轨迹，可以看到有些动态信息仍可测。</p>')
    parts.append(fig("dynamic__dynamic_nds_summary.png"))
    parts.append('<p class="small">自然保留是观察性问题。即使某一项 NDS 较低，也不能由此断定改变参考时该项一定可控。</p></section>')

    parts.append(f'''<section id="segmental"><div class="eyebrow">05｜音段重建</div><h2>EH→AE：偏误元音出现规范方向的声学移动</h2><div class="metric-grid"><div class="metric"><em>{val(eh, True)}</em><span>EH→AE matched DID；95% CI {interval(eh)}；39 对 / 11 人</span></div><div class="metric"><em>{val(ih, True)}</em><span>IH→IY matched DID；95% CI {interval(ih)}；56 对 / 14 人</span></div><div class="metric"><em>≠ 全面纠正</em><span>IY→IH、r 音对比的区间也跨零</span></div></div><p>正向 DID 表示偏误词从原声到克隆的移动，超过同说话人正确词对照的相应移动，并指向说话人自己的规范元音端点。EH 的总体方向有证据；IH 的最终结果异质且不确定。</p>''')
    parts.append(fig("final__speaker_level_effects.png"))
    parts.append('<div class="takeaway warning">这是声学元音轴上的位移，不能直接说“模型把发音纠正了”或“听者一定听成 EH”。</div></section>')

    parts.append('''<section id="listening"><div class="eyebrow">06｜专家听辨</div><h2>声学移动有一部分能被人耳注意到</h2><div class="metric-grid"><div class="metric"><em>10 / 18</em><span>两位知情专家都判断更接近 EH</span></div><div class="metric"><em>6 / 18</em><span>两位都判断没有明显更近</span></div><div class="metric"><em>κ = 0.769</em><span>18 个选定词项、6 位说话人</span></div></div><p>在 14 个声学指标朝 EH 移动的选定词项中，9 个得到两位专家相同的“更近”判断。这是有限的声学—听觉对应证据，不是盲法音素识别，更不能把 10/18 推成总体纠正率。</p><div class="takeaway">有些声学变化可听见；并非每一个声学正向位移都有明显听感。</div><p class="source">来源：<a href="../reports/lab_meeting_2026_10/source_results/expert_audibility_results.json">专家听辨结果</a>。10 月盲听材料已质检，但<a href="../reports/lab_meeting_2026_10/source_results/perceptual_materials_report.md">尚无真实听者回答</a>。</p></section>''')

    parts.append('<section id="intervention"><div class="eyebrow">07｜实验设计升级</div><h2>只看相关性，分不清“复制”还是“重新生成”</h2><p class="lead">参考与克隆相似，可能来自说话人、句子内容、目标文本或模型固有输出习惯。为了问“参考特征本身有没有传递”，我们固定目标并操纵参考。</p><div class="flow"><span>同一说话人</span><b>+</b><span>同一目标句与随机种子</span><b>+</b><span>受控参考变体</span><b>→</b><span>比较输出差异</span></div>')
    parts.append(fig("final__preservation_vs_controllability.png"))
    parts.append('<p class="small">图中横轴自然保留与纵轴主动可控性是两个不同问题。尤其 F0 范围可随参考大幅改变，并不意味着自然 F0 轮廓会无误复制。</p></section>')

    parts.append(f'''<section id="f0"><div class="eyebrow">08｜核心干预一：F0 范围</div><h2>人为增大参考 F0 范围，克隆输出明显跟随</h2><div class="metric-grid"><div class="metric"><em>{val(f0)}</em><span>RCI；95% CI {interval(f0)}</span></div><div class="metric"><em>91 / 95</em><span>完整目标三元组严格单调</span></div><div class="metric"><em>16 / 16</em><span>说话人平均方向为正</span></div></div><p>参考端扩张—压缩的中位差约 4.127 半音，输出中位差约 2.532 半音。RCI 直觉上是人为加入参考中的 F0 范围变化，有多少比例反映到输出里；统计采用说话人等权。</p>''')
    parts.append(fig("final__f0_reference_response.png"))
    parts.append('<div class="takeaway">目前最强的主动可控证据：F5 输出的全局 F0 范围对参考干预稳定响应。</div></section>')

    parts.append(f'''<section id="timing"><div class="eyebrow">09｜核心干预二：局部时间</div><h2>同样改变参考停顿，目标内部时序只弱响应</h2><div class="bar-row"><b>F0 范围</b><div class="bar-track"><div class="bar-fill" style="width:72.7%"></div></div><span class="bar-value">RCI {val(f0)}</span></div><div class="bar-row"><b>局部词间隔</b><div class="bar-track"><div class="bar-fill" style="width:21.1%"></div></div><span class="bar-value">RCI {val(gap)}</span></div><div class="bar-row"><b>低能段停顿</b><div class="bar-track"><div class="bar-fill" style="width:6.7%"></div></div><span class="bar-value">RCI {val(pause)}</span></div><p class="small">上面三条长度只用于直观看本次 RCI 的点估计；测量对象不同，须结合区间和定义。词间隔 CI {interval(gap)}；冻结低能段 CI {interval(pause)}。两项时间指标均为 72 个完整目标、12 人。</p>''')
    parts.append(fig("final__timing_reference_response.png"))
    parts.append('<p>56/72 个冻结低能检测器的端点变化为零；仅 4/72 个词间隔三元组严格单调。与 F0 对照，12 位共同说话人的 RCI 差为 +0.543 [0.359, 0.707]。</p><div class="takeaway warning">弱响应不等于“模型没有时间表示”。冻结的低能段检测器也不等于人工听到的停顿。</div></section>')

    parts.append(f'''<section id="confirmatory"><div class="eyebrow">10｜单独归纳：最终确认实验</div><h2>四个主结果，回答四个具体问题</h2><table><thead><tr><th>特征</th><th>问题</th><th>结果与 95% CI</th><th>有效支持</th><th>目前读法</th></tr></thead><tbody><tr><td>F0 范围</td><td>参考干预能否推动输出？</td><td class="num">RCI {val(f0)} {interval(f0)}</td><td>95 个目标 / 16 人</td><td>强响应</td></tr><tr><td>MFA 词间隔</td><td>局部时间能否传递？</td><td class="num">RCI {val(gap)} {interval(gap)}</td><td>72 / 12</td><td>较弱、异质</td></tr><tr><td>冻结低能段</td><td>对应声学低能段是否改变？</td><td class="num">RCI {val(pause)} {interval(pause)}</td><td>72 / 12</td><td>很小，依赖检测定义</td></tr><tr><td>EH→AE</td><td>偏误元音是否朝规范方向移动？</td><td class="num">DID {val(eh, True)} {interval(eh)}</td><td>39 对 / 11 人</td><td>有声学证据</td></tr></tbody></table><div class="takeaway">更稳妥的主结论：<b>不同输出维度具有不同的自然保留图谱和参考可控性。</b></div><p>IH→IY 的最终 DID 为 {val(ih, True)} {interval(ih)}；因此 EH 不能代表所有偏误元音。原先改变参考总长度的停顿试验会影响 F5 生成帧预算，最终时间证据以等帧设计为准。</p><p class="source">下载：<a href="../reports/lab_meeting_2026_10/confirmatory_results.csv">确认性结果 CSV</a>、<a href="../reports/lab_meeting_2026_10/experiment_summary.json">完整汇总 JSON</a>。</p></section>''')

    parts.append('<section id="extension"><div class="eyebrow">11｜10 月独立扩展：跨模型复验</div><h2>Qwen 也呈现 F0 强、局部时间弱的方向</h2><p>Qwen3-TTS 音频+文本与仅说话人向量两种输入方式的 F0-range RCI 分别为 0.684 [0.581, 0.788] 和 0.776 [0.652, 0.909]（各 96 个目标、16 人）。局部词间隔分别为 0.088 [−0.138, 0.383] 和 0.139 [0.014, 0.283]（71/72 个目标、12 人）。这是一项独立复验，不与 F5 确认性估计合并。</p>')
    parts.append(fig("qwen_external__reference_controllability.png"))
    parts.append('<div class="takeaway">跨模型扩展增强了“特征选择性”的外部线索，但不同接口与模型的差别不能被解释为某个单一内部机制。</div></section>')

    parts.append(f'''<section id="vowel-control"><div class="eyebrow">12｜10 月独立扩展：局部元音可控性</div><h2>“重建”之外，局部元音线索也能部分传递</h2><p>F5 的 EH 和 IH 五点轨迹斜率分别为 <b>{val(f5eh)} {interval(f5eh)}</b>（48 个目标、12 人）与 <b>{val(f5ih)} {interval(f5ih)}</b>（33 个目标、11 人）。Qwen 两格分别为 {val(qeh)} {interval(qeh)}（48/12）和 {val(qih, True)} {interval(qih)}（30/11），区间都跨零。</p>''')
    parts.append(fig("vowel_f5_eh__vowel_reference_response.png"))
    parts.append(fig("vowel_qwen_eh__four_cell_transfer.png"))
    parts.append('<div class="takeaway warning">这组结果要求修正过于简单的叙述：不能说“音段特征都被模型规范化”。F5 在两类已测元音上出现部分声学传递；差别具有模型与条件依赖性。四格模型关联差仍属探索性。</div></section>')

    parts.append('<section id="measurement"><div class="eyebrow">13｜测量边界与后续复核</div><h2>“56/72 没变”依赖我们怎样定义停顿</h2><p>冻结 RMS 低能段检测器给出的声学停顿 RCI 为 0.067，并有 56/72 个零端点变化；后来用 −35 dBFS 跨边界低能段重测，同批目标得到 RCI 0.287 [0.128, 0.462]，零变化为 10/72。MFA 词间隔 RCI 0.211 可复算。不同检测器回答的是不同操作定义，不能把任何一个零计数当作“完全没有时间变化”。</p>')
    parts.append(fig("timing_reaudit__full_boundary_diagnostics.png"))
    parts.append('<p>另一次 10 月 22 日五点元音复分析得到 EH→AE 平均轨迹位移 +0.898 [0.450, 1.503]（35 对、11 人），与冻结中点正方向一致，但动态形状改变未被确立，也不替换主 DID。</p></section>')

    parts.append('''<section id="synthesis"><div class="eyebrow">14｜当前科学故事</div><h2>选择性保留：一条有证据、也有边界的主线</h2><div class="cols"><div class="box teal"><h3>目前支持</h3><ul><li>不同特征的自然保留图谱不同；ECAPA 仅是身份代理。</li><li>F5 参考 F0 范围干预产生强而稳定的输出响应。</li><li>等帧局部时间响应比 F0 弱，并随检测定义改变。</li><li>EH→AE 有匹配的规范方向声学位移。</li><li>局部元音线索在 F5 两个已测对立中可部分传递。</li></ul></div><div class="box ochre"><h3>尚不能推出</h3><ul><li>所有二语口音、元音、辅音或架构都如此。</li><li>声学移动等于听者感知到音类纠正。</li><li>某个模型在所有维度总体最优。</li><li>系统内部有独立的 F0、时间、音段通道。</li><li>朗读语料结果可直接外推到自发对话。</li></ul></div></div><div class="takeaway">可以把“参考证据、目标文本与模型先验共同影响重建”作为解释假说；正式陈述应始终落在已测输出与干预响应上。</div></section>''')

    atlas_by_group = [
        ("最终确认实验：补充个体与对照图", ["final__speaker_trait_heatmap.png"]),
        ("动态元音：说话人和元音细节", ["dynamic__f5_speaker_dynamic_heatmap.png", "dynamic__trajectory_delta_by_vowel.png"]),
        ("F5 EH 局部干预：斜率与三类特征对照", ["vowel_f5_eh__vowel_speaker_slopes.png", "vowel_f5_eh__selective_transfer_summary.png"]),
        ("Qwen IH 与 F5 IH：复验过程", ["vowel_qwen_ih__ih_reference_response.png", "vowel_qwen_ih__ih_speaker_slopes.png", "vowel_qwen_ih__ih_pointwise_f1_f2_slopes.png", "vowel_qwen_ih__qwen_ih_vs_f5_eh.png", "vowel_f5_ih__f5_ih_reference_response.png", "vowel_f5_ih__f5_ih_pointwise_f1_f2.png", "vowel_f5_ih__three_cell_transfer.png"]),
        ("Qwen EH 与自然保留扩展", ["vowel_qwen_eh__qwen_eh_pointwise_f1_f2.png", "qwen_external__preservation_common_support.png"]),
        ("时间测量：频谱实例与结构匹配", ["timing_spectrogram__spectrogram_sample_01.png", "timing_spectrogram__spectrogram_sample_02.png", "timing_spectrogram__spectrogram_sample_03.png", "timing_structure__structure_match_gap_rci.png"]),
    ]
    assert {x for _,xs in atlas_by_group for x in xs} == set(files) - set(MAIN)
    parts.append('<section id="atlas"><div class="eyebrow">15｜完整实验图集</div><h2>28 张原实验图，全部可在这里核对</h2><p>前面用于讲述的 10 张关键原图不重复铺陈；下方展示其余 18 张。每张都保留原始像素和来源路径，中文图注说明读法及证据边界。<a href="../reports/lab_meeting_2026_10/figure_registry.csv">下载图表来源索引</a>。</p>')
    for heading, names in atlas_by_group:
        parts.append(f'<div class="atlas-group"><h3>{escape(heading)}</h3><div class="atlas">')
        parts.extend(fig(name, compact=True) for name in names)
        parts.append('</div></div>')
    parts.append('</section>')

    parts.append('''<section id="supervisor"><div class="eyebrow">16｜请教陈老师</div><h2>下一步需要导师判断的五个问题</h2><div class="question"><strong>1．论文主线</strong>现在的跨特征结果能否把“选择性保留与重建”固定为硕士研究的核心问题，并把主动可控性作为关键检验？</div><div class="question"><strong>2．音段证据的深度</strong>EH→AE 有确认性声学结果，IH→IY 和其他对比仍不稳定；应继续增加音段对立，还是将 EH 作为代表性受控案例，重点推进跨特征比较？</div><div class="question"><strong>3．模型范围</strong>是深入 F5 的机制与可控性，保留三模型观察性背景；还是给 CosyVoice、OpenVoice 同样规模的干预？Qwen 扩展已有外部线索，但增加全模型干预成本很高。</div><div class="question"><strong>4．语言学解释的强度</strong>能否在讨论中提出“参考线索与规范语言先验共同影响输出”的解释？正式结论是否应保持为“不同声学维度的参考可控性不同”，避免推断模型内部表示？</div><div class="question"><strong>5．优先投入</strong>下一阶段最值得优先做什么：增加说话人、扩大元音对立、增加模型、完成真实听辨、深入干预，还是加强统计建模？盲听材料已准备，但目前没有听者效应结果。</div></section>''')

    parts.append('</main><footer>组会实验进展 · 2026 年 10 月 28 日 · 离线单文件 HTML，原图另存于 reports/lab_meeting_2026_10/figures/source/。</footer></body></html>')
    doc = root / "docs" / "lab_meeting_progress_2026_10.html"
    doc.write_text("\n".join(parts), encoding="utf-8")
    return doc, len(files), len(MAIN)
