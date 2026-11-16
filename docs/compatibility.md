# Are these datasets compatible?

Short answer: **the trial-level data are compatible and can be pooled** (with one
exception), but **the published model parameters are not comparable across the three
papers**. The two statements need separating carefully, because they point to
different analysis strategies.

## The four datasets side by side

| | Kool `daw paradigm` | Kool `novel paradigm` | Gillan Exp 1 / Exp 2 | Gilger (Dresden) |
|---|---|---|---|---|
| Task | Daw et al. (2011) two-step | Kool's redesign | Daw et al. (2011) two-step | Daw et al. (2011) two-step |
| First stage | 1 state, 2 options | **2 states**, 2 options | 1 state, 2 options | 1 state, 2 options |
| Transitions | 70 / 30 | **deterministic** | 70 / 30 | 70 / 30 |
| Second stage | 2 states x 2 options | 2 states x **1 action** | 2 states x 2 options | 2 states x 2 options |
| Reward | binary, 4 drifting probabilities | **scalar points −4…+5** | binary, 4 drifting probabilities | binary (20 ct), drifting |
| Drift | random walk, sigma = 0.025, bounds 0.25 / 0.75 | random walk, sigma = 2, bounds −4 / +5 | random walk, bounds 0.25 / 0.75 | random walk, bounds 0.25 / 0.75 |
| Trials | 125 (+25 practice) | 125 (+25 practice) | 200 | **201 x 3 sessions** |
| Deadline | 2000 ms / stage | 2000 ms / stage | ~2500 ms / stage | not stated |
| Setting | MTurk, jsPsych | MTurk, jsPsych | MTurk | fMRI lab, within-subject crossover |
| Subjects | 206 complete, **197 analysed** (the paper says 207 completed; one is missing from the released file) | 199 complete, **184 analysed** | **548** / **1413** analysed (649 / 1712 task files) | **98** behavioural, 88 fMRI |
| Covariates | age, gender | age, gender | age, gender, IQ, 3 or 9 questionnaires, 3 factor scores | tryptophan condition, 5-HTTLPR genotype, fMRI |
| Public? | yes, GitHub | yes, GitHub | yes, OSF | **no** |

## 1. Trial-level data: compatible

Kool's `daw paradigm`, both Gillan experiments and Gilger's dataset are **the same
task**: one first-stage state with two options, 70/30 probabilistic transitions to two
second-stage states, two options each, binary reward whose probability drifts as a
Gaussian random walk inside [0.25, 0.75]. They differ in trial count (125 / 200 / 201),
session count (1 / 1 / 3), and recording setting (online vs. scanner), but not in
structure. `data/processed/twostep_trials_harmonized.csv` puts them in one table with
one coding; see [codebook_harmonized.md](codebook_harmonized.md).

Trial count is the one thing to keep in mind when pooling: parameter estimates from
125 trials are noisier than from 200, and the within-subject design of Gilger's data
means its three sessions are not independent observations.

### The coding differences that actually bite

These are mechanical but each one silently corrupts an analysis if missed:

| | Kool | Gillan |
|---|---|---|
| Second-stage state | 1 / 2 | **2 / 3** |
| Transition | `common` = 1 / 0 | `transition` = `true` / `false` / `-1` |
| Reward | `win` in points, **−1** if incomplete | `reward` = 1 / 0 / **−1** |
| Timeout | `rt1` or `rt2` = −1 | `s1_response` or `s2_response` = −1 |
| Choice on a timeout | −1 (honest) | **stale value `2`** (dangerous) |
| Trial numbering | 0-based, practice included | 1-based, no practice trials in the file |
| First-stage choice | stimulus identity; side is separate | identity and side are redundant (options never move) |

The last row of that table is the serious one. Gillan's `s1_stim` column reads `2` on
every stage-1 timeout even though no response was made -- 1402 trials in study 1 alone,
across 366 of 649 subjects, up to 155 in a single subject. Taking that column at face
value fabricates a first-stage choice on 1.1% of trials and biases both the stay
probabilities and any model fit. Our extraction flags it and the harmonized table
blanks it.

### The one dataset that cannot be pooled

**Kool's `novel paradigm` is a different task, not a variant.** Transitions are
deterministic, the second stage has a single action, and rewards are scalar points
rather than binary outcomes. Its model-based weight `w` is therefore estimated from a
different likelihood over a different state space -- numerically it is not on the same
scale, and the paradigm's whole purpose was that model-based control pays off there
whereas it barely does in the Daw task. Kool's own analysis of it even defines the
stay-probability cells differently (first-stage-state similarity x previous reward,
rather than transition x previous reward).

It is extracted and documented here as a contrast sample -- useful for a "does this
effect depend on the paradigm" argument -- but it should never be stacked with the
others for a single model fit or a single regression. One consequence is visible
directly in the output: because every transition is common, the rare-transition stay
cells are empty and `mf_index` / `mb_index` are undefined (`nan`) for every
`kool_novel` subject. The reward x transition interaction simply does not exist in
that task.

## 2. Published parameters: not comparable

All three papers report a model-based weight. They are **three different quantities**:

| | Kool et al. (2016) | Gillan et al. (2016) | Gilger et al. (2024) |
|---|---|---|---|
| Model | Daw (2011) hybrid, 6 parameters | Otto et al. (2013) simplification, 6 parameters | Daw (2011) hybrid, **7 parameters** |
| MB measure | `w` in **[0, 1]** | `beta_MB`, **unbounded** | `omega` in [0, 1] |
| MF measure | `1 − w` (by construction) | `beta_MF = beta_MF0 + alpha * beta_MF1`, **separately estimated** | `1 − omega` |
| Learning rates | one `alpha` | one `alpha` | **two** (`alpha1`, `alpha2`) |
| Inverse temperatures | one `beta` | one per value term (3) + `beta_stage2` | **two** (`beta1`, `beta2`) |
| Eligibility trace | `lambda` in [0, 1] | **none** -- absorbed into the two MF weights | `lambda` in [0, 1] |
| Perseveration | choice **and** response stickiness | `beta_stick` (choice only) | `pi` (choice only) |
| Estimator | **MAP** with empirical priors (`mfit`), per subject | **hierarchical EM** (Huys et al. 2011), Julia | not stated in the paper |

Three things make the published numbers non-comparable:

1. **Different parameterization.** Gillan's model has no `w` at all; model-based and
   model-free strength are separate unbounded weights. A `beta_MB` of 1.5 has no
   defined relationship to a `w` of 0.4.
2. **Different estimator.** MAP with a prior shrinks estimates toward the prior mode;
   hierarchical EM shrinks them toward the group mean, which depends on the rest of
   the sample. The same subject's data fitted both ways gives different numbers even
   under the same model.
3. **Different trial counts.** 125 vs. 200 vs. 201 trials means different estimator
   variance and, with shrinkage, different amounts of it.

So a cross-dataset analysis should **not** regress on the published parameters.

Gillan et al. are themselves explicit that the two measurement routes do not give
identical answers: their Supplementary file 5A (vendored at
`sources/gillan2016/paper/elife-11305-supp5-v1.docx`) repeats their main analysis
using the full computational model instead of the stay-probability regression, and the
OCD association in experiment 1 drops from p = 0.049 to p = 0.109 while schizotypy
becomes significant in experiment 2. Same data, same hypothesis, different measurement
instrument -- so which instrument you use is a real analysis decision, not a detail.

## 3. What to do instead

Two routes, and the pipeline supports both:

### Route A -- the model-agnostic stay indices (ready now)

All three papers report, and all three datasets support, the stay-probability
analysis: a model-free learner repeats a rewarded first-stage choice regardless of
the transition; a model-based learner takes the transition into account.

`data/processed/twostep_subjects_harmonized.csv` already carries, per subject and
session, the four stay-probability cells plus

* `mf_index` -- main effect of previous reward on staying,
* `mb_index` -- previous reward x transition interaction.

These need no model and no parameterization choice, so they are comparable across
datasets as they stand. They are computed exactly as Kool's `groupanalysis.m` computes
`maineffect` and `interaction`, and `src/validate.py` checks them against the authors'
own MATLAB output to machine precision. Gillan report that this measure and their
computational fit correlate at 0.87 in their own data.

**And they do in fact line up across datasets.** Running the index over the three
Daw-type samples in this repository:

| dataset | subjects | trials | mean `mf_index` | mean `mb_index` |
|---|---|---|---|---|
| `kool_daw` | 206 | 125 | +0.128 | **+0.095** |
| `gillan_study1` | 649 | 200 | +0.240 | **+0.100** |
| `gillan_study2` | 1712 | 200 | +0.224 | **+0.093** |

Three independent samples, two labs, different years and different trial counts, and
the model-based index agrees to two decimal places. That is the empirical case for
Route A: this quantity travels across datasets. Note that the *model-free* index does
not agree nearly as well (+0.13 vs +0.22/+0.24), which is consistent with it being the
more trial-count-sensitive of the two — a reason to prefer `mb_index` when pooling
samples with different trial counts, and to include trial count as a covariate if both
are used.

The full version of Gillan's analysis is the mixed-effects logistic regression
`glmer(stay ~ reward * transition * predictor + (reward * transition | subject))`,
which the harmonized trial table feeds directly (filter on `usable_for_stay == 1`).

### Route B -- refit one model to all of it

Because the trial data harmonizes, the clean way to compare parameters is to fit **one**
model with **one** estimator to every dataset. `s2_choice_global` is already in the
1–4 coding that hBayesDM's `ts_par7` expects, which is the same 7-parameter Daw (2011)
model Gilger et al. used -- so refitting `ts_par7` across datasets would also put
Marina's analysis on the same footing as Max's published estimates. See the mapping
table at the end of [codebook_harmonized.md](codebook_harmonized.md).

This is not part of the current pipeline; the harmonized table is built to feed it.

## 4. Practical notes on sample definitions

* **Kool**: the analysed sample is "fewer than 25 missed trials out of 125" (>20%),
  which is `groupdata.i` -- 197 of 206 (daw) and 184 of 199 (novel). The `analysed`
  column reproduces it.
* **Gillan**: the task folders hold more subjects than the papers analyse (649 vs. 548;
  1712 vs. 1413). Every self-report ID has a task file, so **the self-report table
  defines the analysed sample**; `in_selfreport` / `analysed` marks it. Gillan do not
  apply a timeout-based exclusion, so if you want a criterion matched to Kool's you
  have to impose it yourself -- `n_timeouts` is in the subject table, and
  `docs/validation_report.md` reports how many subjects a 20% rule would remove in
  each dataset.
* **Gillan study 1 vs. study 2** were separate samples of task-naive subjects; the
  validation report states whether any IDs appear in both.
* **Gilger** is within-subject: 98 subjects x 3 tryptophan sessions. Any pooled
  analysis has to model subject as a random effect rather than treating the three
  sessions as independent.

## 5. Questionnaire compatibility

Only Gillan's datasets carry psychiatric self-report. Usefully, `weights.csv` is the
full 209-item x 3-factor scoring matrix for Anxious-Depression, Compulsive Behaviour
and Intrusive Thought, and Social Withdrawal. `src/validate.py` confirms the scoring
recipe -- z-score the items, dot with the weights, standardise -- against the published
factor scores at **r = 0.9992** for all three factors (see
[codebook_gillan.md](codebook_gillan.md) for why it is not exact). **The same three dimensions can therefore be scored in any new sample
that administers the same items** -- which is the route to relating Marina's own data
to the Gillan dimensions without refitting a factor model. One caveat when doing that:
item 13 of the SDS was mis-worded in Gillan's own administration (see
[codebook_gillan.md](codebook_gillan.md)), so a new sample using the correct wording
is not strictly scoring the same item. The authors report the effect is negligible
(factor scores correlate at r > 0.999 with and without that item).

Kool's datasets carry only age and gender. Gilger's carries tryptophan condition,
5-HTTLPR genotype and fMRI, but no psychiatric questionnaires.
