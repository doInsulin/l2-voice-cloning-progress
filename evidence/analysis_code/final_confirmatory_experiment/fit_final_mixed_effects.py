"""Crossed speaker/target random-intercept REML on complete common support."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research/.acoustic_deps"))
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.stats import norm

MODELS = ("f5_tts", "cosyvoice2", "openvoice_v2")
FAMILIES = ("identity", "segmental", "rhythm", "prosody")
PRIMARY = {"identity": "ecapa_cosine_distance", "segmental": "vowel_median_nds_log_f1_f2",
           "rhythm": "word_boundary_gap_mean_s", "prosody": "f0_contour_rmse_st"}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = []
    for r in read(HERE / "preservation_normalized_long.csv"):
        if r["metric"] != PRIMARY.get(r["trait_family"]) or r["three_model_common_support"] != "1":
            continue
        try:
            nds = float(r["nds"])
        except (ValueError, TypeError):
            continue
        if math.isfinite(nds) and nds >= 0:
            rows.append({**r, "nds_numeric": nds})
    keys = {}
    for r in rows:
        keys.setdefault(r["target_id"], set()).add((r["model"], r["trait_family"]))
    required = {(m, f) for m in MODELS for f in FAMILIES}
    complete = {target for target, available in keys.items() if available == required}
    rows = [r for r in rows if r["target_id"] in complete]
    if len(complete) < 20 or len({r["speaker"] for r in rows}) < 8:
        raise RuntimeError("Insufficient complete crossed-model/trait support for mixed model")
    n = len(rows)
    terms = ["Intercept", "model:cosyvoice2", "model:openvoice_v2",
             "trait:segmental", "trait:rhythm", "trait:prosody"] + \
            [f"model:{model}:trait:{family}" for model in MODELS[1:] for family in FAMILIES[1:]]
    x = np.zeros((n, len(terms)), dtype=float)
    speakers = sorted({r["speaker"] for r in rows})
    targets = sorted(complete)
    sp_index = {s: i for i, s in enumerate(speakers)}
    target_index = {t: i for i, t in enumerate(targets)}
    z = np.zeros((n, len(speakers)+len(targets)), dtype=float)
    y = np.zeros(n, dtype=float)
    for i, r in enumerate(rows):
        model, family = r["model"], r["trait_family"]
        x[i, 0] = 1
        if model != MODELS[0]:
            x[i, terms.index(f"model:{model}")] = 1
        if family != FAMILIES[0]:
            x[i, terms.index(f"trait:{family}")] = 1
        if model != MODELS[0] and family != FAMILIES[0]:
            x[i, terms.index(f"model:{model}:trait:{family}")] = 1
        z[i, sp_index[r["speaker"]]] = 1
        z[i, len(speakers)+target_index[r["target_id"]]] = 1
        y[i] = math.log1p(r["nds_numeric"])
    p = x.shape[1]
    if np.linalg.matrix_rank(x) != p:
        raise RuntimeError("Mixed-model design rank deficient")

    def solve(log_variance: np.ndarray, details: bool = False):
        speaker_var, target_var, residual_var = np.exp(log_variance)
        root = np.r_[np.full(len(speakers), math.sqrt(speaker_var)),
                     np.full(len(targets), math.sqrt(target_var))]
        u = z * root
        core = np.eye(u.shape[1]) + (u.T @ u)/residual_var
        try:
            factor = cho_factor(core, check_finite=False)
        except np.linalg.LinAlgError:
            return (math.inf, None) if details else math.inf
        logdet_v = n*math.log(residual_var) + 2*float(np.log(np.diag(factor[0])).sum())
        def inv_v(v: np.ndarray) -> np.ndarray:
            return v/residual_var - u @ cho_solve(factor, u.T @ v, check_finite=False)/(residual_var**2)
        inv_x, inv_y = inv_v(x), inv_v(y)
        xx = x.T @ inv_x
        try:
            factor_x = cho_factor(xx, check_finite=False)
            beta = cho_solve(factor_x, x.T @ inv_y, check_finite=False)
        except np.linalg.LinAlgError:
            return (math.inf, None) if details else math.inf
        residual = y - x @ beta
        quadratic = float(residual @ inv_v(residual))
        logdet_x = 2*float(np.log(np.diag(factor_x[0])).sum())
        objective = .5*(logdet_v + logdet_x + quadratic + (n-p)*math.log(2*math.pi))
        if details:
            covariance = cho_solve(factor_x, np.eye(p), check_finite=False)
            return objective, (beta, covariance, speaker_var, target_var, residual_var)
        return objective

    variance = float(np.var(y, ddof=1))
    initial = np.log([max(variance*.1, 1e-4), max(variance*.1, 1e-4), max(variance*.8, 1e-4)])
    opt = minimize(solve, initial, method="L-BFGS-B", bounds=[(-15, 8)]*3,
                   options={"maxiter": 250, "ftol": 1e-10})
    objective, fit = solve(opt.x, details=True)
    if fit is None or not math.isfinite(objective):
        raise RuntimeError("Crossed REML failed")
    beta, covariance, speaker_var, target_var, residual_var = fit
    output = []
    def contrast(name: str, vector: np.ndarray, family: str = "", comparison: str = "") -> None:
        estimate = float(vector @ beta)
        se = math.sqrt(max(float(vector @ covariance @ vector), 0))
        zvalue = estimate/se if se > 0 else math.nan
        output.append({"effect": name, "trait_family": family, "comparison": comparison,
                       "estimate_log1p_nds": estimate, "standard_error_wald": se,
                       "ci_low_95_wald": estimate-1.96*se,
                       "ci_high_95_wald": estimate+1.96*se,
                       "p_wald_two_sided": 2*norm.sf(abs(zvalue)) if math.isfinite(zvalue) else "",
                       "n_targets": len(complete), "n_speakers": len(speakers),
                       "n_rows": n, "model": "crossed_speaker_target_random_intercepts_REML"})
    for i, term in enumerate(terms):
        vector = np.zeros(p); vector[i] = 1
        contrast(term, vector)
    for family in FAMILIES:
        for model in MODELS[1:]:
            vector = np.zeros(p)
            vector[terms.index(f"model:{model}")] = 1
            if family != "identity":
                vector[terms.index(f"model:{model}:trait:{family}")] = 1
            contrast(f"{model}_minus_f5_in_{family}", vector, family, f"{model}-f5_tts")
    write(HERE / "mixed_effects_results.csv", output)
    meta = {"status": "PASS" if opt.success else "OPTIMIZER_NOT_CONVERGED", "objective_reml": objective,
            "optimizer_message": str(opt.message), "n_rows": n, "n_targets": len(complete),
            "n_speakers": len(speakers), "speaker_random_intercept_variance": speaker_var,
            "target_random_intercept_variance": target_var,
            "residual_variance": residual_var,
            "outcome": "log1p(NDS)", "trait_primary_metrics": PRIMARY,
            "uncertainty": "conditional Wald SE; variance component uncertainty not included"}
    (HERE / "mixed_effects_model_audit.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
