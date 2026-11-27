"""Does the earlier-roles rule matter? Reruns the main effect and the same-film placebo with
(base) earlier roles, minimum 3; (anyyear) earlier and later non-Nolan roles; (min2) minimum 2 earlier roles.
Run from investigations/:  python3 prior_rules.py base|anyyear|min2 [passages.csv]"""
import sys, os, statistics as st
sys.path.insert(0, os.getcwd())
from collections import defaultdict
import common, film_confound as F
import typecast as T
def anyyear(actor_rows, target, mode="director"):
    return [x for x in actor_rows if x is not target and x["director"] != target["director"]]
def score2(tv, prior):
    dep, ctrl = [], []
    for i, x in enumerate(prior):
        rest = prior[:i] + prior[i+1:]
        c = T.centroid([y["v"] for y in rest]); dep.append(1-T.cos(tv, c)); ctrl.append(1-T.cos(x["v"], c))
    return (st.mean(dep), st.mean(ctrl)) if ctrl else None
def run(label, path=None):
    rows = common.vectorise(common.load_rows(path=path) if path else common.load_rows())
    sc = F.scored_roles(rows)
    nol = defaultdict(list); [nol[s["actor"]].append(s["diff"]) for s in sc if s["is_nolan"]]
    pl = [p for p in F.placebo(rows, sc) if p["is_nolan"]]
    g = defaultdict(list); [g[p["actor"]].append(p["diff"]-p["placebo"]) for p in pl]
    print(common.fmt(common.signflip(nol), label+" | excess departure"))
    print(common.fmt(common.signflip(g), label+" | own minus co-star"))
which = sys.argv[1]; path = sys.argv[2] if len(sys.argv) > 2 else None
if which == "anyyear": F.priors_for = anyyear
if which == "min2": F.MIN_PRIOR = 2; F.score = score2
run(which + (" fandom" if path else ""), path)
