# Codebook: Gillan et al. (2016)

**Paper.** Gillan CM, Kosinski M, Whelan R, Phelps EA, Daw ND (2016).
*Characterizing a psychiatric symptom dimension related to deficits in goal-directed
control.* eLife 5:e11305. <https://doi.org/10.7554/eLife.11305>

**Data.** OSF project <https://osf.io/usdgt/>, vendored whole under
[`sources/gillan2016/osf/`](../sources/gillan2016/osf). The paper and its five
supplementary files are in
[`sources/gillan2016/paper/`](../sources/gillan2016/paper) — supplement 2 lists the
top-loading items for each factor and supplement 5 reports the questionnaire
associations computed from the full computational model.

**Where the column names come from.** The per-subject task files are headerless. The
names below are from the project's own `readme.rtf` (in this repo at
`sources/gillan2016/osf/Experiment 1/readme.rtf`, and reproduced in full at the bottom
of this file). The two things the readme does *not* mention -- the response deadline
and the stale stimulus values on timed-out trials -- were established from the data
and are verified in `src/validate.py`.

## What is on OSF

```
Experiment 1/
    twostep_data_study1/<MTurkID>.csv      649 files, one per subject
    self_report_study1.csv                 548 rows  <- the analysed sample
    readme.rtf
Experiment 2/
    twostep_data_study2/<MTurkID>.csv      1712 files
    self_report_study2.csv                 1413 rows <- the analysed sample
    individual_items_study2.csv            1413 rows x 209 items
    weights.csv                            209 items x 3 factors
    readme.rtf
"Error in adminstration of one SDS Depression Item.rtf"
```

Study 1 reports N = 548 and study 2 N = 1413; the task folders hold more files than
that (649 and 1712). Every self-report ID has a task file, but 101 and 299 task files
respectively have no self-report row. **The self-report table defines the analysed
sample** -- that is what the `in_selfreport` column in our output marks. The two
studies share no subject IDs, consistent with study 2 being described as a task-naive
sample.

The stray RTF at the project root is a correction notice the authors added in 2021,
and anyone reusing these data should read it: **item 13 of the Zung Depression Scale
was mis-worded.** It should read "I am restless and can't keep still" but
participants were actually asked "I am restless and can't sleep". The item is still
present in the data (there are 209 items, as in the paper) and the authors report that
removing it changes nothing -- the SDS total correlates at r = 0.996 with and without
it, and the three factor scores at r > 0.999 -- but it matters for anyone **applying
their factor weights to a new sample**, where the correctly worded item would be used.
`src/fetch.py` downloads this notice to `data/raw/gillan/`.

## Task files: `twostep_data_study<n>/<MTurkID>.csv`

Headerless, ragged, and *not* a rectangular CSV. Structure:

```
AgeDropdown,35                                        <- 2 fields
GenderDropdown,Female                                 <- 2 fields
<id>,INSTRUCT,twostep_instruct_1,23508                <- 4 fields
...                                                   (repeats if the subject
instructionLoop                                          re-read the instructions)
<id>,INSTRUCT,twostep_instruct_9,236842               <- last instruction row
1,0.7426,0.2725,0.7167,0.4791,right,2,1365,true,...   <- trials start here, 15 fields
```

Per the readme, **task data starts on the row after the one containing
`twostep_instruct_9` in column C.** Subjects can have a varying number of rows before
that, so the offset cannot be hard-coded.

**That rule only works for study 1.** All 649 study-1 files contain exactly one marker
row; **no study-2 file contains it at all** -- study 2 was logged without the
`INSTRUCT` rows, so those files go demographics -> a run of bare `instructionLoop`
lines -> trials, and some carry other event rows (`CoinBoxGoodness`) too. Anyone
following the readme literally will fail on all 1712 study-2 files.

`src/extract_gillan.py` therefore locates trials structurally: a trial row is the only
kind with **exactly 15 fields and an integer in the first one**. That rule was checked
against the marker rule on all 649 study-1 files and selects exactly the same rows, so
it is strictly more general.

Trial counts after that: 649/649 study-1 and 1711/1712 study-2 subjects have a full 200
trials numbered 1..200. The exception is study-2 subject
`3570Y55XZPJQZPOYLZCOL50WZE6GYI`, whose file is **missing trial 1** and runs 2..200
(199 trials). The harmonized table keeps the source numbering rather than renumbering,
so that subject stays correctly aligned.

### Trial columns (15 fields, A–O)

| col | name | meaning |
|---|---|---|
| A | `trial_num` | 1…200 |
| B | `drift1` | reward probability of second-stage option 1 |
| C | `drift2` | reward probability of second-stage option 2 |
| D | `drift3` | reward probability of second-stage option 3 |
| E | `drift4` | reward probability of second-stage option 4 |
| F | `s1_response` | first-stage response side, `left` / `right`; **−1 = timeout** |
| G | `s1_stim` | first-stage stimulus chosen, 1 / 2. Redundant with F because the two options never swap sides. **Stale (always `2`) on a stage-1 timeout** |
| H | `s1_rt` | first-stage reaction time, ms |
| I | `transition` | `true` = common (70%), `false` = rare (30%); **`-1` on a stage-1 timeout** |
| J | `s2_response` | second-stage response side, `left` / `right`; −1 = timeout |
| K | `s2_stim` | second-stage stimulus chosen, 1 / 2; also fixed sides. **Stale (always `2`) on a stage-2 timeout** |
| L | `s2_state` | second-stage state identity, **2 or 3** (not 1 or 2); −1 if no first-stage response |
| M | `s2_rt` | second-stage reaction time, ms |
| N | `reward` | 1 = rewarded, 0 = not; **−1 if the trial was not completed** |
| O | — | redundant task variable, always 1 |

**Which drift column belongs to which option.** `drift1…drift4` are indexed by
`(s2_state − 2) * 2 + s2_stim`, i.e. options (2,1), (2,2), (3,1), (3,2) in that
order. This is not stated anywhere in the readme, so `src/validate.py` proves it: for
each option, the mean of its drift column matches the reward rate actually obtained
when that option was chosen, across tens of thousands of trials.

### Missing data -- the main trap in this dataset

The task had a response deadline of about **2500 ms per stage** (undocumented; `s1_rt`
and `s2_rt` on timed-out trials cluster tightly at 2500–2502 ms). Timed-out trials are
*present* in the file, coded with −1 -- but **the stimulus columns are not set to −1,
they keep a stale value of 2**:

| pattern | study 1 | study 2 | `s1_stim` | `transition` | `s2_state` | `s2_stim` | `reward` |
|---|---|---|---|---|---|---|---|
| stage-1 timeout | 1402 | 5549 | **stale `2`** | −1 | −1 | −1 | −1 |
| stage-1 answered, stage-2 timeout | 421 | 1458 | valid | valid | valid | **stale `2`** | −1 |
| **total incomplete** | 1823 (1.4%) | 7007 (2.0%) | | | | | |

Reading column G without first checking column F therefore invents a first-stage
choice on every stage-1 timeout -- 1402 trials in study 1 (1.1% of trials, spread over
366 of the 649 subjects, up to 155 in one subject) and 5549 in study 2. This would bias any stay-probability
or model-based measure. Our extraction keeps the raw columns untouched and adds
explicit `s1_timeout`, `s2_timeout`, `timeout` and `transition_common` columns; the
harmonized table blanks the stale values outright.

Note that `s1_rt` is *not* a reliable timeout indicator on its own: it ranges from 340
to 440,332 ms on timed-out trials. Use `s1_response == -1`.

## Self-report tables

`self_report_study1.csv` (548 rows):

| column | meaning |
|---|---|
| `subj.x` | MTurk ID, matches the task file name |
| `age` | years; identical to the task file's `AgeDropdown` for all 548 subjects |
| `iq` | score from the short IQ test administered after the task |
| `gender` | **effect-coded: −1 = Female, +1 = Male** (verified against `GenderDropdown`) |
| `sds_total` | Zung Self-Rating Depression Scale |
| `stai_total` | State-Trait Anxiety Inventory, trait scale |
| `oci_total` | Obsessive-Compulsive Inventory - Revised |

`self_report_study2.csv` (1413 rows) has `subj` instead of `subj.x`, the same
`age` / `iq` / `gender`, and in addition:

| column | questionnaire |
|---|---|
| `lsas_total` | Liebowitz Social Anxiety Scale |
| `bis_total` | Barratt Impulsiveness Scale |
| `scz_total` | Schizotypy (SPQ) |
| `aes_total` | Apathy Evaluation Scale |
| `eat_total` | Eating Attitudes Test |
| `audit_total` | Alcohol Use Disorders Identification Test |
| `oci_total`, `sds_total`, `stai_total` | as in study 1 |
| `Factor1` | **Anxious-Depression** (AD) |
| `Factor2` | **Compulsive Behaviour and Intrusive Thought** (CIT) |
| `Factor3` | **Social Withdrawal** (SW) |

`individual_items_study2.csv` holds the 209 raw item responses per subject
plus a `subject` column: `SCZ_1…43` (43), `OCI_1…18` (18), `EAT_1…26` (26),
`AES_1…18` (18), `AUDIT_1…10` (10), `SDS_1…20` (20), `STAI_1…20` (20), `BIS_1…30`
(30), `LSAS_1…24` (24) -- 209 in total.

`weights.csv` is the **item x factor scoring matrix** (209 rows x AD / CIT / SW).

**How to score it.** The weights apply to *standardised* item responses, and the
published scores are themselves standardised to unit variance. So:

1. z-score each of the 209 item columns across subjects;
2. take the dot product with the AD / CIT / SW column of `weights.csv`;
3. standardise the three resulting scores to mean 0, SD 1.

`src/validate.py` checks this against the distributed `Factor1–3` columns and gets
**r = 0.9992 for all three factors** (median |difference| ~0.01, max ~0.06). It is
close but *not* exact, because `weights.csv` is a simplified scoring matrix while the
distributed scores appear to come from the factor model's own regression scoring,
which uses the full item covariance matrix. For reference, the published scores have
SD exactly 1.0000 whereas a weighted sum of z-scored items comes out at 0.977-0.985.

A plain dot product of the **raw** (unstandardised) responses is noticeably worse --
r = 0.989-0.998, max |difference| up to 2.8 -- so the standardisation matters.

This recipe is the practical payoff of the file: it means the same three dimensions can
be scored in any new sample that administers the same items, without refitting a factor
model.

## Model used in the paper

Two measures of model-based control are reported, and they correlate at 0.87:

1. **Primary, model-agnostic**: the stay-probability logistic regression
   `glmer(Stay ~ Reward * Transition * SymptomScore_z + Reward * Transition * (IQ_z +
   Age_z + Gender) + (Reward * Transition + 1 | Subject))`. Model-based control is the
   `Reward x Transition` interaction.
2. **Computational**: the Otto et al. (2013) simplification of Daw et al. (2011), with
   **six** free parameters -- a learning rate `alpha` and five weights:
   `beta_MB`, `beta_MF0` (TD(0)), `beta_MF1` (TD(1)), `beta_stick`, `beta_stage2`.
   Instead of a `w` in [0,1] and an eligibility trace `lambda`, model-based and
   model-free strength are *separate* unbounded weights, with
   `beta_MF = beta_MF0 + alpha * beta_MF1` reconstructed afterwards. Fitted per
   subject jointly with group-level distributions by Expectation-Maximisation
   (Huys et al. 2011), implemented in Julia.

This parameterization is **not** the same as Kool's `w` or Gilger's `omega`; see
[compatibility.md](compatibility.md).

## Outputs

| file | contents |
|---|---|
| `gillan_study<n>_trials.csv` | one row per trial: the 15 raw columns under the names above, plus `s1_timeout`, `s2_timeout`, `timeout`, `transition_common` |
| `gillan_study<n>_subjects.csv` | per subject: trial count, timeout counts, `AgeDropdown`/`GenderDropdown`, `in_selfreport`, and all self-report columns |
| `gillan_study2_items.csv` | the 209 individual item responses, copied through |
| `gillan_factor_weights.csv` | the item x factor loading matrix, copied through |

## Verbatim `readme.rtf`

> Claire Gillan - November, 2019
>
> Some basic info for reading in and analysing the task data for the two-step task.
>
> Note:
> - Task data starts the row after the one that lists "twostep_instruct_9" in column C.
> - Subjects can have varying number of rows prior to the start of the task due to them
>   repeating the instructions (having multiple instances of instructionLoop)
>
> **Task data column names:**
> A = trial_num /
> B = drift 1 (probability of reward after second stage option 1) /
> C = drift 2 (probability of reward after second stage option 2) /
> D = drift 3 (probability of reward after second stage option 3) /
> E = drift 4 (probability of reward after second stage option 4) /
> F = stage 1 response (left/right) /
> G = stage 1 selected stimulus (1/2 - note this is redundant with the response as the
> stage 1 options do not switch locations) /
> H = stage 1 RT /
> I = transition (common = TRUE; rare = FALSE) /
> J = stage 2 response (left/right) /
> K = stage 2 selected stimulus (1/2 - note this is redundant with response as the
> stage 2 options also do not switch locations) /
> L = stage 2 state (identity 2 or 3) /
> M = stage 2 RT /
> N = reward (1= yes; 0=no) /
> O = redundant task variable, always set to 1
