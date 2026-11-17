# Codebook: Gilger et al. (2024) -- data pending

**Paper.** Gilger MD, Hellrung L, Neukam PT, Kroemer NB, Nebe S, Pooseh S,
Deza-Lougovski YI, Smolka MN (2024). *Arbitration between model-free and model-based
control is not affected by transient changes in tonic serotonin levels.* Journal of
Psychopharmacology 38(2):178–187. <https://doi.org/10.1177/02698811231216325>
Open access (CC-BY); full text also at
[PMC10863371](https://pmc.ncbi.nlm.nih.gov/articles/PMC10863371/).

## Status: raw logfiles obtained and extracted (17 Nov 2026)

The article carries **no data-availability statement** and its only supplement is a
PDF (`sj-pdf-1-jop-10.1177_02698811231216325.pdf`, SAGE blocks automated download).
There is no OSF, GitHub or OpARA deposit.

The study-030 Psychtoolbox logfiles have since been copied from the lab share into
`sources/gilger2024/data/` (internal, not for redistribution). They match the design
below in every checked respect: 201 trials, 70/30 transitions, 2 s deadline, reward
walks in [0.25, 0.75], 109 subjects with three scanner sessions. The variable coding,
the counterbalancing and the open anomalies are documented in
[`sources/gilger2024/data/README.md`](../sources/gilger2024/data/README.md). Still
missing: the **tryptophan-condition key** (the logfiles are blinded) and the fitting
script.

## Which model produced the published parameters

This was the open question in Marina's mail. The Methods section answers it:

> "To describe the task behaviour in more detail, we applied the computational model
> introduced by **Daw et al. (2011)** to our data. The model consists of **seven
> parameters** in total, including an agent for MF and one for MB learning. […] How
> strong each agent influences behaviour is determined by the weighting parameter
> **omega**. Additionally, the model computes a stage-skipping value update parameter
> **lambda** […], the parameter **pi** for the general first level repetition bias,
> and a learning rate **alpha** for first and second stage learning, respectively
> (see Supplemental Material for further details)."

So the seven parameters are the canonical Daw (2011) hybrid set:

| parameter | meaning |
|---|---|
| `alpha1` | learning rate, first stage |
| `alpha2` | learning rate, second stage |
| `beta1` | inverse temperature, first stage |
| `beta2` | inverse temperature, second stage |
| `lambda` | eligibility trace / stage-skipping value update |
| `omega` (w) | model-based weight, 0 = pure model-free, 1 = pure model-based |
| `pi` | first-stage choice repetition bias (perseveration) |

This is exactly the parameterization distributed as `ts_par7` in
[hBayesDM](https://rdrr.io/cran/hBayesDM/man/ts_par7.html), and the same model the
Dresden group used in Nebe et al. (2018, Addiction Biology) with this task and
sample lineage. Note that the paper does **not** state the estimator (hierarchical
Bayesian vs. maximum likelihood vs. MAP), which is the one detail still worth getting
from the co-authors, because the estimator -- not just the parameterization -- affects
whether the published `omega` values can be compared against anyone else's `w`.

Open questions for the authors:

1. the trial-level task data for all 98 participants x 3 sessions;
2. the fitting script, to pin down the estimator and any priors;
3. whether the reported parameters were fitted per session or once per subject across
   all three sessions.

## Design and expected format

From the Methods:

| | |
|---|---|
| Task | standard Daw et al. (2011) two-step task |
| Trials | **201 per session** |
| Sessions | **3** fMRI sessions, one per tryptophan condition (plus a baseline assessment) |
| Design | randomised, double-blind, cross-over, within-subject |
| Conditions | acute tryptophan **loading** / **balanced** / **depletion** |
| Transitions | 70% common / 30% rare |
| Reward | binary, 20 cents; probabilities drift as Gaussian random walks with reflecting boundaries at **0.25 and 0.75** |
| Duration | ~35 min per session |
| Sample | 170 genotyped, 107 completers, **n = 98 behavioural**, n = 88 fMRI |
| Exclusions | 5 task-unresponsive, 2 technical, 2 randomisation errors |
| Extras | 5-HTTLPR genotype, blood tryptophan levels, fMRI (SPM8, MNI space) |

The task matches Kool's `daw paradigm` and Gillan's task in every structural respect,
so once the data arrives it maps onto the harmonized schema directly.

## Extraction

`src/extract_gilger.py` reads `sources/gilger2024/data/Files_with_Timestamp/` and
writes three files to `data/processed/`:

| file | contents |
|---|---|
| `gilger_trials.csv` | 387 sessions x 201 trials, canonical names: `subject_id, session, condition, trial, s1_choice, s1_rt_ms, transition_common, s2_state, s2_choice, s2_rt_ms, reward, p_reward_1..4, timeout` |
| `gilger_sessions.csv` | one row per logfile (389): missed trials per stage, counterbalancing, and the integrity counts `validate.py` checks |
| `gilger_subjects.csv` | one row per subject (153): sessions present, % missed per session, exclusion flags |

`s2_state` is recoded from the logfile's 2/3 to 1/2, RTs are converted to ms, and
`timeout` is 1 if either stage was missed. Two logfiles are not used: the
`00009999` test run, and the later of `00004863`'s two session-1 files (18 Sep 2014,
after its session 3). `condition` is empty, because the logfiles are blinded.

## Exclusions for the behavioural analysis

The Methods and the Supplement give the same criteria (but no participant IDs):
107 participants finished all three sessions, and 9 of them were excluded, leaving
n = 98:

| reason | n | identifiable from the logfiles? |
|---|---|---|
| task unresponsiveness: > 30% missing trials in at least one session | 5 | **yes** |
| technical issues during data acquisition | 2 | no |
| intervention randomisation error in one session | 2 | no — needs the condition key |

**Unresponsiveness reproduces exactly.** Counting a trial as missing if *either*
stage timed out, and applying "> 30%" (more than 60.3 of 201) to each session, gives
exactly five completers:

| subject | % missed, session 1 / 2 / 3 |
|---|---|
| `00006649` | 8.5 / 36.3 / 27.9 |
| `00007729` | 48.8 / 49.8 / 55.2 |
| `00009117` | 4.0 / 10.0 / 51.2 |
| `00009935` | 20.4 / 41.8 / 12.9 |
| `00011494` | 11.4 / 26.9 / 42.3 |

The cut is not borderline: the next-worst completer peaks at 26.4%. Counting only
stage-1 timeouts would give 2, so the authors' "missing trial" is a trial missed at
either stage. `validate.py` asserts the count of 5.

**The completer count does not reproduce from the logfiles alone.** They have
**110** subjects with sessions 1, 2 and 3, not 107.

### The final sample (lab list)

The lab's final participant list,
`P:\030\Analysis\2-step gender\Repository\Participant characteristics.sav`, copied to
`sources/gilger2024/data/final_sample/`, has **98** subjects with demographics, the
seven fitted parameters and four stay probabilities. All 98
are among the 110 logfile completers, so **12 completers were excluded**:

| subject | first session | % missed, sessions 1 / 2 / 3 | reason |
|---|---|---|---|
| `00006649` | 2015-03-13 | 8.5 / 36.3 / 27.9 | unresponsive (> 30%) |
| `00007729` | 2015-08-22 | 48.8 / 49.8 / 55.2 | unresponsive (> 30%) |
| `00009117` | 2014-11-21 | 4.0 / 10.0 / 51.2 | unresponsive (> 30%) |
| `00009935` | 2015-09-16 | 20.4 / 41.8 / 12.9 | unresponsive (> 30%) |
| `00011494` | 2015-10-04 | 11.4 / 26.9 / 42.3 | unresponsive (> 30%) |
| `00007760` | 2014-04-22 | 0.5 / 0.0 / 0.0 | not stated |
| `00005007` | 2014-05-05 | 10.0 / 20.4 / 8.5 | not stated |
| `00001660` | 2014-05-06 | 0.5 / 1.0 / 1.0 | not stated |
| `00001801` | 2014-05-07 | 1.0 / 2.0 / 2.5 | not stated |
| `00004848` | 2014-05-28 | 0.5 / 1.5 / 0.5 | not stated |
| `00007606` | 2014-11-15 | 2.0 / 5.0 / 3.5 | not stated |
| `00000583` | 2015-01-08 | 5.5 / 11.4 / 12.9 | not stated |

The five unresponsive exclusions are exactly the five the 30% rule identifies. The
other seven behave normally in the task, so they must be the paper's 3 + 2 + 2: the
three it does not count as completers, the two technical exclusions and the two
randomisation errors. Which is which is not recorded in either file. One pattern
stands out: **the five earliest completers (first sessions 22 Apr – 28 May 2014) are
all among the seven**, which points at a problem early in data collection. That is an
inference, not documented.

The three subjects with irregular sessions (`00004863`, `00006582`, `00026416`) are
all **in** the final sample, so they are not the missing completers.

The list matches the paper's sex split (61 male, 37 female) and maximum age (42).
Its age mean, SD and minimum (32.6, 5.9, 21) differ slightly from the paper's
(32.2, 6.1, 20), perhaps because age was taken at a different date.

`gilger_subjects.csv` marks the 98 in `in_final_sample`, and
`gilger_trials_final_sample.csv` holds their trials: 98 x 3 sessions x 201 = 59,094
rows, in the same columns as `gilger_trials.csv`. `validate.py` checks both.

**Cross-check against the lab's stay probabilities.** The list stores
`PStay_RewComm / RewRare / UnrewComm / UnrewRare` per subject. Recomputing them from
the trial table matches closely but not exactly. The closest convention is: the
previous *fully answered* trial, skipping timeouts, computed per session and
averaged over the three sessions. It reproduces 25 of 98 subjects to machine
precision, and every subject within 0.055. So the trials are the same; the lab's
exact stay-probability definition is not recovered.

The two coding questions that differ across the existing datasets are answered by
the logfiles themselves:

* timed-out trials are present: `NaN` choice and RT, `R = 0`, and after a stage-1
  timeout `S(2,t) = 0` and `A(2,t) = 0`, while `trans(t)` is still filled in;
* the second-stage state is labelled **2/3** (as Gillan), and second-stage choices
  are numbered **within state** (1/2).

## Model-free / model-based behaviour and the 7 parameters

`src/fit_gilger.py` computes both measures from `gilger_trials_final_sample.csv`.
**No fitting script is named or linked in the paper, its supplement or the
sex-differences follow-up**, so this module implements what they do specify:

* **MF / MB effects** from the Methods (Eq. 1): `(p_com+ + p_rar+ − p_com− − p_rar−)/2`
  and `(p_com+ − p_rar+ − p_com− + p_rar−)/2`, per session.
* **The Daw (2011) hybrid model**, with the seven parameters α1, α2, λ, ω, β1, β2 and
  π. π sits inside the β1 bracket, as the sex-differences supplement (S-5) writes it:
  `β1·[Q_net(a) + π·rep(a)]`. Fitted separately for each session.

As agreed, the per-subject values are **means over the three tryptophan sessions**,
the same form as the lab's table (`gilger_subject_means_<prior>.csv`).

### Against the lab's own values (final-sample `.sav`)

| | Pearson r | Spearman ρ | our mean of sessions (median) | lab (median) |
|---|---|---|---|---|
| MF effect | 0.997 | | +0.093 (mean) | +0.090 (mean) |
| MB effect | 0.995 | | +0.071 (mean) | +0.070 (mean) |
| α1 | 0.79 | 0.79 | 0.499 | 0.525 |
| α2 | 0.90 | 0.93 | 0.602 | 0.606 |
| λ | 0.91 | 0.90 | 0.609 | 0.634 |
| ω | 0.86 | 0.86 | 0.403 | 0.335 |
| β1 | 0.84 | 0.93 | 4.442 | 4.498 |
| β2 | 0.64 | 0.94 | 2.609 | 2.636 |
| π | 0.74 | 0.89 | 0.192 | 0.191 |

(Parameters from `--prior weak`, the default. The lab's MF / MB effects are computed
from the four stay probabilities stored in the `.sav`.)

What the comparison settles and what it does not:

* **The stay effects reproduce** (r ≈ 0.997; differences up to 0.03, from a
  slightly different trial-pair rule).
* **π is inside the β1 bracket.** With π outside (Daw's own form) our π has median
  0.62 against the lab's 0.19 and ρ = 0.54; inside, the medians agree and ρ = 0.89.
* **The lab used some regularisation, or bounds on β.** Plain maximum likelihood
  (`--prior none`) lets β run off on a few flat sessions: the largest difference
  from the lab is about 90 for β1 and 49 for β2, against 10 and 16 with weak priors,
  and every correlation is lower. The lab's values also approach but never reach 0 and 1 (lowest ω
  4·10⁻⁸), which fits an optimiser on transformed parameters.
* **The lab's exact estimator is not recovered.** No parameter matches value for
  value, and ω runs a little higher here (median 0.40 vs 0.34). The likely
  differences are the priors, the number of starting points, or a hierarchical step
  (e.g. Huys' `emfit`, common in this Dresden/Berlin lineage). The script itself
  would settle it.

Fitting all 294 sessions takes about 9 minutes on 8 cores (pure-Python likelihood,
10 starts per session), so it is a separate step and not part of `validate.py`.
