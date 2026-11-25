# Follow-up analyses (`investigations/`)

These scripts test whether the role-similarity result is about the part or about the film, add the
network baselines, and produce the new Fig. 3. All reuse `typecast.py`'s vectoriser, cosine and
leave-one-out scoring, and `director_test.py`'s director table, so the numbers are the same
quantities as in the rest of the repo. Run them from this folder with `python3 <script>`
(scripts marked * need networkx/scipy/matplotlib/PyMuPDF; run those from `Final project`).

| Script | What it tests | Numbers in the paper |
|---|---|---|
| `common.py` | Shared loading, director attachment, scoring, actor-clustered sign-flip | - |
| `explore_film_vocab.py` | How lexically unusual Nolan passages are | median cosine to corpus 0.096 vs 0.124; Nolan-only words |
| `film_confound.py` | A: paper's test and Nolan-vs-other-directors (clustered); B: same-film placebo; C: film-specific vocabulary removed; D: wrong-article roles removed | +0.0234; +0.0165 (p 3e-4); placebo +0.0227 (diff +0.001, p 0.80); film foreignness +0.015 (p 0.002); vocabulary removed +0.011 (p 0.012) |
| `placebo_checks.py` | Placebo fairness: passage length, length-matched placebo, bootstrap CI | CI -0.005..+0.007; 60 words -0.001 |
| `selection_test.py` | Rank of the cast actor's type among all actors' types for the same passage. **Superseded**: types of different sizes bias the rank (see next row) | not used any more |
| `selection_fixed_size.py` | Shows the bias (rank vs number of earlier roles, rho 0.66) and reruns with equal-size types (3 or 5 roles) | rho 0.66 -> 0.02 (Methods) |
| `selection_placebo.py` | Equal-size ranking for the actor's own passage vs a same-film co-star's passage; regulars vs one-timers on the same measure | Nolan 0.52 vs 0.55 (p 0.21); other 0.58 vs 0.56 (p 0.48); 3+ regulars film fit 0.63 vs 0.51 (p 0.06; 0.04 at k=5) |
| `actor_signal.py` | Does role text identify its actor at all? | mean percentile 0.61 (not in paper) |
| `returning_placebo.py` | Returning actors' Nolan pairs vs co-star pairs from the same two films | 0.0123 vs 0.0118 (p 0.88) |
| `ledger_audit.py` | Term contributions for one role (default: Heath Ledger's Joker) | police, officers, kill, gang |
| `robustness.py` | Minimum earlier roles 3/5/8/12; reprised characters once | +0.027 at 8; +0.024 reprised once |
| `surname_contamination.py` | Roles whose passages describe a co-star with the same surname | 14 dropped -> +0.024 |
| `betweenness_null.py` * | Betweenness vs 200 degree-preserving rewired networks | Table 1 null z |
| `era_test.py` * | Shared cast vs gap in release years (permutation of years) | rho -0.47 (p 1e-4); -0.43 without Batman |
| `link_regulars.py` * | Network core vs one-timers: departure, co-star-corrected departure, rank; Spearman with betweenness | all p > 0.2; abs(rho) < 0.2 |
| `link_film_network.py` * | Mantel test: shared actors vs film text similarity (shared actors' passages left out), with/without Batman, partial on years | rho 0.05 (p 0.72); -0.11 without Batman |
| `link_homophily.py` * | Type similarity of co-stars outside Nolan (QAP), with gender/era/size controls and the mainstream decomposition | 0.23 vs 0.16 raw; distinctive part p 0.25 |
| `fig_role_or_film.py` * | New Fig. 3 (`figures/fig3_role_or_film.png`) with bootstrap intervals; panel b uses `selection_placebo.run(rows, 3)` | Fig. 3 |
| `verify_fig1.py` * | Checks every drawn link, dot and label of Fig. 1 against the raw CSV | 0 problems |

`*.out` files hold the last printed output of each script; `*.json` hold machine-readable results.
| `sequel_control.py` | Positive control: reprised characters vs same-film co-star (departure, rank, direct cosine) | -0.007 (p 0.67); direct +0.026 (p 0.07) |
