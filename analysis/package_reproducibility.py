"""Package the public posts' analyses without requiring GitHub repository access.

Run after changing either analysis: python analysis/package_reproducibility.py
Only the explicitly listed course files are included; no repository metadata.
"""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/downloads"
COMMON = ["site/data/week1_nodes.tsv", "site/data/week1_edges.tsv"]
PACKAGES = {
    "week1": {
        "files": COMMON + ["analysis/build_week1.py", "analysis/week1.ipynb", "requirements.txt"],
        "readme": """# Week 1 — A universe, unevenly connected

Reproduce the Social Graphs course post from the frozen 26 August 2026 dataset.
Source: https://sunelehmann.com/socialgraphs2026-web/data/
Post: https://birkir-freyr.github.io/social-graphs/

Use Python 3.10 or newer. Extract the archive, open a terminal in this folder,
then run:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python analysis/build_week1.py

This generates site/data/week1.json and site/assets/week1-degrees.svg, checking
the graph counts, degree distributions, components, and removal experiment.
Optionally open the included notebook with:

    .venv/bin/jupyter lab analysis/week1.ipynb

On Windows, use .venv\\Scripts\\python.exe in place of .venv/bin/python and
.venv\\Scripts\\jupyter.exe in place of .venv/bin/jupyter.
""",
    },
    "week2": {
        "files": COMMON + ["analysis/build_week2.py", "site/data/week1.json"],
        "readme": """# Week 2 — Even superheroes have more popular friends

Reproduce the Social Graphs course post from the frozen 26 August 2026 dataset.
Source: https://sunelehmann.com/socialgraphs2026-web/data/
Post: https://birkir-freyr.github.io/social-graphs/weeks/week2.html

Use Python 3.10 or newer. Extract the archive, open a terminal in this folder,
then run:

    python3 -m venv .venv
    .venv/bin/python -m pip install networkx==3.4.2
    .venv/bin/python analysis/build_week2.py

On Windows, use .venv\\Scripts\\python.exe in place of .venv/bin/python.

This generates site/data/week2.json and site/data/week2-null-trials.csv. It
recalculates the exact sampling expectations and 100 graphs for each of two
nulls. Every labelled degree is checked after each degree-preserving shuffle.
The included Week 1 JSON supplies layout coordinates only; measurements come
from the original node roster and edge list. No network access or GitHub login
is needed after installing NetworkX. Seeds and source hashes are exported.
""",
    },
}


def build():
    OUT.mkdir(exist_ok=True)
    for week, spec in PACKAGES.items():
        destination = OUT / f"{week}-analysis.zip"
        members = {name: (ROOT/name).read_bytes() for name in spec["files"]}
        members["README.md"] = spec["readme"].encode()
        with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
            for name, contents in sorted(members.items()):
                info = ZipInfo(f"{week}-analysis/{name}", date_time=(2026, 9, 14, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, contents)
        with ZipFile(destination) as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == len(members)
        print(f"{destination.relative_to(ROOT)}: {len(members)} files")


if __name__ == "__main__":
    build()
