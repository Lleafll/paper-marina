# Two-step task datasets: sources, extraction, codebooks, compatibility

**New to the methodology?** Start with [`PRIMER.md`](PRIMER.md) — a plain-language
explanation of the two-step task, what model-based vs model-free control means, what
the model parameters are, and what each of the three papers did. Written for a
STEM/software background without assuming statistics.

This repository answers three questions about the datasets in `mail.txt`:

1. **Are they compatible?** → [`docs/compatibility.md`](docs/compatibility.md).
   Short version: the *trial-level data* are compatible and now sit in one table; the
   *published model parameters* are not comparable, because the three papers fit
   different models with different estimators.
2. **What does each column mean?** → [`docs/codebook_kool.md`](docs/codebook_kool.md)
   and [`docs/codebook_gillan.md`](docs/codebook_gillan.md), derived from the authors'
   own analysis code and readme, not guessed.
3. **Which model produced Max Gilger's parameters?** → the Daw et al. (2011) hybrid
   model in its 7-parameter form (`alpha1, alpha2, beta1, beta2, lambda, omega, pi`),
   the same parameterization as hBayesDM's `ts_par7`. Details and the exact quote from
   the Methods are in [`docs/codebook_gilger.md`](docs/codebook_gilger.md).

## The datasets

| dataset | paper | public | in this repo |
|---|---|---|---|
| Kool `daw paradigm` | Kool, Cushman & Gershman (2016), PLoS Comput Biol 12:e1005090 | [GitHub](https://github.com/wkool/tradeoffs) | yes |
| Kool `novel paradigm` | same | same | yes, but **not poolable** — a different task |
| Gillan study 1 + 2 | Gillan et al. (2016), eLife 5:e11305 | [OSF usdgt](https://osf.io/usdgt/) | yes |
| Gilger et al. | Gilger et al. (2024), J Psychopharmacol 38:178-187 | **no** — no data-availability statement | paper only; documented slot for the data |

## Layout

```
sources/        the original material, as published -- committed
  kool2016/     paper + 6 supplements + the complete wkool/tradeoffs repo @ 6f849e13
  gillan2016/   paper + 5 supplements + the complete osf.io/usdgt project
  gilger2024/   paper + full text; no data (not public)
  README.md     provenance and per-item licence status -- read before redistributing
  MANIFEST.tsv  size, SHA-256 and origin URL of all 2,545 vendored files
src/            the pipeline
docs/           codebooks, the compatibility verdict, the validation report
data/processed/ derived outputs -- regenerable, not committed
```

`sources/` is 75 MB and deliberately self-contained: the project does not depend on
GitHub, OSF or the journals staying reachable. Note that while all three papers are
CC-BY, **neither dataset carries an explicit licence** — see
[`sources/README.md`](sources/README.md) before redistributing any of it.

## Running it

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python -m src.fetch            # refresh sources/ (a no-op once populated)
.venv/bin/python -m src.extract_kool     # data.mat  -> named CSVs
.venv/bin/python -m src.extract_gillan   # OSF CSVs  -> named CSVs
.venv/bin/python -m src.harmonize        # -> one cross-dataset table
.venv/bin/python -m src.validate         # check it against the authors' own output
```

`src.fetch` is cached, so it only fetches what is missing. On a fresh clone with
`sources/` already committed it does nothing.

If you ever need to re-download Gillan's 2,361 per-subject task files: fetching them
individually trips OSF's anonymous rate limit (HTTP 429) after a few hundred, so each
task folder is pulled as one archive from OSF's `?zip=` endpoint. OSF builds those on
the fly and streams them slowly — the larger one takes 10-20 minutes and prints
progress. A client-side time limit will cut the stream off mid-archive; the fetcher
detects a truncated archive and tells you to re-run rather than unpacking a partial
dataset.

## Outputs

Everything lands in `data/processed/`.

**Per dataset, faithful to the source** (raw values preserved, names and missingness
flags added):

| file | rows |
|---|---|
| `kool_daw_trials.csv` | 206 subjects x 150 trials (125 experimental + 25 practice, flagged) |
| `kool_novel_trials.csv` | 199 subjects x 150 trials |
| `kool_*_subjects.csv` | per subject: counts, exclusion flag, age, gender |
| `kool_*_published_params.csv` | the authors' own MAP fits, 12 model variants |
| `gillan_study1_trials.csv` | 649 subjects x 200 trials |
| `gillan_study2_trials.csv` | 1712 subjects x 200 trials (one subject has 199) |
| `gillan_*_subjects.csv` | per subject: counts, demographics, questionnaire totals, factor scores |
| `gillan_study2_items.csv`, `gillan_factor_weights.csv` | 209 individual items, and the item x factor scoring matrix |

**Harmonized across datasets** ([schema](docs/codebook_harmonized.md)):

| file | contents |
|---|---|
| `twostep_trials_harmonized.csv` | 522,824 trials, all datasets, one coding, sentinels replaced by empty cells |
| `twostep_subjects_harmonized.csv` | 2,766 subject-sessions, with the model-agnostic `mf_index` / `mb_index` |

## Why `validate.py` is worth running

Each check recomputes something whose correct answer is known independently of this
repository, so a mistake in a column mapping shows up as a numeric mismatch instead of
passing quietly. Currently **51 checks, 0 failures**
([report](docs/validation_report.md)):

* the per-subject stay probabilities, MB/MF indices, reward rates, mean reward
  probabilities and timeout counts are compared against `groupdata.mat` — the output
  of Kool's own MATLAB `groupanalysis.m` — and match at **max |diff| = 0**;
* the two undocumented `subinfo.mat` columns are identified by recomputing them for all
  405 subjects;
* Gillan's published `Factor1-3` scores are recomputed from the 209 item responses and
  the loading matrix, recovering the scoring recipe at r = 0.9992 per factor;
* the undocumented `drift1..4` column ordering is proven by checking that the drift of
  the chosen option predicts the reward actually received;
* within every subject, the transition label must be implied by the (choice, state)
  pairing — which a mis-mapped choice column would break.

## Three traps worth knowing about

* **Gillan's timed-out trials keep a stale choice value.** On a stage-1 timeout the
  file still reads `s1_stim = 2` even though no response was made — 1402 trials in
  study 1 across 366 of 649 subjects, 5549 in study 2. Reading that column without
  checking `s1_response` fabricates a choice on ~1% of trials. The task's ~2500 ms
  response deadline is not documented anywhere either.
* **Gillan's own readme does not work for study 2.** It says task data starts after the
  `twostep_instruct_9` row; that row exists in every study-1 file and in **no** study-2
  file. Trials are located structurally instead.
* **Kool's `daw/data.mat` has 20 columns, not the 19 their own script reads.** The
  trailing column is a jsPsych `time_elapsed` they ignore. Off-by-one here misaligns
  every variable.
