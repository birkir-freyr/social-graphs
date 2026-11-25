"""Why does Heath Ledger's Joker score as close to type?

Contribution audit (course Week 6): for L2-normalised vectors, cosine(role, centroid) is the
sum over terms of role[t] * centroid[t]. We list the terms that contribute most, and the
same for Ledger's control roles, to see what 'type' means to this measure.

Run from 'Final project/investigations':  python3 ledger_audit.py [actor] [film]
"""
import sys
from common import T, load_rows, vectorise, by_actor, priors_for

actor = sys.argv[1] if len(sys.argv) > 1 else "Heath Ledger"
film = sys.argv[2] if len(sys.argv) > 2 else "The Dark Knight"
rows = vectorise(load_rows("role_text_blind"))
rs = by_actor(rows)[actor]
target = next(r for r in rs if r["film"] == film)
prior = priors_for(rs, target, "typecast")
c = T.centroid([x["v"] for x in prior])
print(f"{actor} as {target['character']} in {film}: {len(prior)} earlier roles")
for x in sorted(prior, key=lambda x: x["year"]):
    print(f"   {x['year']} {x['film'][:28]:<30} {x['character'][:24]:<26} cos to type {T.cos(x['v'], c):.3f}")
print(f"cos(role, type) = {T.cos(target['v'], c):.4f}   (departure {1 - T.cos(target['v'], c):.4f})")
contrib = sorted(((target['v'][w] * c.get(w, 0), w) for w in target['v']), reverse=True)
print("top shared terms (contribution, term, weight in role, weight in type):")
for val, w in contrib[:15]:
    print(f"   {val:.4f}  {w:<16} {target['v'][w]:.3f}  {c.get(w, 0):.3f}")
print("heaviest terms in the role passage that the type lacks:")
for w, x in sorted(target["v"].items(), key=lambda kv: -kv[1])[:15]:
    if c.get(w, 0) == 0:
        print(f"   {x:.3f}  {w}")
print("\nRole passage (all names masked):\n", target["text"][:1500])
