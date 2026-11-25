"""Is the Nolan effect about the ROLE or about Nolan FILMS' vocabulary?

Three tests, all with actor-clustered sign-flip inference:

A. Reproduce the paper's within-actor result and the clustered Nolan-vs-other-directors
   comparison (Nolan roles minus the same actor's later roles for other directors).
B. Same-film placebo: score another character's passage from the SAME film against the
   actor's type. If the actor's own Nolan role departs no more than a random co-star's
   description does, the departure is a property of the film's text, not of the casting.
   The same placebo is computed for non-Nolan films that have 2+ characters in the data,
   which measures how 'foreign' an ordinary new film is to an actor's type.
C. Remove film-specific vocabulary (terms concentrated in one film) and rerun A.

Run from 'Final project':  python3 investigations/film_confound.py
"""
import statistics as st
from collections import defaultdict
from common import (load_rows, vectorise, priors_for, score, by_actor, signflip, fmt,
                    page_mismatch, MIN_PRIOR, ROOT)
import sys
sys.path.insert(0, ROOT)
import within_nolan as W


def scored_roles(rows, mode="director"):
    """Every target role with enough priors, scored like director_test.py."""
    A = by_actor(rows)
    out = []
    for actor, rs in A.items():
        for t in rs:
            if not t["year"] or not t["director"]:
                continue
            prior = priors_for(rs, t, mode)
            if len(prior) < MIN_PRIOR:
                continue
            s = score(t["v"], prior)
            if s is None:
                continue
            out.append(dict(actor=actor, film=t["film"], year=t["year"], character=t["character"],
                            is_nolan=t["is_nolan"], director=t["director"], dep=s[0], ctrl=s[1],
                            diff=s[0] - s[1], prior=prior, target=t))
    return out


def within_nolan(scored):
    g = defaultdict(list)
    for s in scored:
        if s["is_nolan"]:
            g[s["actor"]].append(s["diff"])
    return signflip(g)


def nolan_vs_others(scored):
    """Per actor: mean diff of Nolan roles minus mean diff of the actor's other scored roles."""
    a = defaultdict(lambda: {"n": [], "o": []})
    for s in scored:
        a[s["actor"]]["n" if s["is_nolan"] else "o"].append(s["diff"])
    g = {k: [st.mean(v["n"]) - st.mean(v["o"])] for k, v in a.items() if v["n"] and v["o"]}
    return signflip(g)


def placebo(rows, scored):
    """For each scored role, score every OTHER character's passage from the same film."""
    film_rows = defaultdict(list)
    for r in rows:
        film_rows[(r["film"], r["year"])].append(r)
    out = []
    for s in scored:
        own = W.char_tokens(s["character"])
        # a co-star is a DIFFERENT character: not the same actor, not a shared surname (young and
        # adult Murph in Interstellar share one passage) and not an identical passage
        mates = [r for r in film_rows[(s["film"], s["year"])]
                 if r["actor"] != s["actor"] and not (W.char_tokens(r["character"]) & own)
                 and r["text"] != s["target"]["text"]]
        if not mates:
            continue
        diffs = []
        for m in mates:
            sc = score(m["v"], s["prior"])
            if sc is not None:
                diffs.append(sc[0] - sc[1])
        if diffs:
            out.append(dict(s, placebo=st.mean(diffs), n_mates=len(mates)))
    return out


def report(rows, label):
    print(f"\n=== {label} ===")
    scored = scored_roles(rows)
    nol = [s for s in scored if s["is_nolan"]]
    print(f"scored roles {len(scored)} (Nolan {len(nol)})")
    print(fmt(within_nolan(scored), "A1 Nolan role vs own earlier roles (paper's test)"))
    print(fmt(nolan_vs_others(scored), "A2 Nolan minus same actor's other later roles"))
    pl = placebo(rows, scored)
    pn = [p for p in pl if p["is_nolan"]]
    po = [p for p in pl if not p["is_nolan"]]
    g = defaultdict(list)
    for p in pn:
        g[p["actor"]].append(p["diff"] - p["placebo"])
    print(f"placebo available: Nolan roles {len(pn)}, non-Nolan roles {len(po)}")
    print(f"   mean diff: Nolan real {st.mean(p['diff'] for p in pn):+.4f}  "
          f"Nolan placebo {st.mean(p['placebo'] for p in pn):+.4f}  |  "
          f"other real {st.mean(p['diff'] for p in po):+.4f}  "
          f"other placebo {st.mean(p['placebo'] for p in po):+.4f}")
    print(fmt(signflip(g), "B1 Nolan: real role minus same-film placebo"))
    g = defaultdict(list)
    for p in po:
        g[p["actor"]].append(p["diff"] - p["placebo"])
    print(fmt(signflip(g), "B2 other films: real role minus same-film placebo"))
    # film foreignness: placebo of Nolan films vs placebo of the same actor's other films
    a = defaultdict(lambda: {"n": [], "o": []})
    for p in pl:
        a[p["actor"]]["n" if p["is_nolan"] else "o"].append(p["placebo"])
    g = {k: [st.mean(v["n"]) - st.mean(v["o"])] for k, v in a.items() if v["n"] and v["o"]}
    print(fmt(signflip(g), "B3 placebo: Nolan films minus same actor's other films"))
    return scored, pl


if __name__ == "__main__":
    rows = vectorise(load_rows())
    scored, pl = report(rows, "Baseline (all-names masked, as in paper)")

    # C. film-specific vocabulary: terms whose documents are >= 50% from one film
    docs_by_term = defaultdict(lambda: defaultdict(int))
    from typecast import tokens
    for r in rows:
        for w in set(tokens(r["text"])):
            docs_by_term[w][(r["film"], r["year"])] += 1
    film_terms = set()
    for w, films in docs_by_term.items():
        tot = sum(films.values())
        if tot >= 2 and max(films.values()) / tot >= 0.5:
            film_terms.add(w)
    print(f"\nfilm-concentrated terms removed: {len(film_terms)} "
          f"(e.g. {sorted(t for t in film_terms if t in {'subconscious','inverted','dilation','tesseract','dream','bomb','batman','joker','gotham'})})")
    rows_c = vectorise(load_rows(), drop_terms=frozenset(film_terms))
    report(rows_c, "C. Film-concentrated vocabulary removed")

    rows_m = [r for r in load_rows() if not page_mismatch(r)]
    print(f"\nroles dropped as possible wrong-article matches: {len(load_rows()) - len(rows_m)}")
    report(vectorise(rows_m), "D. Possible wrong-article roles removed")
