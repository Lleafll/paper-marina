"""Placeholder for the Gilger et al. (2024) Dresden dataset.

Gilger MD, Hellrung L, Neukam PT, Kroemer NB, Nebe S, Pooseh S, Deza-Lougovski YI &
Smolka MN (2024). "Arbitration between model-free and model-based control is not
affected by transient changes in tonic serotonin levels." J Psychopharmacol
38:178-187. doi:10.1177/02698811231216325

This data is NOT public: the article has no data-availability statement and its only
supplement is a PDF. It has to come from the authors. See docs/codebook_gilger.md for
the format the paper implies and for the identification of the model used.

To wire it up once the files arrive:
  1. put them under sources/gilger2024/data/
  2. implement `write_trials()` below so it emits data/processed/gilger_trials.csv
     with the columns listed in EXPECTED_COLUMNS
  3. src/harmonize.py already picks that file up automatically if it exists
"""

from __future__ import annotations

import sys

from .paths import GILGER_DATA, PROCESSED

# What harmonize.py expects from data/processed/gilger_trials.csv. Sessions are the
# three tryptophan conditions; the paper reports 98 participants x 3 sessions x 201
# trials of the standard Daw (2011) two-step task.
EXPECTED_COLUMNS = [
    "subject_id",
    "session",             # 1..3; also record which tryptophan condition each is
    "condition",           # depletion / balanced / loading
    "trial",               # 1..201
    "s1_choice",           # 1 or 2 (first-stage stimulus identity)
    "s1_rt_ms",
    "transition_common",   # 1 = common (70%), 0 = rare (30%)
    "s2_state",            # 1 or 2
    "s2_choice",           # 1 or 2 within the second-stage state
    "s2_rt_ms",
    "reward",              # 1 or 0
    "p_reward_1", "p_reward_2", "p_reward_3", "p_reward_4",
    "timeout",             # 1 if the trial was missed
]

MESSAGE = f"""\
Gilger et al. (2024) data is not publicly available, so there is nothing to extract.

  Expected input:  {GILGER_DATA}/  (currently {{state}})
  Expected output: {PROCESSED}/gilger_trials.csv
  Target columns:  {", ".join(EXPECTED_COLUMNS)}

Request from the authors (Smolka lab, TU Dresden):
  - trial-level task data for all 98 participants x 3 sessions
  - the model-fitting script, to confirm the estimator behind the published
    7-parameter estimates (alpha1, alpha2, beta1, beta2, lambda, omega, pi)

See docs/codebook_gilger.md.
"""


def write_trials() -> None:
    raise NotImplementedError(
        "No parser yet: Gilger et al. (2024) data has not been obtained. "
        "See docs/codebook_gilger.md.")


def main() -> int:
    present = sorted(p.name for p in GILGER_DATA.glob("*")) if GILGER_DATA.exists() else []
    print(MESSAGE.format(state=f"{len(present)} file(s): {present}" if present else "empty"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
