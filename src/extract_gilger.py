"""Extract the Gilger et al. (2024) study-030 logfiles into documented CSVs.

Gilger MD, Hellrung L, Neukam PT, Kroemer NB, Nebe S, Pooseh S, Deza-Lougovski YI &
Smolka MN (2024). "Arbitration between model-free and model-based control is not
affected by transient changes in tonic serotonin levels." J Psychopharmacol
38:178-187. doi:10.1177/02698811231216325

The data is not public. `sources/gilger2024/data/` holds the Psychtoolbox logfiles
copied from the Dresden lab share; each `.mat` is the task's whole workspace, saved
once per subject and session. The variable coding below is decoded from those files
and documented in sources/gilger2024/data/README.md and docs/codebook_gilger.md.

    A(1,t)    first-stage choice 1/2; NaN = stage-1 timeout
    A(2,t)    second-stage choice within state 1/2; NaN = stage-2 timeout,
              0 after a stage-1 timeout
    S(2,t)    second-stage state 2/3; 0 after a stage-1 timeout
    trans(t)  1 = common, 0 = rare; pre-drawn, so it is set on stage-1 timeouts too
    R(t)      reward 1/0
    RT(:,t)   reaction times in seconds; NaN = timeout
    dawrandomwalks(state-1, choice, t)   reward probabilities
    randCWS   "C_W_S" counterbalancing; C sets which state is common for choice 1

The tryptophan condition of each session is NOT in the logfiles (the study was
double-blind), so `condition` stays empty until the unblinding key is available.

The analysed sample (n = 98) comes from the lab's final participant list,
`final_sample/Participant characteristics.sav`, which names subjects but not the
reason anyone was left out.

Outputs (data/processed/):
    gilger_trials.csv               one row per trial, canonical column names
    gilger_trials_final_sample.csv  the same, restricted to the 98 analysed subjects
    gilger_sessions.csv             one row per logfile: missed trials and integrity
                                    checks
    gilger_subjects.csv             one row per subject: completion, the exclusion
                                    rule that can be applied from the logfiles, and
                                    membership of the final sample
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime

import numpy as np
import pyreadstat
from scipy.io import loadmat

from .paths import GILGER_DATA, PROCESSED, ensure_dirs

# The lab's curated set: one repaired logfile per subject and session. The other
# folders hold the pre-repair originals, discarded repeats and practice runs.
SESSION_DIR = GILGER_DATA / "Files_with_Timestamp"
FINAL_SAMPLE = GILGER_DATA / "final_sample" / "Participant characteristics.sav"

EXPECTED_COLUMNS = [
    "subject_id",
    "session",             # 1..3, from the (corrected) file name
    "condition",           # depletion / balanced / loading -- empty, see above
    "trial",               # 1..201
    "s1_choice",           # 1 or 2 (first-stage stimulus identity)
    "s1_rt_ms",
    "transition_common",   # 1 = common (70%), 0 = rare (30%)
    "s2_state",            # 1 or 2 (the logfile's 2/3, minus one)
    "s2_choice",           # 1 or 2 within the second-stage state
    "s2_rt_ms",
    "reward",              # 1 or 0
    "p_reward_1", "p_reward_2", "p_reward_3", "p_reward_4",
                           # indexed as (s2_state - 1) * 2 + s2_choice
    "timeout",             # 1 if either stage was missed
]

N_TRIALS = 201
COMMON_P = 0.7

# Logfile name: TS_030_<8-digit subject>_<session>__<yymmdd>_<hhmm>.mat
FILE_NAME = re.compile(r"TS_030_(\d{8})_([1-3])__(\d{6})_(\d{4})\.mat$")

# Test-run IDs the lab README lists ("9999", "8888", "0000"); one sits among the
# session files.
TEST_SUBJECTS = {"00009999", "00008888", "00000000"}

# Methods / Supplement: "five participants due to task unresponsiveness (more than
# 30% missing trials in at least one session)". The paper does not define a missing
# trial; `timeout` (either stage missed) is used, and stage-1-only is reported too.
MAX_MISSED_FRACTION = 0.30

VARIABLES = ["A", "S", "R", "RT", "trans", "dawrandomwalks", "rewprob", "randCWS",
             "nt", "Z", "aborted", "subjn", "session"]


def _fmt(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:.6g}"


def list_session_files() -> list[dict]:
    """The usable session logfiles, one per subject and session.

    Test runs are dropped. Where a session has two logfiles (00004863 session 1,
    3 Jul and 18 Sep 2014, the latter after its session 3), the earlier one is kept
    and the other is reported as a duplicate.
    """
    files = []
    for path in sorted(SESSION_DIR.glob("*.mat")):
        m = FILE_NAME.search(path.name)
        if not m:
            raise ValueError(f"unexpected logfile name: {path.name}")
        subject, session, day, clock = m.groups()
        files.append({
            "path": path,
            "subject_id": subject,
            "session": int(session),
            "started": datetime.strptime(day + clock, "%y%m%d%H%M"),
        })
    kept: dict[tuple[str, int], dict] = {}
    for f in sorted(files, key=lambda f: f["started"]):
        f["status"] = ("test_run" if f["subject_id"] in TEST_SUBJECTS else
                       "duplicate" if (f["subject_id"], f["session"]) in kept else "used")
        if f["status"] == "used":
            kept[(f["subject_id"], f["session"])] = f
    return sorted(files, key=lambda f: (f["subject_id"], f["session"], f["started"]))


def load_final_sample() -> set[str]:
    """Subject IDs of the analysed sample, zero-padded like the logfile names."""
    data, _ = pyreadstat.read_sav(FINAL_SAMPLE, output_format="dict")
    return {f"{int(x):08d}" for x in data["Subject_ID"]}


def load_session(path) -> dict:
    s = loadmat(path, variable_names=VARIABLES, squeeze_me=True, struct_as_record=False)
    choice1 = np.asarray(s["A"][0], dtype=float)
    choice2 = np.asarray(s["A"][1], dtype=float)
    state2 = np.asarray(s["S"][1], dtype=float)
    rt = np.asarray(s["RT"], dtype=float)
    s1_timeout = np.isnan(choice1)
    s2_timeout = ~s1_timeout & (np.isnan(choice2) | (state2 == 0))
    return {
        "s": s,
        "choice1": choice1, "choice2": choice2, "state2": state2,
        "rt1": rt[0], "rt2": rt[1],
        "trans": np.asarray(s["trans"], dtype=bool),
        "reward": np.asarray(s["R"], dtype=float),
        "walks": np.asarray(s["dawrandomwalks"], dtype=float),
        "outcomes": np.asarray(s["rewprob"], dtype=bool),
        "s1_timeout": s1_timeout,
        "s2_timeout": s2_timeout,
        "timeout": s1_timeout | s2_timeout,
    }


def check_session(d: dict) -> dict:
    """Integrity counts; every one should be zero (or True) for a usable file."""
    s = d["s"]
    cws = str(s["randCWS"])
    code_c = int(cws[0])
    # Counterbalancing digit C: 2 -> choice 1 commonly leads to state 3,
    # 1 -> choice 1 commonly leads to state 2.
    common_state_of_choice1 = 3 if code_c == 2 else 2
    answered1 = ~d["s1_timeout"]
    implied_common = (d["choice1"] == 1) == (d["state2"] == common_state_of_choice1)
    answered2 = ~d["timeout"]
    t = np.flatnonzero(answered2)
    drawn = d["outcomes"][d["state2"][t].astype(int) - 2, d["choice2"][t].astype(int) - 1, t]
    return {
        "randCWS": cws,
        "n_trials": int(s["nt"]),
        "common_p": float(s["Z"].p),
        "aborted": int(s["aborted"]),
        "internal_subjn": str(s["subjn"]),
        "internal_session": str(s["session"]),
        "bad_transition": int((implied_common[answered1] != d["trans"][answered1]).sum()),
        "bad_reward": int((d["reward"][t] != drawn).sum()),
        "walks_in_bounds": int(d["walks"].min() >= 0.25 and d["walks"].max() <= 0.75),
    }


def trial_rows(f: dict, d: dict) -> list[list[str]]:
    rows = []
    for t in range(len(d["choice1"])):
        s1_missed, missed = bool(d["s1_timeout"][t]), bool(d["timeout"][t])
        state = None if s1_missed else d["state2"][t] - 1
        choice2 = None if missed else d["choice2"][t]
        rows.append([
            f["subject_id"], f["session"], "", t + 1,
            _fmt(None if s1_missed else d["choice1"][t]),
            _fmt(None if s1_missed else round(d["rt1"][t] * 1000, 1)),
            _fmt(None if s1_missed else int(d["trans"][t])),
            _fmt(state),
            _fmt(choice2),
            _fmt(None if missed else round(d["rt2"][t] * 1000, 1)),
            _fmt(None if missed else d["reward"][t]),
            *(_fmt(d["walks"][st, ch, t]) for st in (0, 1) for ch in (0, 1)),
            int(missed),
        ])
    return rows


def write_trials(final: set[str]) -> list[dict]:
    """Write the trial tables and gilger_sessions.csv; return the session records."""
    sessions = []
    trials_path = PROCESSED / "gilger_trials.csv"
    final_path = PROCESSED / "gilger_trials_final_sample.csv"
    with trials_path.open("w", newline="") as fh, final_path.open("w", newline="") as fh_final:
        writer, writer_final = csv.writer(fh), csv.writer(fh_final)
        writer.writerow(EXPECTED_COLUMNS)
        writer_final.writerow(EXPECTED_COLUMNS)
        for f in list_session_files():
            d = load_session(f["path"])
            n = len(d["choice1"])
            record = {
                "subject_id": f["subject_id"],
                "session": f["session"],
                "file": f["path"].name,
                "started": f["started"].isoformat(sep=" ", timespec="minutes"),
                "status": f["status"],
                "n_missed": int(d["timeout"].sum()),
                "n_missed_s1": int(d["s1_timeout"].sum()),
                "n_missed_s2": int(d["s2_timeout"].sum()),
                "pct_missed": round(100 * d["timeout"].sum() / n, 1),
                **check_session(d),
            }
            sessions.append(record)
            if f["status"] == "used":
                rows = trial_rows(f, d)
                writer.writerows(rows)
                if f["subject_id"] in final:
                    writer_final.writerows(rows)

    sessions_path = PROCESSED / "gilger_sessions.csv"
    with sessions_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(sessions[0]))
        writer.writeheader()
        writer.writerows(sessions)
    used = [s for s in sessions if s["status"] == "used"]
    used_final = [s for s in used if s["subject_id"] in final]
    print(f"  {trials_path.name}: {len(used)} sessions x {N_TRIALS} trials")
    print(f"  {final_path.name}: {len({s['subject_id'] for s in used_final})} subjects, "
          f"{len(used_final)} sessions x {N_TRIALS} trials")
    print(f"  {sessions_path.name}: {len(sessions)} logfiles "
          f"({len(sessions) - len(used)} not used: test run / duplicate)")
    return sessions


def write_subjects(sessions: list[dict], final: set[str]) -> list[dict]:
    by_subject: dict[str, list[dict]] = {}
    for s in sessions:
        if s["status"] == "used":
            by_subject.setdefault(s["subject_id"], []).append(s)

    subjects = []
    for subject, rows in sorted(by_subject.items()):
        rows.sort(key=lambda r: r["session"])
        completer = sorted(r["session"] for r in rows) == [1, 2, 3]
        worst = max(r["n_missed"] for r in rows) / N_TRIALS
        worst_s1 = max(r["n_missed_s1"] for r in rows) / N_TRIALS
        subjects.append({
            "subject_id": subject,
            "sessions": "".join(str(r["session"]) for r in rows),
            "completer": int(completer),
            **{f"pct_missed_s{r['session']}": r["pct_missed"] for r in rows},
            "max_pct_missed": round(100 * worst, 1),
            "max_pct_missed_stage1": round(100 * worst_s1, 1),
            "excl_unresponsive": int(completer and worst > MAX_MISSED_FRACTION),
            "excl_unresponsive_stage1": int(completer and worst_s1 > MAX_MISSED_FRACTION),
            "in_final_sample": int(subject in final),
        })
    missing = final - set(by_subject)
    if missing:
        raise ValueError(f"final-sample subjects without logfiles: {sorted(missing)}")

    fields = ["subject_id", "sessions", "completer", "pct_missed_s1", "pct_missed_s2",
              "pct_missed_s3", "max_pct_missed", "max_pct_missed_stage1",
              "excl_unresponsive", "excl_unresponsive_stage1", "in_final_sample"]
    out_path = PROCESSED / "gilger_subjects.csv"
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(subjects)
    completers = [s for s in subjects if s["completer"]]
    excluded = [s["subject_id"] for s in completers if s["excl_unresponsive"]]
    print(f"  {out_path.name}: {len(subjects)} subjects, {len(completers)} with all "
          f"three sessions; {len(excluded)} with > {MAX_MISSED_FRACTION:.0%} missed "
          f"trials in a session: {', '.join(excluded)}")
    return subjects


def main() -> int:
    ensure_dirs()
    if not SESSION_DIR.exists():
        print(f"No logfiles at {SESSION_DIR} -- see docs/codebook_gilger.md.")
        return 0
    print("Gilger et al. (2024), study 030:")
    final = load_final_sample()
    write_subjects(write_trials(final), final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
