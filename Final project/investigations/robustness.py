"""Robustness of the headline numbers to (a) the minimum number of earlier roles and
(b) counting reprised characters once.

check_leaveoneout.py showed the matched scoring still rejects a true null ~12% of the time
when actors have only 3 earlier roles, so the main estimate is recomputed with stricter
minimums. Run from 'Final project/investigations':  python3 robustness.py
"""
import sys, os
from collections import defaultdict
import common
from common import load_rows, vectorise, signflip, fmt
from film_confound import scored_roles, within_nolan, nolan_vs_others, placebo
sys.path.insert(0, common.ROOT)
import within_nolan as W

rows = vectorise(load_rows())
for m in (3, 5, 8, 12):
    common.MIN_PRIOR = m
    import film_confound
    film_confound.MIN_PRIOR = m
    sc = scored_roles(rows)
    pl = placebo(rows, sc)
    g = defaultdict(list)
    for p in pl:
        if p["is_nolan"]:
            g[p["actor"]].append(p["diff"] - p["placebo"])
    print(f"\nmin earlier roles = {m}")
    print("  ", fmt(within_nolan(sc), "Nolan role vs own earlier roles"))
    print("  ", fmt(nolan_vs_others(sc), "Nolan minus same actor's other later roles"))
    print("  ", fmt(signflip(g), "Nolan real role minus same-film placebo"))

common.MIN_PRIOR = 3
film_confound.MIN_PRIOR = 3
sc = [s for s in scored_roles(rows) if s["is_nolan"]]
sc.sort(key=lambda s: s["year"])
seen, keep = defaultdict(list), []
for s in sc:
    tk = W.char_tokens(s["character"])
    if any(tk & x for x in seen[s["actor"]]):
        continue
    seen[s["actor"]].append(tk)
    keep.append(s)
g = defaultdict(list)
for s in keep:
    g[s["actor"]].append(s["diff"])
print("\n", fmt(signflip(g), "Nolan role vs own earlier roles, reprised characters once"))
