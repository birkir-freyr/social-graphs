#!/usr/bin/env python3
"""
Why both sides of the comparison are scored leave-one-out.

The measure asks how far a Nolan role sits from the centroid of an
actor's earlier roles, against how far those earlier roles sit from each
other. The obvious way to compute that is:

    Nolan role   vs  centroid of ALL n prior roles
    each prior   vs  centroid of the OTHER n-1

which is wrong, and not obviously so. A centroid built from n vectors is
denser than one built from n-1, and a denser centroid scores higher
cosine against anything. The Nolan role is therefore measured against a
slightly friendlier target than the controls are, which biases the
contrast toward "casts to type".

This script measures that bias on data constructed to contain no effect
at all: every role, treatment included, is drawn from the same
actor-specific vocabulary, so the true difference is zero. Anything the
test reports is bias.

    python3 check_leaveoneout.py
    python3 check_leaveoneout.py --reps 40 --actors 30

Reproduces the sentence in Methods: "On synthetic data constructed with
no effect, that asymmetry alone produced p = 0.04."
"""

import argparse, math, random, statistics, string

import typecast as T          # the real vectoriser, cosine and centroid

N_PERM = 2000                 # per replication; the headline is the rate


def synthetic(n_actors, n_prior, vocab_size=400, own=40, words=60, rng=None):
    """Actors with private vocabularies and NO treatment effect.

    Each actor draws every role, treatment included, from the same
    personal word pool, so a correct test should find nothing.
    """
    rng = rng or random
    vocab = ["".join(rng.choices(string.ascii_lowercase, k=6))
             for _ in range(vocab_size)]
    rows = []
    for a in range(n_actors):
        pool = rng.sample(vocab, own)
        for j in range(n_prior):
            rows.append({"actor": f"A{a}", "is_nolan": False,
                         "text": " ".join(rng.choices(pool, k=words))})
        rows.append({"actor": f"A{a}", "is_nolan": True,
                     "text": " ".join(rng.choices(pool, k=words))})
    return rows


def score(rows, matched):
    """Per-actor difference (treatment departure minus control departure).

    matched=False reproduces the asymmetric scoring: the treatment role
    is compared against the centroid of ALL priors while each control is
    held out of its own centroid.
    matched=True is what typecast.py does: both sides leave one out.
    """
    vecs = T.tfidf_vectors(rows)
    for r, v in zip(rows, vecs):
        r["v"] = v
    by = {}
    for r in rows:
        by.setdefault(r["actor"], []).append(r)

    diffs = []
    for actor, rs in by.items():
        treat = [r for r in rs if r["is_nolan"]]
        prior = [r for r in rs if not r["is_nolan"]]
        if not treat or len(prior) < 3:
            continue
        t = treat[0]
        ctrl, dep = [], []
        for i, x in enumerate(prior):
            rest = prior[:i] + prior[i + 1:]
            if len(rest) < 2:
                continue
            c = T.centroid([y["v"] for y in rest])
            ctrl.append(1 - T.cos(x["v"], c))
            if matched:
                dep.append(1 - T.cos(t["v"], c))
        if not ctrl:
            continue
        if matched:
            d_treat = statistics.mean(dep)
        else:
            whole = T.centroid([y["v"] for y in prior])   # all n of them
            d_treat = 1 - T.cos(t["v"], whole)
        diffs.append(d_treat - statistics.mean(ctrl))
    return diffs


def sign_flip_p(diffs, rng):
    """Actor-clustered sign-flip null, as in typecast.py."""
    if not diffs:
        return float("nan"), float("nan")
    obs = statistics.mean(diffs)
    hits = 0
    for _ in range(N_PERM):
        m = statistics.mean([d if rng.random() < .5 else -d for d in diffs])
        if abs(m) >= abs(obs):
            hits += 1
    return obs, (hits + 1) / (N_PERM + 1)


def one_setting(n_actors, n_prior, reps, rng):
    un_obs, un_p, ma_obs, ma_p = [], [], [], []
    for _ in range(reps):
        rows = synthetic(n_actors, n_prior, rng=rng)
        o1, p1 = sign_flip_p(score([dict(r) for r in rows], matched=False), rng)
        o2, p2 = sign_flip_p(score([dict(r) for r in rows], matched=True), rng)
        un_obs.append(o1); un_p.append(p1)
        ma_obs.append(o2); ma_p.append(p2)
    rate = lambda ps: sum(1 for p in ps if p < .05) / len(ps)
    return {"un_obs": statistics.mean(un_obs),
            "un_p": statistics.median(un_p), "un_fp": rate(un_p),
            "ma_obs": statistics.mean(ma_obs),
            "ma_p": statistics.median(ma_p), "ma_fp": rate(ma_p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--actors", type=int, default=30)
    ap.add_argument("--prior", type=int, default=0,
                    help="pin one prior-role count; default sweeps 3-6")
    ap.add_argument("--seed", type=int, default=2805)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    priors = [args.prior] if args.prior else [3, 4, 5, 6]

    print(f"{args.reps} replications per setting, {args.actors} actors, "
          f"no true effect in the data.")
    print("A correct test gives a mean difference near zero and rejects at")
    print("5% about 5% of the time. Anything else is bias.\n")
    print(f"{'prior':>6} | {'unmatched':^30} | {'matched (typecast.py)':^30}")
    print(f"{'roles':>6} | {'mean diff':>11}{'med p':>9}{'false+':>9} | "
          f"{'mean diff':>11}{'med p':>9}{'false+':>9}")
    print("-" * 74)

    worst = None
    for n_prior in priors:
        r = one_setting(args.actors, n_prior, args.reps, rng)
        print(f"{n_prior:>6} | {r['un_obs']:>+11.4f}{r['un_p']:>9.3f}"
              f"{r['un_fp']:>9.0%} | {r['ma_obs']:>+11.4f}{r['ma_p']:>9.3f}"
              f"{r['ma_fp']:>9.0%}")
        if worst is None or r["un_fp"] > worst[1]["un_fp"]:
            worst = (n_prior, r)

    n, r = worst
    print("\n" + "=" * 74)
    print("The unmatched scoring compares the treatment role against a")
    print("centroid of n prior roles while each control is held out of its")
    print("own centroid of n-1. The denser centroid flatters the treatment")
    print("role, so the contrast leans toward 'casts to type' -- the")
    print("negative mean difference above, on data with no effect at all.")
    print(f"\nWorst at {n} prior roles: median p = {r['un_p']:.3f}, "
          f"rejecting at 5% in {r['un_fp']:.0%} of runs")
    print(f"versus {r['ma_fp']:.0%} when both sides are scored leave-one-out.")
    print("\nThe bias shrinks as the centroid grows, because n and n-1 differ")
    print("less. It is therefore worst at the minimum prior count the")
    print(f"analysis admits, which typecast.py sets to {getattr(T, 'MIN_PRIOR', 3)}.")
    print("=" * 74)


if __name__ == "__main__":
    main()
