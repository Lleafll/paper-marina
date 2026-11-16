# Gilger et al. (2024) — the PDFs have to be added by hand

SAGE and PMC both block automated download, so `src/fetch.py` cannot retrieve these.
It checks for them and prints what is missing instead of failing.

| file | status | where to get it |
|---|---|---|
| `gilger2024-jpsychopharmacol.pdf` | **present** | <https://journals.sagepub.com/doi/pdf/10.1177/02698811231216325> (open access), or the PDF link on <https://pmc.ncbi.nlm.nih.gov/articles/PMC10863371/> |
| `gilger2024-supplemental.pdf` | **missing** | <https://journals.sagepub.com/doi/10.1177/02698811231216325> → "Supplementary Materials" → `sj-pdf-1-jop-10.1177_02698811231216325.pdf` |

`fulltext.xml` is the complete CC-BY full text from EuropePMC and *is* fetched
automatically, so the article's text is available here either way. What the XML does
not include is the supplement.

## Why the supplement is worth getting

It is the one place the model is likely to be fully specified. The main text says only:

> "we applied the computational model introduced by Daw et al. (2011) to our data. The
> model consists of seven parameters in total […] the weighting parameter omega […] a
> stage-skipping value update parameter lambda […] the parameter pi for the general
> first level repetition bias, and a learning rate alpha for first and second stage
> learning, respectively (see Supplemental Material for further details)."

That identifies the parameterization (see `docs/codebook_gilger.md`) but **not the
estimator** — hierarchical Bayesian, maximum likelihood or MAP, and with what priors.
The estimator is what decides whether this paper's `omega` can be compared against
Kool's `w` at all, so it is the single most useful missing fact in the project. See
`docs/compatibility.md`.

Once the supplement is here, read it and fill in the estimator in
`docs/codebook_gilger.md`.
