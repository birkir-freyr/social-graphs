"""Link A: do the actors at the core of Nolan's casting network get different parts?

Network side: for each actor, the number of Nolan films (degree in the filtered bipartite
graph) and betweenness (normalised, filtered graph, as in Table 1).
Text side, per scored Nolan role (3+ earlier roles by other directors):
  diff     excess departure (the paper's measure)
  role     diff minus the mean diff of same-film co-stars' passages (placebo-corrected; the
           part of the departure that belongs to the role, not to the film's vocabulary)
  pct      selection percentile (share of other actors whose type is further from the passage)

Questions
  1. Regulars (2+ Nolan films) vs one-timers: actor-level means, label permutation test.
  2. First Nolan role only (did Nolan first cast future regulars differently?).
  3. Spearman of actor mean vs betweenness and vs number of Nolan films.

Run from 'Final project' with networkx:  python investigations/link_regulars.py
"""
import json, os, random, statistics as st
from collections import defaultdict
import networkx as nx
from scipy.stats import spearmanr
from common import load_rows, vectorise, ROOT
from film_confound import scored_roles, placebo
from selection_test import percentiles

# ---------- network ----------
G_all = nx.read_graphml(os.path.join(ROOT, "data/nolan/graphs/nolan_bipartite.graphml"))
G = G_all.copy()
G.remove_edges_from([(a, b) for a, b, d in G_all.edges(data=True)
                     if d["uncredited"] or d["voice"] or d["archive_footage"]])
G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
bc = nx.betweenness_centrality(G, normalized=True)
k_nolan, btw = {}, {}
for n, d in G.nodes(data=True):
    if d["node_type"] == "actor":
        k_nolan[d["label"]] = G.degree(n)
        btw[d["label"]] = bc[n]

# ---------- text ----------
rows = vectorise(load_rows())
scored = scored_roles(rows)
nol = [s for s in scored if s["is_nolan"]]
pl = {(p["actor"], p["film"], p["character"]): p["placebo"] for p in placebo(rows, scored)}
pc = {}
for p in percentiles(rows):
    if p["is_nolan"]:
        pc.setdefault((p["actor"], p["film"]), p["pct"])

roles = []
for s in nol:
    key = (s["actor"], s["film"], s["character"])
    roles.append(dict(actor=s["actor"], film=s["film"], year=s["year"], diff=s["diff"],
                      role=(s["diff"] - pl[key]) if key in pl else None,
                      pct=pc.get((s["actor"], s["film"])),
                      k=k_nolan.get(s["actor"]), b=btw.get(s["actor"])))
missing = [r["actor"] for r in roles if r["k"] is None]
print(f"scored Nolan roles {len(roles)}; actors not matched to network: {sorted(set(missing))}")
roles = [r for r in roles if r["k"] is not None]


def actor_means(rs, field):
    g = defaultdict(list)
    for r in rs:
        if r[field] is not None:
            g[r["actor"]].append(r[field])
    return {a: st.mean(v) for a, v in g.items()}


def perm_diff(means, is_reg, n_perm=10000, seed=2805):
    """Difference of group means (regulars - one-timers) over actors, label permutation."""
    acts = list(means)
    lab = [is_reg[a] for a in acts]
    val = [means[a] for a in acts]
    def d(l):
        r = [v for v, x in zip(val, l) if x]
        o = [v for v, x in zip(val, l) if not x]
        return st.mean(r) - st.mean(o)
    obs = d(lab)
    rng = random.Random(seed)
    null = []
    for _ in range(n_perm):
        l = lab[:]
        rng.shuffle(l)
        null.append(d(l))
    p = (1 + sum(abs(x) >= abs(obs) for x in null)) / (n_perm + 1)
    return obs, p, sum(lab), len(lab) - sum(lab)


out = {}
first = {}
for r in sorted(roles, key=lambda r: r["year"]):
    first.setdefault(r["actor"], r)
for thresh in (2, 3):
    print(f"\n--- regulars = {thresh}+ Nolan films ---")
    for subset, rs in (("all Nolan roles", roles), ("first Nolan role", list(first.values()))):
        for field in ("diff", "role", "pct"):
            m = actor_means(rs, field)
            is_reg = {a: k_nolan[a] >= thresh for a in m}
            reg = [m[a] for a in m if is_reg[a]]
            one = [m[a] for a in m if not is_reg[a]]
            obs, p, nr, no = perm_diff(m, is_reg)
            print(f"{subset:<17} {field:<5} regulars {st.mean(reg):+.4f} (n={nr})  "
                  f"one-timers {st.mean(one):+.4f} (n={no})  diff {obs:+.4f}  p {p:.3f}")
            out[f"k{thresh}_{subset.split()[0]}_{field}"] = dict(
                regulars=st.mean(reg), one_timers=st.mean(one), n_reg=nr, n_one=no, diff=obs, p=p)

print("\n--- Spearman over actors (all Nolan roles, actor means) ---")
for field in ("diff", "role", "pct"):
    m = actor_means(roles, field)
    acts = list(m)
    for xname, x in (("betweenness", btw), ("n Nolan films", k_nolan)):
        rho, p = spearmanr([x[a] for a in acts], [m[a] for a in acts])
        print(f"{field:<5} vs {xname:<14} rho {rho:+.3f}  p {p:.3f}  (n={len(acts)})")
        out[f"spearman_{field}_{xname.split()[0]}"] = dict(rho=rho, p=p, n=len(acts))

print("\n--- regulars, role by role (k>=2) ---")
for r in sorted(roles, key=lambda r: (-r["k"], r["actor"], r["year"])):
    if r["k"] >= 2:
        f = lambda v: "   n/a" if v is None else f"{v:+.3f}"
        print(f"  {r['actor']:<22} k={r['k']}  {r['film']:<28} diff {f(r['diff'])}  "
              f"role {f(r['role'])}  pct {f(r['pct'])}")

json.dump(out, open(os.path.join(ROOT, "investigations/link_regulars.json"), "w"), indent=1)

# ---------- robustness of the one result with p < 0.05 (3+ films, pct, all roles) ----------
print("\n--- robustness: regulars (3+) vs one-timers, selection percentile ---")
m = actor_means(roles, "pct")
is_reg = {a: k_nolan[a] >= 3 for a in m}
for drop in [a for a in m if is_reg[a]]:
    mm = {a: v for a, v in m.items() if a != drop}
    obs, p, nr, no = perm_diff(mm, {a: is_reg[a] for a in mm})
    print(f"  without {drop:<20} diff {obs:+.3f}  p {p:.3f}")
# reprised characters (same character in an earlier Nolan film) counted once: keep first only
seen, once = set(), []
for r in sorted(roles, key=lambda r: r["year"]):
    ch = next(s["character"] for s in nol if s["actor"] == r["actor"] and s["film"] == r["film"])
    key = (r["actor"], ch.split()[-1].lower())
    if key in seen:
        continue
    seen.add(key)
    once.append(r)
m = actor_means(once, "pct")
obs, p, nr, no = perm_diff(m, {a: k_nolan[a] >= 3 for a in m})
print(f"  reprised characters counted once ({len(once)} roles): diff {obs:+.3f}  p {p:.3f}")
# role-level, actor-clustered: regress pct on log(k) is overkill; report the 18 tests caveat
print("  note: 18 regulars-vs-one-timers comparisons above; one p < 0.05 is what chance gives.")
