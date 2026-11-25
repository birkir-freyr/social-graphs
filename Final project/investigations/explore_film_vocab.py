"""Is the Nolan 'departure' a property of the role, or of Nolan films' vocabulary?

Exploration step 1: how lexically unusual are Nolan passages compared with every
other passage in the corpus, independent of who plays the role?

Run from 'Final project/investigations':  python3 explore_film_vocab.py
"""
import os, sys, statistics as st
from collections import defaultdict, Counter
from common import T, ROOT

rows = T.load(os.path.join(ROOT, "passages.csv"), "role_text_blind")
vecs = T.tfidf_vectors(rows)
for r, v in zip(rows, vecs):
    r["v"] = v

nolan = [r for r in rows if r["is_nolan"]]
other = [r for r in rows if not r["is_nolan"]]
print(f"{len(rows)} usable passages: {len(nolan)} Nolan, {len(other)} other")

# 1. Typicality: cosine of a passage to the centroid of ALL OTHER passages in the corpus
#    (leave-one-out is unnecessary at this size, but we exclude the passage's own film).
by_film = defaultdict(list)
for r in rows:
    by_film[(r["film"], r["year"])].append(r)
total = defaultdict(float)
for r in rows:
    for k, x in r["v"].items():
        total[k] += x
def typicality(r):
    own = defaultdict(float)
    for q in by_film[(r["film"], r["year"])]:
        for k, x in q["v"].items():
            own[k] += x
    rest = {k: total[k] - own.get(k, 0.0) for k in total}
    n = sum(x * x for x in rest.values()) ** 0.5
    rest = {k: x / n for k, x in rest.items()}
    return T.cos(r["v"], rest)
for r in rows:
    r["typ"] = typicality(r)
print(f"typicality (cos to corpus centroid, own film excluded): "
      f"Nolan median {st.median(r['typ'] for r in nolan):.4f}  "
      f"other median {st.median(r['typ'] for r in other):.4f}")

# 2. Within-film similarity: how alike are different characters' passages in the same film?
def within(rs):
    out = []
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            if rs[i]["character"] != rs[j]["character"]:
                out.append(T.cos(rs[i]["v"], rs[j]["v"]))
    return out
nw, ow = [], []
for k, rs in by_film.items():
    sims = within(rs)
    if not sims:
        continue
    (nw if rs[0]["is_nolan"] else ow).extend(sims)
print(f"within-film cosine between different characters: Nolan mean {st.mean(nw):.4f} "
      f"(n pairs {len(nw)}), other mean {st.mean(ow) if ow else float('nan'):.4f} (n pairs {len(ow)})")
multi = sum(1 for rs in by_film.values() if len({r['character'] for r in rs}) >= 2 and not rs[0]['is_nolan'])
print(f"non-Nolan films with 2+ characters in our data: {multi}")

# 3. Which terms carry the most weight in Nolan passages but are rare elsewhere?
df_n, df_o = Counter(), Counter()
for r in nolan:
    df_n.update(set(r["v"]))
for r in other:
    df_o.update(set(r["v"]))
ratio = sorted(((df_n[w] / len(nolan)) / ((df_o[w] + 1) / len(other)), w, df_n[w], df_o[w])
               for w in df_n if df_n[w] >= 4)
print("terms most over-represented in Nolan passages (ratio, term, #nolan, #other):")
for x in ratio[-30:][::-1]:
    print(f"  {x[0]:6.1f}  {x[1]:<16} {x[2]:>3} {x[3]:>4}")
