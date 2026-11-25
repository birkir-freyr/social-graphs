"""Is the selection test biased by how many earlier roles define each type?

Found in link_homophily.py: a centroid of many passages sits closer to the corpus mean, so it is
closer to ANY new passage (Spearman 0.93 between an actor's number of passages and their type's
cosine to the corpus centroid). In selection_test.py the cast actor's type is compared with other
actors' types of different sizes, so prolific actors rank as 'cast to type' for that reason alone.

Fix: every type (cast actor and comparison actors alike) is the centroid of exactly k earlier
eligible roles, the k most recent ones. We report k = 3 and k = 5, plus the size-free original.
Also reruns the regulars-vs-one-timers comparison of link_regulars.py on the fixed-size percentile.

Run from 'Final project/investigations':  python3 selection_fixed_size.py
"""
import csv, os, random, statistics as st
from collections import defaultdict
from common import T, load_rows, vectorise, by_actor, priors_for, signflip, fmt, ROOT


def percentiles_k(rows, k):
    A = by_actor(rows)
    cache = {}
    def type_before(actor, year, exclude_film, exclude_director):
        key = (actor, year, exclude_film, exclude_director)
        if key not in cache:
            bp = sorted((x for x in A[actor] if x["year"] and x["year"] < year and x["film"] != exclude_film
                         and x["director"] != exclude_director), key=lambda x: x["year"])
            cache[key] = T.centroid([x["v"] for x in bp[-k:]]) if len(bp) >= k else None
        return cache[key]
    out = []
    for actor, rs in A.items():
        for t in rs:
            if not t["year"] or not t["director"]:
                continue
            own_prior = sorted(priors_for(rs, t, "typecast" if t["is_nolan"] else "director"),
                               key=lambda x: x["year"])
            if len(own_prior) < k:
                continue
            own = T.cos(t["v"], T.centroid([x["v"] for x in own_prior[-k:]]))
            others = [T.cos(t["v"], c) for b in A if b != actor
                      for c in [type_before(b, t["year"], t["film"], t["director"])] if c is not None]
            if len(others) < 10:
                continue
            out.append(dict(actor=actor, is_nolan=t["is_nolan"], film=t["film"], n_prior=len(own_prior),
                            pct=sum(o < own for o in others) / len(others)))
    return out


def summary(P, label):
    nol = [p for p in P if p["is_nolan"]]
    oth = [p for p in P if not p["is_nolan"]]
    print(f"\n[{label}] {len(P)} roles ({len(nol)} Nolan)")
    print(f"   mean percentile: Nolan {st.mean(p['pct'] for p in nol):.3f}   other {st.mean(p['pct'] for p in oth):.3f}")
    from scipy.stats import spearmanr
    rho, pv = spearmanr([p["n_prior"] for p in P], [p["pct"] for p in P])
    print(f"   Spearman(n earlier roles, percentile) rho {rho:+.3f} p {pv:.2g}")
    g = defaultdict(list)
    for p in nol:
        g[p["actor"]].append(p["pct"] - 0.5)
    print("  ", fmt(signflip(g), "Nolan actors vs random actor (pct - 0.5)"))
    g = defaultdict(list)
    for p in oth:
        g[p["actor"]].append(p["pct"] - 0.5)
    print("  ", fmt(signflip(g), "Other directors' actors vs random actor"))
    a = defaultdict(lambda: {"n": [], "o": []})
    for p in P:
        a[p["actor"]]["n" if p["is_nolan"] else "o"].append(p["pct"])
    g = {kk: [st.mean(v["n"]) - st.mean(v["o"])] for kk, v in a.items() if v["n"] and v["o"]}
    print("  ", fmt(signflip(g), "Nolan minus same actor's other roles (pct)"))
    # regulars (3+ Nolan films, filtered cast) vs one-timers
    films = defaultdict(set)
    titles = {r["film_id"]: r["title"] for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_films.csv")))}
    for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_cast.csv"), encoding="utf-8")):
        if r["uncredited"] == "False" and r["voice"] == "False" and r["archive_footage"] == "False":
            films[r["actor_name"]].add(titles[r["film_id"]])
    m = defaultdict(list)
    for p in nol:
        m[p["actor"]].append(p["pct"])
    m = {kk: st.mean(v) for kk, v in m.items()}
    for th in (2, 3):
        reg = [v for kk, v in m.items() if len(films[kk]) >= th]
        one = [v for kk, v in m.items() if len(films[kk]) < th]
        acts = list(m); lab = [len(films[kk]) >= th for kk in acts]; val = [m[kk] for kk in acts]
        d = lambda l: st.mean([v for v, x in zip(val, l) if x]) - st.mean([v for v, x in zip(val, l) if not x])
        obs = d(lab); rng = random.Random(2805); hits = 0
        for _ in range(10000):
            l = lab[:]; rng.shuffle(l); hits += abs(d(l)) >= abs(obs)
        print(f"   regulars {th}+ films {st.mean(reg):.3f} (n={len(reg)}) vs one-timers {st.mean(one):.3f} "
              f"(n={len(one)}): diff {obs:+.3f} p {(hits + 1) / 10001:.3f}")


if __name__ == "__main__":
    rows = vectorise(load_rows())
    from selection_test import percentiles
    P0 = percentiles(rows)
    A = by_actor(rows)
    for p in P0:   # attach n_prior for the size-free version
        t = next(x for x in A[p["actor"]] if x["film"] == p["film"])
        p["n_prior"] = len(priors_for(A[p["actor"]], t, "typecast" if t["is_nolan"] else "director"))
    summary(P0, "original: all earlier roles (sizes differ)")
    for k in (3, 5):
        summary(percentiles_k(rows, k), f"fixed size: the {k} most recent earlier roles")
