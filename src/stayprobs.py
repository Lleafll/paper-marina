"""Model-agnostic model-based / model-free indices from first-stage stay behaviour.

This is the one measure that is directly comparable across all the two-step datasets
here, because it needs no model fit and no parameterization choice: a model-free
learner repeats a rewarded first-stage choice regardless of the transition, while a
model-based learner takes the transition into account, so

    MF index = main effect of previous reward on staying
    MB index = previous reward x previous transition interaction

The implementation deliberately mirrors Kool's `groupanalysis.m` so that the numbers
can be checked against the authors' own output (see validate.py):

    stay_prob[0] = P(stay | previous trial rewarded, common transition)
    stay_prob[1] = P(stay | previous trial rewarded, rare transition)
    stay_prob[2] = P(stay | previous trial unrewarded, common transition)
    stay_prob[3] = P(stay | previous trial unrewarded, rare transition)
    mf_index = (sp[0] + sp[1]) - (sp[2] + sp[3])
    mb_index = (sp[0] + sp[3]) - (sp[1] + sp[2])

(The header comment in groupanalysis.m labels the stayprobs columns
"[common_x_win common_x_loss rare_x_win rare_x_loss]", but its code computes the
order used above. The code is what produced the published figures.)
"""

from __future__ import annotations

import math

CELL_NAMES = [
    "stay_prob_rewarded_common",
    "stay_prob_rewarded_rare",
    "stay_prob_unrewarded_common",
    "stay_prob_unrewarded_rare",
]


def stay_indices(choice1, reward, common, missed) -> dict[str, float]:
    """Compute the four stay probabilities plus the MF and MB indices.

    All four arguments are per-trial sequences for a single subject and session, in
    trial order. `missed` flags trials the subject failed to respond on; a trial is
    used only if neither it nor the trial before it was missed, which also drops the
    first trial (it has no predecessor).
    """
    cells: list[list[int]] = [[], [], [], []]
    for t in range(1, len(choice1)):
        if missed[t] or missed[t - 1]:
            continue
        stay = int(choice1[t] == choice1[t - 1])
        slot = (0 if reward[t - 1] else 2) + (0 if common[t - 1] else 1)
        cells[slot].append(stay)

    out = {name: (sum(c) / len(c) if c else math.nan)
           for name, c in zip(CELL_NAMES, cells)}
    out["n_stay_trials"] = sum(len(c) for c in cells)
    sp = [out[name] for name in CELL_NAMES]
    out["mf_index"] = (sp[0] + sp[1]) - (sp[2] + sp[3])
    out["mb_index"] = (sp[0] + sp[3]) - (sp[1] + sp[2])
    return out
