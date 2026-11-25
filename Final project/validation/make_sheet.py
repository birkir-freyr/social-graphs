"""Build the hand-labelled validation sample.

Does cosine similarity between two role passages track what a reader would call 'the same
kind of character'? We draw 24 pairs:
  - 18 WITHIN-ACTOR pairs: one actor's Nolan role vs one of the same actor's earlier roles
    (exactly the comparison the paper makes), 6 from each tercile of cosine similarity;
  - 5 SAME-FILM pairs: two different characters from the same Nolan film with high cosine.
    If readers judge these different while the measure calls them similar, the measure is
    tracking the film rather than the character (the same-film placebo, seen by people);
  - 1 CASE pair: Heath Ledger's Joker vs his outlaw role in Ned Kelly.
Passages are limited to 30-250 words (the case pair excepted) so that rating takes ~25 min.
Raters see the own-name-masked text (character and film title replaced) and nothing else;
cosine and pair type are kept in validation_key.csv.

Run from 'Final project':  python3 validation/make_sheet.py
"""
import csv, os, random, sys
from itertools import combinations
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "investigations"))
from common import T, load_rows, vectorise, by_actor, priors_for
sys.path.insert(0, os.path.dirname(HERE))
from check_descriptors import is_descriptor          # Hanna's rule: credit names no person
import within_nolan as W                              # surname rule for 'same character'

rng = random.Random(2805)
rows = vectorise(load_rows("role_text_blind"))           # cosine as in the paper
masked = {(r["actor"], r["film"], r["character"]): r["text"]
          for r in load_rows("role_text_masked")}         # what raters read
GENERIC = {"member", "soldier", "man", "woman", "officer", "agent", "guard", "technician", "driver",
           "cop", "pilot", "doctor", "nurse", "reporter", "waiter", "boy", "girl", "kid", "henchman",
           "thug", "prisoner", "worker", "assistant", "trader", "student", "guest", "clerk"}
long_credit = lambda c: (len(c.split("/")[0].split()) >= 4      # 'Younger Gotham Water Board Technician'
                         or any(w.lower().strip(".#0123456789") in GENERIC for w in c.split()))
ok_len = lambda r: (30 <= r["n_words"] <= 250 and not is_descriptor(r["character"])
                    and not long_credit(r["character"]))
A = by_actor(rows)

within = []
for actor, rs in A.items():
    for t in rs:
        if not t["is_nolan"] or not ok_len(t):
            continue
        for p in priors_for(rs, t, "typecast"):
            if ok_len(p):
                within.append((T.cos(t["v"], p["v"]), actor, t, p))
within.sort(key=lambda x: x[0])
n = len(within)
terciles = [within[: n // 3], within[n // 3: 2 * n // 3], within[2 * n // 3:]]
chosen, used_actors = [], set()
for tier, pool in zip(("low", "mid", "high"), terciles):
    pool = pool[:]
    rng.shuffle(pool)
    picked = 0
    for cos_, actor, t, p in pool:
        if actor in used_actors:
            continue
        chosen.append(dict(kind="within_actor", tier=tier, cos=cos_, actor_a=actor, actor_b=actor, a=t, b=p))
        used_actors.add(actor)
        picked += 1
        if picked == 6:
            break

film_rows = {}
for r in rows:
    if r["is_nolan"] and ok_len(r):
        film_rows.setdefault(r["film"], []).append(r)
same_film = []
for film, rs in film_rows.items():
    for a, b in combinations(rs, 2):
        same_character = bool(W.char_tokens(a["character"]) & W.char_tokens(b["character"]))
        if a["actor"] != b["actor"] and not same_character and a["text"] != b["text"]:
            same_film.append((T.cos(a["v"], b["v"]), film, a, b))
same_film.sort(key=lambda x: -x[0])
seen_films = set()
for cos_, film, a, b in same_film:                      # highest-cosine pair per film, 5 films
    if film in seen_films or a["actor"] in used_actors or b["actor"] in used_actors:
        continue
    chosen.append(dict(kind="same_film", tier="high", cos=cos_, actor_a=a["actor"], actor_b=b["actor"], a=a, b=b))
    seen_films.add(film)
    if len(seen_films) == 5:
        break

ledger = A["Heath Ledger"]
joker = next(r for r in ledger if r["film"] == "The Dark Knight")
kelly = next(r for r in ledger if r["film"] == "Ned Kelly")
chosen.append(dict(kind="case", tier="case", cos=T.cos(joker["v"], kelly["v"]),
                   actor_a="Heath Ledger", actor_b="Heath Ledger", a=joker, b=kelly))

rng.shuffle(chosen)
for i, c in enumerate(chosen, 1):
    c["id"] = f"P{i:02d}"
    if rng.random() < 0.5:                               # random left/right order
        c["a"], c["b"] = c["b"], c["a"]
        c["actor_a"], c["actor_b"] = c["actor_b"], c["actor_a"]

txt = lambda r: masked[(r["actor"], r["film"], r["character"])]
with open(os.path.join(HERE, "validation_sheet.md"), "w", encoding="utf-8") as f:
    f.write("# Character-similarity rating sheet\n\n"
            "**Rate each pair before looking at the scores in `validation_key.csv`.**\n\n"
            "For each pair, read the two character descriptions (taken from Wikipedia plot "
            "summaries; the character's own name is replaced by CHARACTER and the film title by "
            "FILM). Then answer:\n\n"
            "> *How similar are these two characters as kinds of character?*\n\n"
            "Think about their role in the story (hero, villain, mentor, victim, love interest, "
            "sidekick...), their occupation or social position, their moral alignment, and their "
            "personality as far as the text shows it. **Ignore whether the films themselves are "
            "similar** (genre, setting, era) and do not try to guess the actor.\n\n"
            "| Score | Meaning |\n|---|---|\n"
            "| 1 | Completely different kinds of character |\n"
            "| 2 | Mostly different, one minor similarity |\n"
            "| 3 | Some clear similarities and some clear differences |\n"
            "| 4 | Mostly the same kind of character |\n"
            "| 5 | Essentially the same kind of character |\n\n"
            "Write the scores in the `rating` column of `validation_ratings.csv`.\n\n")
    for c in chosen:
        f.write(f"---\n\n## {c['id']}\n\n**Character A.** {txt(c['a'])}\n\n"
                f"**Character B.** {txt(c['b'])}\n\n")
ratings_path = os.path.join(HERE, "validation_ratings.csv")
if not os.path.exists(ratings_path):                     # never overwrite existing ratings
    with open(ratings_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "rating"])
        for c in chosen:
            w.writerow([c["id"], ""])
with open(os.path.join(HERE, "validation_key.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["pair_id", "kind", "cos_tier", "cosine", "actor_a", "film_a", "character_a",
                "words_a", "actor_b", "film_b", "character_b", "words_b"])
    for c in chosen:
        w.writerow([c["id"], c["kind"], c["tier"], f"{c['cos']:.4f}", c["actor_a"], c["a"]["film"],
                    c["a"]["character"], c["a"]["n_words"], c["actor_b"], c["b"]["film"],
                    c["b"]["character"], c["b"]["n_words"]])
print(f"{len(chosen)} pairs: " + ", ".join(f"{k} {sum(c['kind'] == k for c in chosen)}"
                                           for k in ("within_actor", "same_film", "case")))
print(f"within-actor candidate pairs {n}; tercile cut points "
      f"{terciles[1][0][0]:.4f} / {terciles[2][0][0]:.4f}")
