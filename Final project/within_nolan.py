#!/usr/bin/env python3
"""
The paper's second question: when Nolan reuses an actor, are those roles
more alike than that actor's other roles are to each other?

This is NOT the same measure as typecast.py. There we asked how far a
Nolan role sits from an actor's earlier type. Here we ask how alike an
actor's several Nolan roles are TO EACH OTHER, against the obvious
control: how alike that same actor's non-Nolan roles are to each other.

Reprised characters are counted once, as the paper states. Alfred in
three Batman films is one character; leaving all three in would measure
sequels, not casting.

    python3 within_nolan.py --roles passages.csv

Writes within_nolan.csv and within_nolan.json.
"""

import argparse, csv, json, random, re, statistics, sys
from collections import defaultdict
from itertools import combinations

import typecast as T

random.seed(2805)
N_PERM = 10000


TITLES = {"commissioner", "detective", "professor", "doctor", "captain",
          "commander", "officer", "sergeant", "lieutenant", "colonel",
          "general", "major", "agent", "inspector", "sir", "lord", "lady",
          "mister", "miss", "mrs", "young", "old", "the"}


def char_tokens(c):
    """Name tokens of a credited character, titles removed.

    'Commissioner Gordon', 'Gordon' and 'Jim Gordon' are one part. Taking
    the first token would make them three, which would count a reprised
    character once per sequel — the opposite of what the paper states.
    """
    c = re.sub(r"\(.*?\)", " ", c or "")
    c = re.sub(r"[^A-Za-z\s/]", " ", c)
    c = c.replace("/", " ")
    return {t.lower() for t in c.split()
            if len(t) > 2 and t.lower() not in TITLES}


def group_characters(roles):
    """Merge an actor's roles whose names share any name token."""
    groups = []            # list of (tokenset, [roles])
    for r in roles:
        tk = char_tokens(r["character"])
        hit = None
        for g in groups:
            if tk & g[0]:
                hit = g
                break
        if hit:
            hit[0].update(tk)
            hit[1].append(r)
        else:
            groups.append([set(tk), [r]])
    # keep the fullest passage from each group
    return [max(g[1], key=lambda r: len(r["text"].split())) for g in groups]


def mean_pairwise(vs):
    ps = [T.cos(a, b) for a, b in combinations(vs, 2)]
    return statistics.mean(ps) if ps else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default="passages.csv")
    ap.add_argument("--text", default="role_text_blind")
    ap.add_argument("--draws", type=int, default=200,
                    help="random subsets used to size-match the control")
    args = ap.parse_args()

    rows = T.load(args.roles, args.text)
    vecs = T.tfidf_vectors(rows)
    for r, v in zip(rows, vecs):
        r["v"] = v

    by_actor = defaultdict(list)
    for r in rows:
        by_actor[r["actor"]].append(r)

    out = []
    for actor, rs in by_actor.items():
        nol, oth = [], [r for r in rs if not r["is_nolan"]]

        # one row per distinct Nolan character, keeping the fullest passage
        nol = group_characters([r for r in rs if r["is_nolan"]])

        if len(nol) < 2 or len(oth) < 2:
            continue

        sim_nolan = mean_pairwise([r["v"] for r in nol])

        # size-matched control: same number of roles, drawn from that
        # actor's non-Nolan work. Mean pairwise similarity drifts with the
        # number of roles, so the control must use the same count.
        k = len(nol)
        if len(oth) < k:
            continue
        draws = []
        for _ in range(args.draws):
            samp = random.sample(oth, k)
            m = mean_pairwise([r["v"] for r in samp])
            if m is not None:
                draws.append(m)
        if not draws:
            continue
        sim_ctrl = statistics.mean(draws)

        out.append({
            "actor": actor,
            "n_nolan_characters": k,
            "n_other_roles": len(oth),
            "characters": " | ".join(sorted(r["character"][:22] for r in nol)),
            "sim_nolan": sim_nolan,
            "sim_control": sim_ctrl,
            "diff": sim_nolan - sim_ctrl,
        })

    if len(out) < 5:
        sys.exit(f"only {len(out)} actors with 2+ distinct Nolan characters "
                 f"and enough other roles — not testable")

    diffs = [o["diff"] for o in out]
    obs = statistics.mean(diffs)
    null = [statistics.mean([d if random.random() < .5 else -d for d in diffs])
            for _ in range(N_PERM)]
    sd = statistics.pstdev(null)
    z = obs / sd if sd else float("nan")
    p = (sum(1 for v in null if abs(v) >= abs(obs)) + 1) / (N_PERM + 1)
    above = sum(1 for d in diffs if d > 0)
    p_floor = 2.0 ** -len(out)

    print("=" * 66)
    print(f"actors with 2+ distinct Nolan characters   {len(out)}")
    print(f"mean pairwise similarity, Nolan roles      "
          f"{statistics.mean([o['sim_nolan'] for o in out]):.4f}")
    print(f"mean pairwise similarity, control          "
          f"{statistics.mean([o['sim_control'] for o in out]):.4f}")
    print(f"mean difference                            {obs:+.4f}")
    print(f"actors where Nolan roles are MORE alike    {above}/{len(out)}")
    print(f"sign-flip null                             z = {z:+.2f}  p = {p:.4f}")
    print("=" * 66)

    if p_floor > .05:
        print(f"\nTOO FEW ACTORS. With {len(out)} the smallest reachable p is "
              f"{p_floor:.3f}.")
    elif p < .05 and obs > 0:
        print("\nMORE ALIKE. An actor's several Nolan roles resemble each other")
        print("more than that actor's other roles resemble each other — he")
        print("reuses people for the same kind of part.")
    elif p < .05:
        print("\nLESS ALIKE. An actor's Nolan roles resemble each other LESS")
        print("than their other roles do — when he reuses someone, he uses")
        print("them differently each time.")
    else:
        print("\nNO DIFFERENCE. An actor's Nolan roles are no more alike than")
        print("that actor's other roles are. Reuse does not mean repetition,")
        print("but it does not mean deliberate variation either.")

    out.sort(key=lambda o: -o["diff"])
    print(f"\n{'actor':<20}{'chars':>6}{'nolan':>9}{'ctrl':>9}{'diff':>9}   characters")
    for o in out:
        print(f"{o['actor'][:18]:<20}{o['n_nolan_characters']:>6}"
              f"{o['sim_nolan']:>9.4f}{o['sim_control']:>9.4f}"
              f"{o['diff']:>+9.4f}   {o['characters'][:46]}")

    with open("within_nolan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    with open("within_nolan.json", "w", encoding="utf-8") as f:
        json.dump({"n_actors": len(out), "obs": obs, "z": z, "p": p,
                   "above": above, "p_floor": p_floor,
                   "sim_nolan": statistics.mean([o["sim_nolan"] for o in out]),
                   "sim_control": statistics.mean([o["sim_control"] for o in out])},
                  f, indent=1)
    print("\nwrote within_nolan.csv, within_nolan.json")


if __name__ == "__main__":
    main()
