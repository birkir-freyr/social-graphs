#!/usr/bin/env python3
"""
Does Nolan cast against type?

For every actor with a Nolan role and enough earlier roles:

    centroid   = the average of that actor's roles BEFORE the Nolan film
    departure  = 1 - cosine(nolan role, centroid)

Then the control, which is the whole point: how far does a NON-Nolan role
of the same actor sit from the same centroid? Computed leave-one-out, so
both sides are treated identically. If Nolan departure is no bigger than
an ordinary role's departure, he casts to type.

This control is within-actor, so it automatically absorbs the fact that
some actors are simply more varied than others.

    python3 typecast.py                 # TF-IDF, no dependencies
    python3 typecast.py --embed         # sentence-transformers if installed

Input: a CSV with (at minimum) these columns, under any of the spellings
in COLUMN_ALIASES below:
    actor, film, year, is_nolan, role_text
"""

import argparse, csv, math, random, statistics, sys
from collections import defaultdict, Counter

random.seed(2805)

COLUMN_ALIASES = {
    "actor":     ["actor", "actor_name", "name", "actor_id"],
    "film":      ["film", "movie", "title", "film_id", "movie_id"],
    "year":      ["year", "release_year", "release_date"],
    "is_nolan":  ["is_nolan", "nolan", "is_nolan_film", "director_nolan"],
    "role_text": ["role_text", "character_text", "description", "text",
                  "passage", "plot_text"],
    "character": ["character", "role", "character_name"],
}

MIN_WORDS = 25      # a role needs this much text to be worth embedding
MIN_PRIOR = 3       # earlier roles needed to define a centroid
N_PERM = 10000


def resolve(header):
    got, low = {}, {h.lower().strip(): h for h in header}
    for want, names in COLUMN_ALIASES.items():
        for n in names:
            if n in low:
                got[want] = low[n]
                break
    missing = [k for k in ("actor", "film", "is_nolan", "role_text")
               if k not in got]
    if missing:
        sys.exit(f"could not find column(s) {missing}.\n"
                 f"header was: {header}\n"
                 f"add the right spelling to COLUMN_ALIASES at the top.")
    return got


def truthy(v):
    return str(v).strip().lower() in {"1", "true", "yes", "y", "nolan", "t"}


def load(path, text_col=""):
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        col = resolve(rd.fieldnames or [])
        if text_col:
            if text_col not in (rd.fieldnames or []):
                sys.exit(f"no column {text_col!r}. have: {rd.fieldnames}")
            col["role_text"] = text_col
        rows = []
        for r in rd:
            txt = (r.get(col["role_text"]) or "").strip()
            if len(txt.split()) < MIN_WORDS:
                continue
            yr = (r.get(col.get("year", ""), "") or "")[:4]
            rows.append({
                "actor": r[col["actor"]].strip(),
                "film": r[col["film"]].strip(),
                "year": int(yr) if yr.isdigit() else None,
                "is_nolan": truthy(r[col["is_nolan"]]),
                "character": (r.get(col.get("character", ""), "") or "").strip(),
                "text": txt,
            })
    return rows


# ------------------------------------------------------------ vectorising
STOP = set("""a an the and or but if of to in on at by for with from as is are
was were be been being this that these those it its they them their he she his
her him we us our you your not no also have has had do does did which who whom
what when where how than then so such other more most some any all each both
few many much very can could would should may might will shall must about into
over under between during after before while because although however film
movie character played role story plot scene later finally eventually""".split())


def tokens(t):
    import re
    return [w for w in re.findall(r"[a-z]+", t.lower())
            if len(w) > 2 and w not in STOP]


def tfidf_vectors(rows):
    toks = [tokens(r["text"]) for r in rows]
    df = Counter(w for t in toks for w in set(t))
    N = len(rows)
    idf = {w: math.log(N / c) for w, c in df.items() if c >= 2}
    vecs = []
    for t in toks:
        tf = Counter(t)
        n = sum(tf.values()) or 1
        v = {w: (c / n) * idf[w] for w, c in tf.items() if w in idf}
        nm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / nm for w, x in v.items()})
    return vecs


def dense_vectors(rows):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("all-MiniLM-L6-v2")
    embs = m.encode([r["text"] for r in rows], show_progress_bar=True,
                    normalize_embeddings=True)
    return [dict(enumerate(e.tolist())) for e in embs]


def cos(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b[k] for k, v in a.items() if k in b)


def centroid(vecs):
    acc = defaultdict(float)
    for v in vecs:
        for k, x in v.items():
            acc[k] += x
    n = math.sqrt(sum(x * x for x in acc.values())) or 1.0
    return {k: x / n for k, x in acc.items()}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default="roles.csv")
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--text", default="",
                    help="which text column: role_text, role_text_masked, "
                         "role_text_blind. Run all three — if the answer "
                         "only holds for one, it is an artefact of names.")
    ap.add_argument("--min-results", type=int, default=8)
    ap.add_argument("--json", default="", help="also write results as JSON")
    ap.add_argument("--truncate", type=int, default=0,
                    help="cut every passage to its first N words before "
                         "vectorising. Length and apparent 'departure' are "
                         "correlated (short text looks unlike everything), "
                         "so a result that survives truncation is about the "
                         "role and not about how much Wikipedia wrote.")
    args = ap.parse_args()

    rows = load(args.roles, args.text)
    print(f"text column: {args.text or 'role_text (default)'}")
    if args.truncate:
        rows = [r for r in rows if len(r["text"].split()) >= args.truncate]
        for r in rows:
            r["text"] = " ".join(r["text"].split()[:args.truncate])
        print(f"truncated to {args.truncate} words each "
              f"({len(rows)} roles long enough)")
    print(f"{len(rows)} roles with {MIN_WORDS}+ words of text")
    print(f"  Nolan roles   {sum(1 for r in rows if r['is_nolan'])}")

    vecs = dense_vectors(rows) if args.embed else tfidf_vectors(rows)
    for r, v in zip(rows, vecs):
        r["v"] = v

    by_actor = defaultdict(list)
    for r in rows:
        by_actor[r["actor"]].append(r)

    results = []
    for actor, rs in by_actor.items():
        nolan = [r for r in rs if r["is_nolan"]]
        other = [r for r in rs if not r["is_nolan"]]
        if not nolan or len(other) < MIN_PRIOR:
            continue
        for nr in nolan:
            # earlier roles only — a later role can't define an earlier type
            prior = [r for r in other
                     if r["year"] and nr["year"] and r["year"] < nr["year"]]
            if len(prior) < MIN_PRIOR:
                continue
            # Both sides must see a centroid built from the SAME number of
            # roles. A centroid of n roles is denser than one of n-1 and
            # therefore scores higher similarity against anything, so
            # comparing the Nolan role against all n priors while each
            # control role sees only n-1 biases the whole measure toward
            # "casts to type". On synthetic data with no effect at all
            # that bias alone produced p = 0.04. So the Nolan role is
            # also scored leave-one-out, and averaged.
            nol = []
            ctrl = []
            for i, r in enumerate(prior):
                rest = prior[:i] + prior[i + 1:]
                if len(rest) < 2:
                    continue
                c = centroid([x["v"] for x in rest])
                nol.append(1 - cos(nr["v"], c))
                ctrl.append(1 - cos(r["v"], c))
            if not ctrl:
                continue
            dep_nolan = statistics.mean(nol)
            results.append({
                "actor": actor, "film": nr["film"],
                "character": nr["character"], "year": nr["year"],
                "n_prior": len(prior),
                "nolan": dep_nolan, "control": statistics.mean(ctrl),
                "diff": dep_nolan - statistics.mean(ctrl),
            })

    if len(results) < args.min_results:
        sys.exit(f"\nonly {len(results)} testable actor-roles. Loosen MIN_PRIOR "
                 f"or MIN_WORDS, or collect more films per actor.")

    diffs = [r["diff"] for r in results]
    obs = statistics.mean(diffs)

    # Sign-flip permutation. The unit of randomisation is the ACTOR, not
    # the role: one actor can contribute several Nolan roles, and those
    # share a centroid and a filmography, so they are not independent
    # observations. Flipping each role on its own would treat six Michael
    # Caine roles as six actors and shrink p by a factor it has not
    # earned. With k actors the smallest reachable p is about 1/2^k, so a
    # handful of actors cannot produce significance however large the
    # effect looks.
    groups = defaultdict(list)
    for r in results:
        groups[r["actor"]].append(r["diff"])
    gkeys = list(groups)
    n_roles = len(diffs)

    null = []
    for _ in range(N_PERM):
        tot = 0.0
        for g in gkeys:
            s = 1 if random.random() < .5 else -1
            tot += s * sum(groups[g])
        null.append(tot / n_roles)
    mu, sd = statistics.mean(null), statistics.pstdev(null)
    z = (obs - mu) / sd if sd else float("nan")
    p = (sum(1 for v in null if abs(v) >= abs(obs)) + 1) / (N_PERM + 1)
    above = sum(1 for d in diffs if d > 0)
    p_floor = 2.0 ** -len(gkeys)

    if args.json:
        import json
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({
                "text_col": args.text or "role_text",
                "truncate": args.truncate,
                "n_roles": len(results), "n_actors": len(gkeys),
                "mean_nolan": statistics.mean([r["nolan"] for r in results]),
                "mean_control": statistics.mean([r["control"] for r in results]),
                "obs": obs, "z": z, "p": p, "p_floor": p_floor,
                "above": above,
                "null_sd": sd,
                "results": results,
            }, f)

    print("\n" + "=" * 64)
    print(f"testable actor-roles        {len(results)}")
    print(f"mean departure, Nolan role  {statistics.mean([r['nolan'] for r in results]):.4f}")
    print(f"mean departure, control     {statistics.mean([r['control'] for r in results]):.4f}")
    print(f"mean difference             {obs:+.4f}")
    print(f"actors where Nolan is further  {above}/{len(results)}")
    print(f"distinct actors             {len(gkeys)}")
    print(f"sign-flip null (by actor)   z = {z:+.2f}   p = {p:.4f}")
    print("=" * 64)
    if p_floor > .05:
        print(f"\nTOO FEW ACTORS TO TEST. With {len(gkeys)} actors the smallest")
        print(f"p this design can reach is {p_floor:.3f}. Whatever p prints")
        print("above, it is a property of the test, not evidence. Collect")
        print("more actors before reporting any of this.")
        print(f"\n(direction so far: mean difference {obs:+.4f}, "
              f"{above}/{len(results)} roles further from type)")
    elif p < .05 and obs > 0:
        print("\nAGAINST TYPE. Nolan roles sit further from an actor's prior")
        print("work than that actor's own other roles do.")
    elif p < .05:
        print("\nTO TYPE. Nolan roles are CLOSER to prior work than usual —")
        print("he casts people as what they already are.")
    else:
        print("\nNO DIFFERENCE. Nolan roles are no further from an actor's")
        print("prior work than any other role. 'Casting against type' is not")
        print("visible in this measure.")

    results.sort(key=lambda r: -r["diff"])
    print("\nfurthest from type:")
    for r in results[:6]:
        print(f"  {r['actor'][:20]:<22}{r['character'][:18]:<20}"
              f"{r['film'][:18]:<20}{r['diff']:+.3f}  (n={r['n_prior']})")
    print("\nclosest to type:")
    for r in results[-6:]:
        print(f"  {r['actor'][:20]:<22}{r['character'][:18]:<20}"
              f"{r['film'][:18]:<20}{r['diff']:+.3f}  (n={r['n_prior']})")

    with open("typecast_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["actor", "film", "character", "year",
                                          "n_prior", "nolan", "control", "diff"])
        w.writeheader(); w.writerows(results)
    print("\nwrote typecast_results.csv")
    print("\nSANITY CHECK before you believe any of it: Heath Ledger as the")
    print("Joker should be near the top. If he is not, read his role_text —")
    print("the extraction is probably wrong, not the finding.")


if __name__ == "__main__":
    main()
