"""Re-run the paper's estimators on Fandom and on identical credits from both sources."""
import csv
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "investigations"))
from common import load_rows, signflip, vectorise
from film_confound import placebo, scored_roles
from selection_placebo import run as selection_ranks

RESULTS = HERE / "results"
ROLE_COLUMNS = ("actor", "film", "year", "character")
MAIN_SAMPLES = ("fandom", "fandom_shared", "wikipedia_shared")


def role_key(row):
    return tuple(row[column] for column in ROLE_COLUMNS)


def estimate(groups, null_value=0):
    if not groups:
        return dict(n=0, actors=0, mean=None, p=None, ci95=None)
    centered = {a: [v - null_value for v in group] for a, group in groups.items()}
    difference, _, p, n, k = signflip(centered)
    mean = difference + null_value
    rng = random.Random(2805)
    totals = [(sum(g), len(g)) for g in groups.values()]
    boot = []
    for _ in range(5000):
        sampled = [rng.choice(totals) for _ in range(k)]
        boot.append(sum(t for t, _ in sampled) / sum(n for _, n in sampled))
    boot.sort()
    return dict(n=n, actors=k, mean=mean, p=p, ci95=[boot[125], boot[4874]])


def summarize(rows, include_ranks=True):
    rows = vectorise([dict(r) for r in rows])
    scored = scored_roles(rows)
    mates = {role_key(p): p for p in placebo(rows, scored)}
    ranks = selection_ranks(rows, 3) if include_ranks else []
    groups = defaultdict(lambda: defaultdict(list))
    comparisons = defaultdict(lambda: defaultdict(list))
    detail = []
    for s in scored:
        k = role_key(s)
        a = s["actor"]
        sample = "nolan" if s["is_nolan"] else "other"
        groups[sample + "_excess"][a].append(s["diff"])
        comparisons[a][sample].append(s["diff"])
        m = mates.get(k)
        delta = None
        if m:
            delta = m["diff"] - m["placebo"]
            groups[sample + "_own_minus_costar"][a].append(delta)
            groups[sample + "_own_paired"][a].append(m["diff"])
            groups[sample + "_costar_paired"][a].append(m["placebo"])
            comparisons[a][sample + "_costar"].append(m["placebo"])
        detail.append({
            **dict(zip(ROLE_COLUMNS, k)),
            "group": sample, "director": s["director"], "n_prior": len(s["prior"]),
            "excess": s["diff"], "n_costars": m["n_mates"] if m else 0, "own_minus_costar": delta,
        })
    for actor, values in comparisons.items():
        for suffix in ("", "_costar"):
            nolan = values.get("nolan" + suffix)
            other = values.get("other" + suffix)
            if nolan and other:
                groups["nolan_minus_other" + suffix][actor] = [st.mean(nolan) - st.mean(other)]
    for r in ranks:
        sample = "nolan" if r["is_nolan"] else "other"
        for col in ("own", "placebo", "diff"):
            groups[f"{sample}_rank_{col}"][r["actor"]].append(r[col])
    names = ["nolan_excess", "other_excess", "nolan_minus_other", "nolan_minus_other_costar"]
    names.extend(f"{s}_{m}" for s in ("nolan", "other")
                 for m in ("own_minus_costar", "own_paired", "costar_paired"))
    if include_ranks:
        names.extend(f"{s}_rank_{m}" for s in ("nolan", "other") for m in ("own", "placebo", "diff"))
    return {k: estimate(groups[k], 0.5 if k.endswith(("_rank_own", "_rank_placebo")) else 0)
            for k in names}, detail


def save_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    RESULTS.mkdir(exist_ok=True)
    path = HERE / "passages.csv"
    f = load_rows(path=str(path))
    w = load_rows()
    shared = {role_key(r) for r in f} & {role_key(r) for r in w}
    inputs = {"fandom": f, "fandom_shared": [r for r in f if role_key(r) in shared],
              "wikipedia_shared": [r for r in w if role_key(r) in shared]}
    with open(path, newline="", encoding="utf-8") as file:
        corpus = list(csv.DictReader(file))
    by_key = {role_key(dict(row, year=int(row["year"]) if row["year"].isdigit() else None)): row
              for row in corpus}
    for size in (40, 60, 80, 100, 120):
        inputs[f"fandom_{size}_words"] = [dict(r, text=" ".join(r["text"].split()[:size])) for r in f
                                          if len(r["text"].split()) >= size]
    inputs["fandom_general_wikis"] = [r for r in f if by_key[role_key(r)]["source_url"].split("/")[2]
                                      in {"hero.fandom.com", "villains.fandom.com"}]
    alternatives = load_rows(path=str(HERE / "general_wiki_alternatives.csv"))
    inputs["fandom_general_wikis"] += alternatives
    inputs["fandom_profile_sections"] = [r for r in f if by_key[role_key(r)]["selection"] == "profile"]
    inputs["fandom_character_and_film_masked"] = load_rows("role_text_masked", path=str(path))
    inputs["fandom_unmasked"] = load_rows("role_text", path=str(path))
    # Refit vocabulary independently in each corpus, including on the common support.
    summaries, details = {}, {}
    for label, rows in inputs.items():
        stats, detail = summarize(rows, include_ranks=label in MAIN_SAMPLES)
        summaries[label] = dict(passages=len(rows), nolan=sum(r["is_nolan"] for r in rows), tests=stats)
        details[label] = detail
    for label in MAIN_SAMPLES:
        save_csv(RESULTS / f"{label}_scores.csv", details[label])
    # Paired change in the paper's main placebo contrast for the identical actor, film and priors.
    old = {role_key(r): r for r in details["wikipedia_shared"]}
    new = {role_key(r): r for r in details["fandom_shared"]}
    if old.keys() != new.keys():
        raise ValueError("The matched corpora produced different target roles")
    change = defaultdict(list)
    departure_change = defaultdict(list)
    for k, r in new.items():
        base = old[k]
        if (r["n_prior"], r["n_costars"]) != (base["n_prior"], base["n_costars"]):
            raise ValueError(f"Different comparison sets for the matched role {k}")
        if r["group"] == "nolan":
            departure_change[r["actor"]].append(r["excess"] - base["excess"])
        if r["group"] == "nolan" and r["n_costars"]:
            change[r["actor"]].append(r["own_minus_costar"] - base["own_minus_costar"])
    summaries["shared_change_in_nolan_excess"] = estimate(departure_change)
    summaries["shared_change_in_nolan_placebo"] = estimate(change)
    summaries["coverage"] = dict(roster=len(corpus), nolan_roster=sum(r["is_nolan"]=="1" for r in corpus),
                                 status=dict(Counter(r["status"] for r in corpus)),
                                 actors=len({r["actor"] for r in f}), films=len({(r["film"],r["year"]) for r in f}),
                                 by_nolan_film=dict(Counter(r["film"] for r in f if r["is_nolan"])),
                                 by_wiki=dict(Counter(by_key[role_key(r)]["source_url"].split("/")[2] for r in f)),
                                 median_words={s:st.median(r["n_words"] for r in f if r["is_nolan"]==v)
                                               for s,v in (("nolan",True),("other",False))})
    (RESULTS / "comparison.json").write_text(json.dumps(summaries,indent=2,allow_nan=False)+"\n")
    for name in MAIN_SAMPLES:
        out = summaries[name]["tests"]
        print(name, summaries[name]["passages"], out["nolan_excess"], out["nolan_own_minus_costar"])


if __name__ == "__main__":
    main()
