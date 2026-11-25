"""Link C: does the career co-star network agree with the text types? (type homophily)

Each actor's type = centroid of their non-Nolan role passages (names masked). Two actors are
co-stars if they share a non-Nolan film in their TMDB filmographies (actor_movie_roles.csv); this
is the extended network of the paper, restricted to the actors we can type.

If the text type captures something real about an actor's line of work, actors who work together
should have more similar types than actors who do not (homophily, Week 3: assortativity). A
shared film would make this mechanical (two passages from one plot share words), so for every
pair both types are rebuilt WITHOUT any film that both actors were in.

Tests (QAP: permute actor labels of the co-star matrix, 10,000 draws):
  1. mean type similarity, co-star pairs vs other pairs
  2. Spearman between number of shared non-Nolan films and type similarity
  3. pairs who shared a Nolan film: are their (pre-casting) types closer than other pairs?
     i.e. does Nolan put similar actors together, or mix them?

Run from 'Final project' with networkx/numpy:  python investigations/link_homophily.py
"""
import csv, json, os, random, re, itertools
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr
from common import T, load_rows, vectorise, ROOT

MIN = 3
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

rows = vectorise(load_rows())
other = defaultdict(list)          # actor -> non-Nolan passages
nolan_films = defaultdict(set)
for r in rows:
    if r["is_nolan"]:
        nolan_films[r["actor"]].add(r["film"])
    else:
        other[r["actor"]].append(r)
actors = sorted(a for a, v in other.items() if len(v) >= MIN)

# TMDB filmographies -> co-star (non-Nolan) film sets
nolan_titles = {norm(r["title"]) for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_films.csv")))}
filmo = defaultdict(set)
for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/actor_movie_roles.csv"), encoding="utf-8")):
    if r["actor_name"] in other and norm(r["title"]) not in nolan_titles:
        filmo[r["actor_name"]].add((norm(r["title"]), r["year"]))
# Nolan co-cast from the filtered cast list (main + supporting, credited, on screen)
nolan_cast = defaultdict(set)
title_of = {r["film_id"]: r["title"] for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_films.csv")))}
for r in csv.DictReader(open(os.path.join(ROOT, "data/nolan/nolan_cast.csv"), encoding="utf-8")):
    if r["uncredited"] == "False" and r["voice"] == "False" and r["archive_footage"] == "False":
        nolan_cast[r["actor_name"]].add(title_of.get(r["film_id"], r["film_id"]))

missing = [a for a in actors if not filmo[a]]
print(f"typed actors: {len(actors)}; without TMDB filmography: {missing}")

n = len(actors)
S = np.full((n, n), np.nan); K = np.zeros((n, n)); NK = np.zeros((n, n)); dropped = []
for i, j in itertools.combinations(range(n), 2):
    a, b = actors[i], actors[j]
    shared = filmo[a] & filmo[b]
    K[i, j] = K[j, i] = len(shared)
    NK[i, j] = NK[j, i] = len(nolan_cast[a] & nolan_cast[b])
    st_titles = {t for t, _ in shared}
    pa = [r["v"] for r in other[a] if norm(r["film"]) not in st_titles]
    pb = [r["v"] for r in other[b] if norm(r["film"]) not in st_titles]
    # also drop any passage film the two share in OUR data (covers title spelling differences)
    common_films = {r["film"] for r in other[a]} & {r["film"] for r in other[b]}
    pa = [r["v"] for r in other[a] if norm(r["film"]) not in st_titles and r["film"] not in common_films]
    pb = [r["v"] for r in other[b] if norm(r["film"]) not in st_titles and r["film"] not in common_films]
    if len(pa) < 2 or len(pb) < 2:
        dropped.append((a, b)); continue
    S[i, j] = S[j, i] = T.cos(T.centroid(pa), T.centroid(pb))

iu = np.triu_indices(n, 1)
s, k, nk = S[iu], K[iu], NK[iu]
ok = ~np.isnan(s)
print(f"pairs {ok.sum()} (dropped {len(dropped)} with < 2 passages left); co-star pairs "
      f"{int((k[ok] > 0).sum())}; Nolan co-cast pairs {int((nk[ok] > 0).sum())}")


def qap(stat, n_perm=10000, seed=2805):
    obs = stat(K, NK)
    rng = random.Random(seed)
    null = []
    for _ in range(n_perm):
        p = list(range(n)); rng.shuffle(p)
        null.append(stat(K[np.ix_(p, p)], NK[np.ix_(p, p)]))
    null = np.array(null)
    return obs, (1 + np.sum(np.abs(null - null.mean()) >= abs(obs - null.mean()))) / (n_perm + 1), null.mean()


def diff_costar(Km, NKm):
    kk = Km[iu]
    return np.nanmean(s[ok & (kk > 0)]) - np.nanmean(s[ok & (kk == 0)])


def rho_costar(Km, NKm):
    return spearmanr(Km[iu][ok], s[ok])[0]


def diff_nolan(Km, NKm):
    kk = NKm[iu]
    return np.nanmean(s[ok & (kk > 0)]) - np.nanmean(s[ok & (kk == 0)])


def diff_nolan_given_costar(Km, NKm):
    """Nolan co-cast vs not, among pairs that never co-starred elsewhere (removes career overlap)."""
    kk, nn = K[iu], NKm[iu]
    sel = ok & (kk == 0)
    return np.nanmean(s[sel & (nn > 0)]) - np.nanmean(s[sel & (nn == 0)])


out = {}
print(f"\nmean type similarity: co-stars {np.nanmean(s[ok & (k > 0)]):.4f}  "
      f"others {np.nanmean(s[ok & (k == 0)]):.4f}")
for name, f in (("1 co-star minus other pairs", diff_costar),
                ("2 Spearman(shared films, similarity)", rho_costar),
                ("3 Nolan co-cast minus other pairs", diff_nolan),
                ("3b Nolan co-cast minus other, pairs never co-starred elsewhere", diff_nolan_given_costar)):
    obs, p, mu = qap(f)
    print(f"{name:<64} obs {obs:+.4f}  null mean {mu:+.4f}  p {p:.4f}")
    out[name] = dict(obs=float(obs), null_mean=float(mu), p=float(p))
print(f"Nolan co-cast pairs: mean similarity {np.nanmean(s[ok & (nk > 0)]):.4f}  "
      f"(n={int((ok & (nk > 0)).sum())})")

# gradient: similarity by number of shared films
for lo, hi in ((0, 0), (1, 1), (2, 3), (4, 99)):
    sel = ok & (k >= lo) & (k <= hi)
    print(f"  shared non-Nolan films {lo}-{hi}: pairs {int(sel.sum()):>5}  mean sim {np.nanmean(s[sel]):.4f}")

json.dump(out, open(os.path.join(ROOT, "investigations/link_homophily.json"), "w"), indent=1)

# ---------------- confounds ----------------
# (a) gender: character pronouns in the actor's passages (she/her vs he/his/him). TF-IDF keeps
#     'she'/'her' (rarer than 'he'), so same-gender pairs may look alike for that reason alone.
# (b) era: the mean year of the actor's non-Nolan roles; actors of one generation co-star more and
#     plot summaries of one era may share vocabulary.
# (c) franchise/world vocabulary: rebuild every vector with only GENERIC terms, those used in
#     passages from 20+ different films, so 'Hogwarts'-type words cannot carry the result.
from collections import Counter
fem = {}
era = {}
for a in actors:
    toks = Counter(w for r in other[a] for w in re.findall(r"[a-z]+", r["text"].lower()))
    f, m = toks["she"] + toks["her"], toks["he"] + toks["his"] + toks["him"]
    fem[a] = f / (f + m) if f + m else 0.5
    era[a] = np.mean([r["year"] for r in other[a] if r["year"]])
gender = {a: fem[a] > 0.5 for a in actors}
print(f"\nactors coded female by pronouns: {sum(gender.values())} of {n}: {sorted(a for a in actors if gender[a])}")
SG = np.array([[gender[actors[i]] == gender[actors[j]] for j in range(n)] for i in range(n)], float)
DE = np.array([[abs(era[actors[i]] - era[actors[j]]) for j in range(n)] for i in range(n)])
# (d) prolific actors: more passages give a smoother centroid (closer to everyone) AND more co-stars.
#     Label permutation does not remove this, so the number of passages of both actors and how
#     close each actor's type is to the corpus mean ('generic actor') are controlled too.
npass = {a: np.log(len(other[a])) for a in actors}
glob = T.centroid([r["v"] for a in actors for r in other[a]])
typ = {a: T.cos(T.centroid([r["v"] for r in other[a]]), glob) for a in actors}
NP_S = np.array([[npass[actors[i]] + npass[actors[j]] for j in range(n)] for i in range(n)])
NP_P = np.array([[npass[actors[i]] * npass[actors[j]] for j in range(n)] for i in range(n)])
TY_S = np.array([[typ[actors[i]] + typ[actors[j]] for j in range(n)] for i in range(n)])
TY_P = np.array([[typ[actors[i]] * typ[actors[j]] for j in range(n)] for i in range(n)])


def resid(y, Xcols):
    X = np.column_stack([np.ones(len(y))] + Xcols)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def controlled(svec, label):
    """Semi-partial QAP: residualise similarity on same-gender and era gap, then permute K/NK."""
    sel = ~np.isnan(svec)
    r = np.full(len(svec), np.nan)
    r[sel] = resid(svec[sel], [SG[iu][sel], DE[iu][sel], NP_S[iu][sel], NP_P[iu][sel],
                              TY_S[iu][sel], TY_P[iu][sel]])
    rng = random.Random(2805)
    def stats(Km, NKm):
        kk, nn = Km[iu], NKm[iu]
        return (np.nanmean(r[sel & (kk > 0)]) - np.nanmean(r[sel & (kk == 0)]),
                np.nanmean(r[sel & (nn > 0)]) - np.nanmean(r[sel & (nn == 0)]),
                np.nanmean(r[sel & (K[iu] == 0) & (nn > 0)]) - np.nanmean(r[sel & (K[iu] == 0) & (nn == 0)]))
    obs = stats(K, NK)
    null = []
    for _ in range(10000):
        p = list(range(n)); rng.shuffle(p)
        null.append(stats(K[np.ix_(p, p)], NK[np.ix_(p, p)]))
    null = np.array(null)
    print(f"\n[{label}] residual similarity after gender, era, passages, genericness")
    for idx, name in enumerate(("co-star minus other", "Nolan co-cast minus other",
                                "Nolan co-cast minus other, never co-starred elsewhere")):
        p = (1 + np.sum(np.abs(null[:, idx]) >= abs(obs[idx]))) / (len(null) + 1)
        print(f"  {name:<56} {obs[idx]:+.4f}  p {p:.4f}")
        out[f"{label}: {name}"] = dict(obs=float(obs[idx]), p=float(p))
    # how much do the controls themselves matter?
    X = np.column_stack([np.ones(sel.sum()), SG[iu][sel], DE[iu][sel], NP_S[iu][sel], NP_P[iu][sel],
                         TY_S[iu][sel], TY_P[iu][sel], (K[iu][sel] > 0)])
    beta, *_ = np.linalg.lstsq(X, svec[sel], rcond=None)
    print(f"  OLS coefficients: same gender {beta[1]:+.4f}, era gap per year {beta[2]:+.5f}, co-star {beta[-1]:+.4f}  (R2 of controls shown by the drop below)")
    print(f"  raw co-star gap {np.nanmean(svec[sel & (K[iu] > 0)]) - np.nanmean(svec[sel & (K[iu] == 0)]):+.4f}")


controlled(s, "all terms")

# generic vocabulary only
films_per_term = defaultdict(set)
for r in rows:
    for w in set(T.tokens(r["text"])):
        films_per_term[w].add(r["film"])
specific = frozenset(w for w, f in films_per_term.items() if len(f) < 20)
rows_g = vectorise(load_rows(), drop_terms=specific)
other_g = defaultdict(list)
for r in rows_g:
    if not r["is_nolan"]:
        other_g[r["actor"]].append(r)
print(f"\ngeneric vocabulary: kept {len(films_per_term) - len(specific)} of {len(films_per_term)} terms")
Sg = np.full((n, n), np.nan)
for i, j in itertools.combinations(range(n), 2):
    a, b = actors[i], actors[j]
    st_titles = {t for t, _ in filmo[a] & filmo[b]}
    common_films = {r["film"] for r in other_g[a]} & {r["film"] for r in other_g[b]}
    pa = [r["v"] for r in other_g[a] if norm(r["film"]) not in st_titles and r["film"] not in common_films and r["v"]]
    pb = [r["v"] for r in other_g[b] if norm(r["film"]) not in st_titles and r["film"] not in common_films and r["v"]]
    if len(pa) >= 2 and len(pb) >= 2:
        Sg[i, j] = Sg[j, i] = T.cos(T.centroid(pa), T.centroid(pb))
sg = Sg[iu]
print(f"generic terms: co-stars {np.nanmean(sg[k > 0]):.4f}  others {np.nanmean(sg[k == 0]):.4f}")
controlled(sg, "generic terms only")
json.dump(out, open(os.path.join(ROOT, "investigations/link_homophily.json"), "w"), indent=1)

# ---------------- actor fixed effects (double centring) ----------------
# The cleanest dyadic test: remove each actor's average similarity to everyone (like correcting
# for degree), so only who-matches-whom is left: s_ij - mean_i - mean_j + grand mean.
def double_centre(M):
    M = M.copy()
    np.fill_diagonal(M, np.nan)
    rm = np.nanmean(M, axis=1)
    gm = np.nanmean(M)
    D = M - rm[:, None] - rm[None, :] + gm
    return D


print("\n=== actor fixed effects (double-centred similarity), QAP 10,000 ===")
for label, M in (("all terms", S), ("generic terms only", Sg)):
    D = double_centre(M)
    d = D[iu]
    sel = ~np.isnan(d)
    rng = random.Random(2805)
    def stats(Km, NKm):
        kk, nn = Km[iu], NKm[iu]
        return (np.mean(d[sel & (kk > 0)]) - np.mean(d[sel & (kk == 0)]),
                spearmanr(kk[sel], d[sel])[0],
                np.mean(d[sel & (nn > 0)]) - np.mean(d[sel & (nn == 0)]),
                np.mean(d[sel & (K[iu] == 0) & (nn > 0)]) - np.mean(d[sel & (K[iu] == 0) & (nn == 0)]))
    obs = stats(K, NK)
    null = []
    for _ in range(10000):
        p = list(range(n)); rng.shuffle(p)
        null.append(stats(K[np.ix_(p, p)], NK[np.ix_(p, p)]))
    null = np.array(null)
    for idx, name in enumerate(("co-star minus other", "Spearman(shared films, sim)",
                                "Nolan co-cast minus other",
                                "Nolan co-cast minus other, never co-starred elsewhere")):
        mu = null[:, idx].mean()
        p = (1 + np.sum(np.abs(null[:, idx] - mu) >= abs(obs[idx] - mu))) / (len(null) + 1)
        print(f"  [{label}] {name:<54} {obs[idx]:+.4f}  null {mu:+.4f}  p {p:.4f}")
        out[f"fixed effects, {label}: {name}"] = dict(obs=float(obs[idx]), null=float(mu), p=float(p))
    for lo, hi in ((0, 0), (1, 1), (2, 3), (4, 99)):
        s2 = sel & (K[iu] >= lo) & (K[iu] <= hi)
        print(f"     shared films {lo}-{hi}: pairs {int(s2.sum()):>5}  mean centred sim {np.mean(d[s2]):+.4f}")
json.dump(out, open(os.path.join(ROOT, "investigations/link_homophily.json"), "w"), indent=1)

# ---------------- exact removal of the 'mainstream' direction ----------------
# For unit vectors a, b and the unit corpus mean g:  cos(a,b) = t_a t_b + sqrt(1-t_a^2) sqrt(1-t_b^2) cos(a_perp, b_perp)
# with t = cos(., g). The first term is pure 'how mainstream is each actor'. cos(a_perp, b_perp)
# is the similarity of what is DISTINCTIVE about each type. Homophily in that part is the real test.
def perp_cos(ca, cb, g):
    def perp(c):
        t = T.cos(c, g)
        v = {w: x - t * g.get(w, 0.0) for w, x in c.items()}
        for w, x in g.items():
            if w not in v:
                v[w] = -t * x
        nm = sum(x * x for x in v.values()) ** 0.5 or 1.0
        return {w: x / nm for w, x in v.items()}
    return T.cos(perp(ca), perp(cb))


gn = {w: x / (sum(y * y for y in glob.values()) ** 0.5) for w, x in glob.items()}
Sp = np.full((n, n), np.nan)
for i, j in itertools.combinations(range(n), 2):
    a, b = actors[i], actors[j]
    st_titles = {t for t, _ in filmo[a] & filmo[b]}
    common_films = {r["film"] for r in other[a]} & {r["film"] for r in other[b]}
    pa = [r["v"] for r in other[a] if norm(r["film"]) not in st_titles and r["film"] not in common_films]
    pb = [r["v"] for r in other[b] if norm(r["film"]) not in st_titles and r["film"] not in common_films]
    Sp[i, j] = Sp[j, i] = perp_cos(T.centroid(pa), T.centroid(pb), gn)
sp = Sp[iu]
print(f"\n=== distinctive part of each type (mainstream direction removed) ===")
print(f"mean: co-stars {sp[k > 0].mean():+.4f}  others {sp[k == 0].mean():+.4f}")
for label, M in (("raw", Sp), ("double-centred", double_centre(Sp))):
    d = M[iu]
    rng = random.Random(2805)
    def stats(Km, NKm):
        kk, nn = Km[iu], NKm[iu]
        return (d[kk > 0].mean() - d[kk == 0].mean(), d[nn > 0].mean() - d[nn == 0].mean(),
                d[(K[iu] == 0) & (nn > 0)].mean() - d[(K[iu] == 0) & (nn == 0)].mean())
    obs = stats(K, NK)
    null = np.array([stats(K[np.ix_(p, p)], NK[np.ix_(p, p)])
                     for p in (rng.sample(range(n), n) for _ in range(10000))])
    for idx, name in enumerate(("co-star minus other", "Nolan co-cast minus other",
                                "Nolan co-cast minus other, never co-starred elsewhere")):
        mu = null[:, idx].mean()
        p = (1 + np.sum(np.abs(null[:, idx] - mu) >= abs(obs[idx] - mu))) / (len(null) + 1)
        print(f"  [{label}] {name:<54} {obs[idx]:+.4f}  null {mu:+.4f}  p {p:.4f}")
        out[f"distinctive, {label}: {name}"] = dict(obs=float(obs[idx]), null=float(mu), p=float(p))
for lo, hi in ((0, 0), (1, 1), (2, 3), (4, 99)):
    s2 = (k >= lo) & (k <= hi)
    print(f"     shared films {lo}-{hi}: pairs {int(s2.sum()):>5}  mean distinctive sim {sp[s2].mean():+.4f}")
json.dump(out, open(os.path.join(ROOT, "investigations/link_homophily.json"), "w"), indent=1)
