#!/usr/bin/env python3
"""
Is Nolan unusual AMONG DIRECTORS?

typecast.py answers a narrower question: does a Nolan role sit further from
an actor's prior work than that actor's own other roles do. That is a
within-actor comparison, and it cannot tell you whether Nolan is unusual or
whether every director looks like this — a first film with a new director is
probably a departure whoever the director is.

So: attach a director to every role, compute the SAME departure score for
every (actor, film) pair in the dataset, group by director, and ask where
Nolan falls among directors with comparable numbers of roles.

Directors are parsed from the Wikipedia articles already in cache_wiki/,
so this costs no network requests.

    python3 director_test.py --roles passages.csv

Writes director_results.csv and director_test.json.
"""

import argparse, csv, hashlib, json, math, os, random, re, statistics, sys
from collections import defaultdict, Counter
from urllib.parse import quote

import typecast as T          # reuse the exact vectoriser and distance

random.seed(2805)

WIKI = "https://en.wikipedia.org/w/api.php"
CACHE = "cache_wiki"
N_PERM = 10000

DIRECTED = re.compile(
    r"(?:directed and (?:written|produced) by|written and directed by|"
    r"directed by)\s+([A-Z][\w.'’-]+(?:\s+[A-Z][\w.'’-]+){0,3})")


def cached_extract(page):
    u = (f"{WIKI}?action=query&prop=extracts&explaintext=1&format=json"
         f"&redirects=1&titles={quote(page)}")
    p = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest()[:20] + ".json")
    if not os.path.exists(p):
        return ""
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return ""
    pages = (d.get("query", {}) or {}).get("pages", {}) or {}
    return next(iter(pages.values()), {}).get("extract", "") or ""


def director_of(page):
    """Parse the director from the article's lead. Returns '' if unsure."""
    t = cached_extract(page)
    if not t:
        return ""
    m = DIRECTED.search(t[:1500])
    if not m:
        return ""
    name = m.group(1).strip()
    # a trailing sentence-start word gets swept up now and then
    name = re.sub(r"\s+(The|It|This|He|She|They|In|A|An)$", "", name)
    return normalise(name)


def normalise(name):
    """'Christopher Nolan.' and 'Christopher Nolan' are one director.

    Without this the same person splits into several entries, each with
    too few roles to be estimated, and the one we care about loses part
    of his own sample.
    """
    name = (name or "").strip().replace("’", "'")
    name = re.sub(r"\s+", " ", name)

    # The name pattern allows a dot inside a token so that initials
    # ("J.J. Abrams") survive, which also lets it run past the end of a
    # sentence: "directed by Rahul Rawail. Written by..." captured
    # "Rahul Rawail. Written". Cut at the first token that looks like a
    # word ending a sentence rather than an initial.
    out = []
    for tok in name.split():
        if re.fullmatch(r"[A-Z][a-z]{2,}\.", tok):
            out.append(tok[:-1])
            break
        out.append(tok)
    name = " ".join(out)

    name = re.sub(r"[.,;:]+$", "", name)
    return name if len(name.split()) >= 2 else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default="passages.csv")
    ap.add_argument("--text", default="role_text_blind")
    ap.add_argument("--min-prior", type=int, default=3)
    ap.add_argument("--min-roles", type=int, default=5,
                    help="a director needs this many scored roles to enter "
                         "the comparison distribution")
    args = ap.parse_args()

    rows = T.load(args.roles, args.text)
    raw = {(r["actor"], r["film"]): r for r in
           csv.DictReader(open(args.roles, encoding="utf-8"))}
    print(f"{len(rows)} roles with text")

    # --- attach directors -------------------------------------------------
    pages, miss = {}, 0
    for r in rows:
        src = raw.get((r["actor"], r["film"]), {})
        pg = src.get("wiki_page", "")
        if r["is_nolan"]:
            r["director"] = "Christopher Nolan"
            continue
        if pg not in pages:
            pages[pg] = director_of(pg) if pg else ""
        r["director"] = normalise(pages[pg])
        if not r["director"]:
            miss += 1
    print(f"  director parsed for {len(rows)-miss}/{len(rows)} roles "
          f"({(len(rows)-miss)/len(rows):.0%})")

    # --- score EVERY role the same way typecast.py scores a Nolan role ----
    vecs = T.tfidf_vectors(rows)
    for r, v in zip(rows, vecs):
        r["v"] = v
    by_actor = defaultdict(list)
    for r in rows:
        by_actor[r["actor"]].append(r)

    scored = []
    for actor, rs in by_actor.items():
        for target in rs:
            if not target["year"] or not target["director"]:
                continue
            prior = [x for x in rs
                     if x is not target and x["year"]
                     and x["year"] < target["year"]
                     and x["director"] != target["director"]]
            if len(prior) < args.min_prior:
                continue
            dep, ctrl = [], []
            for i, x in enumerate(prior):
                rest = prior[:i] + prior[i + 1:]
                if len(rest) < 2:
                    continue
                c = T.centroid([y["v"] for y in rest])
                dep.append(1 - T.cos(target["v"], c))
                ctrl.append(1 - T.cos(x["v"], c))
            if not ctrl:
                continue
            scored.append({
                "actor": actor, "director": target["director"],
                "film": target["film"], "year": target["year"],
                "character": target["character"],
                "is_nolan": int(bool(target["is_nolan"])),
                "n_prior": len(prior),
                "diff": statistics.mean(dep) - statistics.mean(ctrl),
            })

    if not scored:
        sys.exit("nothing scored — loosen --min-prior")

    by_dir = defaultdict(list)
    for s in scored:
        by_dir[s["director"]].append(s["diff"])

    nolan = by_dir.get("Christopher Nolan", [])
    if not nolan:
        sys.exit("no Nolan roles scored")
    nolan_mean = statistics.mean(nolan)
    k = len(nolan)

    # comparison distribution: directors with enough roles to be estimated
    pool = {d: v for d, v in by_dir.items()
            if d != "Christopher Nolan" and len(v) >= args.min_roles}
    means = sorted(((statistics.mean(v), d, len(v)) for d, v in pool.items()),
                   reverse=True)
    rank = sum(1 for m, _, _ in means if m >= nolan_mean) + 1

    # Permutation: how often does a random set of k roles reach Nolan's
    # mean? This asks whether his value is unusual GIVEN how many roles he
    # has -- a director with three roles can look extreme by luck alone.
    #
    # The draw is from NON-Nolan roles only. Sampling from all scored roles
    # would put his own 143 into the null and pull it toward the value
    # being tested, which makes the test too easy by exactly the amount
    # his roles are unusual.
    others = [s["diff"] for s in scored if not s["is_nolan"]
              and s["director"] != "Christopher Nolan"]
    pooled_mu_all = statistics.mean(others) if others else 0.0
    pooled_sd_all = statistics.pstdev(others) if len(others) > 1 else 0.0
    hits = 0
    for _ in range(N_PERM):
        samp = random.sample(others, min(k, len(others)))
        if statistics.mean(samp) >= nolan_mean:
            hits += 1
    p_perm = (hits + 1) / (N_PERM + 1)

    # Sample-size-adjusted standing among directors.
    #
    # The permutation below draws k roles from the non-Nolan pool, but
    # that pool comes from only a few more actors than Nolan's own, so
    # the draw exhausts most of the population and the null has almost
    # no spread. It also treats roles as exchangeable when every one of
    # them belongs to an actor Nolan cast. This z compares directors to
    # each other instead, which is the claim actually being made, and is
    # what the funnel plot draws: each director's mean expressed in
    # standard errors at their own number of roles.
    zs = {}
    for d, v in by_dir.items():
        if len(v) >= args.min_roles and pooled_sd_all:
            zs[d] = ((statistics.mean(v) - pooled_mu_all)
                     / (pooled_sd_all / math.sqrt(len(v))))
    nolan_z = zs.get("Christopher Nolan")
    beat = [d for d, x in zs.items()
            if nolan_z is not None and x >= nolan_z and d != "Christopher Nolan"]

    print("\n" + "=" * 66)
    print(f"roles scored                  {len(scored)}")
    print(f"directors with >= {args.min_roles} roles       {len(pool)}")
    print(f"Nolan roles scored            {k}")
    print(f"Nolan mean departure          {nolan_mean:+.4f}")
    if nolan_z is not None:
        print(f"Nolan z at his own sample size {nolan_z:+.2f}")
        print(f"directors reaching that z      {len(beat)} of {len(zs)-1}")
    if means:
        allm = [m for m, _, _ in means]
        print(f"other directors, mean         {statistics.mean(allm):+.4f}")
        print(f"other directors, median       {statistics.median(allm):+.4f}")
        print(f"Nolan's rank                  {rank} of {len(means)+1}")
    print(f"permutation (k={k} random roles) p = {p_perm:.4f}")
    print("=" * 66)

    if p_perm < .05:
        print("\nNOLAN IS UNUSUAL. His roles depart from an actor's prior type")
        print("more than a random set of the same size drawn from all")
        print("director-actor pairings in the data.")
    else:
        print("\nNOLAN IS NOT UNUSUAL AMONG DIRECTORS. His roles depart about")
        print("as much as any director's do. The within-actor effect is real")
        print("but it is not specific to him — working with a new director")
        print("is itself a departure. Report the narrower claim.")

    print("\ndirectors furthest from type (>= "
          f"{args.min_roles} roles):")
    for m, d, n in means[:8]:
        mark = "  <-- Nolan" if d == "Christopher Nolan" else ""
        print(f"  {d[:28]:<30}{m:+.4f}  (n={n}){mark}")
    print(f"  {'Christopher Nolan':<30}{nolan_mean:+.4f}  (n={k})   [rank {rank}]")
    print("\nclosest to type:")
    for m, d, n in means[-5:]:
        print(f"  {d[:28]:<30}{m:+.4f}  (n={n})")

    # ---- funnel plot: mean against sample size ---------------------------
    # Nolan ranks mid-table among raw means, but every director above him
    # has three or four roles. A funnel shows why: small samples scatter
    # widely by construction, and the question is whether a director sits
    # outside the spread EXPECTED at his own sample size.
    try:
        import figstyle as S
        import matplotlib.pyplot as plt
        S.apply()

        pooled_sd, pooled_mu = pooled_sd_all, pooled_mu_all
        pts = [(len(v), statistics.mean(v), d) for d, v in by_dir.items()
               if d != "Christopher Nolan" and len(v) >= 3]

        fig, ax = plt.subplots(figsize=(S.COL1, S.HEIGHT))
        if pooled_sd:
            ns = list(range(3, max(k, 10) + 60))
            hi = [pooled_mu + 1.96 * pooled_sd / math.sqrt(n) for n in ns]
            lo = [pooled_mu - 1.96 * pooled_sd / math.sqrt(n) for n in ns]
            ax.fill_between(ns, lo, hi, color=S.GREY, lw=0, zorder=1)
        ax.axhline(pooled_mu, color=S.LINE, lw=0.8, ls=(0, (5, 4)), zorder=2)
        ax.scatter([n for n, _, _ in pts], [m for _, m, _ in pts],
                   s=20, color=S.OTHER, lw=0.7, edgecolor=S.SURFACE, zorder=3,
                   label=f"Other directors ({len(pts)})")
        ax.scatter([k], [nolan_mean], s=46, color=S.NOLAN, lw=0.8,
                   edgecolor=S.SURFACE, zorder=5, marker="s", label="Nolan")
        ax.set_xscale("log")
        S.frame(ax, "Nolan among directors",
                xlabel="Roles scored for that director",
                ylabel="Mean departure from type",
                grid="y", legend_cols=2)
        os.makedirs("figures", exist_ok=True)
        fig.savefig("figures/fig4_directors.png")
        plt.close(fig)
        print("wrote figures/fig4_directors.png")
    except ImportError:
        print("(matplotlib missing — skipped the funnel plot)")

    with open("director_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["actor", "director", "film", "year",
                                          "character", "is_nolan", "n_prior",
                                          "diff"])
        w.writeheader(); w.writerows(scored)
    with open("director_test.json", "w", encoding="utf-8") as f:
        json.dump({"n_scored": len(scored), "n_directors": len(pool),
                   "k_nolan": k, "nolan_mean": nolan_mean,
                   "rank": rank, "n_ranked": len(means) + 1,
                   "p_perm": p_perm, "nolan_z": nolan_z,
                   "directors_reaching_z": len(beat),
                   "n_z": len(zs) - 1,
                   "other_mean": statistics.mean([m for m, _, _ in means])
                   if means else None,
                   "top": [{"director": d, "mean": m, "n": n}
                           for m, d, n in means[:15]]}, f, indent=1)
    print("\nwrote director_results.csv, director_test.json")


if __name__ == "__main__":
    main()
