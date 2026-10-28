"""Build the offline meeting report and figures from packaged frozen result snapshots.

Run: python reports/lab_meeting_2026_10/build_report.py
Only the Python standard library is required. Do not edit numerical constants in the HTML;
the builder reads the CSV/JSON files in source_results/.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE / "source_results"
FIG = HERE / "figures"
DOC = ROOT / "docs" / "lab_meeting_progress_2026_10.html"
FIG.mkdir(exist_ok=True)
DOC.parent.mkdir(exist_ok=True)


def rows(name):
    with (SRC / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def obj(name):
    return json.loads((SRC / name).read_text(encoding="utf-8"))


def one(items, **filters):
    found = [r for r in items if all(r.get(k) == v for k, v in filters.items())]
    if len(found) != 1:
        raise ValueError(f"Expected one row for {filters}, found {len(found)}")
    return found[0]


def n(x):
    return float(x) if x not in (None, "") else None


def fmt(x, d=3):
    return f"{x:.{d}f}"


def esc(x):
    return html.escape(str(x), quote=True)


def svg_base(w, h, inner, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
            '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202124} .small{font-size:14px} .tick{font-size:13px;fill:#555} .label{font-size:17px;font-weight:600} .title{font-size:22px;font-weight:700} .muted{fill:#60646a} .axis{stroke:#45494d;stroke-width:1.5} .grid{stroke:#e0e2e4;stroke-width:1} .ink{fill:#202124} .teal{fill:#147d78} .gold{fill:#a3691b}</style>'
            + inner + '</svg>')


def write_svg(name, w, h, inner, title, desc):
    (FIG / name).write_text(svg_base(w, h, inner, title, desc), encoding="utf-8")


qc_data = obj("final_confirmatory_summary.json")
qc = rows("preservation_sample_qc.csv")
pres = rows("preservation_model_trait_summary.csv")
ctrl = rows("reference_controllability_summary.csv")
seg = rows("segmental_confirmatory_results.csv")
f0rows = rows("f0_controllability_results.csv")
timingrows = rows("timing_controllability_results.csv")
expert = obj("expert_audibility_results.json")
vowel = rows("vowel_transfer_overall_results.csv")
qf0 = obj("qwen_f0_summary.json")["mode_summaries"]
qtiming = rows("qwen_timing_summary.csv")
qeh = rows("qwen_eh_overall_results.csv")
fih = rows("f5_ih_overall_results.csv")
qih = rows("qwen_ih_overall_results.csv")
factorial = rows("qwen_factorial_contrasts.csv")
dynamic = rows("dynamic_reconstruction_overall_results.csv")
reverse_vowel = obj("iy_to_ih_results.json")
rhoticity = obj("rhoticity_results.json")
reference_density = rows("reference_condition_effects.csv")

model_names = {"f5_tts": "F5-TTS", "cosyvoice2": "CosyVoice 2", "openvoice_v2": "OpenVoice V2"}
trait_names = {"identity": "ECAPA identity distance", "segmental": "Vowel F1/F2 distance", "rhythm": "MFA word-gap distance", "prosody": "F0 contour distance"}

summary = []
def add(experiment, trait, model, speakers, count, metric, estimate, lo, hi, interpretation, status, source):
    summary.append({"experiment": experiment, "trait": trait, "model": model, "speakers": int(speakers),
                    "n": int(count), "metric": metric, "estimate": n(estimate), "ci_lower": n(lo),
                    "ci_upper": n(hi), "interpretation": interpretation,
                    "exploratory_or_confirmatory": status, "source_file": source})

for r in pres:
    if r["support"] != "common_support":
        continue
    add("Three-model natural preservation", r["trait_family"], model_names[r["model"]],
        r["n_speakers"], r["n_target_metric_rows"], "speaker_equal_NDS",
        r["speaker_equal_mean_nds"], r["speaker_cluster_bootstrap_95ci_low"],
        r["speaker_cluster_bootstrap_95ci_high"], "Lower distortion relative to held-out natural variability; metric families are not one scale.",
        "confirmatory", "source_results/preservation_model_trait_summary.csv")

for metric, trait, interpretation in [
    ("F0_range", "estimated voiced-F0 range", "Strong positive output response to a fixed-target reference range intervention."),
    ("local_word_gap", "MFA local word-boundary gap", "Small, heterogeneous output response under equal-frame reference redistribution."),
    ("local_acoustic_pause", "RMS-detected low-energy interval", "Very small detector-specific response; zero does not imply no timing change.")]:
    r = one(ctrl, outcome=metric, level="overall_speaker_equal")
    add("Final reference intervention", trait, "F5-TTS", r["n_speakers"], r["n_targets"], "speaker_equal_RCI",
        r["estimate_rci"], r["ci_low_95"], r["ci_high_95"], interpretation, "confirmatory",
        "source_results/reference_controllability_summary.csv")

r = one(ctrl, outcome="F0_range_minus_local_word_gap_RCI", level="paired_speaker_difference")
add("Final paired intervention contrast", "F0 range minus local gap", "F5-TTS", r["n_speakers"], 12,
    "paired_speaker_RCI_difference", r["estimate_rci"], r["ci_low_95"], r["ci_high_95"],
    "F0 response exceeds local-gap response among 12 shared speakers; n counts speakers.", "confirmatory",
    "source_results/reference_controllability_summary.csv")

for contrast, status, interpretation in [
    ("EH_TO_AE", "confirmatory", "Positive matched acoustic movement toward canonical EH, not a listener phone label."),
    ("IH_TO_IY", "confirmatory_boundary", "Direction uncertain in the expanded final sample; CI spans zero.")]:
    r = one(seg, contrast=contrast, level="overall_speaker_equal", feature="did_delta_p")
    add("Final matched segmental reconstruction", contrast.replace("_TO_", "→"), "F5-TTS", r["n_speakers"], r["n_pairs"],
        "canonical_axis_matched_DID", r["estimate"], r["ci_low_95"], r["ci_high_95"], interpretation,
        status, "source_results/segmental_confirmatory_results.csv")

add("Informed expert audibility", "EH→AE target words", "F5-TTS", 6, expert["n"], "both_experts_closer_count",
    expert["both_1_rate"] * expert["n"], None, None, "Both informed experts judged 10 of 18 clones closer to EH; descriptive selected items.",
    "supporting_exploratory", "source_results/expert_audibility_results.json")
add("Informed expert audibility", "EH→AE target words", "F5-TTS", 6, expert["n"], "Cohens_kappa",
    expert["cohens_kappa"], None, None, "Expert agreement on the selected items; not blind phoneme classification.",
    "supporting_exploratory", "source_results/expert_audibility_results.json")

r = reverse_vowel["reverse_did_delta_p"]
add("Earlier boundary contrast", "IY→IH reverse direction", "F5-TTS", r["n_speakers"], r["n_pairs"],
    "old_axis_matched_DID", r["estimate"], r["ci_low"], r["ci_high"],
    "Interval crosses zero on the previously defined IH→IY axis; does not support bidirectional canonical attraction.",
    "exploratory_boundary", "source_results/iy_to_ih_results.json")
r = one(rhoticity["effects"], metric="delta_f3_minus_f2_hz")
add("Earlier boundary contrast", "post-vocalic rhoticity", "F5-TTS", r["n_speakers"], r["n_pairs"],
    "F3_minus_F2_matched_DID_Hz", r["estimate"], r["ci_low"], r["ci_high"],
    "Directional estimate is uncertain; no confirmed cross-mechanism rhotic correction.",
    "exploratory_boundary", "source_results/rhoticity_results.json")
r = one(reference_density, metric="delta_p", estimand="error", contrast="ERROR_RICH_minus_PHONE_FREE")
add("Earlier reference-density test", "error-rich versus phone-free reference", "F5-TTS", r["speakers"], r["common_pairs"],
    "canonical_axis_error_delta_p", r["estimate_equal_speaker_mean"], r["ci_low"], r["ci_high"],
    "Mixed speaker directions and interval crossing zero; not an RCI intervention.",
    "exploratory_boundary", "source_results/reference_condition_effects.csv")

for srcname, model, trait, data in [
    ("vowel_transfer_overall_results.csv", "F5-TTS", "EH–AE local vowel", vowel),
    ("f5_ih_overall_results.csv", "F5-TTS", "IH–IY local vowel", fih),
    ("qwen_eh_overall_results.csv", "Qwen3-TTS 0.6B", "EH–AE local vowel", qeh),
    ("qwen_ih_overall_results.csv", "Qwen3-TTS 0.6B", "IH–IY local vowel", qih)]:
    r = one(data, outcome="generated_axis_p")
    add("October local-vowel reference intervention", trait, model, r["n_speakers"], r["n_targets"],
        "five_point_reference_output_slope", r["estimate"], r["ci_low_95"], r["ci_high_95"],
        "Partial or uncertain local acoustic transfer under a vowel-specific manipulation; not the final EH matched DID.",
        "exploratory_extension", "source_results/" + srcname)

for r in qf0:
    add("October Qwen external replication", "estimated voiced-F0 range", "Qwen3-TTS 0.6B / " + r["mode"],
        r["n_speakers"], r["n_valid"], "speaker_equal_RCI", r["estimate"], r["ci_low"], r["ci_high"],
        "Positive reference-range response in a separate model and input mode.", "independent_extension",
        "source_results/qwen_f0_summary.json")
for r in qtiming:
    add("October Qwen external replication", r["outcome"], "Qwen3-TTS 0.6B / " + r["mode"],
        r["n_speakers"], r["n_valid"], "speaker_equal_RCI", r["estimate"], r["ci_low"], r["ci_high"],
        "Local timing response under the equal-frame reference manipulation; detector-dependent.",
        "independent_extension", "source_results/qwen_timing_summary.csv")

r = one(factorial, contrast="average_model_effect")
add("October 2×2 local-vowel comparison", "mean F5 minus Qwen slope", "F5-TTS vs Qwen3-TTS", r["n_common_speakers"], 11,
    "paired_speaker_slope_difference", r["estimate"], r["ci_low_95"], r["ci_high_95"],
    "Limited exploratory model-associated difference; stimulation and multiplicity constrain inference.",
    "exploratory_extension", "source_results/qwen_factorial_contrasts.csv")
r = one(dynamic, support="strict", subset="all_speakers", contrast="EH_TO_AE", metric="translation_p")
add("October dynamic-vowel reanalysis", "EH→AE five-point mean", "F5-TTS", r["n_speakers"], r["n_pairs"],
    "five_point_canonical_axis_matched_DID", r["estimate"], r["ci_low_95"], r["ci_high_95"],
    "Exploratory trajectory reanalysis consistent with positive midpoint direction; does not replace the frozen DID.",
    "exploratory_extension", "source_results/dynamic_reconstruction_overall_results.csv")

fields = ["experiment", "trait", "model", "speakers", "n", "metric", "estimate", "ci_lower", "ci_upper",
          "interpretation", "exploratory_or_confirmatory", "source_file"]
with (HERE / "experiment_summary.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(summary)
(HERE / "experiment_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

confirm = [r for r in summary if r["exploratory_or_confirmatory"] in ("confirmatory", "confirmatory_boundary") and
           r["experiment"] != "Three-model natural preservation"]
with (HERE / "confirmatory_results.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(confirm)

qcs = []
for key, name in model_names.items():
    rr = [r for r in qc if r["model"] == key]
    qcs.append({"model": name, "generated_success": qc_data["generation_counts"][key + "_preservation"]["SUCCESS"],
                "frozen_targets": 160, "global_qc_pass": sum(r["global_qc_status"] == "PASS" for r in rr),
                "speakers": len({r["speaker"] for r in rr}), "source_file": "source_results/preservation_sample_qc.csv"})
with (HERE / "model_qc_summary.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(qcs[0])); w.writeheader(); w.writerows(qcs)

manifest = []
for p in sorted(SRC.iterdir()):
    if p.is_file() and p.name != "SHA256SUMS.csv":
        manifest.append({"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size})
with (SRC / "SHA256SUMS.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["file", "sha256", "bytes"]); w.writeheader(); w.writerows(manifest)

# QC and metric-specific support
parts = ['<text x="42" y="45" class="title">Final three-model sample flow</text>',
         '<text x="42" y="72" class="small muted">16 L2 speakers · 160 fixed targets per model · September frozen confirmation</text>']
for i, q in enumerate(qcs):
    y = 125 + i * 76
    bar = 560 * q["global_qc_pass"] / 160
    parts += [f'<text x="42" y="{y+22}" class="label">{esc(q["model"])}</text>',
              f'<rect x="290" y="{y}" width="560" height="27" fill="#ededed"/>',
              f'<rect x="290" y="{y}" width="{bar:.1f}" height="27" fill="#147d78"/>',
              f'<text x="865" y="{y+21}" class="small">QC {q["global_qc_pass"]}/160</text>']
parts += ['<text x="42" y="374" class="small muted">Metric-specific three-model common support: identity 156 · vowel 144 · word gap 156 · F0 contour 110 (15 speakers)</text>',
          '<text x="42" y="400" class="small muted">All 480 preservation generations succeeded; QC and metric extraction define the analysis denominators.</text>']
write_svg("qc_and_support.svg", 1050, 435, ''.join(parts), "Final model QC and support", "QC PASS counts from final frozen preservation sample; support varies by measured trait.")

# NDS profile: panels avoid suggesting one common perceptual scale.
parts = ['<text x="36" y="42" class="title">Natural preservation differs by measured trait</text>',
         '<text x="36" y="68" class="small muted">Speaker-equal NDS with 95% speaker-bootstrap CI; lower means less distortion within each metric family.</text>']
trait_keys = ["identity", "segmental", "rhythm", "prosody"]
for j, trait in enumerate(trait_keys):
    x0 = 40 + (j % 2) * 525; y0 = 105 + (j // 2) * 295
    parts += [f'<text x="{x0}" y="{y0}" class="label">{esc(trait_names[trait])}</text>',
              f'<text x="{x0}" y="{y0+25}" class="small muted">Own natural-variation scale; NDS = 1 marked</text>']
    for k, model in enumerate(model_names):
        r = one(pres, model=model, trait_family=trait, support="common_support")
        val, lo, hi = [n(r[c]) for c in ("speaker_equal_mean_nds", "speaker_cluster_bootstrap_95ci_low", "speaker_cluster_bootstrap_95ci_high")]
        yy = y0 + 65 + k * 53; sx=lambda v: x0 + 162 + v / 4.2 * 262
        parts += [f'<text x="{x0}" y="{yy+5}" class="small">{esc(model_names[model])}</text>',
                  f'<line x1="{sx(1):.1f}" x2="{sx(1):.1f}" y1="{y0+44}" y2="{y0+197}" stroke="#999" stroke-dasharray="4 4"/>',
                  f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{yy}" y2="{yy}" stroke="#202124" stroke-width="3"/>',
                  f'<circle cx="{sx(val):.1f}" cy="{yy}" r="6" fill="#147d78"/>',
                  f'<text x="{x0+430}" y="{yy+5}" class="small">{val:.3f}</text>']
    parts += [f'<line x1="{x0+162}" x2="{x0+424}" y1="{y0+221}" y2="{y0+221}" class="axis"/>',
              f'<text x="{x0+162}" y="{y0+242}" class="tick">0</text><text x="{x0+285}" y="{y0+242}" class="tick">2</text><text x="{x0+410}" y="{y0+242}" class="tick">4 NDS</text>']
write_svg("trait_profile.svg", 1080, 705, ''.join(parts), "Four separate natural preservation profiles", "The NDS panels use different acoustic distance constructions and cannot be combined into a model ranking.")

# Segmental DID forest
parts = ['<text x="40" y="46" class="title">Matched vowel reconstruction: canonical direction</text>',
         '<text x="40" y="75" class="small muted">F5-TTS · positive DID means greater error-token movement toward the speaker-specific canonical endpoint than correct controls</text>']
for i, contrast in enumerate(["EH_TO_AE", "IH_TO_IY"]):
    r=one(seg,contrast=contrast,level="overall_speaker_equal",feature="did_delta_p")
    v,lo,hi=[n(r[k]) for k in ("estimate","ci_low_95","ci_high_95")]
    y=162+i*105; sx=lambda x: 420+(x+0.5)/2.2*390
    parts += [f'<text x="42" y="{y+5}" class="label">{esc(contrast.replace("_TO_","→"))}</text>',
              f'<text x="42" y="{y+29}" class="small muted">{r["n_pairs"]} pairs · {r["n_speakers"]} speakers</text>',
              f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y}" y2="{y}" stroke="#202124" stroke-width="3"/>',
              f'<circle cx="{sx(v):.1f}" cy="{y}" r="7" fill="#147d78"/>',
              f'<text x="830" y="{y+5}" class="small">{v:+.3f} [{lo:.3f}, {hi:.3f}]</text>']
parts += [f'<line x1="{420+0.5/2.2*390:.1f}" x2="{420+0.5/2.2*390:.1f}" y1="112" y2="290" stroke="#999" stroke-dasharray="5 5"/>',
          '<text x="42" y="345" class="small muted">Zero line indicates no matched directional difference. EH supports acoustic reconstruction; IH remains uncertain.</text>']
write_svg("segmental_did.svg",1050,380,''.join(parts),"Final segmental matched DID","EH positive with CI above zero; IH confidence interval crosses zero.")

# F0 output change from actual complete triplets.
valid=[r for r in f0rows if r["technical_status"]=="PASS"]
parts=['<text x="42" y="46" class="title">F0 range responds to reference intervention</text>',
       '<text x="42" y="72" class="small muted">F5-TTS · each point is one fixed-target compressed→expanded triplet (95 valid / 96 frozen; 16 speakers)</text>']
x0,y0,w,h=115,110,620,310
for tick in range(0,11,2):
    xx=x0+tick/10*w; yy=y0+h-tick/10*h
    parts += [f'<line x1="{xx}" x2="{xx}" y1="{y0}" y2="{y0+h}" class="grid"/>',
              f'<line x1="{x0}" x2="{x0+w}" y1="{yy}" y2="{yy}" class="grid"/>',
              f'<text x="{xx-8}" y="{y0+h+23}" class="tick">{tick}</text>',
              f'<text x="{x0-35}" y="{yy+5}" class="tick">{tick}</text>']
parts += [f'<line x1="{x0}" x2="{x0+w}" y1="{y0+h}" y2="{y0+h}" class="axis"/>',
          f'<line x1="{x0}" x2="{x0}" y1="{y0}" y2="{y0+h}" class="axis"/>']
for r in valid:
    x=n(r["delta_reference_expanded_minus_compressed_st"]); y=n(r["delta_output_expanded_minus_compressed_st"])
    cx=x0+max(0,min(10,x))/10*w; cy=y0+h-max(0,min(10,y))/10*h
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.8" fill="#147d78" opacity=".56"/>')
parts += [f'<text x="{x0+135}" y="{y0+h+58}" class="small">Reference F0-range change (semitones)</text>',
          '<text x="29" y="299" transform="rotate(-90 29 299)" class="small">Output F0-range change (semitones)</text>',
          '<text x="790" y="175" class="label">RCI 0.727</text>',
          '<text x="790" y="200" class="small">95% CI 0.662–0.794</text>',
          '<text x="790" y="237" class="small">91/95 strictly monotonic</text>',
          '<text x="790" y="262" class="small">16/16 speaker means positive</text>',
          '<text x="42" y="525" class="small muted">RCI is the speaker-equal output/reference end-contrast ratio, not the slope of this pooled scatter.</text>']
write_svg("f0_response.svg",1050,555,''.join(parts),"F0 range reference and output changes","95 fixed-target triplets; the summary RCI is speaker equal, whereas dots show individual triplets.")

# RCI comparison forest.
parts=['<text x="40" y="44" class="title">Reference controllability differs by trait</text>',
       '<text x="40" y="72" class="small muted">F5-TTS frozen confirmation · speaker-equal RCI and 95% speaker-bootstrap CI</text>']
for i,(metric,label) in enumerate([("F0_range","Estimated F0 range"),("local_word_gap","MFA word gap"),("local_acoustic_pause","RMS low-energy interval")]):
    r=one(ctrl,outcome=metric,level="overall_speaker_equal")
    v,lo,hi=[n(r[k]) for k in ("estimate_rci","ci_low_95","ci_high_95")]
    y=145+i*93; sx=lambda x: 365+x*470
    parts += [f'<text x="42" y="{y+5}" class="label">{esc(label)}</text>',
              f'<text x="42" y="{y+29}" class="small muted">{r["n_targets"]} triplets · {r["n_speakers"]} speakers</text>',
              f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y}" y2="{y}" stroke="#202124" stroke-width="3"/>',
              f'<circle cx="{sx(v):.1f}" cy="{y}" r="7" fill="{("#147d78" if i==0 else "#a3691b")}"/>',
              f'<text x="860" y="{y+5}" class="small">{v:.3f}</text>']
parts += ['<line x1="365" x2="835" y1="386" y2="386" class="axis"/>']
for x in [0,.25,.5,.75,1]:
    parts.append(f'<text x="{365+x*470-8:.1f}" y="410" class="tick">{x:g}</text>')
parts += ['<text x="42" y="447" class="small muted">Within the 12 shared speakers, F0 minus word-gap RCI = +0.543 [0.359, 0.707].</text>']
write_svg("rci_contrast.svg",1050,480,''.join(parts),"F0 versus local timing RCI","F0 response is larger than local word gap and detector-specific low-energy interval response.")

# October vowel 2x2.
vowel_cells=[("F5-TTS · EH–AE",one(vowel,outcome="generated_axis_p")),
             ("Qwen3 · EH–AE",one(qeh,outcome="generated_axis_p")),
             ("F5-TTS · IH–IY",one(fih,outcome="generated_axis_p")),
             ("Qwen3 · IH–IY",one(qih,outcome="generated_axis_p"))]
parts=['<text x="40" y="44" class="title">October extension: local vowel cues can transfer partially</text>',
       '<text x="40" y="72" class="small muted">Five-point trajectory reference→output slope; exploratory model × contrast comparison</text>']
sx=lambda x: 485+(x+0.3)/0.75*365
parts += [f'<line x1="{sx(0):.1f}" x2="{sx(0):.1f}" y1="110" y2="414" stroke="#999" stroke-dasharray="4 4"/>']
for i,(label,r) in enumerate(vowel_cells):
    y=138+i*76; v,lo,hi=[n(r[k]) for k in ("estimate","ci_low_95","ci_high_95")]
    parts += [f'<text x="42" y="{y+5}" class="label">{esc(label)}</text>',
              f'<text x="42" y="{y+28}" class="small muted">{r["n_targets"]} targets · {r["n_speakers"]} speakers</text>',
              f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y}" y2="{y}" stroke="#202124" stroke-width="3"/>',
              f'<circle cx="{sx(v):.1f}" cy="{y}" r="7" fill="{("#147d78" if "F5" in label else "#a3691b")}"/>',
              f'<text x="870" y="{y+5}" class="small">{v:+.3f}</text>']
parts += ['<text x="42" y="472" class="small muted">These local vowel slopes are distinct from natural preservation NDS and the matched canonical-axis DID.</text>']
write_svg("local_vowel_transfer.svg",1050,505,''.join(parts),"Exploratory local vowel reference transfer","F5 has positive partial acoustic transfer in two tested contrasts; Qwen results are uncertain.")

# Conceptual synthesis: no assertion of internal channels.
parts=['<text x="42" y="45" class="title">Selective preservation is an output pattern</text>',
       '<rect x="42" y="98" width="210" height="75" fill="#ededed" stroke="#202124"/>',
       '<text x="64" y="129" class="label">Reference speech</text><text x="64" y="152" class="small">+ target text</text>',
       '<line x1="252" x2="323" y1="135" y2="135" stroke="#202124" stroke-width="2"/>',
       '<polygon points="323,135 314,129 314,141" fill="#202124"/>',
       '<rect x="323" y="98" width="210" height="75" fill="#ededed" stroke="#202124"/>',
       '<text x="349" y="129" class="label">Cloning system</text><text x="349" y="152" class="small">fixed target / conditions</text>']
labels=[("ECAPA identity cues","retained imperfectly"),("F0 range","strong reference response"),("Internal word gap","weak reference response"),("EH→AE vowel shift","canonical-direction acoustic movement"),("Local vowel cues","partial, model-dependent response")]
for i,(lab,out) in enumerate(labels):
    y=64+i*67
    parts += [f'<line x1="533" x2="594" y1="135" y2="{y+44}" stroke="#777" stroke-width="1.5"/>',
              f'<rect x="594" y="{y+13}" width="414" height="53" fill="{("#e1f0ee" if i in (1,4) else "#f4f4f4")}"/>',
              f'<text x="608" y="{y+35}" class="label">{esc(lab)}</text>',
              f'<text x="608" y="{y+56}" class="small muted">{esc(out)}</text>']
write_svg("selective_preservation.svg",1050,485,''.join(parts),"Selective preservation synthesis","Separate output-level patterns for identity proxy, F0, local timing, and vowel realization.")

from render_chinese_report import render
report_path, source_figure_count, main_figure_count = render(ROOT, HERE, summary)
print(f'Wrote {report_path}')
print(f'{len(summary)} summary records; {len(confirm)} confirmatory/boundary records; {len(qcs)} QC rows; {source_figure_count} original experiment figures ({main_figure_count} in main narrative)')
