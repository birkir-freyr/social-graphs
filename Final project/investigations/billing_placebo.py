"""Same-film placebo (TF-IDF) with both the scored role and its co-stars billed in the top ten.
Run from investigations/:  python3 billing_placebo.py"""
import sys, os, csv, statistics as st
sys.path.insert(0, os.getcwd())
from collections import defaultdict
import common, film_confound as F
rows = common.vectorise(common.load_rows())
bill = {(r["actor"], r["film"], r["character"]): int(r["billing"]) if r["billing"].isdigit() else 99
        for r in csv.DictReader(open(os.path.join(common.ROOT, "passages.csv"), encoding="utf-8"))}
b = lambda r: bill.get((r["actor"], r["film"], r["character"]), 99)
sc = F.scored_roles(rows)
pl = F.placebo([r for r in rows if b(r) <= 10], [s for s in sc if b(s["target"]) <= 10])
for flag, lab in ((True, "Nolan"), (False, "other directors")):
    g = defaultdict(list)
    for p in pl:
        if p["is_nolan"] == flag: g[p["actor"]].append(p["diff"] - p["placebo"])
    print(common.fmt(common.signflip(g), f"own minus co-star, top-10 billing, {lab}"))
