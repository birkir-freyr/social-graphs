"""Positive control: can the measure see casting to type when we KNOW it is there?

The same-film placebo shows the measure cannot tell an actor's own part from a co-star's part
in the same film, for any director. That is either because nobody casts against type, or because
the measure cannot see casting at the level of the part. A reprised character (the same actor
playing the same character in a later film: Caine's Alfred, Oldman's Gordon, franchise sequels in
the wider careers) is casting to type by definition. If the measure works, a reprise must sit
closer to the actor's type than a co-star's part in the same film does.

Type here = all of the actor's earlier roles (any director, Nolan included), so the earlier
version of the character is part of the type. Two versions of each test:
  1. departure (1 - cos to the centroid of earlier roles) of the own part vs the mean over
     same-film co-stars' parts (placebo rule of film_confound.py), actor-clustered sign-flip;
  2. the same with the equal-size rank (3 most recent earlier roles; selection_placebo.py logic).
Run for reprises and, as the comparison, for all other later roles (non-reprises).
A reprise is an earlier role of the same actor, in a different film, whose credited character
shares a surname token (within_nolan.char_tokens), with descriptive credits ('Guard') excluded.

Run from 'Final project':  python3 investigations/sequel_control.py
"""
import os, statistics as st, sys
from collections import defaultdict
from common import T, load_rows, vectorise, by_actor, signflip, fmt, ROOT
sys.path.insert(0, ROOT)
import within_nolan as W
from check_descriptors import is_descriptor

K = 3
# surname matches checked by eye: these share a name but are different characters
NOT_REPRISE = {("Casey Affleck", "Interstellar"), ("Matthew McConaughey", "Interstellar")}
rows = vectorise(load_rows())
A = by_actor(rows)
film_rows = defaultdict(list)
for r in rows:
    film_rows[(r["film"], r["year"])].append(r)


def toks(r):
    return set() if is_descriptor(r["character"]) else W.char_tokens(r["character"])


def earlier(actor, t):
    return sorted((x for x in A[actor] if x["year"] and t["year"] and x["year"] < t["year"]
                   and x["film"] != t["film"]), key=lambda x: x["year"])


# comparison pool for the rank: every actor's K most recent earlier roles (same rule for all)
cache = {}
def type_k(actor, year, exclude_film):
    key = (actor, year, exclude_film)
    if key not in cache:
        bp = sorted((x for x in A[actor] if x["year"] and x["year"] < year and x["film"] != exclude_film),
                    key=lambda x: x["year"])
        cache[key] = T.centroid([x["v"] for x in bp[-K:]]) if len(bp) >= K else None
    return cache[key]


res = []
for actor, rs in A.items():
    for t in rs:
        prior = earlier(actor, t)
        if len(prior) < K:
            continue
        mine = toks(t)
        reprise = [x for x in prior if mine and (toks(x) & mine)]
        if (actor, t["film"]) in NOT_REPRISE:
            reprise = []
        mates = [m for m in film_rows[(t["film"], t["year"])]
                 if m["actor"] != actor and not (W.char_tokens(m["character"]) & W.char_tokens(t["character"]))
                 and m["text"] != t["text"]]
        if not mates:
            continue
        c_all = T.centroid([x["v"] for x in prior])
        dep_own = 1 - T.cos(t["v"], c_all)
        dep_pl = st.mean(1 - T.cos(m["v"], c_all) for m in mates)
        ck = T.centroid([x["v"] for x in prior[-K:]])
        # for reprises, make sure the earlier version is inside the K-role type
        if reprise and not any(x in prior[-K:] for x in reprise):
            ck = T.centroid([x["v"] for x in (prior[-(K - 1):] + [reprise[-1]])])
        pool = [c for b in A if b != actor for c in [type_k(b, t["year"], t["film"])] if c is not None]
        if len(pool) < 10:
            continue
        def pct(v):
            own = T.cos(v, ck)
            return sum(T.cos(v, c) < own for c in pool) / len(pool)
        res.append(dict(actor=actor, film=t["film"], character=t["character"], is_nolan=t["is_nolan"],
                        reprise=bool(reprise), earlier=[f"{x['film']} ({x['character']})" for x in reprise],
                        dep_own=dep_own, dep_pl=dep_pl, pct_own=pct(t["v"]),
                        pct_pl=st.mean(pct(m["v"]) for m in mates),
                        # direct: similarity to the most recent earlier version of the character
                        sim_own=T.cos(t["v"], reprise[-1]["v"]) if reprise else None,
                        sim_pl=st.mean(T.cos(m["v"], reprise[-1]["v"]) for m in mates) if reprise else None))

rep = [r for r in res if r["reprise"]]
non = [r for r in res if not r["reprise"]]
print(f"later roles with a same-film co-star: {len(res)}; reprises {len(rep)} "
      f"({len({r['actor'] for r in rep})} actors; Nolan {sum(r['is_nolan'] for r in rep)})\n")
print("reprises found (check by eye):")
for r in sorted(rep, key=lambda r: (r["actor"], r["film"])):
    print(f"  {r['actor']:<22} {r['film']:<34} {r['character'][:28]:<28} <- {'; '.join(r['earlier'])[:70]}")

for lab, S in (("REPRISES", rep), ("other later roles", non)):
    print(f"\n=== {lab} (n={len(S)}) ===")
    print(f"  departure: own {st.mean(r['dep_own'] for r in S):.4f}   co-star {st.mean(r['dep_pl'] for r in S):.4f}")
    g = defaultdict(list)
    for r in S:
        g[r["actor"]].append(r["dep_own"] - r["dep_pl"])
    print("  ", fmt(signflip(g), "departure own - co-star (negative = closer to type)"))
    print(f"  rank (k={K}): own {st.mean(r['pct_own'] for r in S):.3f}   co-star {st.mean(r['pct_pl'] for r in S):.3f}")
    g = defaultdict(list)
    for r in S:
        g[r["actor"]].append(r["pct_own"] - r["pct_pl"])
    print("  ", fmt(signflip(g), "rank own - co-star (positive = fits own part better)"))
    print(f"  share of parts where own is closer than co-star: "
          f"{sum(r['dep_own'] < r['dep_pl'] for r in S) / len(S):.2f}")

print("\n=== REPRISES, direct: cosine to the earlier version of the same character ===")
print(f"  own part {st.mean(r['sim_own'] for r in rep):.4f}   co-star's part {st.mean(r['sim_pl'] for r in rep):.4f}")
g = defaultdict(list)
for r in rep:
    g[r["actor"]].append(r["sim_own"] - r["sim_pl"])
print("  ", fmt(signflip(g), "own - co-star (positive = recognises the character)"))
print(f"  share where own is closer: {sum(r['sim_own'] > r['sim_pl'] for r in rep) / len(rep):.2f}")
for r in sorted(rep, key=lambda r: r["sim_own"] - r["sim_pl"]):
    print(f"    {r['actor']:<20} {r['film'][:30]:<30} own {r['sim_own']:.3f}  co-star {r['sim_pl']:.3f}")
