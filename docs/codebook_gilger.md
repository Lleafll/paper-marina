# Codebook: Gilger et al. (2024) -- data pending

**Paper.** Gilger MD, Hellrung L, Neukam PT, Kroemer NB, Nebe S, Pooseh S,
Deza-Lougovski YI, Smolka MN (2024). *Arbitration between model-free and model-based
control is not affected by transient changes in tonic serotonin levels.* Journal of
Psychopharmacology 38(2):178–187. <https://doi.org/10.1177/02698811231216325>
Open access (CC-BY); full text also at
[PMC10863371](https://pmc.ncbi.nlm.nih.gov/articles/PMC10863371/).

## Status: not obtainable from the publication

The article carries **no data-availability statement** and its only supplement is a
PDF (`sj-pdf-1-jop-10.1177_02698811231216325.pdf`, SAGE blocks automated download).
There is no OSF, GitHub or OpARA deposit. The trial-level data and the fitting script
have to come from the authors (Smolka lab, TU Dresden).

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

## Wiring it up

`src/extract_gilger.py` is a documented stub. When the files arrive:

1. put them under `data/raw/gilger/`;
2. implement `write_trials()` so it emits `data/processed/gilger_trials.csv` with the
   columns listed in `EXPECTED_COLUMNS` in that module -- they are already the
   canonical names:

   `subject_id, session, condition, trial, s1_choice, s1_rt_ms, transition_common,`
   `s2_state, s2_choice, s2_rt_ms, reward, p_reward_1..4, timeout`

3. `src/harmonize.py` picks that file up automatically and stacks it with the rest;
   `session` 1–3 keeps the three tryptophan conditions as separate rows in the
   subject-level table.

Two coding decisions to confirm against the Dresden script when it arrives, because
both differ across the existing datasets:

* how timeouts are flagged, and whether timed-out trials are present at all;
* whether the second-stage state is labelled 1/2 (as Kool) or 2/3 (as Gillan), and
  whether second-stage choices are numbered within state (1/2) or globally (1–4).
