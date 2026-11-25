"""Selection test with the film held fixed: own passage vs a co-star's passage, equal-size types.

selection_fixed_size.py shows the percentile must use equal-size types. A second worry: an
unusual film's passages share few words with ANY type, so ranks get noisy and drift toward 0.5.
That would make Nolan look 'less cast to type' for reasons of vocabulary, not casting.

Fix: for each scored role, compute the cast actor's percentile twice with the same k-role type
and the same comparison actors: (i) for the actor's own passage and (ii) for each other
character's passage in the same film (different actor, different surname, different text; the
film_confound.py rule). own - placebo = how much better the actor fits THEIR part than another
part of the same film. Film vocabulary affects both equally.

Run from 'Final project/investigations':  python3 selection_placebo.py
"""
import statistics as st, sys
from collections import defaultdict
from common import T, load_rows, vectorise, by_actor, priors_for, signflip, fmt, ROOT
sys.path.insert(0, ROOT)
import within_nolan as W


def run(rows, k):
    A = by_actor(rows)
    film_rows = defaultdict(list)
    for r in rows:
        film_rows[(r["film"], r["year"])].append(r)
    cache = {}
    def type_before(actor, year, exclude_film, exclude_director):
        key = (actor, year, exclude_film, exclude_director)
        if key not in cache:
            bp = sorted((x for x in A[actor] if x["year"] and x["year"] < year and x["film"] != exclude_film
                         and x["director"] != exclude_director), key=lambda x: x["year"])
            cache[key] = T.centroid([x["v"] for x in bp[-k:]]) if len(bp) >= k else None
        return cache[key]
    out = []
    for actor, rs in A.items():
        for t in rs:
            if not t["year"] or not t["director"]:
                continue
            own_prior = sorted(priors_for(rs, t, "typecast" if t["is_nolan"] else "director"),
                               key=lambda x: x["year"])
            if len(own_prior) < k:
                continue
            ct = T.centroid([x["v"] for x in own_prior[-k:]])
            pool = [c for b in A if b != actor
                    for c in [type_before(b, t["year"], t["film"], t["director"])] if c is not None]
            if len(pool) < 10:
                continue
            def pct(vec):
                own = T.cos(vec, ct)
                return sum(T.cos(vec, c) < own for c in pool) / len(pool)
            mine = W.char_tokens(t["character"])
            mates = [m for m in film_rows[(t["film"], t["year"])]
                     if m["actor"] != actor and not (W.char_tokens(m["character"]) & mine) and m["text"] != t["text"]]
            if not mates:
                continue
            p_own = pct(t["v"])
            p_pl = st.mean(pct(m["v"]) for m in mates)
            out.append(dict(actor=actor, is_nolan=t["is_nolan"], own=p_own, placebo=p_pl, diff=p_own - p_pl))
    return out



def regulars(rows):
    """Regulars (2+/3+ Nolan films, filtered cast) vs one-timers on own, co-star and own-minus-co-star."""
    import csv, os, random
    titles = {r["film_id"]: r["title"] for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_films.csv")))}
    films = defaultdict(set)
    for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_cast.csv"), encoding="utf-8")):
        if r["uncredited"] == "False" and r["voice"] == "False" and r["archive_footage"] == "False":
            films[r["actor_name"]].add(titles[r["film_id"]])
    print("\n--- regulars vs one-timers (Nolan roles; actor means; label permutation 10k) ---")
    print("    own = fit to own part; placebo = fit to a co-star's part (film fit); diff = own - placebo")
    for k in (3, 5):
        P = [p for p in run(rows, k) if p["is_nolan"]]
        for field in ("own", "placebo", "diff"):
            m = defaultdict(list)
            for p in P:
                m[p["actor"]].append(p[field])
            m = {a: st.mean(v) for a, v in m.items()}
            for th in (2, 3):
                acts = list(m); lab = [len(films[a]) >= th for a in acts]; val = [m[a] for a in acts]
                d = lambda l: (st.mean([v for v, x in zip(val, l) if x]) -
                               st.mean([v for v, x in zip(val, l) if not x]))
                obs = d(lab); rng = random.Random(2805); h = 0
                for _ in range(10000):
                    l = lab[:]; rng.shuffle(l); h += abs(d(l)) >= abs(obs)
                print(f"k={k} {field:<7} {th}+ films: regulars {st.mean([v for v, x in zip(val, lab) if x]):+.3f} "
                      f"(n={sum(lab)})  one-timers {st.mean([v for v, x in zip(val, lab) if not x]):+.3f}  "
                      f"diff {obs:+.3f}  p {(h + 1) / 10001:.3f}")


if __name__ == "__main__":
    rows = vectorise(load_rows())
    for k in (3, 5):
        P = run(rows, k)
        nol = [p for p in P if p["is_nolan"]]
        oth = [p for p in P if not p["is_nolan"]]
        print(f"\n[k = {k}] roles with a same-film co-star: Nolan {len(nol)}, other {len(oth)}")
        for lab, S in (("Nolan", nol), ("other", oth)):
            print(f"   {lab:<6} own {st.mean(p['own'] for p in S):.3f}  co-star passage {st.mean(p['placebo'] for p in S):.3f}")
        for lab, S in (("Nolan: own minus co-star passage", nol), ("Other films: own minus co-star passage", oth)):
            g = defaultdict(list)
            for p in S:
                g[p["actor"]].append(p["diff"])
            print("  ", fmt(signflip(g), lab))
        a = defaultdict(lambda: {"n": [], "o": []})
        for p in P:
            a[p["actor"]]["n" if p["is_nolan"] else "o"].append(p["diff"])
        g = {kk: [st.mean(v["n"]) - st.mean(v["o"])] for kk, v in a.items() if v["n"] and v["o"]}
        print("  ", fmt(signflip(g), "Nolan minus same actor's other films"))
    regulars(rows)
