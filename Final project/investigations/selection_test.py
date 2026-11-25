"""SUPERSEDED (run 2): types of different sizes bias this rank; see selection_fixed_size.py and
selection_placebo.py, which the paper now uses.

Does Nolan SELECT actors whose type is far from the part, beyond his films being unusual?

The excess-departure statistic cannot separate 'the part is unlike the actor's earlier work'
from 'the film is unlike most films'. A ranking removes the film: for a given role passage,
compare the cast actor's type with the types of every other actor who had 3+ earlier roles by
then. An unusual film is far from everyone's type, so it does not move the rank. If Nolan casts
against type, his actors should rank LOWER (less similar) than other directors' actors do.

percentile = share of other actors whose type is LESS similar to the passage than the cast
actor's type. 0.5 = the cast actor is a random draw; >0.5 = cast to type.

Run from 'Final project/investigations':  python3 selection_test.py
"""
import random, statistics as st
from collections import defaultdict
from common import T, load_rows, vectorise, by_actor, priors_for, signflip, fmt, MIN_PRIOR


def percentiles(rows):
    A = by_actor(rows)
    # cache each actor's role list sorted by year for quick 'before year' centroids
    out = []
    cent_cache = {}
    def type_before(actor, year, exclude_film, exclude_director):
        # same rule as the cast actor's own type: earlier roles, not in this film, and not by
        # this film's director (so Nolan vocabulary cannot leak into other actors' types)
        key = (actor, year, exclude_film, exclude_director)
        if key not in cent_cache:
            bp = [x for x in A[actor] if x["year"] and x["year"] < year and x["film"] != exclude_film
                  and x["director"] != exclude_director]
            cent_cache[key] = T.centroid([x["v"] for x in bp]) if len(bp) >= MIN_PRIOR else None
        return cent_cache[key]
    for actor, rs in A.items():
        for t in rs:
            if not t["year"] or not t["director"]:
                continue
            own_prior = priors_for(rs, t, "typecast" if t["is_nolan"] else "director")
            if len(own_prior) < MIN_PRIOR:
                continue
            own = T.cos(t["v"], T.centroid([x["v"] for x in own_prior]))
            others = []
            for b in A:
                if b == actor:
                    continue
                c = type_before(b, t["year"], t["film"], t["director"])
                if c is not None:
                    others.append(T.cos(t["v"], c))
            if len(others) < 10:
                continue
            out.append(dict(actor=actor, is_nolan=t["is_nolan"], film=t["film"],
                            pct=sum(o < own for o in others) / len(others), n_others=len(others)))
    return out


if __name__ == "__main__":
    for text in ("role_text_blind", "role_text_masked"):
        rows = vectorise(load_rows(text))
        P = percentiles(rows)
        nol = [p for p in P if p["is_nolan"]]
        oth = [p for p in P if not p["is_nolan"]]
        print(f"\n[{text}] scored {len(P)} roles ({len(nol)} Nolan); median comparison pool "
              f"{st.median(p['n_others'] for p in P):.0f} actors")
        print(f"   mean percentile: Nolan {st.mean(p['pct'] for p in nol):.3f}   "
              f"other directors {st.mean(p['pct'] for p in oth):.3f}   (0.5 = random actor)")
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
        g = {k: [st.mean(v["n"]) - st.mean(v["o"])] for k, v in a.items() if v["n"] and v["o"]}
        print("  ", fmt(signflip(g), "Nolan minus same actor's other roles (pct)"))
