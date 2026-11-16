"""Map every extracted dataset onto one canonical trial-level schema.

The point of this step is that the same quantity is called different things in each
source (Kool's `common` vs Gillan's `transition`, Kool's `state2` in {1,2} vs
Gillan's in {2,3}, Kool's `win` in points vs Gillan's binary `reward`, ...). Here
they all become the same columns with the same coding, so one analysis or one model
fit can run across datasets. See docs/codebook_harmonized.md.

Practice trials are dropped (Kool's daw and novel paradigms have 25 of them; the
authors drop them too) and trials are renumbered 1..N per subject and session.

Outputs (data/processed/):
    twostep_trials_harmonized.csv    one row per trial, all datasets stacked
    twostep_subjects_harmonized.csv  one row per subject and session, with the
                                     model-agnostic MB/MF stay indices, demographics,
                                     questionnaire scores and Kool's published fits
"""

from __future__ import annotations

import csv
import sys

from .paths import PROCESSED, ensure_dirs
from .stayprobs import CELL_NAMES, stay_indices

TRIAL_FIELDS = [
    "dataset",             # kool_daw | kool_novel | gillan_study1 | gillan_study2 | gilger
    "subject_id",
    "session",             # 1 for the online samples; 1..3 for Gilger
    "condition",           # within-subject condition label; empty except for Gilger,
                           # where it names the tryptophan level of that session
    "trial",               # trial number as the source records it, made 1-based and
                           # with practice trials excluded. Normally 1..N; one Gillan
                           # study-2 subject is missing trial 1 and runs 2..200
    "s1_state",            # first-stage state; always 1 except in kool_novel (1/2)
    "s1_choice",           # chosen first-stage stimulus identity (not the side)
    "s1_response_side",    # left / right where recorded
    "s1_rt_ms",
    "transition_common",   # 1 = common transition, 0 = rare; always 1 in kool_novel
    "s2_state",            # second-stage state, recoded to 1/2 everywhere
    "s2_choice",           # chosen second-stage option within the state (1/2);
                           # empty in kool_novel, which has a single stage-2 action
    "s2_choice_global",    # (s2_state - 1) * 2 + s2_choice, i.e. 1..4 -- the coding
                           # hBayesDM's ts_par7 calls level2_choice
    "s2_rt_ms",
    "reward",              # 1 = rewarded, 0 = not
    "reward_points",       # raw outcome magnitude (kool_daw: 0/1; kool_novel: -4..+5)
    "p_reward_1", "p_reward_2", "p_reward_3", "p_reward_4",
                           # drifting reward probability of second-stage option 1..4,
                           # indexed as s2_choice_global; empty in kool_novel
    "reward_value_1", "reward_value_2",
                           # kool_novel only: drifting point value of each
                           # second-stage state
    "timeout",             # 1 = subject failed to respond in time
    "prev_reward", "prev_transition_common", "prev_s1_choice",
    "stay",                # 1 = repeated the previous first-stage choice
    "usable_for_stay",     # 1 = this trial and the one before it were both answered,
                           # i.e. the trial enters the stay-probability analysis
]


def _num(value: str):
    if value == "":
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def _read(name: str) -> list[dict]:
    path = PROCESSED / name
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Per-source mapping onto the canonical schema
# ---------------------------------------------------------------------------

def _blank(value):
    """Kool codes every unobserved field as -1; turn those into empty cells."""
    return "" if value == -1 else value


def from_kool_daw(rows: list[dict]) -> list[dict]:
    """Map Kool's daw paradigm across.

    On a stage-1 timeout every field is -1; on a stage-2 timeout the first-stage
    choice, second-stage state and transition are valid and only choice2 and win are
    -1. Those sentinels become empty cells here, so no analysis can read a missed
    trial as an unrewarded one.
    """
    out = []
    for r in rows:
        if int(r["practice"]) == 1:
            continue
        choice1, left = _num(r["choice1"]), _num(r["stim_1_left"])
        state2, choice2, win = _num(r["state2"]), _num(r["choice2"]), _num(r["win"])
        out.append({
            "dataset": "kool_daw",
            "subject_id": r["subject_id"],
            "session": 1,
            # The experimental block restarts at 0 in the source; make it 1-based.
            "trial": _num(r["trial"]) + 1,
            "s1_state": 1,
            "s1_choice": _blank(choice1),
            "s1_response_side": "" if choice1 == -1 else
                                ("left" if choice1 == left else "right"),
            "s1_rt_ms": _blank(_num(r["rt1"])),
            "transition_common": _blank(_num(r["common"])),
            "s2_state": _blank(state2),
            "s2_choice": _blank(choice2),
            "s2_choice_global": "" if -1 in (choice2, state2)
                                else (state2 - 1) * 2 + choice2,
            "s2_rt_ms": _blank(_num(r["rt2"])),
            "reward": "" if win == -1 else int(win > 0),
            "reward_points": _blank(win),
            "p_reward_1": _num(r["ps1a1"]),
            "p_reward_2": _num(r["ps1a2"]),
            "p_reward_3": _num(r["ps2a1"]),
            "p_reward_4": _num(r["ps2a2"]),
            "timeout": int(r["missed"]),
        })
    return out


def from_kool_novel(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if int(r["practice"]) == 1:
            continue
        choice1, left = _num(r["choice1"]), _num(r["stim_left"])
        timeout = int(r["missed"]) == 1
        points = _num(r["points"])
        out.append({
            "dataset": "kool_novel",
            "subject_id": r["subject_id"],
            "session": 1,
            "trial": _num(r["trial"]) + 1,
            "s1_state": _num(r["state1"]),
            "s1_choice": _blank(choice1),
            "s1_response_side": "" if choice1 == -1 else
                                ("left" if choice1 == left else "right"),
            "s1_rt_ms": _blank(_num(r["rt1"])),
            # Transitions are deterministic in this paradigm, so every transition is
            # "common" by construction. Its w is therefore not on the same scale as
            # the Daw-type datasets -- do not pool it.
            "transition_common": "" if choice1 == -1 else 1,
            "s2_state": _blank(_num(r["state2"])),
            "s2_choice": "",          # a single stage-2 action (press space)
            "s2_choice_global": "",
            "s2_rt_ms": _blank(_num(r["rt2"])),
            # Unlike the daw paradigm this file records 0 points rather than -1 on a
            # missed trial, which is indistinguishable from a genuine zero outcome,
            # so it is blanked on the strength of the timeout flag instead.
            "reward": "" if timeout else int(points > 0),
            "reward_points": "" if timeout else points,
            "reward_value_1": _num(r["rews1"]),
            "reward_value_2": _num(r["rews2"]),
            "timeout": int(timeout),
        })
    return out


def from_gillan(rows: list[dict], dataset: str) -> list[dict]:
    """Map Gillan rows across, dropping the values that are stale on a timeout.

    On a stage-1 timeout the raw file still carries s1_stim = 2 and on a stage-2
    timeout s2_stim = 2, even though no response was made. Those become empty here,
    so a stay analysis cannot mistake them for choices. A stage-2 timeout leaves the
    first-stage choice and the transition intact, so only the second stage is blanked.
    """
    out = []
    for r in rows:
        s1_timeout = int(r["s1_timeout"]) == 1
        s2_timeout = int(r["s2_timeout"]) == 1
        # The second-stage states are labelled 2 and 3 in the raw files.
        state2 = "" if s1_timeout else _num(r["s2_state"]) - 1
        choice2 = "" if (s1_timeout or s2_timeout) else _num(r["s2_stim"])
        out.append({
            "dataset": dataset,
            "subject_id": r["subject_id"],
            "session": 1,
            "trial": _num(r["trial_num"]),
            "s1_state": 1,
            "s1_choice": "" if s1_timeout else _num(r["s1_stim"]),
            "s1_response_side": "" if s1_timeout else r["s1_response"],
            "s1_rt_ms": _num(r["s1_rt"]),
            "transition_common": "" if s1_timeout else _num(r["transition_common"]),
            "s2_state": state2,
            "s2_choice": choice2,
            "s2_choice_global": "" if choice2 == "" else (state2 - 1) * 2 + choice2,
            "s2_rt_ms": "" if s1_timeout else _num(r["s2_rt"]),
            "reward": "" if (s1_timeout or s2_timeout) else _num(r["reward"]),
            "reward_points": "" if (s1_timeout or s2_timeout) else _num(r["reward"]),
            "p_reward_1": _num(r["drift1"]),
            "p_reward_2": _num(r["drift2"]),
            "p_reward_3": _num(r["drift3"]),
            "p_reward_4": _num(r["drift4"]),
            "timeout": int(r["timeout"]),
        })
    return out


def from_gilger(rows: list[dict]) -> list[dict]:
    """Pass through a gilger_trials.csv that already uses the canonical names."""
    out = []
    for r in rows:
        record = {"dataset": "gilger"}
        for field in TRIAL_FIELDS:
            if field not in r:
                continue
            try:
                record[field] = _num(r[field])
            except ValueError:
                record[field] = r[field]   # a label such as the condition name
        record.setdefault("s1_state", 1)
        if record.get("s2_state") and record.get("s2_choice"):
            record["s2_choice_global"] = (int(record["s2_state"]) - 1) * 2 \
                                         + int(record["s2_choice"])
        out.append(record)
    return out


# ---------------------------------------------------------------------------

def add_derived(trials: list[dict]) -> list[dict]:
    """Renumber trials and add the previous-trial and stay columns, per session."""
    by_session: dict[tuple, list[dict]] = {}
    for row in trials:
        by_session.setdefault((row["dataset"], row["subject_id"], row["session"]),
                              []).append(row)
    for rows in by_session.values():
        # Keep the source's own trial numbering -- it is the truth about what the
        # subject saw. One Gillan study-2 subject is missing trial 1 and so runs
        # 2..200; renumbering would silently misalign them against everyone else.
        rows.sort(key=lambda r: r.get("trial") or 0)
        for i, row in enumerate(rows, 1):
            row.setdefault("trial", i)
        prev = None
        for row in rows:
            if prev is None:
                row["prev_reward"] = row["prev_transition_common"] = ""
                row["prev_s1_choice"] = row["stay"] = ""
                row["usable_for_stay"] = 0
            else:
                row["prev_reward"] = prev["reward"]
                row["prev_transition_common"] = prev["transition_common"]
                row["prev_s1_choice"] = prev["s1_choice"]
                usable = not (row["timeout"] or prev["timeout"])
                row["stay"] = int(row["s1_choice"] == prev["s1_choice"]) if usable else ""
                row["usable_for_stay"] = int(usable)
            prev = row
    return [row for rows in by_session.values() for row in rows]


def write_trials(trials: list[dict]) -> None:
    out_path = PROCESSED / "twostep_trials_harmonized.csv"
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRIAL_FIELDS, restval="",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trials)
    counts: dict[str, int] = {}
    subjects: dict[str, set] = {}
    for row in trials:
        counts[row["dataset"]] = counts.get(row["dataset"], 0) + 1
        subjects.setdefault(row["dataset"], set()).add(row["subject_id"])
    print(f"  {out_path.name}: {len(trials):,} trials")
    for dataset in sorted(counts):
        print(f"    {dataset:<14} {len(subjects[dataset]):>5} subjects, "
              f"{counts[dataset]:>7,} trials")


# ---------------------------------------------------------------------------
# Subject-level table
# ---------------------------------------------------------------------------

SUBJECT_FIELDS = (
    ["dataset", "subject_id", "session", "condition", "n_trials", "n_timeouts",
     "analysed",
     "reward_rate", "age", "gender", "gender_raw", "iq"]
    + CELL_NAMES + ["n_stay_trials", "mf_index", "mb_index"]
    + ["oci_total", "sds_total", "stai_total", "audit_total", "eat_total",
       "bis_total", "scz_total", "aes_total", "lsas_total",
       "factor_anxious_depression", "factor_compulsivity_intrusive_thought",
       "factor_social_withdrawal"]
    + ["kool_inverse_temperature", "kool_learning_rate",
       "kool_eligibility_trace_decay", "kool_mixing_weight",
       "kool_choice_stickiness", "kool_response_stickiness"]
)

GILLAN_TOTALS = ["oci_total", "sds_total", "stai_total", "audit_total", "eat_total",
                 "bis_total", "scz_total", "aes_total", "lsas_total"]
GILLAN_FACTORS = {"Factor1": "factor_anxious_depression",
                  "Factor2": "factor_compulsivity_intrusive_thought",
                  "Factor3": "factor_social_withdrawal"}
# The full hybrid model with both stickiness terms -- the variant Kool et al. report.
KOOL_REPORTED_VARIANT = "10"


def kool_published(paradigm: str) -> dict[str, dict]:
    out = {}
    for r in _read(f"kool_{paradigm}_published_params.csv"):
        if r["model_variant"] != KOOL_REPORTED_VARIANT:
            continue
        out[r["subject_id"]] = {
            f"kool_{k}": r[k] for k in
            ("inverse_temperature", "learning_rate", "eligibility_trace_decay",
             "mixing_weight", "choice_stickiness", "response_stickiness")
        }
    return out


def subject_extras() -> dict[tuple[str, str], dict]:
    """Demographics, questionnaires and published fits, keyed by (dataset, subject)."""
    extras: dict[tuple[str, str], dict] = {}
    for paradigm in ("daw", "novel"):
        dataset = f"kool_{paradigm}"
        fits = kool_published(paradigm)
        for r in _read(f"kool_{paradigm}_subjects.csv"):
            extras[(dataset, r["subject_id"])] = {
                "age": r["age"],
                "gender": r["gender"],
                "gender_raw": r["gender"],
                "analysed": r["analysed"],
                **fits.get(r["subject_id"], {}),
            }
    for study in ("study1", "study2"):
        dataset = f"gillan_{study}"
        for r in _read(f"gillan_{study}_subjects.csv"):
            gender = r.get("task_gender", "").strip().lower()
            record = {
                "age": r.get("age") or r.get("task_age", ""),
                "gender": {"female": "f", "male": "m"}.get(gender, ""),
                "gender_raw": r.get("task_gender", ""),
                "iq": r.get("iq", ""),
                # The self-report table defines the analysed sample (548 / 1413).
                "analysed": r.get("in_selfreport", ""),
            }
            for key in GILLAN_TOTALS:
                if r.get(key):
                    record[key] = r[key]
            for src, dest in GILLAN_FACTORS.items():
                if r.get(src):
                    record[dest] = r[src]
            extras[(dataset, r["subject_id"])] = record
    return extras


def write_subjects(trials: list[dict]) -> None:
    grouped: dict[tuple, list[dict]] = {}
    for row in trials:
        grouped.setdefault((row["dataset"], row["subject_id"], row["session"]),
                           []).append(row)
    extras = subject_extras()

    out_path = PROCESSED / "twostep_subjects_harmonized.csv"
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUBJECT_FIELDS, restval="",
                                extrasaction="ignore")
        writer.writeheader()
        for (dataset, subject, session), rows in grouped.items():
            rows.sort(key=lambda r: r["trial"])
            answered = [r for r in rows if not r["timeout"]]
            indices = stay_indices(
                [r["s1_choice"] for r in rows],
                [r["reward"] for r in rows],
                [r["transition_common"] for r in rows],
                [bool(r["timeout"]) for r in rows],
            )
            writer.writerow({
                "dataset": dataset,
                "subject_id": subject,
                "session": session,
                "condition": rows[0].get("condition", ""),
                "n_trials": len(rows),
                "n_timeouts": sum(r["timeout"] for r in rows),
                "reward_rate": (sum(r["reward"] for r in answered) / len(answered)
                                if answered else ""),
                **indices,
                **extras.get((dataset, subject), {}),
            })
    print(f"  {out_path.name}: {len(grouped)} subject-sessions")


def main() -> int:
    ensure_dirs()
    print("Harmonizing:")
    trials: list[dict] = []
    trials += from_kool_daw(_read("kool_daw_trials.csv"))
    trials += from_kool_novel(_read("kool_novel_trials.csv"))
    trials += from_gillan(_read("gillan_study1_trials.csv"), "gillan_study1")
    trials += from_gillan(_read("gillan_study2_trials.csv"), "gillan_study2")
    gilger = _read("gilger_trials.csv")
    if gilger:
        trials += from_gilger(gilger)
    else:
        print("    (no gilger_trials.csv -- see docs/codebook_gilger.md)")
    if not trials:
        raise RuntimeError("nothing to harmonize; run the extract_* steps first")
    trials = add_derived(trials)
    write_trials(trials)
    write_subjects(trials)
    return 0


if __name__ == "__main__":
    sys.exit(main())
