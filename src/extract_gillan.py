"""Extract Gillan et al. (2016) OSF data into documented CSVs.

The per-subject task files on OSF are headerless and ragged: two demographic rows,
then a variable number of instruction rows (subjects could repeat `instructionLoop`),
then the trials. Column names come from the project's own readme.rtf.

The readme says "task data starts the row after the one that lists
'twostep_instruct_9' in column C". That rule holds for every study-1 file but **for no
study-2 file at all**: study 2 was logged without the `INSTRUCT` rows, so the marker is
simply absent, and some study-2 files carry other event rows (`CoinBoxGoodness`)
instead. So trials are located structurally instead -- a trial row is the only kind
with exactly 15 fields and an integer in the first one. That rule was checked against
the marker rule on all 649 study-1 files and picks out exactly the same rows, so it is
strictly more general.

Two things the readme does not mention, established from the data itself (see
docs/codebook_gillan.md and validate.py):

  * The task had a response deadline of roughly 2500 ms per stage, and timed-out
    trials are coded with -1 rather than being absent.
  * On a timed-out stage the *stimulus* column is not set to -1 but left at a stale
    value of 2. Reading `s1_stim` without checking `s1_response` therefore invents a
    first-stage choice on every stage-1 timeout. The derived columns here
    (`s1_timeout`, `s2_timeout`, `timeout`, `transition_common`) encode this
    explicitly so downstream code cannot fall into it.

Outputs (data/processed/):
    gillan_study<n>_trials.csv      one row per trial, named columns, raw values
                                    preserved plus explicit missingness columns
    gillan_study<n>_subjects.csv    task summary + demographics merged with the
                                    self-report table; `in_selfreport` marks the
                                    analysed sample (548 / 1413)
    gillan_study2_items.csv         the 208 individual questionnaire items
    gillan_factor_weights.csv       item x factor loading matrix (AD / CIT / SW)
"""

from __future__ import annotations

import csv
import shutil
import sys

from .paths import GILLAN_OSF, PROCESSED, ensure_dirs

# Column names for the 15 fields of a trial row, from readme.rtf (cols A-O).
TRIAL_COLUMNS = [
    "trial_num",          # A: 1..200
    "drift1",             # B: reward probability of second-stage option 1
    "drift2",             # C: reward probability of second-stage option 2
    "drift3",             # D: reward probability of second-stage option 3
    "drift4",             # E: reward probability of second-stage option 4
    "s1_response",        # F: first-stage response side (left/right); -1 = timeout
    "s1_stim",            # G: first-stage stimulus chosen (1/2); the two options
                          #    never swap sides, so this is redundant with F.
                          #    STALE (=2) on a stage-1 timeout -- see s1_timeout.
    "s1_rt",              # H: first-stage reaction time, ms
    "transition",         # I: true = common, false = rare; -1 on a stage-1 timeout
    "s2_response",        # J: second-stage response side (left/right); -1 = timeout
    "s2_stim",            # K: second-stage stimulus chosen (1/2); also fixed sides.
                          #    STALE (=2) on a stage-2 timeout -- see s2_timeout.
    "s2_state",           # L: second-stage state identity (2 or 3); -1 if no
                          #    first-stage response was made
    "s2_rt",              # M: second-stage reaction time, ms
    "reward",             # N: 1 = rewarded, 0 = not; -1 if the trial was not completed
    "redundant_col_o",    # O: redundant task variable, always 1
]

DERIVED_COLUMNS = [
    "s1_timeout",         # 1 = no first-stage response; s1_stim and everything
                          #     downstream of it are meaningless on this trial
    "s2_timeout",         # 1 = no second-stage response; s2_stim and reward are
                          #     meaningless, but s1 and the transition are valid
    "timeout",            # 1 = trial incomplete at either stage
    "transition_common",  # 1 = common, 0 = rare, empty on a stage-1 timeout
]

INT_COLUMNS = {"trial_num", "s1_stim", "s1_rt", "s2_stim", "s2_state", "s2_rt",
               "reward", "redundant_col_o"}
FLOAT_COLUMNS = {"drift1", "drift2", "drift3", "drift4"}

MISSING = "-1"
# The readme's marker, kept for reference; present in every study-1 file and no
# study-2 file. Trials are found structurally instead -- see parse_subject_file.
TASK_START_MARKER = "twostep_instruct_9"
EXPECTED_TRIALS = 200

STUDIES = {
    "study1": {
        "osf_folder": "Experiment 1",   # the directory name used on OSF
        "task_dir": "twostep_data_study1",
        "self_report": "self_report_study1.csv",
        "id_column": "subj.x",
    },
    "study2": {
        "osf_folder": "Experiment 2",
        "task_dir": "twostep_data_study2",
        "self_report": "self_report_study2.csv",
        "id_column": "subj",
    },
}


def parse_subject_file(path) -> tuple[list[dict], dict]:
    """Return (trials, meta) for one per-subject OSF task file."""
    with path.open(newline="") as fh:
        rows = list(csv.reader(fh))

    meta = {"subject_id": path.stem, "task_age": "", "task_gender": ""}
    for row in rows:
        if len(row) >= 2 and row[0] == "AgeDropdown":
            meta["task_age"] = row[1]
        elif len(row) >= 2 and row[0] == "GenderDropdown":
            meta["task_gender"] = row[1]

    trials = []
    for row in rows:
        if len(row) != len(TRIAL_COLUMNS):
            continue        # demographics, instruction and other event rows
        record = dict(zip(TRIAL_COLUMNS, (v.strip() for v in row)))
        try:
            int(record["trial_num"])
        except ValueError:
            continue        # a 15-field row that is not a trial
        trials.append(record)
    if not trials:
        raise ValueError(f"{path.name}: no trial rows found")

    numbers = [int(t["trial_num"]) for t in trials]
    meta["n_trials"] = len(trials)
    meta["first_trial"] = numbers[0]
    meta["trial_nums_contiguous"] = int(
        numbers == list(range(numbers[0], numbers[0] + len(numbers))))
    meta["n_s1_timeouts"] = sum(t["s1_response"] == MISSING for t in trials)
    meta["n_s2_timeouts"] = sum(t["s2_response"] == MISSING for t in trials)
    meta["n_timeouts"] = sum(t["s1_response"] == MISSING or t["s2_response"] == MISSING
                             for t in trials)
    return trials, meta


def normalise(record: dict) -> dict:
    """Add the explicit missingness columns and coerce numeric types.

    The raw column values are passed through unchanged, so the CSV stays a faithful
    copy of what OSF holds; the derived columns carry the interpretation.
    """
    out = dict(record)
    for key in INT_COLUMNS:
        out[key] = int(record[key]) if record[key] != "" else ""
    for key in FLOAT_COLUMNS:
        out[key] = float(record[key]) if record[key] != "" else ""

    s1_timeout = record["s1_response"] == MISSING
    s2_timeout = record["s2_response"] == MISSING
    out["s1_timeout"] = int(s1_timeout)
    out["s2_timeout"] = int(s2_timeout)
    out["timeout"] = int(s1_timeout or s2_timeout)

    transition = record["transition"].strip().lower()
    if s1_timeout:
        out["transition_common"] = ""      # no choice was made, so no transition
    elif transition in ("true", "false"):
        out["transition_common"] = int(transition == "true")
    else:
        raise ValueError(f"unexpected transition value {record['transition']!r} on a "
                         f"trial with a first-stage response")
    return out


def write_trials(study: str) -> dict[str, dict]:
    info = STUDIES[study]
    task_dir = GILLAN_OSF / info["osf_folder"] / info["task_dir"]
    files = sorted(task_dir.glob("*.csv"))
    if not files:
        raise RuntimeError(f"no task files in {task_dir}; run `python -m src.fetch` first")

    out_path = PROCESSED / f"gillan_{study}_trials.csv"
    header = ["subject_id"] + TRIAL_COLUMNS + DERIVED_COLUMNS
    metas: dict[str, dict] = {}
    n_trials_total = n_timeouts_total = 0
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for path in files:
            trials, meta = parse_subject_file(path)
            metas[meta["subject_id"]] = meta
            for trial in trials:
                writer.writerow({"subject_id": meta["subject_id"], **normalise(trial)})
            n_trials_total += len(trials)
            n_timeouts_total += meta["n_timeouts"]
    odd = [m["subject_id"] for m in metas.values()
           if m["n_trials"] != EXPECTED_TRIALS or m["first_trial"] != 1]
    print(f"  {out_path.name}: {len(metas)} subjects, {n_trials_total:,} trials, "
          f"{n_timeouts_total:,} timed out ({n_timeouts_total / n_trials_total:.1%})"
          + (f"; {len(odd)} subject(s) not a full 1..{EXPECTED_TRIALS}: "
             f"{', '.join(odd)}" if odd else ""))
    return metas


def read_self_report(study: str) -> tuple[list[str], dict[str, dict]]:
    info = STUDIES[study]
    path = GILLAN_OSF / info["osf_folder"] / info["self_report"]
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    # The first column is R's unnamed row-number column.
    fields = [f for f in rows[0] if f not in ("", info["id_column"])]
    return fields, {row[info["id_column"]]: {f: row[f] for f in fields} for row in rows}


def write_subjects(study: str, metas: dict[str, dict]) -> None:
    fields, self_report = read_self_report(study)
    out_path = PROCESSED / f"gillan_{study}_subjects.csv"
    header = (["subject_id", "n_trials", "first_trial", "trial_nums_contiguous",
               "n_s1_timeouts", "n_s2_timeouts", "n_timeouts", "task_age",
               "task_gender", "in_selfreport"] + fields)
    n_matched = 0
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, restval="")
        writer.writeheader()
        for subject, meta in metas.items():
            record = self_report.get(subject)
            n_matched += record is not None
            writer.writerow({**meta, "in_selfreport": int(record is not None),
                             **(record or {})})
    orphans = set(self_report) - set(metas)
    print(f"  {out_path.name}: {len(metas)} subjects, {n_matched} in the self-report "
          f"table (the analysed sample), {len(metas) - n_matched} task-only"
          + (f", {len(orphans)} self-report rows with no task file" if orphans else ""))


def copy_questionnaire_tables() -> None:
    """Copy the study-2 item-level table and the factor loading matrix through."""
    for src_name, dest_name in (
        ("individual_items_study2.csv", "gillan_study2_items.csv"),
        ("weights.csv", "gillan_factor_weights.csv"),
    ):
        src = GILLAN_OSF / STUDIES["study2"]["osf_folder"] / src_name
        if src.exists():
            shutil.copyfile(src, PROCESSED / dest_name)
            print(f"  {dest_name}: copied from {src_name}")


def main() -> int:
    ensure_dirs()
    for study in STUDIES:
        print(f"Gillan {study}:")
        metas = write_trials(study)
        write_subjects(study, metas)
    copy_questionnaire_tables()
    return 0


if __name__ == "__main__":
    sys.exit(main())
