# Codebook: the harmonized tables

Produced by `python -m src.harmonize` from the per-dataset extractions. The point of
this layer is that the same quantity has a different name, a different coding and a
different missing-data convention in each source; here they all become one schema, so
a single analysis or model fit can run across datasets.

Two files:

* `data/processed/twostep_trials_harmonized.csv` -- one row per trial
* `data/processed/twostep_subjects_harmonized.csv` -- one row per subject and session

## What this layer changes relative to the raw data

| | decision |
|---|---|
| Practice trials | **dropped** (Kool's 25 per subject), as the authors do |
| Trial numbering | renumbered **1…N** per subject and session; the raw files are 0-based (Kool) or 1-based (Gillan) |
| Second-stage state | recoded to **1/2** everywhere (Gillan's raw files use 2/3) |
| Missing values | every unobserved field is an **empty cell**, never a sentinel. Kool's `-1` and Gillan's `-1` are both translated, and the stale `s1_stim`/`s2_stim` values Gillan leaves on timed-out trials are blanked |
| Reward | `reward` is **always binary 0/1**; the raw magnitude stays in `reward_points` (Kool novel: −4…+5) |
| Option index | `s2_choice_global` = `(s2_state − 1) * 2 + s2_choice`, i.e. 1–4, which is the coding hBayesDM's `ts_par7` calls `level2_choice` |

`dataset` is one of `kool_daw`, `kool_novel`, `gillan_study1`, `gillan_study2`,
`gilger`. **`kool_novel` is present but must not be pooled with the others** -- see
[compatibility.md](compatibility.md).

## `twostep_trials_harmonized.csv`

| column | type | meaning |
|---|---|---|
| `dataset` | string | source dataset, as above |
| `subject_id` | string | ID as used in the source |
| `session` | int | 1 everywhere except Gilger (1–3 tryptophan conditions) |
| `condition` | string | within-subject condition label; empty except for Gilger, where it names that session's tryptophan level (depletion / balanced / loading) |
| `trial` | int | 1…N within subject and session, practice excluded |
| `s1_state` | int | first-stage state; always 1 except `kool_novel` (1/2) |
| `s1_choice` | int | chosen first-stage stimulus **identity**, not the side. 1/2, or 1–4 in `kool_novel` (3/4 when `s1_state` = 2). Empty on a stage-1 timeout |
| `s1_response_side` | string | `left` / `right` where recorded; empty for Gilger if unavailable |
| `s1_rt_ms` | int | first-stage reaction time |
| `transition_common` | int | 1 = common (70%), 0 = rare (30%). Always 1 in `kool_novel` (deterministic). Empty on a stage-1 timeout |
| `s2_state` | int | second-stage state, 1 or 2 |
| `s2_choice` | int | chosen second-stage option within the state, 1 or 2. **Always empty in `kool_novel`**, which has a single second-stage action |
| `s2_choice_global` | int | 1–4, `(s2_state − 1) * 2 + s2_choice`; empty in `kool_novel` |
| `s2_rt_ms` | int | second-stage reaction time |
| `reward` | int | 1 = rewarded, 0 = not. Empty if the trial was not completed |
| `reward_points` | number | raw outcome magnitude: 0/1 for the binary tasks, −4…+5 for `kool_novel` |
| `p_reward_1…4` | float | current drifting reward **probability** of second-stage option 1–4, indexed as `s2_choice_global`. Empty in `kool_novel` |
| `reward_value_1…2` | int | `kool_novel` only: current drifting **point value** of each second-stage state |
| `timeout` | int | 1 = the subject failed to respond at one or both stages |
| `prev_reward` | int | `reward` of the preceding trial; empty on the first trial |
| `prev_transition_common` | int | `transition_common` of the preceding trial |
| `prev_s1_choice` | int | `s1_choice` of the preceding trial |
| `stay` | int | 1 = repeated the previous first-stage choice; empty when not computable |
| `usable_for_stay` | int | 1 = this trial **and** the one before it were both answered, i.e. the trial enters the stay-probability analysis. This is the filter Kool, Gillan and Daw all apply |

`p_reward_*` and `reward_value_*` are the values in force **on that trial**, so the
outcome of trial *t* is governed by `p_reward_<s2_choice_global>` of trial *t*.

## `twostep_subjects_harmonized.csv`

One row per `(dataset, subject_id, session)`.

| column | meaning |
|---|---|
| `dataset`, `subject_id`, `session` | key |
| `condition` | the session's condition label (Gilger only) |
| `n_trials`, `n_timeouts` | counts after dropping practice trials |
| `analysed` | 1 if the subject is in the source's own analysed sample: fewer than 25 missed trials for Kool (`groupdata.i`), presence in the self-report table for Gillan |
| `reward_rate` | proportion of answered trials rewarded |
| `age`, `gender`, `gender_raw`, `iq` | demographics; `gender` is normalised to `f` / `m`, `gender_raw` keeps the source coding |
| `stay_prob_rewarded_common` | P(stay \| previous trial rewarded, common transition) |
| `stay_prob_rewarded_rare` | P(stay \| rewarded, rare) |
| `stay_prob_unrewarded_common` | P(stay \| unrewarded, common) |
| `stay_prob_unrewarded_rare` | P(stay \| unrewarded, rare) |
| `n_stay_trials` | trials entering those four cells |
| `mf_index` | **model-free index**: main effect of previous reward on staying, `(rc + rr) − (uc + ur)` |
| `mb_index` | **model-based index**: reward x transition interaction, `(rc + ur) − (rr + uc)` |
| `oci_total`, `sds_total`, `stai_total`, `audit_total`, `eat_total`, `bis_total`, `scz_total`, `aes_total`, `lsas_total` | Gillan questionnaire totals (study 1 has only OCI, SDS, STAI) |
| `factor_anxious_depression` | Gillan study 2 `Factor1` (AD) |
| `factor_compulsivity_intrusive_thought` | Gillan study 2 `Factor2` (CIT) |
| `factor_social_withdrawal` | Gillan study 2 `Factor3` (SW) |
| `kool_inverse_temperature`, `kool_learning_rate`, `kool_eligibility_trace_decay`, `kool_mixing_weight`, `kool_choice_stickiness`, `kool_response_stickiness` | the authors' own MAP fits of the full hybrid model (variant 10), Kool subjects only |

`mf_index` and `mb_index` are computed exactly as Kool's `groupanalysis.m` computes
`maineffect` and `interaction`, which is why `src/validate.py` can check them against
the authors' own output to machine precision. They are **undefined (`nan`) for
`kool_novel`**: its transitions are deterministic, so the two rare-transition cells
are empty and the interaction does not exist. **They are the measure to use for
cross-dataset comparison**, because they need no model fit and therefore no
parameterization choice.

## Feeding a model fit

The trial table is laid out so that a common refit needs no further recoding. For
hBayesDM's `ts_par7`, filter to one Daw-type dataset and map:

| hBayesDM | column |
|---|---|
| `subjID` | `subject_id` |
| `level1_choice` | `s1_choice` |
| `level2_choice` | `s2_choice_global` |
| `reward` | `reward` |

dropping rows where `timeout == 1`. Note that `ts_par7` infers the transition
structure from the choice-state pairing, so no transition column is needed; our
`transition_common` is still the right thing for the stay-probability regression.
