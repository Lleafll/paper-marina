"""Model-free / model-based behaviour and the 7-parameter hybrid model, Gilger et al.

Neither the paper nor its supplement names or links a fitting script. What they do
specify is reproduced here:

* the stay-probability effects from the Methods (Eq. 1),

      MF effect = (p_com+ + p_rar+ - p_com- - p_rar-) / 2
      MB effect = (p_com+ - p_rar+ - p_com- + p_rar-) / 2

  where p_com+ is P(stay | previous trial rewarded, common transition) and so on;

* the hybrid model "introduced by Daw et al. (2011)" with seven parameters,
  alpha1, alpha2, lambda, omega, beta1, beta2, pi (Supplement, "Computational
  model"; the sex-differences follow-up describes the same model in its S-5):

      stage 2:  Q2(s', a2) += alpha2 * (r - Q2(s', a2))
      stage 1:  Q_MF(a1)   += alpha1 * (Q2(s', a2) - Q_MF(a1))
                              + alpha1 * lambda * (r - Q2(s', a2))
      MB:       Q_MB(a)     = 0.7 * max Q2(common state of a) + 0.3 * max Q2(other)
      choice 1: P(a) ~ exp(beta1 * [(omega * Q_MB + (1 - omega) * Q_MF)(a) + pi * rep(a)])
      choice 2: P(a) ~ exp(beta2 * Q2(s', a))

  pi sits inside the beta1 bracket, as written in the sex-differences supplement;
  the lab's pi values match this and not pi outside the bracket (Daw's own form),
  see docs/codebook_gilger.md.

  Values start at 0 and are reset at the start of each session. A trial that timed
  out at stage 1 contributes nothing and changes nothing; one that timed out at stage
  2 contributes its stage-1 choice but no update. `rep(a)` refers to the last
  first-stage choice actually made.

How the parameters were estimated is the open question, so the estimator is a
command-line choice and the result is compared against the lab's own estimates in
`final_sample/Participant characteristics.sav` (see docs/codebook_gilger.md):
plain maximum likelihood (`--prior none`), or maximum a posteriori with weak priors
(`--prior weak`: Beta(1.1, 1.1) on alpha1, alpha2, lambda, omega; Gamma(1.2, 5) on
beta1, beta2; Normal(0, 1) on pi). These priors are this module's choice, not
documented by the authors; they only keep beta from running off on sessions where
the likelihood is flat.
Parameters are optimised in an unbounded space -- logistic for alpha1, alpha2,
lambda, omega; exponential for beta1, beta2; identity for pi -- which matches the
lab's values approaching but never reaching 0 and 1.

Outputs (data/processed/):
    gilger_stay_effects.csv   per subject and session: the four stay
                              probabilities and the MF / MB effects
    gilger_model_fits_<scope>_<prior>.csv
                              per subject and session (--scope session) or per
                              subject across sessions (--scope pooled): the seven
                              parameters, negative log-likelihood, BIC
    gilger_subject_means_<prior>.csv
                              per subject: MF / MB effects and the seven
                              parameters averaged over the three tryptophan
                              sessions -- the form of the lab's own table
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize

from .paths import PROCESSED

PARAMS = ["alpha1", "alpha2", "lambda", "omega", "beta1", "beta2", "pi"]
UNIT = {"alpha1", "alpha2", "lambda", "omega"}   # logistic transform
POSITIVE = {"beta1", "beta2"}                    # exponential transform

STAY_CELLS = ["p_rew_common", "p_rew_rare", "p_unrew_common", "p_unrew_rare"]

N_STARTS = 10
SEED = 20240101


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _int(value: str):
    return int(float(value)) if value != "" else None


def load_sessions(path=PROCESSED / "gilger_trials_final_sample.csv") -> dict:
    """{subject: {session: [trial, ...]}}, trials as small tuples, in trial order.

    Each trial is (s1_choice, s2_state, s2_choice, reward, common) with None for
    anything not observed. States and choices are 0-based.
    """
    sessions: dict[str, dict[int, list]] = {}
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh):
            c1, st, c2 = _int(r["s1_choice"]), _int(r["s2_state"]), _int(r["s2_choice"])
            trial = (None if c1 is None else c1 - 1,
                     None if st is None else st - 1,
                     None if c2 is None else c2 - 1,
                     _int(r["reward"]),
                     _int(r["transition_common"]))
            sessions.setdefault(r["subject_id"], {}).setdefault(int(r["session"]), []).append(trial)
    return sessions


# ---------------------------------------------------------------------------
# Stay-probability effects (Methods, Eq. 1)
# ---------------------------------------------------------------------------

def stay_effects(trials: list) -> dict:
    """Stay probabilities after each (reward, transition) cell, and the two effects.

    A pair of consecutive trials is used when the earlier one was answered at both
    stages (so its reward and transition are known) and the later one at stage 1.
    """
    counts = [[0, 0] for _ in STAY_CELLS]   # [stays, total]
    for prev, cur in zip(trials, trials[1:]):
        if prev[2] is None or cur[0] is None:
            continue
        cell = (0 if prev[3] else 2) + (0 if prev[4] else 1)
        counts[cell][0] += prev[0] == cur[0]
        counts[cell][1] += 1
    p = [s / n if n else math.nan for s, n in counts]
    out = dict(zip(STAY_CELLS, p))
    out["mf_effect"] = (p[0] + p[1] - p[2] - p[3]) / 2
    out["mb_effect"] = (p[0] - p[1] - p[2] + p[3]) / 2
    return out


# ---------------------------------------------------------------------------
# Hybrid model
# ---------------------------------------------------------------------------

def common_state(trials: list) -> list[int]:
    """Which second-stage state is common for each first-stage choice.

    This is counterbalanced across subjects (randCWS), so it is read off the data:
    the state reached most often after each choice.
    """
    seen = [[0, 0], [0, 0]]
    for c1, st, *_ in trials:
        if c1 is not None and st is not None:
            seen[c1][st] += 1
    return [int(seen[a][1] > seen[a][0]) for a in (0, 1)]


def to_params(x) -> dict:
    out = {}
    for name, v in zip(PARAMS, x):
        if name in UNIT:
            out[name] = 1.0 / (1.0 + math.exp(-max(min(v, 30.0), -30.0)))
        elif name in POSITIVE:
            out[name] = math.exp(max(min(v, 5.0), -10.0))
        else:
            out[name] = v
    return out


def from_params(p: dict) -> np.ndarray:
    x = []
    for name in PARAMS:
        v = p[name]
        if name in UNIT:
            v = min(max(v, 1e-6), 1 - 1e-6)
            x.append(math.log(v / (1 - v)))
        elif name in POSITIVE:
            x.append(math.log(v))
        else:
            x.append(v)
    return np.array(x)


def neg_loglik(p: dict, sessions: list[list]) -> float:
    """Negative log-likelihood of all choices in the given sessions."""
    a1, a2, lam, w = p["alpha1"], p["alpha2"], p["lambda"], p["omega"]
    b1, b2, pi = p["beta1"], p["beta2"], p["pi"]
    nll = 0.0
    for trials in sessions:
        common = common_state(trials)
        q1 = [0.0, 0.0]
        q2 = [[0.0, 0.0], [0.0, 0.0]]
        last = None
        for c1, st, c2, r, _ in trials:
            if c1 is None:
                continue
            m = [max(q2[0]), max(q2[1])]
            qmb = [0.7 * m[common[a]] + 0.3 * m[1 - common[a]] for a in (0, 1)]
            v = [b1 * (w * qmb[a] + (1 - w) * q1[a] + (pi if last == a else 0.0))
                 for a in (0, 1)]
            nll -= v[c1] - _logsumexp2(v[0], v[1])
            last = c1
            if c2 is None:
                continue
            u = [b2 * q2[st][0], b2 * q2[st][1]]
            nll -= u[c2] - _logsumexp2(u[0], u[1])
            pe2 = r - q2[st][c2]
            q1[c1] += a1 * (q2[st][c2] - q1[c1]) + a1 * lam * pe2
            q2[st][c2] += a2 * pe2
    return nll


def _logsumexp2(x: float, y: float) -> float:
    m = x if x > y else y
    return m + math.log(math.exp(x - m) + math.exp(y - m))


def neg_log_prior(p: dict) -> float:
    """Weak priors (see module docstring), up to a constant."""
    out = 0.0
    for name in UNIT:
        v = p[name]
        out -= 0.1 * (math.log(v) + math.log(1 - v)) if 0 < v < 1 else math.inf
    for name in POSITIVE:
        out -= 0.2 * math.log(p[name]) - p[name] / 5
    out += 0.5 * p["pi"] ** 2
    return out


def fit(sessions: list[list], prior: str = "none", seed: int = SEED,
        starts: int = N_STARTS) -> dict:
    """ML or MAP fit from several random starts; the best one is kept."""
    def objective(x):
        p = to_params(x)
        return neg_loglik(p, sessions) + (neg_log_prior(p) if prior == "weak" else 0.0)

    rng = np.random.default_rng(seed)
    best = None
    for _ in range(starts):
        x0 = np.concatenate([rng.normal(0, 1.5, 4), rng.normal(1, 1, 2), rng.normal(0, 0.5, 1)])
        res = minimize(objective, x0, method="BFGS")
        if best is None or res.fun < best.fun:
            best = res
    n = sum(sum(1 + (t[2] is not None) for t in s if t[0] is not None) for s in sessions)
    out = to_params(best.x)
    out["nll"] = neg_loglik(out, sessions)
    out["bic"] = 2 * out["nll"] + len(PARAMS) * math.log(n)
    out["n_choices"] = n
    return out


def _fit_job(job):
    key, sessions, prior = job
    return key, fit(sessions, prior)


def write_subject_means(prior: str) -> None:
    """Average the stay effects and per-session fits over each subject's sessions."""
    stay: dict[str, list[dict]] = {}
    with (PROCESSED / "gilger_stay_effects.csv").open(newline="") as fh:
        for r in csv.DictReader(fh):
            stay.setdefault(r["subject_id"], []).append(r)
    fits: dict[str, list[dict]] = {}
    with (PROCESSED / f"gilger_model_fits_session_{prior}.csv").open(newline="") as fh:
        for r in csv.DictReader(fh):
            fits.setdefault(r["subject_id"], []).append(r)

    fields = ["subject_id", "n_sessions"] + STAY_CELLS + ["mf_effect", "mb_effect"] + PARAMS
    path = PROCESSED / f"gilger_subject_means_{prior}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for subject in sorted(fits):
            row = {"subject_id": subject, "n_sessions": len(fits[subject])}
            for name in STAY_CELLS + ["mf_effect", "mb_effect"]:
                row[name] = float(np.mean([float(r[name]) for r in stay[subject]]))
            for name in PARAMS:
                row[name] = float(np.mean([float(r[name]) for r in fits[subject]]))
            w.writerow(row)
    print(f"  {path.name}: {len(fits)} subjects, means over sessions")


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scope", choices=["session", "pooled"], default="session",
                    help="fit each session separately, or one parameter set per "
                         "subject across its three sessions")
    ap.add_argument("--prior", choices=["none", "weak"], default="weak",
                    help="maximum likelihood, or MAP with weak priors")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args(argv)

    data = load_sessions()
    print(f"Gilger final sample: {len(data)} subjects")

    path = PROCESSED / "gilger_stay_effects.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["subject_id", "session"] + STAY_CELLS
                           + ["mf_effect", "mb_effect"])
        w.writeheader()
        for subject, by_session in sorted(data.items()):
            for session, trials in sorted(by_session.items()):
                w.writerow({"subject_id": subject, "session": session, **stay_effects(trials)})
    print(f"  {path.name}: {sum(len(s) for s in data.values())} subject-sessions")

    if args.scope == "session":
        jobs = [((s, k), [t], args.prior) for s, by in sorted(data.items())
                for k, t in sorted(by.items())]
    else:
        jobs = [((s, ""), [by[k] for k in sorted(by)], args.prior)
                for s, by in sorted(data.items())]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_fit_job, jobs))

    path = PROCESSED / f"gilger_model_fits_{args.scope}_{args.prior}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["subject_id", "session"] + PARAMS
                           + ["nll", "bic", "n_choices"])
        w.writeheader()
        for (subject, session), res in results:
            w.writerow({"subject_id": subject, "session": session, **res})
    print(f"  {path.name}: {len(results)} fits ({args.scope}, prior: {args.prior})")
    if args.scope == "session":
        write_subject_means(args.prior)
    return 0


if __name__ == "__main__":
    sys.exit(main())
