# Gilger et al. (2024) — study 030 two-step logfiles

The paper itself has no public data. These are the original Psychtoolbox logfiles of
the Dresden study 030 two-step task (task version `twostep-4.1.140317`), copied on
**17 November 2026** from the lab share:

```
P:\030\Ancillary_data\Level_1_source_data\2-Step\
```

That source is internal and not public, so **do not redistribute these files** and do
not push them anywhere public without the Smolka lab's agreement. Names and layout
are kept as they are on the share, so this copy can be diffed against it.

## What was copied

| folder | files | what it is |
|---|---|---|
| `README.txt` | 1 | the lab's own description of the folders |
| `Files_with_Timestamp/` | 389 | **the curated session logfiles**: one per subject x session, already repaired |
| `Files_with_wrong_SubjID/` | 26 | originals with mistyped IDs; `README.txt` documents each fix; `Corrected/` holds renamed copies |
| `Participants_with_4_Sessions/` | 3 | two discarded repeat sessions (6582 s2, 26416 s1), plus a README |
| `Training/` | 290 | practice-run logfiles from before session 1 |
| `final_sample/Participant characteristics.sav` | 1 | the lab's final list of the 98 analysed participants (demographics, fitted parameters, stay probabilities), copied 17 Nov 2026 from `P:\030\Analysis\2-step gender\Repository\` |

Left on the share on purpose: `all_data_sync/` (a sync copy of everything, 1,203
files), `_SYNCAPP/` (sync-tool metadata), `Files_without_Timestamp/` (short-name
duplicates; the lab README says it is incomplete and unrepaired), `Test Runs/` (IDs
9999 / 8888 / 0000) and `incomplete,aborted,crashed or duplicated data/`.

## Compatibility check (all 399 session files)

Every file in `Files_with_Timestamp/`, `Corrected/` and `Participants_with_4_Sessions/`
was loaded and checked. The task is the standard Daw (2011) two-step task that the
paper describes, and it maps onto the harmonized schema:

| check | result |
|---|---|
| trials per session (`nt`, `Z.Ntrials`) | 201 in every file except the `00009999` test run (12) |
| common transition probability (`Z.p`) | 0.70 everywhere |
| response deadline (`Z.max_choice_time`) | 2 s, both stages |
| reward-probability walks (`dawrandomwalks`) | inside [0.25, 0.75] in all files, two walk sets (`dawrandomwalks_1/2.mat`) |
| reward = the pre-drawn outcome `rewprob(state-1, s2 choice, t)` | 0 mismatches in any file |
| `trans` = the (s1 choice, state) pairing | consistent in every file, given the counterbalancing below |
| `aborted` flag | 0 everywhere; all files are scanner sessions (`doscanner = 1`) |

### Variable coding (from the logfile variables)

| variable | shape | meaning |
|---|---|---|
| `A(1,t)` | 1 x 201 | stage-1 choice, 1/2; `NaN` = stage-1 timeout |
| `A(2,t)` | | stage-2 choice **within state**, 1/2; `NaN` = stage-2 timeout, `0` after a stage-1 timeout |
| `S(2,t)` | | second-stage state, **2/3** (as Gillan); `0` after a stage-1 timeout |
| `trans(t)` | | 1 = common, 0 = rare. Pre-drawn, so it is set even on stage-1 timeouts — mask it |
| `R(t)` | | reward 1/0; 0 on any timeout |
| `RT(1:2,t)` | | response times in **seconds**; `NaN` on timeouts |
| `dawrandomwalks(state-1, choice, t)` | 2 x 2 x 201 | reward probabilities |
| `randCWS` | `"C_W_S"` | counterbalancing: transition mapping, walk set, stimulus set |

The common transition is counterbalanced by the first digit of `randCWS`
(`codeC`): **C = 2** → choice 1 commonly leads to state 3; **C = 1** → choice 1
commonly leads to state 2. This held in all 399 files.

### Coverage

154 subject IDs in `Files_with_Timestamp/`: **109 with 3 sessions**, 14 with 2,
30 with 1, 1 with 4 (see below). The paper reports 107 completers and n = 98 in the
behavioural analysis, so the exclusions still have to be applied.

### Things to resolve before extraction

* **The tryptophan condition is not in the logfiles.** The study was double-blind,
  so session number does not identify depletion / balanced / loading. The
  unblinding key has to come from the lab.
* `00009999_1` is a 12-trial test run that sits in `Files_with_Timestamp/`; drop it.
* `00004863` has two session-1 files, 3 Jul 2014 and 18 Sep 2014 (after its session
  3), and no lab note explaining it.
* `00010062_2__150627_1405.mat` still records `session = '1'` internally; the
  filename (session 2) is the corrected value, per `Files_with_wrong_SubjID/README.txt`.
* `00007483_3` has `randCWS = "2_2_5ccccc"` (stray keypresses); read it as `2_2_5`.
* The `Corrected/` copies differ byte-wise from the same-named files in
  `Files_with_Timestamp/`: the latter had their internal `subjn` repaired in
  2016. Use `Files_with_Timestamp/`.
* Missed-response rates vary widely: 13 sessions miss more than 50 of 201 trials
  (`00007729` misses ~100 in all three sessions). These are likely the paper's
  "task-unresponsive" exclusions.

## Extraction

`src/extract_gilger.py` turns these files into `data/processed/gilger_*.csv`, and
`src/validate.py` re-checks everything above on every run. The exclusion analysis
(5 of 5 unresponsive participants reproduced; 110 rather than 107 completers) is in
`docs/codebook_gilger.md`.
