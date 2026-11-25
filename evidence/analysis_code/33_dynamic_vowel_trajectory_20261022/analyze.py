"""Frozen-data trajectory geometry and matched canonical reconstruction follow-up.

One vowel is one 2 x 5 outcome. No synthesis, alignment, or thesis files are edited.
Run with Python 3.12 and PYTHONPATH=research/.acoustic_deps.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DYN = ROOT / "research/27_dynamic_vowel_analysis"
FINAL = ROOT / "research/final_confirmatory_experiment"
sys.path[:0] = [str(ROOT / "research/.acoustic_deps"), str(DYN), str(ROOT / "research/07_auto_qc")]
import numpy as np
import parselmouth
from extract_dynamic_vowels import extract_track, dynamic_flags

SEED = 20261022
MODELS = ("f5_tts", "cosyvoice2", "openvoice_v2")
VOWELS = ("EH", "AE", "IH", "IY")
GEOMETRY = ("position", "direction", "path_length", "curvature", "temporal_asymmetry")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    if not rows:
        raise RuntimeError(f"empty {name}")
    with (HERE / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs():
    freeze = json.loads((HERE / "design_freeze.json").read_text(encoding="utf-8"))
    for name, digest in freeze["inputs_sha256"].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError(f"frozen input drift: {name}")


def vec(row, prefix):
    a = np.array([json.loads(row[prefix + "log_f1"]), json.loads(row[prefix + "log_f2"])], float).T
    if a.shape != (5, 2) or not np.isfinite(a).all():
        raise ValueError("invalid 2D trajectory")
    return a


def geometry(a):
    step = np.linalg.norm(np.diff(a, axis=0), axis=1)
    path = float(step.sum())
    return {
        "position": a.mean(axis=0),
        "direction": a[4] - a[0],
        "path_length": path,
        "curvature": a[2] - (a[0] + a[4]) / 2,
        "temporal_asymmetry": float((step[:2].sum() - step[2:].sum()) / path) if path > 1e-9 else 0.0,
    }


def geometry_error(a, b):
    ga, gb = geometry(a), geometry(b)
    return {k: (float(np.linalg.norm(ga[k] - gb[k]) / math.sqrt(2)) if k in
                ("position", "direction", "curvature") else abs(float(ga[k] - gb[k]))) for k in GEOMETRY}


def rng_for(*parts):
    digest = hashlib.sha256("|".join(map(str, (SEED, *parts))).encode()).hexdigest()
    return np.random.default_rng(int(digest[:16], 16) % 2**32)


def speaker_boot(values, *parts, draws=8000):
    x = np.asarray(values, float)
    if len(x) < 2:
        return float(x.mean()), math.nan, math.nan
    rng = rng_for(*parts)
    samples = x[rng.integers(0, len(x), (draws, len(x)))].mean(axis=1)
    return float(x.mean()), *map(float, np.quantile(samples, [.025, .975]))


def step1():
    dynamic = read(DYN / "dynamic_vowel_tokens.csv")
    natural = read(DYN / "natural_dynamic_vowels.csv")
    by_natural = defaultdict(list)
    for row in natural:
        by_natural[row["speaker"], row["phone"]].append(row)
    scales, scale_rows = {}, []
    for support, qc in (("strict", "strict_dynamic_qc_pass"), ("track", "track_qc_pass")):
        for (speaker, phone), rows in sorted(by_natural.items()):
            good = [r for r in rows if r[qc] == "1"]
            candidates = []
            for i, left in enumerate(good):
                for right in good[i + 1:]:
                    if left["utterance_id"] != right["utterance_id"]:
                        key = hashlib.sha256(f"{SEED}|{support}|{speaker}|{phone}|{left['token_id']}|{right['token_id']}".encode()).hexdigest()
                        candidates.append((key, left, right))
            values = defaultdict(list)
            for _, left, right in sorted(candidates, key=lambda z: z[0])[:200]:
                for metric, value in geometry_error(vec(left, ""), vec(right, "")).items():
                    values[metric].append(value)
            for metric in GEOMETRY:
                scale = float(np.median(values[metric])) if len(values[metric]) >= 20 else math.nan
                if not math.isfinite(scale) or scale <= 1e-9:
                    raise RuntimeError(f"unestimable natural scale: {support}/{speaker}/{phone}/{metric}")
                scales[support, speaker, phone, metric] = scale
                scale_rows.append(dict(support=support, speaker=speaker, phone=phone, metric=metric,
                                       n_tokens=len(good), n_pairs=len(values[metric]), natural_median=scale))
    write("geometry_natural_scales.csv", scale_rows)
    common = {}
    for support, qc in (("strict", "strict_dynamic_qc_pass"), ("track", "track_qc_pass")):
        groups = defaultdict(set)
        for row in dynamic:
            if row[qc] == "1":
                groups[row["token_key"]].add(row["model"])
        common[support] = {k for k, models in groups.items() if set(MODELS) <= models}
    token_rows = []
    for row in dynamic:
        if row["track_qc_pass"] != "1":
            continue
        error = geometry_error(vec(row, "original_"), vec(row, "clone_"))
        out = {k: row[k] for k in ("model", "speaker", "phone", "target_id", "token_key")}
        out.update(strict_qc=row["strict_dynamic_qc_pass"], common_strict=int(row["token_key"] in common["strict"]),
                   common_track=int(row["token_key"] in common["track"]))
        for metric in GEOMETRY:
            out[metric + "_error"] = error[metric]
            for support in ("strict", "track"):
                out[metric + "_nds_" + support] = error[metric] / scales[support, row["speaker"], row["phone"], metric]
        token_rows.append(out)
    write("geometry_token_metrics.csv", token_rows)
    supports = {
        "common_strict": ("strict", lambda r: r["common_strict"] == 1),
        "model_strict": ("strict", lambda r: r["strict_qc"] == "1"),
        "common_track": ("track", lambda r: r["common_track"] == 1),
    }
    speakers, overall = [], []
    for support, (scale_set, selector) in supports.items():
        for model in MODELS:
            for phone in (*VOWELS, "ALL_EQUAL_VOWELS"):
                for metric in GEOMETRY:
                    grouped = defaultdict(list)
                    for row in token_rows:
                        if row["model"] == model and selector(row) and (phone == "ALL_EQUAL_VOWELS" or row["phone"] == phone):
                            grouped[row["speaker"], row["phone"]].append(float(row[metric + "_nds_" + scale_set]))
                    estimates, n_tokens = [], 0
                    for speaker in sorted({k[0] for k in grouped}):
                        ph = VOWELS if phone == "ALL_EQUAL_VOWELS" else (phone,)
                        if not all(grouped[speaker, p] for p in ph):
                            continue
                        value = float(np.mean([np.mean(grouped[speaker, p]) for p in ph]))
                        count = sum(len(grouped[speaker, p]) for p in ph)
                        speakers.append(dict(support=support, model=model, phone=phone, metric=metric,
                                             speaker=speaker, estimate_nds=value, n_tokens=count))
                        estimates.append(value)
                        n_tokens += count
                    if estimates:
                        mean, low, high = speaker_boot(estimates, "geometry", support, model, phone, metric)
                        overall.append(dict(support=support, model=model, phone=phone, metric=metric,
                                            estimate_nds=mean, ci_low_95=low, ci_high_95=high,
                                            n_speakers=len(estimates), n_tokens=n_tokens))
    write("geometry_speaker_results.csv", speakers)
    write("geometry_overall_results.csv", overall)
    return {"common_strict_tokens": len(common["strict"]), "common_track_tokens": len(common["track"]),
            "geometry_rows": len(token_rows)}


def extract_segmental():
    frozen = [json.loads(s) for s in (FINAL / "features/f5_tts_segmental_tokens.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    pair_qc = {r["pair_id"]: r for r in read(FINAL / "segmental_pair_qc.csv")}
    ceilings = json.loads((FINAL / "final_formant_ceilings.json").read_text(encoding="utf-8"))["speakers"]
    sex = {r["speaker"]: r["sex"] for r in read(ROOT / "research/01_corpus_audit/l2_arctic_token_inventory.csv")}
    seen, rows = {}, []
    parity_max = 0.0
    for row in frozen:
        if pair_qc[row["pair_id"]]["pair_status"] != "PASS":
            continue
        out = {k: row[k] for k in ("contrast", "speaker", "pair_id", "role", "target_id")}
        reasons = []
        for part, path_key, interval_key, frozen_key in (
            ("original", "original_wav", "original_interval", "original_formants"),
            ("clone", "output_wav", "clone_interval", "clone_formants"),
        ):
            path = row[path_key]
            if path not in seen:
                seen[path] = parselmouth.Sound(path)
            sound = seen[path]
            interval = row[interval_key]["phone"]
            phone = {"start": float(interval[0]), "end": float(interval[1])}
            ceiling = int(ceilings[row["speaker"]]["chosen_ceiling_hz"])
            f1, f2, check = extract_track(sound, phone, ceiling, sex[row["speaker"]], {})
            duration = phone["end"] - phone["start"]
            bounds = phone["start"] >= 0 and phone["end"] <= sound.duration
            track, strict = dynamic_flags(f1, f2, duration, check, bounds)
            out[part + "_log_f1"] = json.dumps([math.log(x) if x else None for x in f1])
            out[part + "_log_f2"] = json.dumps([math.log(x) if x else None for x in f2])
            out[part + "_duration_s"] = duration
            out[part + "_track_qc"] = int(not track)
            out[part + "_strict_qc"] = int(not strict)
            out[part + "_reasons"] = "|".join(strict)
            reasons += [part + ":" + x for x in strict]
            for name, vals in (("f1", f1), ("f2", f2)):
                prior = row[frozen_key]["midpoint_" + name + "_hz"]
                if vals[2] is None or abs(vals[2] - prior) > 1e-6:
                    raise RuntimeError(f"frozen midpoint mismatch {row['target_id']}/{part}/{name}: {vals[2]} vs {prior}")
                parity_max = max(parity_max, abs(vals[2] - prior))
        out["pair_strict_qc"] = int(out["original_strict_qc"] and out["clone_strict_qc"])
        out["pair_track_qc"] = int(out["original_track_qc"] and out["clone_track_qc"])
        rows.append(out)
    if len(rows) != 190:
        raise RuntimeError(f"expected 190 frozen PASS pair tokens, got {len(rows)}")
    write("reconstruction_token_trajectories.csv", rows)
    return rows, parity_max


def projected(a, axis):
    d = np.array(axis["axis_vector"], float)
    return (a @ d) / float(d @ d)


def step2():
    rows, parity_max = extract_segmental()
    axes = json.loads((FINAL / "natural_vowel_axes.json").read_text(encoding="utf-8"))["axes"]
    by_pair = defaultdict(dict)
    for row in rows:
        by_pair[row["pair_id"]][row["role"]] = row
    pair_rows = []
    for pair_id, roles in sorted(by_pair.items()):
        if set(roles) != {"ERROR", "CONTROL"}:
            raise RuntimeError(f"incomplete frozen pair {pair_id}")
        e, c = roles["ERROR"], roles["CONTROL"]
        base = dict(contrast=e["contrast"], speaker=e["speaker"], pair_id=pair_id,
                    strict_qc=int(e["pair_strict_qc"] and c["pair_strict_qc"]),
                    track_qc=int(e["pair_track_qc"] and c["pair_track_qc"]))
        if base["track_qc"]:
            delta = (vec(e, "clone_") - vec(e, "original_")) - (vec(c, "clone_") - vec(c, "original_"))
            mean = delta.mean(axis=0)
            dynamic = delta - mean
            axis = axes[e["speaker"]][e["contrast"]]
            p = projected(delta, axis)
            base.update(did_log_trajectory=json.dumps(delta.tolist()),
                        translation_f1=mean[0], translation_f2=mean[1],
                        translation_p=float(p.mean()),
                        dynamic_rms=float(np.sqrt(np.mean(dynamic**2))),
                        early_late_p=float((p[3] + p[4] - p[0] - p[1]) / 2),
                        curvature_p=float(p[2] - (p[0] + p[4]) / 2))
        pair_rows.append(base)
    write("reconstruction_pair_results.csv", pair_rows)
    speaker_rows, overall, trajectory_rows = [], [], []
    for support, field in (("strict", "strict_qc"), ("track", "track_qc")):
        for contrast in ("EH_TO_AE", "IH_TO_IY"):
            selected = [r for r in pair_rows if r["contrast"] == contrast and r[field] == 1]
            counts = defaultdict(int)
            for r in selected:
                counts[r["speaker"]] += 1
            for subset in ("all_speakers", "ge4_pairs"):
                group = defaultdict(list)
                for row in selected:
                    if subset == "all_speakers" or counts[row["speaker"]] >= 4:
                        group[row["speaker"]].append(row)
                if len(group) < 2:
                    continue
                speaker_vectors = []
                for speaker, items in sorted(group.items()):
                    d = np.mean([np.array(json.loads(r["did_log_trajectory"]), float) for r in items], axis=0)
                    axis = axes[speaker][contrast]
                    p = projected(d, axis)
                    mean = d.mean(axis=0)
                    rec = dict(support=support, subset=subset, contrast=contrast, speaker=speaker,
                               n_pairs=len(items), translation_p=float(p.mean()),
                               early_late_p=float((p[3] + p[4] - p[0] - p[1]) / 2),
                               curvature_p=float(p[2] - (p[0] + p[4]) / 2),
                               dynamic_rms=float(np.sqrt(np.mean((d - mean)**2))),
                               translation_f1=float(mean[0]), translation_f2=float(mean[1]),
                               mean_did_trajectory=json.dumps(d.tolist()))
                    speaker_rows.append(rec)
                    speaker_vectors.append(d)
                relevant = [r for r in speaker_rows if r["support"] == support and r["subset"] == subset and r["contrast"] == contrast]
                raw = np.array([np.array(json.loads(r["mean_did_trajectory"]), float) for r in relevant])
                p_tracks = np.array([projected(raw[i], axes[r["speaker"]][contrast])
                                     for i, r in enumerate(relevant)])
                rng = rng_for("trajectory_envelope", support, subset, contrast)
                selections = rng.integers(0, len(relevant), size=(8000, len(relevant)))
                mean_raw, mean_p = raw.mean(axis=0), p_tracks.mean(axis=0)
                raw_boot = raw[selections].mean(axis=1)
                p_boot = p_tracks[selections].mean(axis=1)
                # One maximum-deviation band covers the full five-point function
                # for each outcome, not five separate pointwise tests.
                raw_radius = float(np.quantile(np.max(np.abs(raw_boot - mean_raw), axis=(1, 2)), .95))
                p_radius = float(np.quantile(np.max(np.abs(p_boot - mean_p), axis=1), .95))
                for i, point in enumerate((20, 35, 50, 65, 80)):
                    trajectory_rows.append(dict(support=support, subset=subset, contrast=contrast,
                                                time_pct=point, n_speakers=len(relevant),
                                                n_pairs=sum(len(v) for v in group.values()),
                                                did_log_f1=float(mean_raw[i, 0]),
                                                did_log_f2=float(mean_raw[i, 1]),
                                                simultaneous_log_band_radius=raw_radius,
                                                did_canonical_p=float(mean_p[i]),
                                                simultaneous_p_band_radius=p_radius))
                for metric in ("translation_p", "early_late_p", "curvature_p", "translation_f1", "translation_f2"):
                    est, low, high = speaker_boot([r[metric] for r in relevant], "reconstruction", support, subset, contrast, metric)
                    overall.append(dict(support=support, subset=subset, contrast=contrast, metric=metric,
                                        estimate=est, ci_low_95=low, ci_high_95=high,
                                        n_speakers=len(group), n_pairs=sum(len(v) for v in group.values())))
                # Omnibus sign-flip test on the mean-centered five-point 2D DID function.
                matrix = np.array(speaker_vectors)
                matrix -= matrix.mean(axis=1, keepdims=True)
                observed = float(np.sqrt(np.mean(matrix.mean(axis=0)**2)))
                rng = rng_for("shape_signflip", support, subset, contrast)
                flips = rng.choice([-1, 1], size=(20000, len(matrix)))
                null = np.sqrt(np.mean((np.einsum("bs,sij->bij", flips, matrix) / len(matrix))**2, axis=(1, 2)))
                p_value = float((1 + np.count_nonzero(null >= observed)) / (len(null) + 1))
                overall.append(dict(support=support, subset=subset, contrast=contrast, metric="dynamic_shape_omnibus_rms",
                                    estimate=observed, ci_low_95="", ci_high_95="", signflip_p=p_value,
                                    n_speakers=len(group), n_pairs=sum(len(v) for v in group.values())))
    write("reconstruction_speaker_results.csv", speaker_rows)
    write("reconstruction_overall_results.csv", overall)
    write("reconstruction_trajectory_summary.csv", trajectory_rows)
    counts = defaultdict(lambda: defaultdict(int))
    for r in pair_rows:
        counts[r["contrast"]]["frozen_pass"] += 1
        counts[r["contrast"]]["dynamic_strict"] += r["strict_qc"]
        counts[r["contrast"]]["dynamic_track"] += r["track_qc"]
    return {"midpoint_max_abs_hz": parity_max, "pair_counts": counts,
            "n_segmental_tokens": len(rows)}


def main():
    verify_inputs()
    a = step1()
    b = step2()
    output = {"status": "COMPUTED_NEEDS_INTERPRETIVE_REVIEW", "step1": a, "step2": b,
              "output_sha256": {p.name: sha(p) for p in sorted(HERE.glob("*.csv"))}}
    (HERE / "analysis_audit.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
