"""New Fig. 3: is the Nolan departure about the role or about the film?

(a) Mean excess departure, with actor-clustered bootstrap 95% intervals, for
    - the actor's own Nolan role,
    - a co-star's passage from the same Nolan film scored against the same actor's type
      (same-film placebo),
    - the actor's own later roles for other directors,
    - a co-star's passage from those other films (placebo for other directors).
(b) Selection test with the film held fixed: where the cast actor's type ranks among all other
    actors' types (0.5 = a random actor), for the actor's own passage and for a co-star's passage
    from the same film. Every type is the centroid of the actor's 3 most recent eligible earlier
    roles, because a centroid of more roles is closer to every passage (selection_fixed_size.py).

Writes figures/fig3_role_or_film.png/.pdf and investigations/fig_role_or_film.json.
Run from 'Final project':  python investigations/fig_role_or_film.py
"""
import json, os, random, statistics as st, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common
from common import load_rows, vectorise
from film_confound import scored_roles, placebo
import selection_placebo as SPL
sys.path.insert(0, common.ROOT)
import figstyle as S
import matplotlib.pyplot as plt

S.apply()
rows = vectorise(load_rows())
sc = scored_roles(rows)
pl = placebo(rows, sc)
P = SPL.run(rows, 3)


def cluster_boot(values_by_actor, B=5000, seed=2805):
    rng = random.Random(seed)
    keys = [k for k, v in values_by_actor.items() if v]
    flat = lambda ks: [x for k in ks for x in values_by_actor[k]]
    est = st.mean(flat(keys))
    boots = sorted(st.mean(flat([rng.choice(keys) for _ in keys])) for _ in range(B))
    return est, boots[int(0.025 * B)], boots[int(0.975 * B) - 1], len(flat(keys)), len(keys)


def grouped(items, key):
    g = defaultdict(list)
    for it in items:
        g[it["actor"]].append(key(it))
    return g


bars = [
    ("Nolan role", grouped([s for s in sc if s["is_nolan"]], lambda s: s["diff"]), S.NOLAN),
    ("Co-star in the\nsame Nolan film", grouped([p for p in pl if p["is_nolan"]], lambda p: p["placebo"]), "#e3a67a"),
    # same roles as the placebo next to it: other directors' roles that have a co-star passage
    ("Same actor,\nother director", grouped([p for p in pl if not p["is_nolan"]], lambda p: p["diff"]), S.OTHER),
    ("Co-star in the\nsame other film", grouped([p for p in pl if not p["is_nolan"]], lambda p: p["placebo"]), "#8fbfd6"),
]
res_a = [(lab, *cluster_boot(g), col) for lab, g, col in bars]
sel = [
    ("Nolan\nrole", grouped([p for p in P if p["is_nolan"]], lambda p: p["own"]), S.NOLAN),
    ("Co-star,\nNolan film", grouped([p for p in P if p["is_nolan"]], lambda p: p["placebo"]), "#e3a67a"),
    ("Other\ndirector", grouped([p for p in P if not p["is_nolan"]], lambda p: p["own"]), S.OTHER),
    ("Co-star,\nother film", grouped([p for p in P if not p["is_nolan"]], lambda p: p["placebo"]), "#8fbfd6"),
]
res_b = [(lab, *cluster_boot(g), col) for lab, g, col in sel]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(S.COL2, 2.55),
                               gridspec_kw={"width_ratios": [1.6, 1.25]}, layout="constrained")
for i, (lab, est, lo, hi, n, k, col) in enumerate(res_a):
    ax1.bar(i, est, color=col, width=0.66, zorder=2)
    ax1.errorbar(i, est, yerr=[[est - lo], [hi - est]], color=S.INK, lw=0.9, capsize=2.5, zorder=3)
ax1.axhline(0, color=S.LINE, lw=0.8, zorder=1)
ax1.set_xticks(range(len(res_a)))
ax1.set_xticklabels([r[0] for r in res_a], fontsize=6.6)
ax1.set_ylabel("Mean excess departure\nfrom the actor's type")
ax1.spines[["top", "right"]].set_visible(False)
ax1.grid(axis="y", color=S.GREY, lw=0.5, zorder=0)
ax1.text(-0.18, 1.02, "a", transform=ax1.transAxes, fontsize=9, fontweight="bold", va="bottom")

for i, (lab, est, lo, hi, n, k, col) in enumerate(res_b):      # points, not bars: axis is not from 0
    ax2.errorbar(i, est, yerr=[[est - lo], [hi - est]], color=col, lw=1.4, capsize=3, zorder=3,
                 marker="o", ms=6, mec=S.SURFACE, mew=0.8)
ax2.axhline(0.5, color=S.INK2, lw=0.9, ls=(0, (4, 3)), zorder=1)
ax2.text(1.5, 0.485, "random actor", fontsize=6.2, color=S.INK2, va="top", ha="center")
ax2.set_ylim(0.4, 0.7)
ax2.set_xlim(-0.6, 3.6)
ax2.set_xticks(range(len(res_b)))
ax2.set_xticklabels([r[0] for r in res_b], fontsize=6.6)
ax2.set_ylabel("Rank of the cast actor's type\n(share of other actors further away)")
ax2.spines[["top", "right"]].set_visible(False)
ax2.grid(axis="y", color=S.GREY, lw=0.5, zorder=0)
ax2.text(-0.30, 1.02, "b", transform=ax2.transAxes, fontsize=9, fontweight="bold", va="bottom")

out = os.path.join(common.ROOT, "figures", "fig3_role_or_film")
fig.savefig(out + ".png", dpi=300)
fig.savefig(out + ".pdf")
nums = {"a": [dict(label=r[0].replace("\n", " "), mean=round(r[1], 4), lo=round(r[2], 4),
                   hi=round(r[3], 4), n=r[4], actors=r[5]) for r in res_a],
        "b": [dict(label=r[0].replace("\n", " "), mean=round(r[1], 3), lo=round(r[2], 3), hi=round(r[3], 3),
                   n=r[4], actors=r[5]) for r in res_b]}
json.dump(nums, open(os.path.join(HERE, "fig_role_or_film.json"), "w"), indent=1)
print(json.dumps(nums, indent=1))
