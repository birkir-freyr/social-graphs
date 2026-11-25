"""Can the role-text measure tell actors apart at all?

If 'type' is real and the measure captures it, a role's passage should be closer to the SAME
actor's earlier roles than to other actors' earlier roles. We test this as identification:
for every scored role, rank its own actor's prior centroid among the prior centroids of all
actors who had 3+ roles before that year. Chance gives a mean percentile of 0.5.

Two comparisons control for the film:
 - co-star: is the actor's own passage closer to their type than a co-star's passage from the
   same film is? (the placebo, now per role, for all directors)
 - film-level: the same identification with the film title's other characters removed.

Run from 'Final project/investigations':  python3 actor_signal.py
"""
import random, statistics as st
from collections import defaultdict
from common import T
from common import load_rows, vectorise, by_actor, priors_for, MIN_PRIOR


def centroid_excluding_film(prior, film):
    keep = [x for x in prior if x["film"] != film]
    return T.centroid([x["v"] for x in keep]) if len(keep) >= 2 else None


def run(text):
    rows = vectorise(load_rows(text))
    A = by_actor(rows)
    pct, pct_nolan, top1 = [], [], 0
    for actor, rs in A.items():
        for t in rs:
            if not t["year"]:
                continue
            own_prior = priors_for(rs, t, "typecast" if t["is_nolan"] else "director") if t["director"] else []
            if len(own_prior) < MIN_PRIOR:
                continue
            own = T.cos(t["v"], T.centroid([x["v"] for x in own_prior]))
            others = []
            for b, bs in A.items():
                if b == actor:
                    continue
                bp = [x for x in bs if x["year"] and x["year"] < t["year"] and x["film"] != t["film"]]
                if len(bp) >= MIN_PRIOR:
                    others.append(T.cos(t["v"], T.centroid([x["v"] for x in bp])))
            if len(others) < 10:
                continue
            p = sum(o < own for o in others) / len(others)
            (pct_nolan if t["is_nolan"] else pct).append(p)
            top1 += own > max(others)
    allp = pct + pct_nolan
    print(f"[{text}] roles tested {len(allp)}: mean percentile of OWN actor "
          f"{st.mean(allp):.3f} (chance 0.5); ranked first {top1}/{len(allp)}; "
          f"Nolan roles {st.mean(pct_nolan):.3f} (n={len(pct_nolan)}), others {st.mean(pct):.3f}")
    return allp


if __name__ == "__main__":
    for text in ("role_text_blind", "role_text_masked", "role_text"):
        run(text)
