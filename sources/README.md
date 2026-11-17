# Original source material

Everything this project is built on, as its authors published it. The layout mirrors
each source — directory names included, spaces and all — so a vendored copy can be
diffed against the original. `python -m src.fetch` retrieves and refreshes all of it;
`MANIFEST.tsv` records the size, SHA-256 and origin URL of every file.

Retrieved **16 November 2025**.

## Licence status — read before redistributing

This is not uniform across the three sources, so it is recorded per item.

| item | licence | redistributable? |
|---|---|---|
| Kool et al. (2016) paper + supplements | **CC-BY 4.0** (PLOS) | yes, with attribution |
| Gillan et al. (2016) paper + supplements | **CC-BY 4.0** (eLife) | yes, with attribution |
| Gilger et al. (2024) paper | **CC-BY** (SAGE open access) | yes, with attribution |
| `kool2016/repo/` (data, code, task) | **none stated** — the GitHub repository has no LICENSE file | unclear |
| `gillan2016/osf/` (data) | **none stated** — the OSF project has no licence set (`node_license: null`) | unclear |
| `gilger2024/data/` (study-030 logfiles) | **unpublished** — internal participant data from the Dresden lab share | **no** |

The two datasets are publicly posted but carry **no explicit grant of
redistribution**. Mirroring them for one's own analysis is routine academic practice
and is what this directory is for. But if this repository is ever made public,
published or redistributed, check the licence position with the authors first —
Wouter Kool (wkool@fas.harvard.edu) and Claire Gillan — rather than assuming the
absence of a licence implies permission.

## `kool2016/`

Kool W, Cushman FA, Gershman SJ (2016). *When Does Model-Based Control Pay Off?*
PLoS Computational Biology 12(8):e1005090.
<https://doi.org/10.1371/journal.pcbi.1005090>

```
paper/pcbi.1005090.pdf          the paper (34 pp)
paper/pcbi.1005090.s001.eps     S1 Fig  — drift rate across a broad range of RL parameters
paper/pcbi.1005090.s002.eps     S2 Fig  — volume under the surface for all 32 generated tasks
paper/pcbi.1005090.s003.docx    S1 Text — reliability of the model-fitting procedure
paper/pcbi.1005090.s004.docx    S2 Text — multilevel logistic regression analyses
paper/pcbi.1005090.s005.docx    S1 Table — model comparison, with/without perseveration
paper/pcbi.1005090.s006.docx    S2 Table — model comparison, hybrid vs pure MB and MF
paper/fulltext.xml              machine-readable full text (EuropePMC, PMC5001643)
repo/                           github.com/wkool/tradeoffs @ 6f849e13 (157 files)
```

`repo/` is the complete repository, pinned to commit
`6f849e13a8fe32c0b62ad768d3578068b93ee69e` (17 Oct 2017) so the vendored copy is
reproducible. It holds three things worth knowing about:

* `repo/data/{daw,novel} paradigm/` — the `.mat` data **and the authors' own MATLAB
  analysis scripts**. `make_raw_data.m` is the authoritative source for what each
  column of `data.mat` means, which is where `docs/codebook_kool.md` comes from, and
  `groupanalysis.m` produced the `groupdata.mat` that `src/validate.py` checks our
  extraction against. Also `MB_MF_*_rllik.m` (the likelihood functions) and
  `set_opts.m` (parameter bounds and priors).
* `repo/tasks/` — the jsPsych implementations of both tasks, i.e. the ground truth for
  the 2000 ms response deadline, the stimulus coding and the cover story.
* `repo/simulations/` — the code behind the paper's simulation figures.

## `gillan2016/`

Gillan CM, Kosinski M, Whelan R, Phelps EA, Daw ND (2016). *Characterizing a
psychiatric symptom dimension related to deficits in goal-directed control.*
eLife 5:e11305. <https://doi.org/10.7554/eLife.11305>

```
paper/elife-11305-v1.pdf              the paper (24 pp)
paper/elife-11305-supp1-v1.docx       Supp 1 — questionnaire total scores, both experiments
paper/elife-11305-supp2-v1.docx       Supp 2 — top-loading items for each of the three factors
paper/elife-11305-supp3-v1.docx       Supp 3 — 'putative patients' (top 25%) vs normal range
paper/elife-11305-supp4-v1.docx       Supp 4 — item-level predictors from the supervised analysis
paper/elife-11305-supp5-v1.docx       Supp 5 — questionnaire associations using the FULL
                                               computational model (not the regression)
paper/fulltext.xml                    machine-readable full text (eLife JATS)
osf/                                  osf.io/usdgt, complete (2368 files)
```

Two of those supplements matter for the compatibility question specifically:
**Supp 5** reports the questionnaire-to-model-based-learning associations computed
from the full RL model rather than the stay-probability regression, and **Supp 2**
lists the items loading on Anxious-Depression, Compulsive Behaviour and Intrusive
Thought, and Social Withdrawal — which is what makes `osf/Experiment 2/weights.csv`
interpretable.

`osf/` keeps OSF's own folder names (`Experiment 1`, `Experiment 2`). Note the
correction notice at its root, `Error in adminstration of one SDS Depression
Item.rtf` (the authors' spelling): item 13 of the Zung Depression Scale was
mis-worded when these data were collected. See `docs/codebook_gillan.md`.

## `gilger2024/`

Gilger MD, Hellrung L, Neukam PT, Kroemer NB, Nebe S, Pooseh S, Deza-Lougovski YI,
Smolka MN (2024). *Arbitration between model-free and model-based control is not
affected by transient changes in tonic serotonin levels.* Journal of
Psychopharmacology 38(2):178–187. <https://doi.org/10.1177/02698811231216325>

```
paper/gilger2024-jpsychopharmacol.pdf   the paper (10 pp) — added by hand
paper/fulltext.xml                      machine-readable full text (EuropePMC, PMC10863371)
paper/README.md                         how to obtain the missing supplement
data/                                   study-030 logfiles from the lab share (internal)
```

**No public data.** The article has no data-availability statement and its only
supplement is a PDF. `data/` now holds the study-030 logfiles copied from the Dresden
lab share on 17 Nov 2026. They are internal, so **not redistributable**;
`data/README.md` records what was copied and how it was checked. See
`docs/codebook_gilger.md`, which identifies the model they used (the Daw 2011 hybrid
in its 7-parameter form) from the Methods text.

SAGE and PMC both block automated PDF download, so the two PDFs here are manual
additions — `paper/README.md` records where they come from. The **supplement is still
missing** and is worth getting: it should contain the full model specification.
