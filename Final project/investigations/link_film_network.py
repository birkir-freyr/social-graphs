"""Link B: do Nolan films that share more actors also read more alike?

Three 13 x 13 film matrices (78 pairs):
  C  casting overlap: number of shared actors in the filtered bipartite graph (the film
     projection), and the Jaccard version (shared / union of the two casts)
  S  text similarity: cosine between the two films' centroids of role passages (names masked).
     To stop the link being mechanical (an actor's passages in two films describe the same
     character), each pair's centroids are built WITHOUT the passages of actors in both films.
  Y  years between the films
Mantel test (Spearman between upper triangles; permute film labels, 10,000 draws) and a partial
version that removes Y from both C and S (Spearman partial correlation, same permutation).
Repeated without the three Batman films, the obvious franchise block.

Run from 'Final project' with networkx:  python investigations/link_film_network.py
"""
import json, os, random, itertools
import numpy as np
import networkx as nx
from scipy.stats import spearmanr, rankdata
from common import T, load_rows, vectorise, ROOT

G_all = nx.read_graphml(os.path.join(ROOT, "data/nolan/graphs/nolan_bipartite.graphml"))
G = G_all.copy()
G.remove_edges_from([(a, b) for a, b, d in G_all.edges(data=True)
                     if d["uncredited"] or d["voice"] or d["archive_footage"]])
G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
film_nodes = {d["label"]: n for n, d in G.nodes(data=True) if d["node_type"] == "film"}
cast = {f: {G.nodes[a]["label"] for a in G.neighbors(n)} for f, n in film_nodes.items()}

rows = vectorise(load_rows())
nol = [r for r in rows if r["is_nolan"]]
films = sorted({r["film"] for r in nol}, key=lambda f: min(r["year"] for r in nol if r["film"] == f))
year = {f: min(r["year"] for r in nol if r["film"] == f) for f in films}
missing = [f for f in films if f not in cast]
assert not missing, missing
print("films with passages:", len(films), "| passages per film:",
      {f: sum(r["film"] == f for r in nol) for f in films})


def text_sim(f, g, exclude_shared=True):
    shared = cast[f] & cast[g] if exclude_shared else set()
    a = [r["v"] for r in nol if r["film"] == f and r["actor"] not in shared]
    b = [r["v"] for r in nol if r["film"] == g and r["actor"] not in shared]
    if not a or not b:
        return float("nan")
    return T.cos(T.centroid(a), T.centroid(b))


def matrices(fs):
    n = len(fs)
    C = np.zeros((n, n)); J = np.zeros((n, n)); S = np.zeros((n, n)); S0 = np.zeros((n, n))
    Y = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        f, g = fs[i], fs[j]
        sh = len(cast[f] & cast[g])
        C[i, j] = C[j, i] = sh
        J[i, j] = J[j, i] = sh / len(cast[f] | cast[g])
        S[i, j] = S[j, i] = text_sim(f, g, True)
        S0[i, j] = S0[j, i] = text_sim(f, g, False)
        Y[i, j] = Y[j, i] = abs(year[f] - year[g])
    return C, J, S, S0, Y


def upper(M):
    return M[np.triu_indices(len(M), 1)]


def partial(x, y, z):
    """Spearman partial correlation of x and y given z."""
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz)
    ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
    return np.corrcoef(ex, ey)[0, 1]


def mantel(A, B, Z=None, n_perm=10000, seed=2805):
    a, b = upper(A), upper(B)
    ok = ~np.isnan(b)
    stat = (lambda a_, b_, z_: partial(a_, b_, z_)) if Z is not None else \
           (lambda a_, b_, z_: spearmanr(a_, b_)[0])
    z = upper(Z) if Z is not None else None
    obs = stat(a[ok], b[ok], z[ok] if z is not None else None)
    rng = random.Random(seed)
    n = len(A)
    hits = 0
    for _ in range(n_perm):
        p = list(range(n)); rng.shuffle(p)
        Bp = B[np.ix_(p, p)]
        bp = upper(Bp); okp = ~np.isnan(bp) & ok
        # permuting B's labels keeps A and Z fixed (Z describes the same films as A)
        s = stat(a[okp], bp[okp], z[okp] if z is not None else None)
        hits += abs(s) >= abs(obs)
    return obs, (hits + 1) / (n_perm + 1), int(ok.sum())


out = {}
for label, fs in (("all films", films),
                  ("without Batman", [f for f in films if "Batman" not in f and "Dark Knight" not in f])):
    C, J, S, S0, Y = matrices(fs)
    print(f"\n=== {label} ({len(fs)} films, {len(fs)*(len(fs)-1)//2} pairs) ===")
    for name, A, B, Z in (("shared actors ~ text (shared actors' passages removed)", C, S, None),
                          ("Jaccard ~ text (shared removed)", J, S, None),
                          ("shared actors ~ text (all passages)", C, S0, None),
                          ("years apart ~ text (shared removed)", Y, S, None),
                          ("years apart ~ shared actors", Y, C, None),
                          ("shared actors ~ text | years (partial)", C, S, Y)):
        r, p, n = mantel(A, B, Z)
        print(f"  {name:<56} rho {r:+.3f}  p {p:.4f}  (pairs {n})")
        out[f"{label}: {name}"] = dict(rho=r, p=p, pairs=n)
    # the most similar pairs, for reading
    pairs = sorted(((S[i, j], C[i, j], fs[i], fs[j]) for i, j in itertools.combinations(range(len(fs)), 2)
                    if not np.isnan(S[i, j])),
                   reverse=True)
    print("  top text-similar pairs (cos, shared actors):")
    for s, c, f, g in pairs[:6]:
        print(f"    {s:.3f}  {int(c):>2}  {f} / {g}")
    print("  least similar:")
    for s, c, f, g in pairs[-3:]:
        print(f"    {s:.3f}  {int(c):>2}  {f} / {g}")

json.dump(out, open(os.path.join(ROOT, "investigations/link_film_network.json"), "w"), indent=1)
