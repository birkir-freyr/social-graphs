"""The paper's two main tests with a sentence encoder (all-MiniLM-L6-v2, course Week 7) instead
of TF-IDF. Same passages, same masking, same leave-one-out scoring, same co-star placebo; only the
vectors change. Also prints similarity levels (same film, same actor, random pairs).
Run from investigations/ in an environment with torch and transformers:
    python minilm_main.py [passages.csv]"""
import sys, os, random, statistics as st, importlib.util
sys.path.insert(0, os.getcwd())
from collections import defaultdict
import common, film_confound as F, typecast as T
sys.path.insert(0, os.path.join(common.ROOT, "fandom"))
spec = importlib.util.spec_from_file_location("sp", os.path.join(common.ROOT, "fandom", "semantic_pilot.py"))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)

path = sys.argv[1] if len(sys.argv) > 1 else None
rows = common.load_rows(path=path) if path else common.load_rows()
dense, _ = sp.encode([r["text"] for r in rows], None)
for r in rows:
    r["v"] = dict(enumerate(dense[r["text"]].tolist()))

def levels(rows, seed=1):
    rng = random.Random(seed); byf = defaultdict(list); [byf[r["film"]].append(r) for r in rows]
    same = [T.cos(a["v"], b["v"]) for g in byf.values() for i, a in enumerate(g) for b in g[i+1:]
            if a["actor"] != b["actor"] and a["text"] != b["text"]]
    act, rnd = [], []
    for _ in range(20000):
        a, b = rng.sample(rows, 2)
        if a["film"] != b["film"]:
            (act if a["actor"] == b["actor"] else rnd).append(T.cos(a["v"], b["v"]))
    return st.mean(same), st.mean(act), st.mean(rnd)

s, a, r = levels(rows)
print(f"levels: same film {s:.3f}  same actor {a:.3f}  random {r:.3f}")
sc = F.scored_roles(rows)
nol = defaultdict(list); oth = defaultdict(list)
for x in sc:
    (nol if x["is_nolan"] else oth)[x["actor"]].append(x["diff"])
print(common.fmt(common.signflip(nol), "excess departure, Nolan"))
pl = F.placebo(rows, sc)
for flag, lab in ((True, "Nolan"), (False, "other directors")):
    g = defaultdict(list)
    for p in pl:
        if p["is_nolan"] == flag:
            g[p["actor"]].append(p["diff"] - p["placebo"])
    print(common.fmt(common.signflip(g), f"own minus co-star, {lab}"))
d = [x["diff"] for x in sc if x["is_nolan"]]
print(f"Nolan roles with positive departure: {sum(v > 0 for v in d)} of {len(d)}")
