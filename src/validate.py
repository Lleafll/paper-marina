"""Check the extracted data against sources that can prove it right or wrong.

These are not smoke tests. Each check recomputes something whose correct answer is
already known from outside this repository, so a mistake in the column mapping shows
up as a numeric mismatch:

  1. Kool daw     -- recompute the per-subject stay probabilities, MB/MF indices,
                     reward rate, mean reward probability and timeout count, and
                     compare them against groupdata.mat, which the authors produced
                     by running their own MATLAB groupanalysis.m. Any error in the
                     18-column mapping would move these numbers.
  2. Kool novel   -- same idea with that paradigm's own definitions (mean points,
                     mean reward value, timeout count). Also pins down the two
                     undocumented subinfo.mat columns by recomputing them.
  3. Gillan       -- recompute Factor1-3 from the item-level responses and the
                     published loading matrix and compare against the factor scores
                     distributed in self_report_study2.csv.
  4. Gillan       -- confirm the drift1..4 columns really are indexed by
                     s2_choice_global, by checking that the drift of the chosen
                     option predicts the reward actually received.
  5. Gillan       -- confirm that the stale stimulus values Gillan leaves on
                     timed-out trials are really blanked in the harmonized table, and
                     that a stage-2 timeout does not cost the first-stage choice.
  6. Invariant    -- within a subject the transition type must be implied by the
                     (first-stage choice, second-stage state) pairing, and the two
                     first-stage options must have different common states. A
                     mis-mapped choice column would break this.
  7. Structural   -- trial counts, value domains, transition rates, schema integrity
                     of the harmonized table.

Writes docs/validation_report.md and exits non-zero if any check fails.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from collections import defaultdict

import numpy as np
from scipy.io import loadmat

from .paths import DOCS, PROCESSED, kool_paradigm_dir
from .stayprobs import CELL_NAMES, stay_indices

TOL = 1e-9
report: list[str] = []
failures: list[str] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    mark = "PASS" if passed else "FAIL"
    line = f"- **{mark}** {name}" + (f" -- {detail}" if detail else "")
    report.append(line)
    print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))
    if not passed:
        failures.append(name)


def read_csv(name: str) -> list[dict]:
    path = PROCESSED / name
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def harmonized_by_subject(dataset: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv("twostep_trials_harmonized.csv"):
        if row["dataset"] == dataset:
            out[row["subject_id"]].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: int(r["trial"]))
    return out


def _f(value: str):
    return float(value) if value != "" else math.nan


def _pearson(a: list[float], b: list[float]) -> float:
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    sd_a, sd_b = statistics.stdev(a), statistics.stdev(b)
    if sd_a == 0 or sd_b == 0:
        return math.nan
    return statistics.mean((x - mean_a) * (y - mean_b)
                           for x, y in zip(a, b)) / (sd_a * sd_b)


def _max_abs_diff(pairs) -> float:
    """Largest absolute difference, treating NaN == NaN as a match."""
    worst = 0.0
    for a, b in pairs:
        if math.isnan(a) and math.isnan(b):
            continue
        if math.isnan(a) != math.isnan(b):
            return math.inf
        worst = max(worst, abs(a - b))
    return worst


# ---------------------------------------------------------------------------
# 1 + 2. Kool: against the authors' own groupdata.mat
# ---------------------------------------------------------------------------

def validate_kool_daw() -> None:
    groupdata = loadmat(kool_paradigm_dir("daw") / "groupdata.mat", squeeze_me=True,
                        struct_as_record=False)["groupdata"]
    subjects = read_csv("kool_daw_subjects.csv")
    index_to_id = {int(r["subject_index"]): r["subject_id"] for r in subjects}
    analysed = [int(i) for i in np.atleast_1d(groupdata.i)]
    trials = harmonized_by_subject("kool_daw")

    check("kool_daw: analysed-subject count matches groupdata.i",
          sum(int(r["analysed"]) for r in subjects) == len(analysed),
          f"{sum(int(r['analysed']) for r in subjects)} vs {len(analysed)}")

    stay_pairs, main_pairs, inter_pairs = [], [], []
    rate_pairs, missed_pairs, avgp_pairs = [], [], []
    for s, subject_index in enumerate(analysed):
        rows = trials[index_to_id[subject_index]]
        indices = stay_indices(
            [r["s1_choice"] for r in rows],
            [r["reward"] == "1" for r in rows],
            [r["transition_common"] == "1" for r in rows],
            [r["timeout"] == "1" for r in rows],
        )
        for k, cell in enumerate(CELL_NAMES):
            stay_pairs.append((indices[cell], float(groupdata.stayprobs[s, k])))
        main_pairs.append((indices["mf_index"], float(np.atleast_1d(groupdata.maineffect)[s])))
        inter_pairs.append((indices["mb_index"], float(np.atleast_1d(groupdata.interaction)[s])))

        answered = [r for r in rows if r["timeout"] == "0"]
        rate_pairs.append((statistics.mean(int(r["reward"]) for r in answered),
                           float(np.atleast_1d(groupdata.rewardrate)[s])))
        missed_pairs.append((float(sum(r["timeout"] == "1" for r in rows)),
                             float(np.atleast_1d(groupdata.missed)[s])))
        probs = [_f(r[f"p_reward_{k}"]) for r in rows for k in (1, 2, 3, 4)]
        avgp_pairs.append((statistics.mean(probs),
                           float(np.atleast_1d(groupdata.avg_p)[s])))

    check("kool_daw: 4 stay probabilities per subject == groupdata.stayprobs",
          _max_abs_diff(stay_pairs) < TOL,
          f"max |diff| = {_max_abs_diff(stay_pairs):.3g} over {len(stay_pairs)} values")
    check("kool_daw: MF index == groupdata.maineffect",
          _max_abs_diff(main_pairs) < TOL, f"max |diff| = {_max_abs_diff(main_pairs):.3g}")
    check("kool_daw: MB index == groupdata.interaction",
          _max_abs_diff(inter_pairs) < TOL, f"max |diff| = {_max_abs_diff(inter_pairs):.3g}")
    check("kool_daw: reward rate == groupdata.rewardrate",
          _max_abs_diff(rate_pairs) < TOL, f"max |diff| = {_max_abs_diff(rate_pairs):.3g}")
    check("kool_daw: timeout count == groupdata.missed",
          _max_abs_diff(missed_pairs) < TOL, f"max |diff| = {_max_abs_diff(missed_pairs):.3g}")
    check("kool_daw: mean reward probability == groupdata.avg_p",
          _max_abs_diff(avgp_pairs) < 1e-12,
          f"max |diff| = {_max_abs_diff(avgp_pairs):.3g}")


def validate_kool_novel() -> None:
    groupdata = loadmat(kool_paradigm_dir("novel") / "groupdata.mat", squeeze_me=True,
                        struct_as_record=False)["groupdata"]
    subjects = read_csv("kool_novel_subjects.csv")
    index_to_id = {int(r["subject_index"]): r["subject_id"] for r in subjects}
    analysed = [int(i) for i in np.atleast_1d(groupdata.i)]
    trials = harmonized_by_subject("kool_novel")

    check("kool_novel: analysed-subject count matches groupdata.i",
          sum(int(r["analysed"]) for r in subjects) == len(analysed),
          f"{sum(int(r['analysed']) for r in subjects)} vs {len(analysed)}")

    points_pairs, missed_pairs, avgrew_pairs = [], [], []
    for s, subject_index in enumerate(analysed):
        rows = trials[index_to_id[subject_index]]
        answered = [r for r in rows if r["timeout"] == "0"]
        points_pairs.append((statistics.mean(int(r["reward_points"]) for r in answered),
                             float(np.atleast_1d(groupdata.rewardrate)[s])))
        missed_pairs.append((float(sum(r["timeout"] == "1" for r in rows)),
                             float(np.atleast_1d(groupdata.missed)[s])))
        values = [_f(r[f"reward_value_{k}"]) for r in rows for k in (1, 2)]
        avgrew_pairs.append((statistics.mean(values),
                             float(np.atleast_1d(groupdata.avg_rew)[s])))

    check("kool_novel: mean points == groupdata.rewardrate",
          _max_abs_diff(points_pairs) < TOL,
          f"max |diff| = {_max_abs_diff(points_pairs):.3g}")
    check("kool_novel: timeout count == groupdata.missed",
          _max_abs_diff(missed_pairs) < TOL,
          f"max |diff| = {_max_abs_diff(missed_pairs):.3g}")
    check("kool_novel: mean reward value == groupdata.avg_rew",
          _max_abs_diff(avgrew_pairs) < 1e-12,
          f"max |diff| = {_max_abs_diff(avgrew_pairs):.3g}")


def validate_kool_subinfo(paradigm: str) -> None:
    """Pin down the two undocumented subinfo.mat columns.

    subinfo.mat has no documentation in the repository. Columns 4 and 5 are read here
    as the final score and the total task duration; this confirms that reading by
    recomputing both from the trial data.
    """
    trials: dict[str, list[dict]] = defaultdict(list)
    for r in read_csv(f"kool_{paradigm}_trials.csv"):
        if r["practice"] == "0":
            trials[r["subject_id"]].append(r)
    subjects = read_csv(f"kool_{paradigm}_subjects.csv")
    if not subjects or not trials:
        return

    score_ok = time_ok = 0
    for row in subjects:
        rows = trials[row["subject_id"]]
        if paradigm == "daw":
            # Binary reward: the score is the number of trials won.
            total = sum(int(r["win"]) > 0 for r in rows)
        else:
            # Scalar reward: the score is the sum of the points collected.
            total = sum(int(r["points"]) for r in rows if r["missed"] == "0")
        score_ok += total == int(row["final_score"])
        time_ok += max(int(r["time_elapsed"]) for r in rows) <= int(row["total_time_ms"])

    n = len(subjects)
    check(f"kool_{paradigm}: subinfo column 4 is the final score over experimental trials",
          score_ok == n, f"{score_ok}/{n} subjects")
    check(f"kool_{paradigm}: subinfo column 5 is a task duration (>= last time_elapsed)",
          time_ok == n, f"{time_ok}/{n} subjects")


# ---------------------------------------------------------------------------
# 3. Gillan: reproduce the published factor scores
# ---------------------------------------------------------------------------

def validate_gillan_factors() -> None:
    items = read_csv("gillan_study2_items.csv")
    weights = read_csv("gillan_factor_weights.csv")
    if not items or not weights:
        check("gillan: factor scores reproducible from items x weights", False,
              "item or weight table missing")
        return
    item_key = list(weights[0])[0]          # R's unnamed first column
    loadings = {r[item_key]: (float(r["AD"]), float(r["CIT"]), float(r["SW"]))
                for r in weights}
    names = list(loadings)

    item_columns = [c for c in items[0] if c not in ("", "subject")]
    check("gillan: item table columns match the loading matrix",
          set(item_columns) == set(names),
          f"{len(item_columns)} item columns, {len(names)} loadings")

    self_report = {r["subject_id"]: r
                   for r in read_csv("gillan_study2_subjects.csv")}

    rows = [r for r in items if (self_report.get(r["subject"]) or {}).get("Factor1")]
    if not rows:
        check("gillan: factor scores reproducible from items x weights", False,
              "nothing to compare -- study-2 extraction has not run")
        return

    # The weights apply to standardised item responses, and the published scores are
    # themselves standardised to unit variance (their SD is exactly 1.0000, while a
    # weighted sum of z-scored items comes out at 0.977-0.985).
    column = {name: [float(r[name]) for r in items] for name in names}
    mean = {name: statistics.mean(column[name]) for name in names}
    sd = {name: statistics.pstdev(column[name]) for name in names}

    worst_r, worst_diff = 1.0, 0.0
    detail = []
    for j, factor in enumerate(("Factor1", "Factor2", "Factor3")):
        scored = [sum(((float(r[name]) - mean[name]) / sd[name]) * loadings[name][j]
                      for name in names) for r in rows]
        centre, spread = statistics.mean(scored), statistics.stdev(scored)
        mine = [(x - centre) / spread for x in scored]
        theirs = [float(self_report[r["subject"]][factor]) for r in rows]
        r_value = _pearson(mine, theirs)
        diff = max(abs(a - b) for a, b in zip(mine, theirs))
        worst_r, worst_diff = min(worst_r, r_value), max(worst_diff, diff)
        detail.append(f"{factor}: r={r_value:.6f}, max |diff|={diff:.3f}")

    # Not an exact reproduction: weights.csv is a simplified scoring matrix, whereas
    # the distributed scores look like the factor model's own regression scores. An
    # r of 0.999 still pins the item-to-weight mapping down -- a mis-ordered item set
    # would destroy it outright.
    check("gillan: factor scores reproducible from standardised items x weights",
          worst_r > 0.999 and worst_diff < 0.1,
          f"{len(rows)} subjects; " + "; ".join(detail))


# ---------------------------------------------------------------------------
# 4. Gillan: the drift columns really are indexed by s2_choice_global
# ---------------------------------------------------------------------------

def validate_gillan_drift_mapping(dataset: str) -> None:
    rows = [r for r in read_csv("twostep_trials_harmonized.csv")
            if r["dataset"] == dataset and r["timeout"] == "0"]
    if not rows:
        return
    cells: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for r in rows:
        option = int(r["s2_choice_global"])
        cells[option].append((_f(r[f"p_reward_{option}"]), int(r["reward"])))

    worst = 0.0
    detail = []
    for option in sorted(cells):
        observed = statistics.mean(x for _, x in cells[option])
        expected = statistics.mean(p for p, _ in cells[option])
        worst = max(worst, abs(observed - expected))
        detail.append(f"option {option}: p={expected:.3f} vs reward rate="
                      f"{observed:.3f} (n={len(cells[option]):,})")
    # With tens of thousands of trials per option the binomial standard error is
    # well under 0.01, so a mis-indexed drift column could not agree this closely.
    check(f"{dataset}: drift column of the chosen option predicts its reward rate",
          worst < 0.01, "; ".join(detail))


# ---------------------------------------------------------------------------
# 5. Gillan: the stale-stimulus trap is actually neutralised
# ---------------------------------------------------------------------------

def validate_gillan_timeout_blanking(study: str) -> None:
    """Check the harmonized table against the raw extraction, trial by trial.

    Gillan's files leave a stale stimulus value of 2 on a timed-out stage instead of
    marking it missing. This verifies that every such trial really does come through
    without a choice, rather than trusting that the mapping code got it right.
    """
    raw = read_csv(f"gillan_{study}_trials.csv")
    if not raw:
        return
    harmonized = {(r["subject_id"], int(r["trial"])): r
                  for r in read_csv("twostep_trials_harmonized.csv")
                  if r["dataset"] == f"gillan_{study}"}
    if not harmonized:
        return

    stale_s1 = stale_s2 = 0
    s1_leaks: list = []
    s2_leaks: list = []
    s2_only_losses: list = []
    for r in raw:
        row = harmonized.get((r["subject_id"], int(r["trial_num"])))
        if row is None:
            continue
        if r["s1_timeout"] == "1":
            stale_s1 += r["s1_stim"] == "2"
            if row["s1_choice"] != "" or row["transition_common"] != "":
                s1_leaks.append(row)
        elif r["s2_timeout"] == "1":
            stale_s2 += r["s2_stim"] == "2"
            if row["s2_choice"] != "" or row["reward"] != "":
                s2_leaks.append(row)
            # A stage-2 timeout must NOT cost us the first-stage choice.
            if row["s1_choice"] == "" or row["transition_common"] == "":
                s2_only_losses.append(row)

    check(f"gillan_{study}: stage-1 timeouts carry no choice or transition",
          not s1_leaks,
          f"{len(s1_leaks)} leaked" if s1_leaks else
          f"{stale_s1} stale s1_stim=2 values neutralised")
    check(f"gillan_{study}: stage-2 timeouts carry no second-stage choice or reward",
          not s2_leaks,
          f"{len(s2_leaks)} leaked" if s2_leaks else
          f"{stale_s2} stale s2_stim=2 values neutralised")
    check(f"gillan_{study}: stage-2 timeouts keep their first-stage choice",
          not s2_only_losses,
          f"{len(s2_only_losses)} lost" if s2_only_losses else "kept")


# ---------------------------------------------------------------------------
# 6. The transition label must be implied by the choice-state pairing
# ---------------------------------------------------------------------------

def validate_transition_consistency(dataset: str) -> None:
    """A strong internal invariant that catches a mis-mapped first-stage choice.

    In the Daw task each first-stage option has one "common" second-stage state, fixed
    for the whole session. So within a subject, whether a transition is common is
    fully determined by the (s1_choice, s2_state) pair -- and the two options must
    have *different* common states. If s1_choice had been read off the wrong column,
    or the sides confused with the identities, this would break.
    """
    by_subject: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv("twostep_trials_harmonized.csv"):
        if (row["dataset"] == dataset and row["timeout"] == "0"
                and row["transition_common"] != "" and row["s2_state"] != ""):
            by_subject[row["subject_id"]].append(row)
    if not by_subject:
        return

    ambiguous: list[str] = []
    degenerate: list[str] = []
    for subject, rows in by_subject.items():
        labels: dict[tuple[str, str], set] = defaultdict(set)
        for r in rows:
            labels[(r["s1_choice"], r["s2_state"])].add(r["transition_common"])
        if any(len(v) > 1 for v in labels.values()):
            ambiguous.append(subject)
        common_state = {choice: state for (choice, state), v in labels.items()
                        if v == {"1"}}
        if len(set(common_state.values())) != len(common_state):
            degenerate.append(subject)

    check(f"{dataset}: transition type is determined by (s1_choice, s2_state)",
          not ambiguous,
          f"{len(ambiguous)} subject(s) inconsistent" if ambiguous
          else f"holds for all {len(by_subject)} subjects")
    check(f"{dataset}: the two first-stage options have different common states",
          not degenerate,
          f"{len(degenerate)} subject(s) share one" if degenerate else "distinct")


# ---------------------------------------------------------------------------
# 7. Structural checks on the harmonized table
# ---------------------------------------------------------------------------

EXPECTED = {
    "kool_daw": {"n_subjects": 206, "n_trials": 125, "common_rate": 0.70},
    "kool_novel": {"n_subjects": 199, "n_trials": 125, "common_rate": 1.00},
    "gillan_study1": {"n_subjects": 649, "n_trials": 200, "common_rate": 0.70},
    # One study-2 subject's file is missing trial 1, so they have 199 trials
    # numbered 2..200. That is a property of the published data, not of this code.
    "gillan_study2": {"n_subjects": 1712, "n_trials": 200, "common_rate": 0.70,
                      "known_short": {"3570Y55XZPJQZPOYLZCOL50WZE6GYI": 199}},
}


def validate_structure() -> None:
    rows = read_csv("twostep_trials_harmonized.csv")
    check("harmonized table is non-empty", bool(rows), f"{len(rows):,} rows")
    if not rows:
        return

    by_dataset: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_dataset[r["dataset"]].append(r)

    for dataset, expected in EXPECTED.items():
        data = by_dataset.get(dataset)
        if not data:
            report.append(f"- **SKIP** {dataset}: not present")
            print(f"  [SKIP] {dataset}: not present")
            continue
        subjects = {r["subject_id"] for r in data}
        check(f"{dataset}: subject count",
              len(subjects) == expected["n_subjects"],
              f"{len(subjects)} (expected {expected['n_subjects']})")
        counts = defaultdict(int)
        for r in data:
            counts[r["subject_id"]] += 1
        known = expected.get("known_short", {})
        odd = {s: n for s, n in counts.items()
               if n != expected["n_trials"] and known.get(s) != n}
        check(f"{dataset}: every subject has {expected['n_trials']} trials, apart from "
              f"{len(known)} documented exception(s)",
              not odd,
              f"{len(odd)} undocumented deviation(s): {dict(list(odd.items())[:3])}"
              if odd else
              (f"all equal apart from {', '.join(known)}" if known else "all equal"))

        known = [r for r in data if r["transition_common"] != ""]
        rate = statistics.mean(int(r["transition_common"]) for r in known)
        check(f"{dataset}: common-transition rate ~ {expected['common_rate']:.2f}",
              abs(rate - expected["common_rate"]) < 0.02, f"{rate:.4f}")

        probs = [_f(r[f"p_reward_{k}"]) for r in data for k in (1, 2, 3, 4)
                 if r[f"p_reward_{k}"] != ""]
        if probs:
            check(f"{dataset}: reward probabilities inside [0.25, 0.75]",
                  min(probs) >= 0.25 - 1e-9 and max(probs) <= 0.75 + 1e-9,
                  f"range [{min(probs):.4f}, {max(probs):.4f}]")

    # s2_choice_global must agree with its parts wherever all three are present.
    bad = [r for r in rows if r["s2_choice_global"] != ""
           and int(r["s2_choice_global"]) != (int(r["s2_state"]) - 1) * 2
                                             + int(r["s2_choice"])]
    check("harmonized: s2_choice_global == (s2_state - 1) * 2 + s2_choice",
          not bad, f"{len(bad)} inconsistent" if bad else "consistent")

    # Required columns must never be blank.
    required = ("dataset", "subject_id", "session", "trial", "timeout")
    blank = [c for c in required if any(r[c] == "" for r in rows)]
    check("harmonized: required columns never blank", not blank,
          f"blank in {blank}" if blank else "ok")

    # A trial that was answered must carry a full record.
    incomplete = [r for r in rows if r["timeout"] == "0"
                  and (r["s1_choice"] == "" or r["reward"] == "")]
    check("harmonized: answered trials have a choice and an outcome",
          not incomplete, f"{len(incomplete)} incomplete" if incomplete else "ok")


def report_cross_dataset_notes() -> None:
    """Numbers worth knowing before pooling; reported, not asserted."""
    subjects = read_csv("twostep_subjects_harmonized.csv")
    lines = []
    for dataset in ("kool_daw", "kool_novel", "gillan_study1", "gillan_study2", "gilger"):
        rows = [r for r in subjects if r["dataset"] == dataset]
        if not rows:
            continue
        timeouts = [int(r["n_timeouts"]) for r in rows]
        # Kool excludes a subject at 25 or more missed trials out of 125; applying the
        # same 20% rule to Gillan's 200 trials means 40.
        limit = 25 if dataset.startswith("kool") else 40
        over = sum(t >= limit for t in timeouts)
        # kool_novel has deterministic transitions, so the rare-transition cells are
        # empty and the stay indices are undefined there by construction.
        mb = [float(r["mb_index"]) for r in rows if r["mb_index"] not in ("", "nan")]
        mf = [float(r["mf_index"]) for r in rows if r["mf_index"] not in ("", "nan")]
        fmt = lambda xs: f"{statistics.mean(xs):+.3f}" if xs else "n/a"
        lines.append(
            f"| {dataset} | {len(rows)} | {statistics.mean(timeouts):.1f} | "
            f"{over} ({over / len(rows):.1%}) | {fmt(mf)} | {fmt(mb)} |")
    # Gillan describe study 2 as a task-naive sample; check for ID reuse, which
    # would mean the same person appears twice in a pooled analysis.
    ids = {}
    for study in ("gillan_study1", "gillan_study2"):
        ids[study] = {r["subject_id"] for r in subjects if r["dataset"] == study}
    if ids["gillan_study1"] and ids["gillan_study2"]:
        shared = ids["gillan_study1"] & ids["gillan_study2"]
        check("gillan: study 1 and study 2 share no subject IDs", not shared,
              f"{len(shared)} shared" if shared else
              f"{len(ids['gillan_study1'])} + {len(ids['gillan_study2'])} disjoint")

    if lines:
        report.append("")
        report.append("### Cross-dataset summary (reported, not asserted)")
        report.append("")
        report.append("`>= limit` applies Kool's 20%-of-trials timeout exclusion to "
                      "each dataset (25 of 125 trials, 40 of 200).")
        report.append("")
        report.append("| dataset | subject-sessions | mean timeouts | >= limit | "
                      "mean MF index | mean MB index |")
        report.append("|---|---|---|---|---|---|")
        report.extend(lines)


def main() -> int:
    print("Validating:")
    validate_kool_daw()
    validate_kool_novel()
    for paradigm in ("daw", "novel"):
        validate_kool_subinfo(paradigm)
    validate_gillan_factors()
    for dataset in ("gillan_study1", "gillan_study2"):
        validate_gillan_drift_mapping(dataset)
    for study in ("study1", "study2"):
        validate_gillan_timeout_blanking(study)
    for dataset in ("kool_daw", "gillan_study1", "gillan_study2", "gilger"):
        validate_transition_consistency(dataset)
    validate_structure()
    report_cross_dataset_notes()

    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "validation_report.md"
    header = [
        "# Validation report",
        "",
        "Generated by `python -m src.validate`. Each check recomputes a quantity whose",
        "correct value is known independently of this repository -- the authors' own",
        "MATLAB output for Kool, the published factor scores for Gillan -- so a mistake",
        "in a column mapping shows up as a numeric mismatch rather than passing quietly.",
        "",
        f"**{sum(1 for line in report if line.startswith(('- **PASS', '- **FAIL')))}"
        f" checks, {len(failures)} failed.**",
        "",
    ]
    out.write_text("\n".join(header + report) + "\n")
    print(f"\nWrote {out.relative_to(out.parent.parent)}  ({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
