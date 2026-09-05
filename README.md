# Social Graphs
A weekly network-science journal for DTU 02805, Fall 2026.

**Members:** Arnar, Birkir, Hanna.

## Week 1
**A universe, unevenly connected.** Does the most visible Marvel Wikipedia character keep the network connected? Interactive map, degree distributions with mixed binning, leaderboards, a removal experiment, and disconnected components.

## Preview
Run from this repository:
```sh
python3 -m http.server 8000 --directory site
```
Open http://localhost:8000. Use an HTTP server: interactive figures fetch a local JSON file.

## Reproduce
Python 3.10 or newer; exact numerical package versions are in requirements.txt.
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python analysis/build_week1.py
.venv/bin/jupyter lab analysis/week1.ipynb
```
The script reads original TSVs in site/data and regenerates site/data/week1.json and site/assets/week1-degrees.svg. The notebook exposes the calculations using the same functions. The deployed site is static and does not run Python.

## GitHub Pages
The workflow targets https://birkir-freyr.github.io/social-graphs/ (intended address; verify after deployment).

1. Open this repository's **Settings → Pages** on GitHub.
2. Set **Source** to **GitHub Actions**.
3. Push the site to main or run **Publish Social Graphs** from Actions.
4. Wait for deployment and use the URL returned by the workflow.

Only site/ is uploaded. All asset paths are relative, supporting project Pages URLs.

## Add another week
Add future posts under site/weeks/ and link them from the main navigation or a growing journal index. Keep Week 1 tied to its frozen snapshot.

## Data and interpretation
Source: https://sunelehmann.com/socialgraphs2026-web/data/ · Snapshot: 2026-08-26.

Directed A → B means A's Wikipedia article links to B's article within this roster. All roster nodes are added before edges. The original TSV comments and columns are retained. The seeded undirected force layout is not a distance measurement. Components and the removal experiment use undirected connectivity; directed reachability is not implied. Incoming degree measures visibility within this network, not general popularity. No power-law fit is claimed.

Coding-agent assistance produced code and draft prose; numerical claims are checked against the supplied snapshot.

