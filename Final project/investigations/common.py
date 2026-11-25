"""Shared helpers for the follow-up analyses in investigations/.

Everything here reuses typecast.py's vectoriser, centroid and cosine, so the scores are the
same quantities the paper reports. Run scripts from the 'Final project' folder.
"""
import csv, math, os, random, re, statistics as st, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import typecast as T            # noqa: E402
import director_test as D       # noqa: E402

TEXT = "role_text_blind"        # all-names masked: the paper's primary specification
MIN_PRIOR = 3


def load_rows(text=TEXT, path=os.path.join(ROOT, "passages.csv")):
    """Usable roles (25+ words) with year, Nolan flag, director and wiki page."""
    rows = T.load(path, text)
    raw = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        raw[(r["actor"], r["film"], r["character"])] = r
    table = D.load_director_table(os.path.join(ROOT, D.DIRECTORS_CSV))
    for r in rows:
        src = raw.get((r["actor"], r["film"], r["character"]), {})
        r["wiki_page"] = src.get("wiki_page", "")
        r["n_words"] = len(r["text"].split())
        r["director"] = ("Christopher Nolan" if r["is_nolan"]
                         else D.normalise(table.get(r["wiki_page"], "")))
    return rows


def page_mismatch(r):
    """True when the Wikipedia article shares no word with the film title (Hanna's flag)."""
    words = lambda s: {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 1}
    t, p = words(r["film"]), words(r["wiki_page"])
    return bool(t) and bool(p) and not (t & p)


def vectorise(rows, drop_terms=frozenset()):
    """typecast.tfidf_vectors, optionally with some terms removed before weighting."""
    if not drop_terms:
        vecs = T.tfidf_vectors(rows)
    else:
        toks = [[w for w in T.tokens(r["text"]) if w not in drop_terms] for r in rows]
        df = Counter(w for t in toks for w in set(t))
        N = len(rows)
        idf = {w: math.log(N / c) for w, c in df.items() if c >= 2}
        vecs = []
        for t in toks:
            tf = Counter(t)
            n = sum(tf.values()) or 1
            v = {w: (c / n) * idf[w] for w, c in tf.items() if w in idf}
            nm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            vecs.append({w: x / nm for w, x in v.items()})
    for r, v in zip(rows, vecs):
        r["v"] = v
    return rows


def priors_for(actor_rows, target, mode="director"):
    """Earlier roles of the same actor that define the 'type' for this target.

    mode='director': earlier roles under a different director (director_test.py rule).
    mode='typecast' : earlier non-Nolan roles (typecast.py rule; identical for Nolan targets).
    """
    if mode == "typecast":
        return [x for x in actor_rows if not x["is_nolan"] and x["year"] and target["year"]
                and x["year"] < target["year"]]
    # Same rule as director_test.py: an earlier role whose director could not be parsed
    # ('') still counts, since it is certainly not by the target's (parsed) director.
    return [x for x in actor_rows if x is not target and x["year"] and target["year"]
            and x["year"] < target["year"] and x["director"] != target["director"]]


def score(target_vec, prior):
    """Leave-one-out excess departure exactly as in typecast.py / director_test.py.

    Returns (departure of the target, mean departure of the controls) or None.
    """
    dep, ctrl = [], []
    for i, x in enumerate(prior):
        rest = prior[:i] + prior[i + 1:]
        if len(rest) < 2:
            continue
        c = T.centroid([y["v"] for y in rest])
        dep.append(1 - T.cos(target_vec, c))
        ctrl.append(1 - T.cos(x["v"], c))
    if not ctrl:
        return None
    return st.mean(dep), st.mean(ctrl)


def by_actor(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["actor"]].append(r)
    return out


def signflip(values_by_cluster, n_perm=10000, seed=2805):
    """Actor-clustered sign-flip test of mean(values) == 0 (two-sided), as in typecast.py.

    values_by_cluster: dict cluster -> list of values. Returns (mean, z, p, n_values, n_clusters).
    """
    rng = random.Random(seed)
    groups = [v for v in values_by_cluster.values() if v]
    n = sum(len(v) for v in groups)
    obs = sum(sum(v) for v in groups) / n
    sums = [sum(v) for v in groups]
    null = []
    for _ in range(n_perm):
        null.append(sum(s if rng.random() < 0.5 else -s for s in sums) / n)
    sd = st.pstdev(null)
    p = (sum(1 for x in null if abs(x) >= abs(obs)) + 1) / (n_perm + 1)
    return obs, (obs / sd if sd else float("nan")), p, n, len(groups)


def fmt(res, label):
    m, z, p, n, k = res
    return f"{label:<58} mean {m:+.4f}  z {z:+5.2f}  p {p:.4f}  (n={n}, actors={k})"
