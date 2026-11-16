"""Extract Kool, Cushman & Gershman (2016) data.mat into documented CSVs.

`data.mat` carries no column names, so the mapping comes verbatim from the
repository's own MATLAB code (`data/<paradigm> paradigm/make_raw_data.m`), which is
the authoritative source. See docs/codebook_kool.md.

Note that data.mat has one more column than make_raw_data.m reads: the authors index
`data(:,2:19)` (daw) / `data(:,2:15)` (novel), leaving a trailing jsPsych
`time_elapsed` column unused in the daw file. It is carried through here for
completeness.

Outputs (data/processed/):
    kool_<paradigm>_trials.csv            one row per trial, named columns,
                                          practice trials kept and flagged
    kool_<paradigm>_subjects.csv          per-subject summary + demographics from
                                          subinfo.mat + exclusion flag
    kool_<paradigm>_published_params.csv  the authors' own fitted parameters from
                                          results.mat, all 12 model variants
"""

from __future__ import annotations

import csv
import sys

import numpy as np
from scipy.io import loadmat

from .paths import PROCESSED, ensure_dirs, kool_paradigm_dir

# ---------------------------------------------------------------------------
# Column mappings. Entry 0 is data.mat column 2; column 1 holds the subject ID.
# Names and comments are those used in make_raw_data.m.
# ---------------------------------------------------------------------------

DAW_COLUMNS = [
    "stim_1_left",   # first-stage stimulus presented on the left
    "stim_1_right",  # first-stage stimulus presented on the right
    "rt1",           # first-stage reaction time, ms; -1 = timeout
    "choice1",       # first-stage choice (stimulus identity, not side); -1 = missed
    "stim_2_left",   # second-stage stimulus presented on the left
    "stim_2_right",  # second-stage stimulus presented on the right
    "rt2",           # second-stage reaction time, ms; -1 = timeout
    "choice2",       # second-stage choice (stimulus identity); -1 = missed
    "win",           # points won at the second stage (>0 => rewarded)
    "state2",        # second-stage state (1 or 2)
    "common",        # transition type: 1 = common (70%), 0 = rare (30%)
    "score",         # cumulative score
    "practice",      # 1 = practice trial, 0 = experimental trial
    "ps1a1",         # reward probability, second-stage state 1 / action 1
    "ps1a2",         # reward probability, second-stage state 1 / action 2
    "ps2a1",         # reward probability, second-stage state 2 / action 1
    "ps2a2",         # reward probability, second-stage state 2 / action 2
    "trial",         # trial number, 0-based, restarting after the practice block
    "time_elapsed",  # ms since task start (jsPsych; not read by make_raw_data.m)
]

NOVEL_COLUMNS = [
    "state1",        # first-stage state (1 or 2)
    "stim_left",     # stimulus presented on the left
    "stim_right",    # stimulus presented on the right
    "rt1",           # first-stage reaction time, ms; -1 = timeout
    "choice1",       # first-stage choice (stimulus identity); -1 = missed
    "rt2",           # second-stage reaction time, ms; -1 = timeout
    "points",        # points won (scalar reward, -4..+5)
    "state2",        # second-stage state (1 or 2)
    "score",         # cumulative score
    "practice",      # 1 = practice trial, 0 = experimental trial
    "rews1",         # current reward value of second-stage state 1
    "rews2",         # current reward value of second-stage state 2
    "trial",         # trial number, 0-based
    "time_elapsed",  # ms since task start
]

# subinfo.mat is undocumented; columns 4 and 5 are inferred (they match the final
# cumulative score and the total task duration in the trial data respectively, which
# validate.py checks).
SUBINFO_COLUMNS = ["subject_id", "age", "gender", "final_score", "total_time_ms"]

# make_raw_data.m keeps only subjects with a complete dataset: the daw version
# requires exactly 150 rows (125 experimental + 25 practice), the novel version is
# called as make_raw_data(150) from groupanalysis.m and requires >= 150.
COMPLETE_ROWS = 150

# groupanalysis.m: "does not analyze data for participants with more than 25 missed
# trials (>20% of all trials)" -- implemented there as `sum(missed) < 25`.
MAX_MISSED = 25

PARADIGMS = {
    "daw": DAW_COLUMNS,
    "novel": NOVEL_COLUMNS,
}


def load_trials(paradigm: str):
    """Return (subject_ids, values) read straight out of data.mat."""
    columns = PARADIGMS[paradigm]
    data = loadmat(kool_paradigm_dir(paradigm) / "data.mat", squeeze_me=True)["data"]
    expected = len(columns) + 1
    if data.shape[1] != expected:
        raise ValueError(f"{paradigm}: data.mat has {data.shape[1]} columns, "
                         f"expected {expected}")
    ids = np.array([str(x) for x in data[:, 0]])
    values = np.array([[float(np.asarray(c).ravel()[0]) for c in row]
                       for row in data[:, 1:]], dtype=float)
    return ids, values


def _fmt(value: float) -> str:
    """Keep integral values integral so the CSV stays readable."""
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def load_subinfo(paradigm: str) -> dict[str, dict]:
    """Subject-level info from subinfo.mat, keyed by subject ID.

    The iteration order of this file is the order make_raw_data.m assigns its
    subject indices in, so it also defines subject_index.
    """
    subinfo = loadmat(kool_paradigm_dir(paradigm) / "subinfo.mat", squeeze_me=True)["subinfo"]
    out = {}
    for row in subinfo:
        record = {}
        for name, cell in zip(SUBINFO_COLUMNS, row):
            value = np.asarray(cell).ravel()[0]
            record[name] = str(value) if isinstance(value, str) else _fmt(float(value))
        out[record.pop("subject_id")] = record
    return out


def write_trials(paradigm: str) -> dict[str, dict]:
    columns = PARADIGMS[paradigm]
    ids, values = load_trials(paradigm)
    idx = {name: i for i, name in enumerate(columns)}
    reward_col = "win" if paradigm == "daw" else "points"

    out_path = PROCESSED / f"kool_{paradigm}_trials.csv"
    summary: dict[str, dict] = {}
    with out_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["subject_id", "subject_index"] + columns + ["missed"])
        kept = 0
        for subject in load_subinfo(paradigm):
            rows = values[ids == subject]
            if rows.shape[0] < COMPLETE_ROWS:
                continue  # incomplete dataset, skipped exactly as in make_raw_data.m
            kept += 1
            for row in rows:
                missed = int(row[idx["rt1"]] == -1 or row[idx["rt2"]] == -1)
                writer.writerow([subject, kept] + [_fmt(v) for v in row] + [missed])

            experimental = rows[rows[:, idx["practice"]] == 0]
            missed = ((experimental[:, idx["rt1"]] == -1)
                      | (experimental[:, idx["rt2"]] == -1))
            rewarded = experimental[:, idx[reward_col]]
            summary[subject] = {
                "subject_index": kept,
                "n_trials": int(experimental.shape[0]),
                "n_missed": int(missed.sum()),
                "analysed": int(missed.sum() < MAX_MISSED),
                "reward_rate": float((rewarded[~missed] > 0).mean()),
                "mean_reward": float(rewarded[~missed].mean()),
            }
    n_analysed = sum(s["analysed"] for s in summary.values())
    print(f"  {out_path.name}: {kept} subjects with complete data, "
          f"{n_analysed} analysed ({kept - n_analysed} with >= {MAX_MISSED} missed trials)")
    return summary


def write_subjects(paradigm: str, summary: dict[str, dict]) -> None:
    subinfo = load_subinfo(paradigm)
    out_path = PROCESSED / f"kool_{paradigm}_subjects.csv"
    fields = (["subject_id", "subject_index", "n_trials", "n_missed", "analysed",
               "reward_rate", "mean_reward"] + SUBINFO_COLUMNS[1:])
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for subject, info in summary.items():
            writer.writerow({"subject_id": subject, **info, **subinfo[subject]})
    print(f"  {out_path.name}: {len(summary)} rows")


# ---------------------------------------------------------------------------
# results.mat -- the authors' own model fits (mfit output over 12 variants).
# Rows are ordered as groupdata.subdata(groupdata.i), i.e. the analysed subjects.
# ---------------------------------------------------------------------------

MODEL_LABELS = {1: "hybrid", 2: "model_based", 3: "model_free"}


def analysed_subject_ids(paradigm: str, summary: dict[str, dict]) -> list[str]:
    """Subject IDs in groupdata.i order -- the row order of results.mat."""
    groupdata = loadmat(kool_paradigm_dir(paradigm) / "groupdata.mat", squeeze_me=True,
                        struct_as_record=False)["groupdata"]
    by_index = {info["subject_index"]: sid for sid, info in summary.items()}
    return [by_index[int(i)] for i in np.atleast_1d(groupdata.i)]


def write_published_params(paradigm: str, summary: dict[str, dict]) -> None:
    results = np.atleast_1d(loadmat(kool_paradigm_dir(paradigm) / "results.mat", squeeze_me=True,
                                    struct_as_record=False)["results"])
    subjects = analysed_subject_ids(paradigm, summary)

    all_params = ["inverse_temperature", "learning_rate", "eligibility_trace_decay",
                  "mixing_weight", "choice_stickiness", "response_stickiness"]
    fields = (["paradigm", "model_variant", "model", "has_choice_stickiness",
               "has_response_stickiness", "subject_id", "subject_index"]
              + all_params + ["loglik", "logpost", "bic", "aic"])

    out_path = PROCESSED / f"kool_{paradigm}_published_params.csv"
    n_rows = 0
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, restval="")
        writer.writeheader()
        for variant, res in enumerate(results, 1):
            names = [str(p.name).replace(" ", "_")
                     for p in np.atleast_1d(res.param)]
            x = np.atleast_2d(np.asarray(res.x, dtype=float))
            if x.shape[0] != len(subjects):
                raise ValueError(f"{paradigm} variant {variant}: results.mat has "
                                 f"{x.shape[0]} rows, groupdata.i has {len(subjects)}")
            opts = res.opts
            for i, subject in enumerate(subjects):
                row = {
                    "paradigm": paradigm,
                    "model_variant": variant,
                    "model": MODEL_LABELS[int(opts.model)],
                    "has_choice_stickiness": int(opts.st),
                    "has_response_stickiness": int(opts.respst),
                    "subject_id": subject,
                    "subject_index": summary[subject]["subject_index"],
                }
                row.update(dict(zip(names, (float(v) for v in x[i]))))
                for key in ("loglik", "logpost", "bic", "aic"):
                    row[key] = float(np.atleast_1d(getattr(res, key))[i])
                writer.writerow(row)
                n_rows += 1
    print(f"  {out_path.name}: {len(results)} model variants x {len(subjects)} "
          f"subjects = {n_rows} rows (variant 10 = full hybrid, the one reported)")


def main() -> int:
    ensure_dirs()
    for paradigm in PARADIGMS:
        print(f"Kool '{paradigm} paradigm':")
        summary = write_trials(paradigm)
        write_subjects(paradigm, summary)
        write_published_params(paradigm, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
