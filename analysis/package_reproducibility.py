"""Package the public posts' analyses without requiring GitHub repository access.

Run after changing an analysis: python analysis/package_reproducibility.py
Only the explicitly listed course files are included; no repository metadata.
"""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/downloads"
COMMON = ["site/data/week1_nodes.tsv", "site/data/week1_edges.tsv"]
PACKAGES = {
    "week7": {
        "files": ["site/data/week1_nodes.tsv", "site/data/marvel_pages.zip",
                  "analysis/data/week7-search-embeddings.npz", "analysis/data/week7-search-embeddings.json",
                  "analysis/data/week7-queries.json", "analysis/data/week7-reading-notes.json",
                  "analysis/build_week7.py", "analysis/encode_week7.py",
                  "analysis/requirements-week7.txt", "analysis/requirements-week7-encoder.txt",
                  "analysis/test_week7.py", "analysis/test_week7.cjs",
                  "site/week7-core.js", "site/week7.js", "site/week7.css",
                  "site/style.css", "site/assets/favicon.svg", "site/weeks/week7.html"],
        "readme": """# Week 7 — Same query. Different results.

Exercise 7.13: how do pooling and passage size change Marvel retrieval?
Compare TF-IDF, a MiniLM page mean, 180-word max passage and 60-word max passage.
Post: https://birkir-freyr.github.io/social-graphs/weeks/week7.html

All 303 raw pages, eight queries, original query/document/passage vectors and
source offsets are bundled. Ordinary measurement reproduction is offline.
Use Python 3.10+ from this extracted folder:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r analysis/requirements-week7.txt
    .venv/bin/python analysis/build_week7.py
    .venv/bin/python -m unittest discover -s analysis -p test_week7.py
    node --test analysis/test_week7.cjs

Windows: use .venv\\Scripts\\python.exe instead of .venv/bin/python.
Node 18+ is only needed for browser-core tests. HTML/CSS/JS support those checks;
this is an analysis package, not a complete copy of all earlier journal pages.
Outputs: site/data/week7.json and gzip copy, week7-rankings.csv (all 9,696 ranks),
week7-target-ranks.csv, and site/assets/week7-search-ranks.svg.

Optional fresh model inference (first run downloads public weights):

    .venv/bin/python -m pip install -r analysis/requirements-week7-encoder.txt
    .venv/bin/python analysis/encode_week7.py
    .venv/bin/python analysis/build_week7.py

Encoder: sentence-transformers/all-MiniLM-L6-v2, revision
1110a243fdf4706b3f48f1d95db1a4f5529b4d41. Windows have at most 180 or 60
whitespace words and 254 wordpieces, leaving two special tokens in the 256-token
encoder. All non-whitespace text is covered. Unit passage vectors are averaged
then normalized for the page-mean view. Max views use the greatest query-passage
cosine per page. Page mean to max changes pooling; 180 to 60 holds max pooling
fixed. Long pages have more passage candidates. Exact score ties use alphabetical
page IDs; passage ties choose earliest source offset.

TF-IDF uses default CountVectorizer lowercase tokens of at least two word
characters, retaining stopwords/numbers. IDF ln(303/DF), no smoothing or +1;
normalize documents and queries. Query IDF is fitted only on the corpus.
Full-page methods show an illustrative selected passage; max-passage methods
show the passage that defines the score. Expanded context does not rerank.

Targets and query texts were recorded before the original local Week7 search;
the article theme and cases were chosen after viewing results. Targets were
proposed by the assistant, not independently judged exhaustive relevance labels.
The spider query fits alternate origins, and the intended Daredevil page is absent.
No aggregate accuracy, universal best method, significance or generated answer
is claimed. Reading notes preserve the negation/alternate-incarnation caveats.

Optional inference can differ slightly across environments. Inspect changed
scores/ranks before updating prose. Model weights are not bundled. Wikipedia
text is CC BY-SA 4.0; the original roster URLs identify pages and live attribution.
Snapshot: 26 August 2026. Page claims are analyzed as supplied.
""",
    },
    "week6": {
        "files": COMMON + ["site/data/marvel_pages.zip", "analysis/build_week6.py",
                  "analysis/requirements-week6.txt", "analysis/test_week6.py",
                  "analysis/test_week6.cjs", "site/week6-core.js",
                  "site/week6.js", "site/weeks/week6.html"],
        "readme": """# Week 6 — Lose the name. Change the neighbor.

Exercise 6.11: a controlled TF-IDF/cosine comparison on all 303 Marvel
Wikipedia pages from the frozen 26 August 2026 course corpus. All inputs bundled.
Source: https://sunelehmann.com/socialgraphs2026-web/data/
Intended post: https://birkir-freyr.github.io/social-graphs/weeks/week6.html

Use Python 3.10+ (tested with 3.10), then from this extracted folder:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r analysis/requirements-week6.txt
    .venv/bin/python analysis/build_week6.py
    .venv/bin/python -m unittest discover -s analysis -p test_week6.py
    node --test analysis/test_week6.cjs

On Windows use .venv\\Scripts\\python.exe instead of .venv/bin/python.
Node.js 18+ is only needed for the optional browser-core checks.
The included HTML and browser script support UI tests; this is an analysis
package, not a copy of the entire journal website.
No network access or NLP model downloads are needed after installation.

Outputs: site/data/week6.json (plus an equivalent gzip copy for the website),
week6-neighbors.csv, week6-removed-terms.csv, and
site/assets/week6-lookalikes.svg. Inputs' SHA-256 hashes, versions and the
complete capitalization audit are saved. The builder creates output folders.

CountVectorizer default lowercase tokens: (?u)\\b\\w\\w+\\b. Keep numbers and
English stopwords. TF=count/retained document length; IDF=ln(N/DF), with no
smoothing or +1. L2-normalize before cosine. Ubiquitous terms get zero weight.
Remove term types capitalized in strictly more than half their [A-Za-z]+
occurrences across the raw corpus, intersected with the vectorizer vocabulary.
This heuristic is not entity recognition. Rebuild lengths and norms, keeping
the same 303 documents and remaining document frequencies. Self is excluded;
exact score ties break alphabetically by node ID.

Each page exports five nearest neighbors in each view (3,030 rows total).
The union of these unordered pairs has a cosine and the five largest positive
coordinate products in BOTH vocabularies. Shares divide the word contribution
by the full pair cosine, not just by the five largest terms. Each term references
two entries in the deduplicated raw-excerpt array. Each entry locates its first
occurrence; offsets are zero-based Python Unicode code points, end exclusive.
These passages locate usage, not all occurrences behind the weight.

The original hyperlink graph is used only for descriptive agreement counts:
a direct link in either direction counts once per neighbor. It is not semantic
ground truth. Cosines from different vocabularies are not directly comparable
as evidence of improved matching. 223 of 303 first matches change; the Storm
and Emma Frost surname cases improve, but meaningful names and pronouns explain
why filtering does not universally improve resemblance.

Wikipedia text is CC BY-SA 4.0; page IDs and roster URLs retain attribution.
https://creativecommons.org/licenses/by-sa/4.0/
""",
    },
    "week5": {
        "files": ["site/data/marvel_pages.zip", "site/data/week1_nodes.tsv",
                  "analysis/build_week5.py", "analysis/test_week5.py",
                  "analysis/test_week5.cjs", "site/week5-core.js"],
        "readme": """# Week 5 — Same universe. Same sentences.

Exercise 5.9: an exact shared-token-run network on the frozen 26 August 2026
Marvel Wikipedia corpus (303 full pages). All inputs are bundled.
Source: https://sunelehmann.com/socialgraphs2026-web/data/
Intended post: https://birkir-freyr.github.io/social-graphs/weeks/week5.html

Use Python 3.10+ with NetworkX 3.4.2 and NumPy 1.26.0:

    python3 -m venv .venv
    .venv/bin/python -m pip install networkx==3.4.2 numpy==1.26.0
    .venv/bin/python analysis/build_week5.py
    .venv/bin/python -m unittest discover -s analysis -p test_week5.py
    node --test analysis/test_week5.cjs

On Windows use .venv\\Scripts\\python.exe instead of .venv/bin/python.
Node.js 18+ is only needed for the optional browser-core checks.

Outputs: site/data/week5.json, week5-pairs.csv, week5-thresholds.csv,
and site/assets/week5-shared-text.svg. The JSON includes source hashes and
raw character spans for every pair sharing at least 20 tokens. The full CSV
contains the longest run for every pair sharing at least 8 tokens.

Normalize by lowercasing tokens matched by \\w+(?:[-'’]\\w+)*. Keep numbers,
stopwords, internal apostrophes and hyphens. Other punctuation/whitespace
delimit tokens. No sequence crosses a document boundary. All 45,753 unordered
pairs are in scope. A missing CSV row means a longest run below 8 tokens.
Network edges are undirected shared-text pairs, not the Week 1 hyperlinks.
Fixed layout: >=20-token graph, seed 509, unweighted spring layout within
each component, with components arranged in a grid. Colors identify those
components. Distances have no linguistic meaning.

Long shared runs do not establish copying direction, originality, or intent.
The inspected examples include a plot summary, editorial history, bibliography
and quotation. Revision histories would be needed to study provenance.
Wikipedia text is CC BY-SA 4.0; the archive retains page identifiers for
attribution. https://creativecommons.org/licenses/by-sa/4.0/
""",
    },
    "week4": {
        "files": ["site/data/week4_philosophers_nodes.tsv", "site/data/week4_philosophers_edges.tsv",
                  "analysis/build_week4.py", "analysis/plot_week4.py", "analysis/test_week4.cjs",
                  "site/week4-core.js", "requirements.txt"],
        "readme": """# Week 4 — Two links. Three islands.

Exercise 4.13: a disparity-filter experiment on the frozen 15 September 2026
philosopher Wikipedia dataset. Source: https://sunelehmann.com/socialgraphs2026-web/data/
Intended post URL: https://birkir-freyr.github.io/social-graphs/weeks/week4.html

Use Python 3.10 or newer. From this extracted folder:

    python3 -m venv .venv
    .venv/bin/python -m pip install networkx==3.4.2 numpy==1.26.0 matplotlib==3.8.3
    .venv/bin/python analysis/build_week4.py
    .venv/bin/python analysis/plot_week4.py

On Windows use .venv\\Scripts\\python.exe instead of .venv/bin/python.
The builder writes site/data/week4.json and week4-sweep.csv. The plotter writes
site/assets/week4-backbones.svg. Input hashes, library version and seeds are saved.
After generation, optionally run the independent checks using Node.js 18+:

    node --test analysis/test_week4.cjs

Both directions are summed. Analysis keeps all 1,374 nodes of the original giant
component, including nodes isolated by filtering. Endpoint significance scores
are calculated once on that original weighted graph. Keep if either score is
strictly below alpha. Every tied-score batch is processed together. The largest
single absolute giant-component decrease is 108 to 65 at 0.04712622658232835.
This is an exhaustive threshold scan, not a statistical change-point estimate.

The overview layout comes from the alpha=0.3 backbone: separate spring layouts
(seed 413, k=0.15, 200 iterations) for components, with normalized radius raised
to 0.4 in the largest component for legibility. Smaller components are placed
around it; reference-layout isolates occupy an artificial outer ring. Colors use unweighted Louvain on the original giant, seed 0.
The 108-node detail layout uses the graph just before the critical cut; its
colors show eventual fragments. No network access is needed after installation.
""",
    },
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
    "week3": {
        "files": COMMON + ["analysis/build_week3.py", "site/data/week1.json"],
        "readme": """# Week 3 — You can remove Spider-Man. The universe stays.

Reproduce the Social Graphs course post from the frozen 26 August 2026 dataset.
Source: https://sunelehmann.com/socialgraphs2026-web/data/
Post: https://birkir-freyr.github.io/social-graphs/weeks/week3.html

Use Python 3.10 or newer. Extract the archive, open a terminal in this folder,
then run:

    python3 -m venv .venv
    .venv/bin/python -m pip install networkx==3.4.2
    .venv/bin/python analysis/build_week3.py

On Windows, use .venv\\Scripts\\python.exe in place of .venv/bin/python.

This generates site/data/week3.json and site/data/week3-random-trials.csv. It
recomputes degree and betweenness after each of 100 targeted removals and runs
500 seeded random removal orders. The included Week 1 JSON supplies layout
coordinates only; measurements come from the original roster and edge list.
No network access or GitHub login is needed after installing NetworkX.
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
