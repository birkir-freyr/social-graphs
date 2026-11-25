"""Passages contaminated by a co-star's shared surname, and the effect of dropping them.

collect_passages.py keeps every plot sentence that contains any capitalised part of the
character's credited name. When two characters in a film share a surname (Dom and Mal Cobb,
Robert and Kitty Oppenheimer, Wilhelm and Jacob Grimm), each passage also collects sentences
about the other. For every usable role we find the sentences that were matched ONLY through a
name another character in the same film also has (age variants of the same character, such as
'Young Bruce Wayne', are not counted), and rerun the main test without roles where such
sentences make up at least a quarter of the passage.

Run from 'Final project/investigations':  python3 surname_contamination.py
"""
import csv, re, os
from collections import defaultdict
import common
from common import load_rows, vectorise, signflip, fmt
from film_confound import scored_roles, within_nolan, nolan_vs_others
import collect_passages as C

ROOT = common.ROOT
films = {r["film_id"]: r["title"] for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_films.csv")))}
cast = defaultdict(set)
for c in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_cast.csv"))):
    cast[films[c["film_id"]]].add((c["actor_name"], c["character"]))
raw = list(csv.DictReader(open(os.path.join(ROOT, "passages.csv"), encoding="utf-8")))
for r in raw:
    cast[r["film"]].add((r["actor"], r["character"]))

AGE = re.compile(r"\b(young|younger|older|old|teen|teenage|child|kid|little|adult)\b|\d|yrs", re.I)
norm = lambda ch: {k.lower() for k in C.name_keys(AGE.sub(" ", ch))}
has = lambda k, s: re.search(rf"\b{re.escape(k)}\b", s)

flagged = {}
for r in raw:
    if int(r["n_words"] or 0) < 25:
        continue
    keys, mine = C.name_keys(r["character"]), norm(r["character"])
    amb = set()
    for a, ch in cast[r["film"]]:
        if a == r["actor"] or ch == r["character"]:
            continue
        other = norm(ch)
        if other and (other <= mine or mine <= other):
            continue                                   # same character at another age / alias
        amb |= {k for k in keys if k.lower() in other}
    if not amb:
        continue
    unique = [k for k in keys if k not in amb]
    bad = [s for s in C.sentences(r["role_text"]) if not any(has(k, s) for k in unique)]
    share = sum(len(s.split()) for s in bad) / int(r["n_words"])
    if share > 0:
        flagged[(r["actor"], r["film"], r["character"])] = (share, r["is_nolan"] == "1", sorted(amb))

drop = {k for k, v in flagged.items() if v[0] >= 0.25}
print(f"roles with sentences matched only through a shared name: {len(flagged)} "
      f"(Nolan {sum(v[1] for v in flagged.values())}); dropped (>= 25% of passage): {len(drop)}")
for k, v in sorted(flagged.items(), key=lambda kv: -kv[1][0])[:12]:
    print(f"   {v[0]:4.0%}  {'N' if v[1] else ' '}  {k[0][:18]:<19}{k[2][:24]:<25}{k[1][:22]:<23} via {v[2]}")

rows = vectorise([r for r in load_rows() if (r["actor"], r["film"], r["character"]) not in drop])
sc = scored_roles(rows)
print(fmt(within_nolan(sc), "Nolan role vs own earlier roles, contaminated roles dropped"))
print(fmt(nolan_vs_others(sc), "Nolan minus same actor's other roles, contaminated dropped"))
