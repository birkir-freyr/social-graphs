# AI methods

We used an AI coding assistant (Claude, by Anthropic, through Claude Code) throughout the project, as the course allows. This file lists every place a model touched our results and how we checked it.

## How we worked with it

We set the research question, chose the data, and made the decisions about what to analyse, what to believe and what to report. The model implemented code, ran analyses we asked for, and drafted text. We also asked it to argue against our own result: it proposed checks that could break the main finding, and we chose which to run and how to report them. For the paper, we told the model what each section should say and how; it drafted, and we reviewed every draft, rejected or rewrote what was wrong, and approved the final wording ourselves.

## Where the model touched the results, and how we checked it

| Where | What the model did | How we checked it |
|---|---|---|
| Data collection (TMDB, IMDb, Wikipedia) | Wrote the download and matching code | We read the saved records for films and actors we know. `check_data.py` counts duplicates, impossible years and shared passages. We recounted the extended-network numbers from the raw CSVs and corrected one in the paper (618 appearances, not 625). |
| Casting network | Wrote the graph and plotting code | We recomputed counts and betweenness from the raw CSV. Checking by hand exposed a voice-only credit (Caine in *Dunkirk*), which led us to drop voice, uncredited and archive credits. |
| Character text and masking | Wrote the extraction and masking code | We read passages. That exposed errors the code missed: a wrong Wikipedia article (*Terrified* matched to *Seven*), a passage about a character's brother, and two characters sharing a surname. We report them and rerun the analyses without the affected roles. |
| Statistics | Implemented the leave-one-out scoring, the actor-clustered sign-flip test and the director comparison | We tested the scoring on synthetic data with no effect, which exposed a bias that we then removed (`check_leaveoneout.py`). Every number in the paper comes from a script in the repo. |
| Follow-up checks | Proposed and implemented the same-film placebo, the selection test, the degree-preserving null, the era test, the network–text tests and the reprised-character control (`investigations/`) | We decided which checks to run and what they meant. When the placebo showed the effect belonged to the films, we changed the paper's main claim. One of the model's own tests was biased by type size, and a later check caught it; we report the corrected version. |
| Figures | Wrote the plotting code | We rejected designs until the figures showed what we wanted. We checked every link and label in Fig. 1 against the raw data (`investigations/verify_fig1.py`). |
| Writing | Drafted text from our instructions, including the abstract and captions | We reviewed every draft and had every number checked against script output. This caught false statements: a caption claiming Nolan was the only director outside the confidence band (four others lie below it), and a table described as using a different network. We checked all references against Crossref, PubMed and the ACL Anthology. |
| Validation sample | Built the rating sheet and the analysis script, and produced trial ratings | We rated the 24 pairs ourselves, once each, without seeing scores or pair types. We discarded the model's trial ratings; the paper uses only our own. |

## What we learned

The model was fast and confident, including when it was wrong. Every substantive error, in the data or in the text, was found by reading the underlying passages or recomputing a number from scratch, not by asking the model whether its output was correct.
