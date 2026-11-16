# Gilger et al. (2024) — no public data

The article carries **no data-availability statement**, there is no OSF, GitHub or
OpARA deposit, and the only supplementary item is a PDF. The trial-level data has to
be requested from the authors (Smolka lab, TU Dresden).

## What to ask for

1. **Trial-level task data** for all 98 participants x 3 sessions x 201 trials. Useful
   either as one long table or per subject/session; `src/extract_gilger.py` lists the
   columns the pipeline expects, and will adapt to whatever shape arrives.
2. **The model-fitting script**, to pin down the estimator behind the published
   7-parameter estimates (`alpha1, alpha2, beta1, beta2, lambda, omega, pi`) — the
   paper names the model but not how it was fitted.
3. Clarification of two coding conventions that differ between the other datasets:
   * how timed-out trials are flagged, and whether they appear in the data at all;
   * whether the second-stage state is labelled 1/2 (as Kool) or 2/3 (as Gillan), and
     whether second-stage choices are numbered within state (1/2) or globally (1–4).
4. Whether the published parameters were fitted **per session** or once per subject
   across all three sessions.

## When it arrives

Put the files in this directory, implement `write_trials()` in
`src/extract_gilger.py` so it emits `data/processed/gilger_trials.csv`, and
`src/harmonize.py` will pick it up automatically and stack it with the rest. See
`docs/codebook_gilger.md`.
