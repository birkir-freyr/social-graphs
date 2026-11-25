# Bugs and errors found, and how they were fixed

A list of what was wrong in the code, the data or the paper, what was changed, and where to check it.
Every fix below is in the repo. Results that changed are noted; the rest left the numbers the same.

## Code

| # | File | What was wrong | Fix | Effect on results |
|---|---|---|---|---|
| 1 | `within_nolan.py` (`char_tokens`) | Characters were matched on *any* name token, so different characters that share a first name merged ('Robert Fischer, Jr.' and 'J. Robert Oppenheimer'). Ducard and Ra's al Ghul (the same character) did not match. | Use only the last name token of each alias; add `jr` to the title list; add an alias map `ducard -> ghul`. | More distinct characters counted correctly; `within_nolan.csv/json` regenerated. |
| 2 | `investigations/film_confound.py` | The same-film placebo could pick a "co-star" who plays the *same character* (young and adult Murph in *Interstellar* share one passage). | Exclude co-stars whose character shares a surname token or whose passage is identical. | Placebo diff +0.0008 (p 0.80). Conclusion unchanged. |
| 3 | `investigations/selection_test.py` | The rank test compared the cast actor's type with other actors' types built under a different rule, and types of different sizes are biased: the rank correlates with the number of earlier roles (rho 0.66), because a centroid of many passages sits near the corpus mean. | Same rule for every actor, and equal-size types (3 most recent earlier roles) in `selection_fixed_size.py` and `selection_placebo.py`. `selection_test.py` is kept but marked superseded. | Rank vs number of roles drops to rho 0.02. The old claim that Nolan picks actors "as typical as other directors" was dropped. |
| 4 | `investigations/link_homophily.py` | Co-stars looked similar in type, but this was the same size artifact as #3 (prolific actors co-star more). | Decompose into a mainstream part and a distinctive part. | Distinctive part shows no homophily (p 0.25). Not a finding; reported as such. |
| 5 | `investigations/sequel_control.py` | Surname matching flagged two reprises that are different characters (Affleck's Toms and McConaughey's Coopers in *Interstellar*). | Hand-checked list `NOT_REPRISE`. | 16 reprises remain. |
| 6 | `investigations/explore_film_vocab.py` | Wrong relative path; failed when run fresh. | Path fixed. | None. |
| 7 | `check_descriptors.py` | Running it overwrote the committed `typecast_results.csv`. | Runs from a scratch directory (commit 7062e7e). | None. |
| 8 | `investigations/common.py` | `priors_for` handled roles with no parsed year differently from `director_test.py`. | Aligned with `director_test.py`. | None. |
| 9 | `director_test.py` | The z-score treated Nolan's 82 roles as independent, but they come from 55 actors. | Added an actor-clustered sign-flip comparison (one number per actor). | Reported alongside the old z in `director_test.json`. |

## Data

| # | What was wrong | Fix |
|---|---|---|
| 10 | Wrong Wikipedia article: *Terrified* matched to *Seven* (1995). | Found by reading passages; affected roles dropped in `film_confound.py` (D). No change to results. |
| 11 | Passages describing someone else: American Pie's 'Tom Myers' passage is about Kevin Myers; the Ra's al Ghul passage mixes Watanabe's decoy with Neeson. | `surname_contamination.py` drops 14 such roles: +0.024, result holds. |

## Paper text

| # | What was wrong | Fix |
|---|---|---|
| 12 | Fig. caption said Nolan was the only director outside the confidence band. Four small directors lie below it (z -2.1 to -2.9). | Caption rewritten; states 4 below against 2.3 expected. |
| 13 | Count of Nolan appearances with an earlier credit was 625; that counted earlier *Nolan* films too. | 618 of 878 (70%) with an earlier credit in another director's film. Caught by Birkir. |
| 14 | "A third of role pairs share no weighted term" was false (1.2% are exactly zero; median cosine 0.009). | Removed. |
| 15 | "His films are also Caine's" was false for *Memento*. | "four of five". |
| 16 | A table was described as using a different network from the one it was computed on. | Description corrected. |
| 17 | Overclaims ("unlike any", "nowhere else", "no other film"). | Toned down. |
| 18 | Zuckerman et al. reference had the wrong end page (1074). | 1018-1073, checked on Crossref. |
| 19 | Main claim: the first draft said Nolan casts actors against type. The same-film placebo showed a co-star's role departs just as far, so the effect belongs to the films. | Main claim, abstract and title changed. |
| 20 | Methods said the symmetric leave-one-out scoring gave false positives in 12% of null runs. That came from only 20 synthetic runs. | Rerun with 200 runs (`check_leaveoneout.py --reps 200`): 4% at three earlier roles, 3-8% at four to eight, close to the nominal 5%. Text corrected. |
| 21 | "With every passage cut to the same length the effect remains" hid how much it shrinks. | Numbers added: +0.006 to +0.014 at 40-120 words (p 0.04 at 40, p <= 0.005 from 60), so length explains roughly half of the effect. Also named in the Discussion's limits. |
| 22 | "Four lie below the band, against 2.3 expected": 2.3 is the expected count outside a two-sided band, not below it. | 1.2 expected below. |
| 23 | "All p > 0.2" for regulars vs one-timers; the smallest is 0.199. | "smallest p = 0.20". |
| 24 | Co-star homophily was explained with "this is because", but the gap survives actor fixed effects and only disappears in the distinctive (non-mainstream) component. | Stated as such. |
| 25 | Discussion said Nolan moves actors away from their type "in the literature's sense", but that literature defines type by genre, which was not tested. | Softened; genre test named as future work. |
| 26 | Other directors: +0.004 in the text vs about 0.010 in Fig. 3a. Different subsets (all roles vs the 103 with a co-star). | Both numbers given with their subsets. |
| 27 | Smaller wording: 878 counted before the credit filter; 77 vs 78 film pairs; two passage-length medians from different subsets; one-sided era test; "or 0.04" for an alternative specification removed. | Each explained in the text. |
| 28 | Validation ratings were in a per-person column layout and the folder was not in the repo. | One `rating` column; `validation/` committed. |
| 29 | LaTeX layout: double periods after Methods headings ("Masking.."), acknowledgements cut off at the bottom of page 5, gap on page 1. | Trailing periods removed; `\newpage` before end matter; `\Parasplit` mid-paragraph. |

## How to check

Rerun the scripts from `Final project` (`python3 investigations/<script>.py`). Each `*.out` file holds the
output the paper's numbers come from; `investigations/README.md` maps each number to its script.
