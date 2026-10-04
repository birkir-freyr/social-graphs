# Social Graphs
A weekly network-science journal for DTU 02805, Fall 2026.

**Members:** Arnar, Birkir, Hanna.

## Week 1
**A universe, unevenly connected.** Does the most visible Marvel Wikipedia character keep the network connected? Interactive map, degree distributions with mixed binning, leaderboards, a removal experiment, and disconnected components.

## Week 2
**Even superheroes have more popular friends.** Exercise 2.11: a free-form post on the friendship paradox, its repeat guests, and what survives degree-preserving randomization. Includes a live pair sampler, two null histograms, and the unexpected local maximum on the nine-character island.

Page: `site/weeks/week2.html` · Intended Pages URL: https://birkir-freyr.github.io/social-graphs/weeks/week2.html

Reproduce from the same frozen TSVs with `python analysis/build_week2.py`. This writes `site/data/week2.json` (exact expectations, named sample graphs, seeds, source hashes, null distributions) and `site/data/week2-null-trials.csv` (all 200 realizations). The existing Week 1 JSON supplies layout coordinates only; it does not supply Week 2 measurements. Every labelled degree is checked after shuffling. Run the sampling checks with `node --test analysis/test_week2.cjs`.

The article uses uniform nonisolated-person → uniform-neighbor sampling. It distinguishes this from uniform edge-endpoint sampling and reports the isolate denominator. The 100-shuffle comparison uses a two-sided corrected empirical test of exact expected friend degree, not noisy sample means.

The assignment also asks the group to share the published link in the Week 2 Teams channel by Monday evening and leave constructive feedback on another group's post; those are separate from building the website.

## Week 3
**You can remove Spider-Man. The universe stays.** Exercise 3.12: an interactive targeted-removal experiment on the 277-character giant component. Compare adaptive degree and adaptive betweenness attacks with 500 random removal orders, scrub through the first 100 deletions, and watch detached components emerge.

Page: `site/weeks/week3.html` · Intended Pages URL: https://birkir-freyr.github.io/social-graphs/weeks/week3.html

Reproduce with `python analysis/build_week3.py`. This writes `site/data/week3.json` and `site/data/week3-random-trials.csv`. Run the graph and saved-claim checks with `node --test analysis/test_week3.cjs`.

## Week 4
**Two links. Three islands.** Exercise **4.13**, Go nuts: a disparity-filter story
on the philosopher network. Find the largest single drop in the giant component,
cut Augustine's two tied links interactively, and explore the losses across alpha.
The critical 108-person component splits into 65, 40 and 3; the article makes
explicit that 1,046 of the original 1,374 philosophers are already isolated.

Page: `site/weeks/week4.html` · Intended Pages URL: https://birkir-freyr.github.io/social-graphs/weeks/week4.html

Reproduce with `python analysis/build_week4.py`, then `python analysis/plot_week4.py`.
Run `node --test analysis/test_week4.cjs` to verify original weight aggregation,
filter significance, reference counts, all slider settings, and the critical cut.
Run `python analysis/package_reproducibility.py` after changing the bundled analysis.
The public ZIP includes the source TSVs and everything needed to regenerate the
data and comparison figure. The post is linked from all previous weeks.

The course also asks you to share the published link in the Week 4 Teams channel
and leave constructive feedback on another group's post. Those remain separate
from preparing this website entry.

## Week 5
**Same universe. Same sentences.** Exercise **5.9**: connect the 303 Marvel
Wikipedia pages by their longest shared token sequence. Eight tokens produce
40,550 page pairs; twenty leave 88. Change the threshold and read both raw
passages behind every surviving link. The inspected matches include a plot
summary, editorial history, a bibliography, and a quotation—repeated text does
not establish copying direction.

Page: `site/weeks/week5.html` · Intended Pages URL: https://birkir-freyr.github.io/social-graphs/weeks/week5.html

Reproduce with `python analysis/build_week5.py` (Python 3.10+, NetworkX 3.4.2,
NumPy 1.26.0). Inputs are bundled in `site/data/marvel_pages.zip` and the Week 1
node roster. Outputs include source hashes, raw spans, all >=8-token pairs,
threshold counts, and the standalone SVG. Run
`python -m unittest discover -s analysis -p test_week5.py` and
`node --test analysis/test_week5.cjs`, then
`python analysis/package_reproducibility.py` to refresh the public ZIP.

Exercises 5.1–5.7 are in the separate local course folder; exercise 5.8 was
skipped. Sharing the published link in Teams and providing another group with
constructive feedback remain separate course actions.

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
The workflow targets https://birkir-freyr.github.io/social-graphs/ 
Only site/ is uploaded. All asset paths are relative, supporting project Pages URLs.

## Add another week
Add future posts under site/weeks/ and link them from the main navigation or a growing journal index. Keep Week 1 tied to its frozen snapshot.

## Data and interpretation
Source: https://sunelehmann.com/socialgraphs2026-web/data/ · Snapshot: 2026-08-26.

Directed A → B means A's Wikipedia article links to B's article within this roster. All roster nodes are added before edges. The original TSV comments and columns are retained. The seeded undirected force layout is not a distance measurement. Components and the removal experiment use undirected connectivity; directed reachability is not implied. Incoming degree measures visibility within this network, not general popularity. No power-law fit is claimed.

Coding-agent assistance produced code and draft prose; numerical claims are checked against the supplied snapshot.

## Public analysis downloads
The website serves self-contained reproduction packages under `site/downloads/`, so readers do not need access to the GitHub repository. After changing an analysis or its bundled inputs, run `python analysis/package_reproducibility.py` and include the regenerated ZIP files in the website update. Each package contains only an explicit list of course files and instructions.
