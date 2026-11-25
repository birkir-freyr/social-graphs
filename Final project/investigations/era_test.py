"""Does Nolan reuse actors in eras? Films close in time should share more cast than distant ones.

Statistic: Spearman correlation, over all 78 film pairs, between the number of shared actors
and the gap in release years (negative = nearby films share more). Null: permute which film
gets which release year (10,000 permutations), keeping the casts fixed (a Mantel-type test).
Also reported without the three Batman films, since sequels share cast by design.

Run with networkx and scipy available, from 'Final project':  python investigations/era_test.py
"""
import os, random, itertools, json
import networkx as nx
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G0 = nx.read_graphml(os.path.join(ROOT, "data/nolan/graphs/nolan_bipartite.graphml"))


def casts(main_only):
    out = {}
    for a, f, d in G0.edges(data=True):
        if d["uncredited"] or d["voice"] or d["archive_footage"]:
            continue
        if main_only and int(d["cast_order"]) >= 10:
            continue
        if G0.nodes[a]["node_type"] != "actor":
            a, f = f, a
        out.setdefault(f, set()).add(a)
    return out


def test(cast, exclude=()):
    films = [f for f in cast if G0.nodes[f]["label"] not in exclude]
    year = {f: G0.nodes[f]["year"] for f in films}
    pairs = list(itertools.combinations(films, 2))
    shared = [len(cast[a] & cast[b]) for a, b in pairs]
    def rho(yr):
        return spearmanr(shared, [abs(yr[a] - yr[b]) for a, b in pairs]).correlation
    obs = rho(year)
    rng = random.Random(2805)
    ys = list(year.values())
    null = []
    for _ in range(10000):
        rng.shuffle(ys)
        null.append(rho(dict(zip(films, ys))))
    p = (1 + sum(x <= obs for x in null)) / (len(null) + 1)
    return obs, p, len(pairs)


res = {}
for main_only in (False, True):
    for excl in ((), ("Batman Begins", "The Dark Knight", "The Dark Knight Rises")):
        label = f"{'main cast' if main_only else 'all credited'}{', no Batman films' if excl else ''}"
        obs, p, n = test(casts(main_only), excl)
        res[label] = dict(spearman=round(obs, 3), p_one_sided=round(p, 4), pairs=n)
        print(f"{label:<36} pairs {n:>2}  Spearman(shared, year gap) {obs:+.3f}  p {p:.4f}")
json.dump(res, open(os.path.join(ROOT, "investigations/era_test.json"), "w"), indent=1)
