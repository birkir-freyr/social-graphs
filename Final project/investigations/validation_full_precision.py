"""Spearman correlation between our ratings and TF-IDF cosine at full precision.
validation_key.csv stores cosines rounded to 4 decimals, which creates ties (rho 0.00 within actors).
Here cosines are recomputed from the passages. Permutation p-values, 10,000 draws.
Run from investigations/:  python3 validation_full_precision.py"""
import sys, os, csv, random
sys.path.insert(0, os.getcwd())
import common, typecast as T
rows = common.vectorise(common.load_rows())
V = {(r["actor"], r["film"], r["character"]): r["v"] for r in rows}
key = list(csv.DictReader(open("../validation/validation_key.csv", encoding="utf-8")))
rat = {r["pair_id"]: int(r["rating"]) for r in csv.DictReader(open("../validation/validation_ratings.csv"))}

def rank(x):
    s = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and x[s[j + 1]] == x[s[i]]: j += 1
        for k in range(i, j + 1): r[s[k]] = (i + j) / 2
        i = j + 1
    return r

def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return num / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5

def perm(a, b, B=10000):
    o = spearman(a, b); rng = random.Random(2805); b = list(b); c = 0
    for _ in range(B):
        rng.shuffle(b); c += abs(spearman(a, b)) >= abs(o) - 1e-12
    return o, (c + 1) / (B + 1)

pairs = [(p["kind"], T.cos(V[(p["actor_a"], p["film_a"], p["character_a"])], V[(p["actor_b"], p["film_b"], p["character_b"])]),
          float(p["cosine"]), rat[p["pair_id"]]) for p in key]
for lab, keep in (("within actor", {"within_actor"}), ("all non-case", {"within_actor", "same_film"})):
    sel = [p for p in pairs if p[0] in keep]
    full = perm([p[1] for p in sel], [p[3] for p in sel]); rnd = perm([p[2] for p in sel], [p[3] for p in sel])
    print(f"{lab:13} n={len(sel)}  full precision rho {full[0]:+.3f} p {full[1]:.3f}   rounded rho {rnd[0]:+.3f} p {rnd[1]:.3f}")
