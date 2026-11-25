"""Second question of the paper: are an actor's several Nolan characters unusually dissimilar?

within_nolan.py compares the mean pairwise cosine among an actor's distinct Nolan characters
with random same-size subsets of that actor's other roles. Those other roles come from
different films too, so the comparison mixes 'different character' with 'different film'.

Placebo: for each pair of the actor's Nolan characters (films X and Y), take pairs of
CO-STAR passages from the same two films. If the actor's own pair is as dissimilar as two
random characters from X and Y, the low similarity belongs to the films, not the casting.

Run from 'Final project/investigations':  python3 returning_placebo.py
"""
import statistics as st
from collections import defaultdict
from itertools import combinations
from common import T, load_rows, vectorise, by_actor, signflip, fmt
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); import within_nolan as W

rows = vectorise(load_rows("role_text_blind"))
A = by_actor(rows)
film_rows = defaultdict(list)
for r in rows:
    film_rows[r["film"]].append(r)

g_real_minus_placebo = defaultdict(list)
real_all, plac_all, ctrl_all = [], [], []
for actor, rs in A.items():
    nol = W.group_characters([r for r in rs if r["is_nolan"]])
    if len(nol) < 2:
        continue
    for a, b in combinations(nol, 2):
        if a["film"] == b["film"]:
            continue
        real = T.cos(a["v"], b["v"])
        mates_a = [x for x in film_rows[a["film"]] if x["actor"] != actor]
        mates_b = [x for x in film_rows[b["film"]] if x["actor"] != actor]
        pairs = [T.cos(x["v"], y["v"]) for x in mates_a for y in mates_b if x["actor"] != y["actor"]]
        if not pairs:
            continue
        plac = st.mean(pairs)
        g_real_minus_placebo[actor].append(real - plac)
        real_all.append(real)
        plac_all.append(plac)

print(f"actor pairs of distinct Nolan characters with placebo: {len(real_all)} "
      f"from {len(g_real_minus_placebo)} actors")
print(f"mean cosine: actor's own pair {st.mean(real_all):.4f}  |  co-star pairs from the same two "
      f"films {st.mean(plac_all):.4f}")
print(fmt(signflip(g_real_minus_placebo), "own pair minus co-star pairs (same films)"))
