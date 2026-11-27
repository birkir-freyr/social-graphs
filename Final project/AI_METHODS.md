# AI methods

We used an AI coding assistant (Claude, by Anthropic, through Claude Code) throughout the project, as the course allows. This file lists every place it touched our results and how we checked it.

## How we worked with it

We set the research question, chose the data and the methods, and decided what to analyse, what to believe and what to report. We used the model as a fast collaborator: it wrote and extended code with us, ran analyses, and drafted text from our outlines. We also used it as a critic. We asked it to argue against our result and to review the code and the paper for bugs, and we checked the same things ourselves; we checked its suggestions and reviews before accepting them. We revised the drafted text ourselves.

## Where the model touched the results, and how we checked it

| Where | How the model helped | How we checked it |
|---|---|---|
| Data collection (TMDB, IMDb, Wikipedia) | Helped write the download and matching code | We read the saved records for films and actors we know. `check_data.py` counts duplicates, impossible years and shared passages. Recounting the extended-network numbers from the raw CSVs, we corrected one in the paper (618 appearances, not 625). |
| Casting network | Helped write the graph and plotting code | We recomputed counts and betweenness from the raw CSV. Checking by hand exposed a voice-only credit (Caine in *Dunkirk*), which led us to drop voice, uncredited and archive credits. |
| Character text and masking | Helped write the extraction and masking code | We read the passages, which exposed errors no automatic check caught: a wrong Wikipedia article (*Terrified* matched to *Seven*), a passage about a character's brother, and two characters sharing a surname. We report them and rerun the analyses without the affected roles. |
| Statistics | Helped implement the leave-one-out scoring, the actor-clustered sign-flip test and the director comparison | We tested the scoring on synthetic data with no effect, which exposed a bias that we then removed (`check_leaveoneout.py`). The numbers in the paper come from scripts in the repo. |
| Follow-up checks | Proposed and implemented robustness checks: the same-film placebo, the selection test, the degree-preserving null, the era test, the network–text tests, the reprised-character control and a sentence-embedding check (`investigations/`) | We reviewed each result and decided what it meant and what to report. When the placebo showed the effect belonged to the films, we changed the paper's main claim. One selection test was biased by type size; a later check caught it and we report the corrected version. |
| Figures | Helped write the plotting code | We iterated on the designs until the figures showed what we needed, and checked every link and label in Fig. 1 against the raw data (`investigations/verify_fig1.py`). |
| Writing | Drafted text from our outlines, including the abstract and captions | We revised the drafts and checked the numbers against script output. This caught false statements, for example a caption claiming Nolan was the only director outside the confidence band (four others lie below it) and a table described as using a different network. We checked the references against Crossref, PubMed and the ACL Anthology. |
| Validation sample | Helped build the rating sheet and the analysis script | We rated the 24 pairs ourselves, once each, without seeing scores or pair types. The cosine measure did not track our ratings (Spearman ρ = 0.04 within actors), which the paper reports as a limit. The paper uses only our ratings. |

## What we learned

The model was fast and confident, including when it was wrong. The errors were found by combining its bug reviews with our own: reading the underlying passages, recomputing numbers from scratch, and checking claims against script output. We did not rely on the model's word that its output was correct.
