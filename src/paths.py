"""Shared paths.

`sources/` holds the original material exactly as its authors published it -- papers,
supplementary files, and the authors' own data and code -- and is committed, so the
project does not depend on GitHub, OSF or the journals staying reachable. The
directory names inside it deliberately mirror the published ones, spaces and all, so
a vendored copy can be diffed against the original.

`data/processed/` holds everything this pipeline derives. It is regenerable and not
committed.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

# Kool, Cushman & Gershman (2016) -- github.com/wkool/tradeoffs, vendored whole.
KOOL_DIR = SOURCES / "kool2016"
KOOL_REPO = KOOL_DIR / "repo"
KOOL_DATA = KOOL_REPO / "data"          # holds "daw paradigm" and "novel paradigm"

# Gillan et al. (2016) -- osf.io/usdgt, vendored whole.
GILLAN_DIR = SOURCES / "gillan2016"
GILLAN_OSF = GILLAN_DIR / "osf"         # holds "Experiment 1" and "Experiment 2"

# Gilger et al. (2024) -- paper only; the data is not public.
GILGER_DIR = SOURCES / "gilger2024"
GILGER_DATA = GILGER_DIR / "data"


def kool_paradigm_dir(paradigm: str) -> Path:
    """Map our short name onto the directory name the repository uses."""
    return KOOL_DATA / f"{paradigm} paradigm"


def ensure_dirs() -> None:
    for d in (SOURCES, PROCESSED, KOOL_DIR, GILLAN_DIR, GILGER_DIR, GILGER_DATA):
        d.mkdir(parents=True, exist_ok=True)
