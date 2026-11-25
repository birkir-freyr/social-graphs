#!/usr/bin/env python3
"""
Figures for the Nolan typecasting paper, in the casting-network's style.

  fig2  the result: every Nolan role against its own control
  fig3  the effect once passage length is equalised
  fig1  (optional) the length confound itself

Every figure is one column wide and one height, carries no text that
belongs in a caption, and draws grid lines only on the axis a reader
reads values off.

    python3 figures.py --roles passages.csv

Writes figures/*.png and figures/figure_numbers.json, which holds every
number quoted in the text and captions, so the two cannot drift apart.
"""

import argparse, csv, json, math, os, statistics, subprocess, sys

import figstyle as S
import matplotlib.pyplot as plt

S.apply()


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** .5
    return num / den if den else float("nan")


HONORIFIC = {"dr", "dr.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "miss",
             "sir", "lord", "lady", "professor", "prof.", "commissioner",
             "detective", "captain", "commander", "colonel", "general",
             "major", "sergeant", "lieutenant", "officer", "agent",
             "inspector", "young", "old", "the"}


def short(actor, character):
    """'Matt Damon', 'Leslie Groves' -> 'Damon · Leslie Groves'.

    Never truncates mid-word — a label reading 'Leslie Grove' looks like
    a misspelling, not an abbreviation. Long names are shortened by
    dropping an honorific or an alias, never by cutting characters.
    """
    surname = actor.split()[-1]
    c = (character or "").split("/")[0].strip()          # 'X / Y' -> 'X'
    toks = [t for t in c.split() if t.lower() not in HONORIFIC]
    c = " ".join(toks) or c
    if len(c) > 18:
        c = toks[-1] if toks else c                      # fall back to surname
    return f"{surname} · {c}" if c else surname


def run_typecast(roles, text, trunc, out_json, min_results):
    cmd = [sys.executable, "typecast.py", "--roles", roles, "--text", text,
           "--truncate", str(trunc), "--json", out_json,
           "--min-results", str(min_results)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(out_json):
        return None, (r.stdout + r.stderr).strip().splitlines()[-1:]
    with open(out_json, encoding="utf-8") as f:
        return json.load(f), None


# --------------------------------------------------------------- figure 2
def fig2(d, out):
    """Each role against its own control.

    One panel, not two. The null distribution used to sit beside this on
    a completely different x-axis, which made the pair hard to read and
    forced a double-width figure; it is the same information the
    p-value in the caption carries.
    """
    res = d["results"]
    above = [r for r in res if r["diff"] > 0]
    below = [r for r in res if r["diff"] <= 0]

    lo = min(min(r["control"] for r in res), min(r["nolan"] for r in res))
    hi = max(max(r["control"] for r in res), max(r["nolan"] for r in res))
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad

    fig, ax = plt.subplots(figsize=(S.COL1, S.HEIGHT))
    ax.plot([lo, hi], [lo, hi], color=S.LINE, lw=0.9, ls=(0, (5, 4)), zorder=2)
    ax.scatter([r["control"] for r in below], [r["nolan"] for r in below],
               s=22, color=S.OTHER, lw=0.7, edgecolor=S.SURFACE, zorder=3,
               label=f"Closer to type ({len(below)})")
    ax.scatter([r["control"] for r in above], [r["nolan"] for r in above],
               s=22, color=S.NOLAN, lw=0.7, edgecolor=S.SURFACE, zorder=4,
               label=f"Further from type ({len(above)})")

    # No point labels. The extremes sit inside a dense cloud, so any
    # label lands on top of other points; naming them in the text costs
    # the reader nothing and keeps the panel readable. short() is kept
    # for the printed table of extremes.
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    S.frame(ax, "",
            xlabel="Departure of the actor's own earlier roles",
            ylabel="Departure of the Nolan role", legend_cols=2)

    fig.savefig(out)
    plt.close(fig)
    return {"n_roles": d["n_roles"], "n_actors": d["n_actors"],
            "obs": d["obs"], "z": d["z"], "p": d["p"],
            "p_floor": d["p_floor"], "above": d["above"],
            "null_sd": d["null_sd"]}


# --------------------------------------------------------------- figure 3
def fig3(sweep, out):
    fig, ax = plt.subplots(figsize=(S.COL1, S.HEIGHT))

    levels = sorted({t for (_, t) in sweep if t}) + [0]
    xpos = {t: i for i, t in enumerate(levels)}

    prim = sorted((xpos[t], d) for (c, t), d in sweep.items()
                  if c == "role_text_blind" and d)
    if prim:
        ax.fill_between([x for x, _ in prim],
                        [-1.96 * d["null_sd"] for _, d in prim],
                        [1.96 * d["null_sd"] for _, d in prim],
                        color=S.GREY, lw=0, zorder=1)
    ax.axhline(0, color=S.LINE, lw=0.8, zorder=2)

    for col, color, mk, label in [
            ("role_text_masked", S.OTHER, "o", "Own name masked"),
            ("role_text_blind",  S.NOLAN, "s", "All names masked")]:
        pts = sorted((xpos[t], d) for (c, t), d in sweep.items()
                     if c == col and d)
        if not pts:
            continue
        ax.plot([x for x, _ in pts], [d["obs"] for _, d in pts],
                color=color, lw=1.5, marker=mk, ms=4.2,
                mec=S.SURFACE, mew=0.8, zorder=3, label=label)

    ax.set_xticks(list(xpos.values()))
    ax.set_xticklabels([str(t) if t else "all" for t in levels])
    ax.set_xlim(-0.3, len(levels) - 0.7)
    S.frame(ax, "",
            xlabel="Words kept per passage",
            ylabel="Mean excess departure",
            grid="y", legend_cols=2)

    fig.savefig(out)
    plt.close(fig)
    return {f"{c}@{t}": (d["obs"] if d else None) for (c, t), d in sweep.items()}


# --------------------------------------------------------------- figure 1
def fig1(rows, full, out):
    nol = [int(r["n_words"]) for r in rows if r["is_nolan"] == "1"]
    oth = [int(r["n_words"]) for r in rows if r["is_nolan"] != "1"]

    fig, ax = plt.subplots(figsize=(S.COL1, S.HEIGHT))
    res = full["results"]
    wl = {(r["actor"], r["film"]): int(r["n_words"])
          for r in rows if r["is_nolan"] == "1"}
    pts = [(wl.get((r["actor"], r["film"])), r["diff"]) for r in res]
    pts = [(a, b) for a, b in pts if a]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    r_len = pearson(xs, ys)

    ax.axhline(0, color=S.LINE, lw=0.8, zorder=2)
    ax.scatter(xs, ys, s=22, color=S.NOLAN, lw=0.7, edgecolor=S.SURFACE,
               zorder=3)
    S.frame(ax, "",
            xlabel="Words in the Nolan role's passage",
            ylabel="Excess departure of the Nolan role", grid="y")

    fig.savefig(out)
    plt.close(fig)
    return {"median_words_nolan": statistics.median(nol),
            "median_words_other": statistics.median(oth),
            "n_nolan_roles": len(nol), "n_other_roles": len(oth),
            "r_length_vs_departure": r_len}


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default="passages.csv")
    ap.add_argument("--outdir", default="figures")
    ap.add_argument("--min-results", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    rows = [r for r in csv.DictReader(open(args.roles, encoding="utf-8"))
            if int(r["n_words"] or 0) >= 25]
    print(f"{len(rows)} usable roles")

    full, err = run_typecast(args.roles, "role_text_blind", 0,
                             "fig_full.json", args.min_results)
    if not full:
        sys.exit(f"typecast.py produced nothing: {err}")

    sweep = {}
    for col in ("role_text_masked", "role_text_blind"):
        for t in (0, 40, 60, 80, 120):
            d, _ = run_typecast(args.roles, col, t,
                                f"fig_sw_{col}_{t}.json", args.min_results)
            sweep[(col, t)] = d
            print(f"  {col:<18} truncate {t:>3}  "
                  + (f"diff {d['obs']:+.4f}  p {d['p']:.4f}"
                     if d else "too few roles"))

    nums = {}
    nums["fig1"] = fig1(rows, full, os.path.join(args.outdir, "fig1_data.png"))
    nums["fig2"] = fig2(full, os.path.join(args.outdir, "fig2_result.png"))
    nums["fig3"] = fig3(sweep, os.path.join(args.outdir, "fig3_robustness.png"))

    with open(os.path.join(args.outdir, "figure_numbers.json"), "w",
              encoding="utf-8") as f:
        json.dump(nums, f, indent=1)

    for k in ("fig1_data.png", "fig2_result.png", "fig3_robustness.png"):
        print(f"wrote {os.path.join(args.outdir, k)}")
    print(f"wrote {os.path.join(args.outdir, 'figure_numbers.json')}")


if __name__ == "__main__":
    main()
