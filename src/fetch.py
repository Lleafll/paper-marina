"""Populate sources/ with the original material from all three papers.

Everything this project is built on is vendored: the publications, their supplementary
files, and the authors' own data and code. Layout mirrors each source as published --
see src/paths.py and sources/README.md.

  Kool, Cushman & Gershman (2016), PLoS Comput Biol 12:e1005090
      paper + 6 supplementary files (PLoS, CC-BY)
      the complete github.com/wkool/tradeoffs repository, pinned to one commit

  Gillan, Kosinski, Whelan, Phelps & Daw (2016), eLife 5:e11305
      paper + 5 supplementary files (eLife, CC-BY)
      the complete osf.io/usdgt project, including 2361 per-subject task files

  Gilger et al. (2024), J Psychopharmacol 38:178-187
      CC-BY full text as XML; the PDF has to be added by hand (see below)

Everything is cached: files already on disk are left alone, so this is resumable and
safe to re-run. Two notes on the slow parts:

  * Gillan's 2361 per-subject CSVs cannot be fetched one by one -- that trips OSF's
    anonymous rate limit (HTTP 429) after a few hundred. Each task folder is pulled as
    a single archive from OSF's WaterButler `?zip=` endpoint instead. OSF builds those
    on the fly and streams them slowly; the larger one takes 10-20 minutes. That is
    normal, not a hang, and progress is printed as it arrives.
  * A client-side time limit will cut such a stream off mid-archive, so a truncated
    archive is detected and reported rather than silently unpacked.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .paths import (GILGER_DIR, GILLAN_DIR, GILLAN_OSF, KOOL_DIR, KOOL_REPO,
                    SOURCES, ensure_dirs)

# --------------------------------------------------------------------------- #
# What to fetch
# --------------------------------------------------------------------------- #

# Pinned so the vendored copy is reproducible; master could move under us.
KOOL_COMMIT = "6f849e13a8fe32c0b62ad768d3578068b93ee69e"
KOOL_TARBALL = f"https://api.github.com/repos/wkool/tradeoffs/tarball/{KOOL_COMMIT}"

PLOS = "https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1005090"
ELIFE = "https://cdn.elifesciences.org/articles/11305"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"

# (url, destination relative to sources/, what it is)
PAPERS: list[tuple[str, str, str]] = [
    (f"{PLOS}&type=printable",
     "kool2016/paper/pcbi.1005090.pdf", "Kool et al. (2016), full paper"),
    (f"{PLOS}.s001&type=supplementary",
     "kool2016/paper/pcbi.1005090.s001.eps", "S1 Fig: drift rate across RL parameters"),
    (f"{PLOS}.s002&type=supplementary",
     "kool2016/paper/pcbi.1005090.s002.eps", "S2 Fig: volume under surface, 32 tasks"),
    (f"{PLOS}.s003&type=supplementary",
     "kool2016/paper/pcbi.1005090.s003.docx", "S1 Text: model-fitting reliability"),
    (f"{PLOS}.s004&type=supplementary",
     "kool2016/paper/pcbi.1005090.s004.docx", "S2 Text: multi-level logistic regressions"),
    (f"{PLOS}.s005&type=supplementary",
     "kool2016/paper/pcbi.1005090.s005.docx", "S1 Table: model comparison, perseveration"),
    (f"{PLOS}.s006&type=supplementary",
     "kool2016/paper/pcbi.1005090.s006.docx", "S2 Table: model comparison, hybrid vs pure"),
    (f"{EPMC}/PMC5001643/fullTextXML",
     "kool2016/paper/fulltext.xml", "Kool et al., machine-readable full text"),

    (f"{ELIFE}/elife-11305-v1.pdf",
     "gillan2016/paper/elife-11305-v1.pdf", "Gillan et al. (2016), full paper"),
    (f"{ELIFE}/elife-11305-supp1-v1.docx",
     "gillan2016/paper/elife-11305-supp1-v1.docx", "Supp file 1: questionnaire total scores"),
    (f"{ELIFE}/elife-11305-supp2-v1.docx",
     "gillan2016/paper/elife-11305-supp2-v1.docx", "Supp file 2: factor loadings (AD/CIT/SW)"),
    (f"{ELIFE}/elife-11305-supp3-v1.docx",
     "gillan2016/paper/elife-11305-supp3-v1.docx", "Supp file 3: 'putative patients' analysis"),
    (f"{ELIFE}/elife-11305-supp4-v1.docx",
     "gillan2016/paper/elife-11305-supp4-v1.docx", "Supp file 4: supervised-analysis predictors"),
    (f"{ELIFE}/elife-11305-supp5-v1.docx",
     "gillan2016/paper/elife-11305-supp5-v1.docx",
     "Supp file 5: questionnaire associations from the full computational model"),
    (f"{ELIFE}/elife-11305-v1.xml",
     "gillan2016/paper/fulltext.xml", "Gillan et al., machine-readable full text"),

    (f"{EPMC}/PMC10863371/fullTextXML",
     "gilger2024/paper/fulltext.xml", "Gilger et al., machine-readable full text (CC-BY)"),
]

# The Gilger PDF cannot be fetched -- SAGE and PMC both block automated download.
GILGER_PDF = "gilger2024/paper/gilger2024-jpsychopharmacol.pdf"
GILGER_SUPPL = "gilger2024/paper/gilger2024-supplemental.pdf"
GILGER_SUPPL_URL = ("https://journals.sagepub.com/doi/10.1177/02698811231216325"
                    " -> Supplementary Materials ->"
                    " sj-pdf-1-jop-10.1177_02698811231216325.pdf")

OSF_NODE = "usdgt"
OSF_API = f"https://api.osf.io/v2/nodes/{OSF_NODE}/files/osfstorage/"
OSF_ZIP = f"https://files.osf.io/v1/resources/{OSF_NODE}/providers/osfstorage/"
# Folder ids read off the OSF API; they are stable. See docs/codebook_gillan.md.
OSF_LAYOUT = {
    "Experiment 1": {
        "folder_id": "5d30a17ba667db0018f7b920",
        "task_folder_id": "5d30a113251f0e00190530ab",
        "task_subfolder": "twostep_data_study1",
        "n_expected": 649,
    },
    "Experiment 2": {
        "folder_id": "5d30a1bd5d2cdc001704ac66",
        "task_folder_id": "5d30a139a667db0018f7b8a4",
        "task_subfolder": "twostep_data_study2",
        "n_expected": 1712,
    },
}

RETRIES = 4
ZIP_TIMEOUT = 1800  # server-side archive generation is slow for the big folder

# Where each vendored file came from, for sources/MANIFEST.tsv.
provenance: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #

def _get(url: str, binary: bool = False, timeout: int = 180):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-marina/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:  # OSF rate limit; back off hard
                time.sleep(60 * (attempt + 1))
            elif exc.code >= 500:
                time.sleep(5 * 2 ** attempt)
            else:
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"failed after {RETRIES} attempts: {url}") from last


def _download(url: str, dest: Path, timeout: int = 180) -> bool:
    """Download to dest unless it is already there. Returns True if fetched."""
    provenance[str(dest.relative_to(SOURCES))] = url
    if dest.exists() and dest.stat().st_size > 0:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_get(url, binary=True, timeout=timeout))
    return True


def _stream(url: str, dest: Path, label: str) -> None:
    """Download a large response to `dest`, reporting progress as it arrives.

    OSF generates folder archives on the fly, so the response has no Content-Length
    and can take many minutes. Reading it in chunks keeps the process visibly alive
    and keeps peak memory down.
    """
    if dest.exists():
        dest.unlink()  # a part-file from an interrupted run is not resumable
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "paper-marina/1.0"})
    written = next_report = 0
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=ZIP_TIMEOUT) as resp, dest.open("wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
            written += len(chunk)
            if written >= next_report:
                print(f"    {label}: {written / 1e6:.1f} MB after "
                      f"{time.monotonic() - started:.0f}s", flush=True)
                next_report = written + (4 << 20)


# --------------------------------------------------------------------------- #
# Papers
# --------------------------------------------------------------------------- #

def fetch_papers() -> None:
    print("Papers and supplementary material (all three papers are CC-BY)")
    for url, relative, description in PAPERS:
        dest = SOURCES / relative
        fetched = _download(url, dest)
        print(f"  {'got ' if fetched else 'have'} {relative}"
              f"  ({dest.stat().st_size:,} bytes)  -- {description}")


def check_gilger_pdf() -> None:
    """Report on the two PDFs that have to be added by hand."""
    pdf, suppl = SOURCES / GILGER_PDF, SOURCES / GILGER_SUPPL
    provenance[GILGER_PDF] = ("manual download: https://journals.sagepub.com/doi/pdf/"
                              "10.1177/02698811231216325")
    provenance[GILGER_SUPPL] = f"manual download: {GILGER_SUPPL_URL}"
    if pdf.exists():
        print(f"  have {GILGER_PDF}  ({pdf.stat().st_size:,} bytes)")
    else:
        print(f"  MISSING {GILGER_PDF}\n"
              f"       get it from https://journals.sagepub.com/doi/pdf/"
              f"10.1177/02698811231216325 (open access)")
    if suppl.exists():
        print(f"  have {GILGER_SUPPL}  ({suppl.stat().st_size:,} bytes)")
    else:
        print(f"  MISSING {GILGER_SUPPL}  -- contains the full model specification\n"
              f"       get it from {GILGER_SUPPL_URL}")


# --------------------------------------------------------------------------- #
# Kool: the whole repository
# --------------------------------------------------------------------------- #

def fetch_kool_repo() -> None:
    print(f"Kool et al. data and code -- github.com/wkool/tradeoffs @ {KOOL_COMMIT[:7]}")
    marker = KOOL_REPO / "data" / "daw paradigm" / "data.mat"
    if marker.exists():
        n = sum(1 for _ in KOOL_REPO.rglob("*") if _.is_file())
        print(f"  have repo/ ({n} files)")
        _record_repo_provenance()
        return

    print("  getting the repository tarball", flush=True)
    blob = _get(KOOL_TARBALL, binary=True, timeout=600)
    KOOL_REPO.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        members = []
        for member in tar.getmembers():
            # Strip the "wkool-tradeoffs-<sha>/" prefix GitHub adds.
            parts = Path(member.name).parts[1:]
            if not parts or member.islnk() or member.issym():
                continue
            member.name = str(Path(*parts))
            members.append(member)
        tar.extractall(KOOL_REPO, members=members, filter="data")
    print(f"  got  repo/ ({sum(1 for m in members if m.isfile())} files)")
    _record_repo_provenance()


def _record_repo_provenance() -> None:
    for path in KOOL_REPO.rglob("*"):
        if path.is_file():
            provenance[str(path.relative_to(SOURCES))] = KOOL_TARBALL


# --------------------------------------------------------------------------- #
# Gillan: the whole OSF project
# --------------------------------------------------------------------------- #

def _osf_list(folder_id: str) -> list[dict]:
    """List one OSF folder, following pagination. An empty id means the root."""
    base = f"{OSF_API}{folder_id}/" if folder_id else OSF_API
    url = f"{base}?page%5Bsize%5D=100"
    out = []
    while url:
        page = _get(url)
        out.extend(page["data"])
        url = page["links"].get("next")
    return out


def fetch_gillan_root_files() -> None:
    """Files at the OSF project root -- notably the authors' 2021 correction notice.

    It records that item 13 of the Zung Depression Scale was mis-worded when these
    data were collected, which matters for anyone applying the published factor
    weights to a new sample. See docs/codebook_gillan.md.
    """
    for entry in _osf_list(""):
        attrs = entry["attributes"]
        if attrs["kind"] != "file":
            continue
        fid = attrs["path"].strip("/")
        fetched = _download(f"https://osf.io/download/{fid}/", GILLAN_OSF / attrs["name"])
        print(f"  {'got ' if fetched else 'have'} osf/{attrs['name']}")


def fetch_gillan_tables(experiment: str) -> None:
    """The handful of files directly inside an Experiment folder."""
    for entry in _osf_list(OSF_LAYOUT[experiment]["folder_id"]):
        attrs = entry["attributes"]
        if attrs["kind"] != "file":
            continue
        fid = attrs["path"].strip("/")
        fetched = _download(f"https://osf.io/download/{fid}/",
                            GILLAN_OSF / experiment / attrs["name"])
        print(f"  {'got ' if fetched else 'have'} osf/{experiment}/{attrs['name']}")


def fetch_gillan_task_data(experiment: str) -> None:
    """The per-subject task CSVs, via one folder archive."""
    info = OSF_LAYOUT[experiment]
    task_dir = GILLAN_OSF / experiment / info["task_subfolder"]
    label = f"osf/{experiment}/{info['task_subfolder']}"
    n_have = len(list(task_dir.glob("*.csv"))) if task_dir.exists() else 0
    for path in task_dir.glob("*.csv") if task_dir.exists() else []:
        provenance[str(path.relative_to(SOURCES))] = (
            f"{OSF_ZIP}{info['task_folder_id']}/?zip=")
    if n_have >= info["n_expected"]:
        print(f"  have {label}/ ({n_have} files)")
        return

    print(f"  getting {label}/ ({info['n_expected']} files). OSF builds these archives "
          f"on the fly and streams slowly -- expect 10-20 minutes for the larger one.",
          flush=True)
    archive_path = GILLAN_OSF / experiment / f"{info['task_subfolder']}.zip"
    _stream(f"{OSF_ZIP}{info['task_folder_id']}/?zip=", archive_path, label)

    blob = archive_path.read_bytes()
    if not blob.startswith(b"PK") or b"PK\x05\x06" not in blob[-100000:]:
        archive_path.unlink()
        raise RuntimeError(
            f"{experiment}: the folder archive came back truncated "
            f"({len(blob):,} bytes, no end-of-central-directory record). OSF streams "
            f"these archives, so a client-side time limit will cut one off "
            f"mid-stream; re-run to try again.")

    task_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) < info["n_expected"]:
            raise RuntimeError(
                f"{experiment}: archive holds {len(names)} CSVs, expected "
                f"{info['n_expected']} -- the download was truncated, re-run")
        for name in names:
            dest = task_dir / name.split("/")[-1]
            if not dest.exists():
                dest.write_bytes(archive.read(name))
            provenance[str(dest.relative_to(SOURCES))] = (
                f"{OSF_ZIP}{info['task_folder_id']}/?zip=")
    archive_path.unlink()
    print(f"  got  {label}/ ({len(names)} files)")


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #

def write_manifest() -> None:
    """Record size, checksum and origin of every vendored file.

    Lets anyone confirm the copies here are byte-identical to what was published.
    """
    rows = []
    for path in sorted(SOURCES.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.tsv":
            continue
        relative = str(path.relative_to(SOURCES))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        origin = provenance.get(relative)
        if origin is None:
            # The hand-written provenance notes in sources/ have no upstream URL.
            origin = ("written for this repository" if path.name == "README.md"
                      else "")
        rows.append((relative, str(path.stat().st_size), digest, origin))
    out = SOURCES / "MANIFEST.tsv"
    with out.open("w") as fh:
        fh.write("path\tbytes\tsha256\tsource_url\n")
        for row in rows:
            fh.write("\t".join(row) + "\n")
    total = sum(int(r[1]) for r in rows)
    unknown = [r[0] for r in rows if not r[3]]
    print(f"  MANIFEST.tsv: {len(rows):,} files, {total / 1e6:.1f} MB"
          + (f" ({len(unknown)} without a recorded origin: "
             f"{', '.join(unknown[:3])})" if unknown else ""))


def main() -> int:
    ensure_dirs()
    fetch_papers()
    print("Gilger et al. PDFs (not machine-fetchable; SAGE and PMC block it)")
    check_gilger_pdf()
    fetch_kool_repo()
    print("Gillan et al. data -- osf.io/usdgt")
    fetch_gillan_root_files()
    for experiment in OSF_LAYOUT:
        fetch_gillan_tables(experiment)
        fetch_gillan_task_data(experiment)
    print("Manifest")
    write_manifest()
    print("\nSources are in sources/. Gilger et al. trial data is not public -- see "
          "docs/codebook_gilger.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
