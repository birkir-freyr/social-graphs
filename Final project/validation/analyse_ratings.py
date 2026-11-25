"""Analyse the hand-labelled validation sample.

Reads validation_ratings.csv (one rating per pair, 1-5) and validation_key.csv (cosine and
pair type, hidden while rating).

Reports:
  1. does cosine track human similarity? Spearman between cosine and the rating, on the 18
     within-actor pairs (the comparison the paper makes) and on all 23 non-case pairs;
  2. the film check: same-film pairs have high cosine; are they also rated similar?
     Mean rating per pair type (same-film pairs vs within-actor pairs by cosine tercile).

Run from 'Final project':  python3 validation/analyse_ratings.py
Writes validation/validation_results.json.
"""
import csv, json, os, random, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5
    return num / den if den else float("nan")


def perm_p(a, b, n=10000, seed=2805):
    """Two-sided permutation p for a Spearman correlation."""
    rng = random.Random(seed)
    obs = spearman(a, b)
    bb = list(b)
    hits = 0
    for _ in range(n):
        rng.shuffle(bb)
        if abs(spearman(a, bb)) >= abs(obs):
            hits += 1
    return obs, (hits + 1) / (n + 1)


def main():
    key = {r["pair_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "validation_key.csv")))}
    rating = {r["pair_id"]: float(r["rating"])
              for r in csv.DictReader(open(os.path.join(HERE, "validation_ratings.csv")))
              if (r["rating"] or "").strip()}
    ids = sorted(key)
    missing = [i for i in ids if i not in rating]
    if missing:
        raise SystemExit(f"no rating for {', '.join(missing)}")
    out = {"n_pairs": len(ids)}

    for label, sel in (("within_actor", lambda k: k["kind"] == "within_actor"),
                       ("all_except_case", lambda k: k["kind"] != "case")):
        sub = [i for i in ids if sel(key[i])]
        r, p = perm_p([float(key[i]["cosine"]) for i in sub], [rating[i] for i in sub])
        out[f"spearman_cosine_vs_rating_{label}"] = round(r, 3)
        out[f"p_{label}"] = round(p, 4)
        out[f"n_{label}"] = len(sub)
        print(f"cosine vs rating ({label}, n={len(sub)}): Spearman {r:+.3f}, permutation p {p:.4f}")

    by_kind = {}
    for i in ids:
        k = key[i]["kind"] + ("_" + key[i]["cos_tier"] if key[i]["kind"] == "within_actor" else "")
        by_kind.setdefault(k, []).append((float(key[i]["cosine"]), rating[i]))
    for k in sorted(by_kind):
        cs, rs = zip(*by_kind[k])
        out[f"group_{k}"] = dict(n=len(cs), mean_cosine=round(st.mean(cs), 4), mean_rating=round(st.mean(rs), 2))
        print(f"   {k:<22} n={len(cs):>2}  mean cosine {st.mean(cs):.4f}  mean rating {st.mean(rs):.2f}")

    json.dump(out, open(os.path.join(HERE, "validation_results.json"), "w"), indent=1)
    print("wrote validation/validation_results.json")


if __name__ == "__main__":
    main()
