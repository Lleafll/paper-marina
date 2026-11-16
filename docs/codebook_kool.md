# Codebook: Kool, Cushman & Gershman (2016)

**Paper.** Kool W, Cushman FA, Gershman SJ (2016). *When Does Model-Based Control Pay
Off?* PLoS Computational Biology 12(8):e1005090.
<https://doi.org/10.1371/journal.pcbi.1005090>

**Data.** <https://github.com/wkool/tradeoffs>, vendored whole at commit
`6f849e13` under [`sources/kool2016/repo/`](../sources/kool2016/repo) — including the
authors' own MATLAB scripts, which are the provenance for everything below. The paper
and its six supplementary files are in
[`sources/kool2016/paper/`](../sources/kool2016/paper).

**Where the column names come from.** `data.mat` is a bare MATLAB cell array with no
header. The mapping below is taken verbatim from the repository's own
`make_raw_data.m` — in this repo at
`sources/kool2016/repo/data/daw paradigm/make_raw_data.m` — which is the authoritative
source: it is the script the authors ran to produce every published number. `src/validate.py` checks the mapping by
recomputing per-subject statistics and comparing them against `groupdata.mat`, the
output of the authors' `groupanalysis.m`.

## Two different paradigms

| | `daw paradigm` | `novel paradigm` |
|---|---|---|
| Task | the standard Daw et al. (2011) two-step task | Kool et al.'s redesign, built so that model-based control actually increases reward |
| First stage | 1 state, 2 options | **2 states**, 2 options each |
| Transitions | 70% common / 30% rare | **deterministic (100%)** |
| Second stage | 2 states x 2 options | 2 states x **1 action** (press space) |
| Reward | binary, 4 drifting probabilities | **scalar points, −4…+5** |
| Drift | Gaussian random walk, sigma = 0.025, reflecting bounds 0.25 / 0.75 | Gaussian random walk, sigma = 2, reflecting bounds −4 / +5 |
| Trials | 25 practice + 125 experimental | 25 practice + 125 experimental |
| Deadline | 2000 ms per stage | 2000 ms per stage |
| Subjects in `data.mat` | **206** (all with 150 rows) | 200 (all with 150 rows) |
| Subjects in `subinfo.mat` | 206 | **199** -- one subject present in `data.mat` is absent here and is therefore dropped, exactly as `make_raw_data.m` does |
| Analysed (`groupdata.i`) | **197** | **184** |

Only the `daw paradigm` dataset is comparable with Gillan and Gilger. See
[compatibility.md](compatibility.md).

Two counts worth noting before quoting sample sizes:

* The paper reports that **207** participants completed the Daw paradigm and 199 the
  novel one (406 recruited in total). `daw/data.mat` holds **206** subjects, so one of
  the 207 is not in the released file. The analysed figure of 197 follows from the
  206 that are there.
* `novel/data.mat` holds 200 subjects but `novel/subinfo.mat` only 199, which matches
  the paper. `make_raw_data.m` iterates over `subinfo`, so that extra subject is
  dropped; our extraction reproduces that.

Task parameters, verified against the paper's Methods: 70% / 30% transitions; second-
stage reward probabilities initialised at 0.25 / 0.75 for one pair of aliens and
0.4 / 0.6 for the other, then drifting as a Gaussian random walk (sigma = 0.025) with
reflecting bounds at 0.25 and 0.75; 2000 ms response deadline at each stage ("F"/"J"
keys at the first stage, space bar at the second); no deadline during training; a new
set of reward walks per participant.

## `daw paradigm/data.mat`

30,900 rows x **20** columns. Column 1 is the subject ID; `make_raw_data.m` reads
columns 2–19 into the 18 variables below. Column 20 is a trailing jsPsych
`time_elapsed` that the authors' code never reads -- it is carried through here for
completeness.

| col | name | meaning |
|---|---|---|
| 1 | `subject_id` | anonymised ID, `subject_1` … `subject_206` |
| 2 | `stim_1_left` | first-stage stimulus presented on the left |
| 3 | `stim_1_right` | first-stage stimulus presented on the right |
| 4 | `rt1` | first-stage reaction time, ms; **−1 = timeout** |
| 5 | `choice1` | first-stage choice as a **stimulus identity**, not a side (compare with `stim_1_left` to recover the side); −1 if missed |
| 6 | `stim_2_left` | second-stage stimulus presented on the left |
| 7 | `stim_2_right` | second-stage stimulus presented on the right |
| 8 | `rt2` | second-stage reaction time, ms; −1 = timeout |
| 9 | `choice2` | second-stage choice (stimulus identity); −1 if missed |
| 10 | `win` | points won at the second stage: 1 = rewarded, 0 = not, **−1 = trial not completed** |
| 11 | `state2` | second-stage state, 1 or 2; −1 if no first-stage response |
| 12 | `common` | transition type: 1 = common (70%), 0 = rare (30%); −1 if no first-stage response |
| 13 | `score` | cumulative score so far |
| 14 | `practice` | **1 = practice trial** (25 per subject; must be dropped), 0 = experimental |
| 15 | `ps1a1` | reward probability, second-stage state 1 / action 1 |
| 16 | `ps1a2` | reward probability, second-stage state 1 / action 2 |
| 17 | `ps2a1` | reward probability, second-stage state 2 / action 1 |
| 18 | `ps2a2` | reward probability, second-stage state 2 / action 2 |
| 19 | `trial` | trial number, **0-based**, restarting after the practice block |
| 20 | `time_elapsed` | ms since task start (not read by `make_raw_data.m`) |

The four probability columns are ordered by (state, action), so they line up with the
option index `(state2 - 1) * 2 + choice2` used in the harmonized table.

### Missing-data coding

A trial is "missed" iff `rt1 == -1 or rt2 == -1` (the definition in
`make_raw_data.m`). There are two distinct patterns, and only one of them loses the
first-stage choice:

| pattern | n (experimental trials) | `choice1` | `state2` / `common` | `choice2` | `win` |
|---|---|---|---|---|---|
| no first-stage response | 722 | −1 | −1 | −1 | −1 |
| responded at stage 1, timed out at stage 2 | 278 | valid | valid | −1 | −1 |

So a stage-2 timeout still yields a usable first-stage choice and transition. Kool's
own analyses nonetheless discard the whole trial, and `src/harmonize.py` keeps that
convention while preserving the distinction in the `timeout` column.

## `novel paradigm/data.mat`

30,000 rows x **15** columns; column 1 is the subject ID, columns 2–15 are read by
that folder's `make_raw_data.m`.

| col | name | meaning |
|---|---|---|
| 1 | `subject_id` | anonymised ID |
| 2 | `state1` | first-stage state, 1 or 2 |
| 3 | `stim_left` | stimulus presented on the left |
| 4 | `stim_right` | stimulus presented on the right |
| 5 | `rt1` | first-stage reaction time, ms; −1 = timeout |
| 6 | `choice1` | first-stage choice (stimulus identity): **1–2 when `state1` = 1, 3–4 when `state1` = 2**; −1 if missed |
| 7 | `rt2` | second-stage reaction time, ms; −1 = timeout |
| 8 | `points` | points won (scalar, −4…+5). **0 on a missed trial**, which is indistinguishable from a genuine zero -- use `rt1`/`rt2` to detect missing data, not `points` |
| 9 | `state2` | second-stage state, 1 or 2; −1 if no first-stage response |
| 10 | `score` | cumulative score |
| 11 | `practice` | 1 = practice trial, 0 = experimental |
| 12 | `rews1` | current point value of second-stage state 1 |
| 13 | `rews2` | current point value of second-stage state 2 |
| 14 | `trial` | trial number, 0-based |
| 15 | `time_elapsed` | ms since task start |

## `subinfo.mat`

Not documented in the repository. 206 x 5 (daw) / 199 x 5 (novel) cell array. Columns
1–3 are unambiguous; the reading of 4 and 5 below was recovered from the data and is
confirmed for every subject by `src/validate.py`:

| col | name | meaning |
|---|---|---|
| 1 | `subject_id` | matches column 1 of `data.mat` |
| 2 | `age` | years |
| 3 | `gender` | `'f'` / `'m'` |
| 4 | `final_score` | total reward over the 125 **experimental** trials -- the number of trials won (daw) or the sum of points (novel); practice trials are not counted |
| 5 | `total_time_ms` | total task duration in ms, always at least the last trial's `time_elapsed` |

**The iteration order of this file defines the subject numbering.**
`make_raw_data.m` walks `subinfo` and assigns `subdata(1..N)` in that order, so
`subject_index` in our outputs is an index into `subinfo`, which is what
`groupdata.i` and the row order of `results.mat` refer back to.

## `groupdata.mat` and `results.mat`

* `groupdata.mat` -- the output of the authors' `groupanalysis.m`. `subdata` holds all
  subjects with complete data; `i` lists the indices of the **analysed** subjects,
  i.e. those with fewer than 25 missed trials (`>20%` of 125). Also holds
  `stayprobs`, `maineffect`, `interaction`, `rewardrate`, `avg_p` (daw) /
  `avg_rew` (novel) and `missed`, one row per analysed subject. `src/validate.py`
  reproduces all of these.
* `results.mat` -- the authors' model fits via
  [mfit](https://github.com/sjgershm/mfit), as a struct array of **12 model variants**
  (the `model x stimulus-stickiness x response-stickiness` grid built in
  `mfit_wrapper.m`). Rows within each variant are ordered as
  `groupdata.subdata(groupdata.i)`.

  | variant | model | choice stickiness | response stickiness |
  |---|---|---|---|
  | 1–3 | hybrid / model-based / model-free | no | no |
  | 4–6 | hybrid / model-based / model-free | yes | no |
  | 7–9 | hybrid / model-based / model-free | no | yes |
  | **10** | **hybrid** | **yes** | **yes** |
  | 11–12 | model-based / model-free | yes | yes |

  **Variant 10 is the full hybrid model the paper reports.** Its six parameters, with
  the bounds and priors from `set_opts.m`:

  | parameter | symbol | bounds | prior |
  |---|---|---|---|
  | `inverse_temperature` | beta | [0, 20] | Gamma(4.82, 0.88) |
  | `learning_rate` | alpha | [0, 1] | flat |
  | `eligibility_trace_decay` | lambda | [0, 1] | flat |
  | `mixing_weight` | **w** | [0, 1] | flat |
  | `choice_stickiness` | pi | [−20, 20] | Normal(0.15, 1.42) |
  | `response_stickiness` | rho | [−20, 20] | Normal(0.15, 1.42) |

  Estimated by maximum a posteriori with these empirical priors (`mfit_optimize`),
  not hierarchically. `w = 1` is pure model-based, `w = 0` pure model-free.

## Outputs

| file | contents |
|---|---|
| `kool_<paradigm>_trials.csv` | one row per trial with the names above, practice trials kept and flagged, plus `subject_index` and a `missed` flag |
| `kool_<paradigm>_subjects.csv` | per subject: trial and timeout counts, `analysed` flag, reward rate, mean reward, and the `subinfo.mat` fields |
| `kool_<paradigm>_published_params.csv` | the authors' fits, all 12 variants x analysed subjects, with `subject_id` attached and per-subject `loglik`, `logpost`, `bic`, `aic` |
