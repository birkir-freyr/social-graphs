"""Is the same-film placebo a fair comparison?

1. Length: short passages look atypical. If co-stars' passages are shorter than the actor's own,
   the placebo departure is inflated and could hide a real casting effect. We compare lengths and
   rerun the placebo with every passage truncated to 60 words (shorter ones dropped).
2. Precision: an actor-clustered bootstrap 95% interval for (own part - co-star part), so the text
   can say how large a casting effect the data rule out.

Run from 'Final project/investigations':  python3 placebo_checks.py
"""
import random, statistics as st
from collections import defaultdict
import common
from common import load_rows, vectorise, signflip, fmt
from film_confound import scored_roles, placebo


def boot_ci(g, B=5000, seed=2805):
    rng = random.Random(seed)
    keys = list(g)
    flat = lambda ks: [x for k in ks for x in g[k]]
    est = st.mean(flat(keys))
    bs = sorted(st.mean(flat([rng.choice(keys) for _ in keys])) for _ in range(B))
    return est, bs[int(.025 * B)], bs[int(.975 * B) - 1]


def run(rows, label):
    sc = scored_roles(rows)
    pl = [p for p in placebo(rows, sc) if p["is_nolan"]]
    g = defaultdict(list)
    for p in pl:
        g[p["actor"]].append(p["diff"] - p["placebo"])
    est, lo, hi = boot_ci(g)
    print(fmt(signflip(g), label), f"  95% CI [{lo:+.4f}, {hi:+.4f}]")
    return pl


rows = vectorise(load_rows())
pl = run(rows, "own minus co-star (full passages)")
# lengths: own passage vs the co-stars it is compared with
film_rows = defaultdict(list)
for r in rows:
    film_rows[r["film"]].append(r)
own_len = [p["target"]["n_words"] for p in pl]
mate_len = [st.mean(m["n_words"] for m in film_rows[p["film"]]
                    if m["actor"] != p["actor"] and m["text"] != p["target"]["text"]) for p in pl]
print(f"passage length: own median {st.median(own_len):.0f} words, co-stars' mean-per-part median "
      f"{st.median(mate_len):.0f} words")

for n in (60, 100):
    tr = []
    for r in load_rows():
        w = r["text"].split()
        if len(w) >= n:
            r["text"] = " ".join(w[:n])
            r["n_words"] = n
            tr.append(r)
    run(vectorise(tr), f"own minus co-star, all passages cut to {n} words")
