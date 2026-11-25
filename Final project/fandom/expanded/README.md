# Additional character descriptions and dialogue

The expanded Fandom dataset has **367 usable descriptions**, including 102 of the 142 Nolan credits and 265 of the 2,497 credits for other directors. It covers 82 actors and 259 films. The search prioritized earlier roles for actors near the paper’s three-role threshold and Nolan credits whose existing pages were short or combined multiple performances. It yielded 47 additional usable credits across 26 actors and 36 films. [Complete expanded dataset](passages.csv) · [Manifest of additions](sources.csv)

| Coverage | Original Fandom collection | Expanded |
|---|---:|---:|
| Nolan descriptions | 97 | 102 |
| Other-director descriptions | 223 | 265 |
| Nolan roles eligible for the same-film comparison | 43 | 52 |
| Actors in that comparison | 21 | 27 |

Five additions describe Nolan roles. Three nonoverlapping passages describe the child, adult and elderly Murph in *Interstellar*. Another describes Casey Affleck’s adult Tom Cooper. In *Memento*, Sammy Jankis’s introduction fell below the word threshold, but his biography has enough character-specific prose. All additions use the original masking and 25-word threshold. Their manifests identify the film, performer, wiki, revision, paragraph indices and extract hash. Source text is attributed to the linked Fandom article contributors and was cleaned and masked under CC BY-SA. [Murphy Cooper](https://interstellarfilm.fandom.com/wiki/Murphy_Cooper) · [Sammy Jankis](https://chrisnolan.fandom.com/wiki/Sammy_Jankis) · [Community licenses](wiki_licenses.json)

## What changed in the casting comparison

Each actor’s Nolan role and eligible co-stars from the same film were compared with the same earlier roles. Negative values mean the actor’s own character was closer to their earlier work. Intervals use an actor-cluster bootstrap and the two-sided tests use actor-cluster sign flips.

| Measure | Own minus co-star on 52 roles | 95% interval | *p* |
|---|---:|---:|---:|
| TF–IDF | −0.0043 | −0.0198 to +0.0085 | 0.584 |
| Week 7 MiniLM | −0.0326 | −0.0644 to −0.0053 | 0.035 |

Several new credits describe reprises. Nine Tony Stark appearances and six Peter Parker appearances come from film-specific sections of two character articles. Counting only the earliest earlier credit per actor and source article retained all 52 targets and gave −0.0041 for TF–IDF (*p* = 0.603) and −0.0307 for MiniLM (*p* = 0.047). This check limits repeated source articles. The corpus still favors franchise roles and has much greater coverage of Nolan credits (71.8%) than other-director credits (10.6%). The 21-item reader worksheet still applies to its original examples. [Results and newly eligible roles](comparison.json) · [Original reader worksheet](../blind_character_comparisons.md)

## A second source for how characters speak

Cornell’s Movie-Dialogs Corpus identifies speakers by film and character. We matched titles and release years to the project’s roster, then matched speaker names and reviewed ambiguities such as Michael versus Don Corleone. The index contains 110 matched credits. **109 have at least 25 words** of dialogue across 80 films and 47 actors. Of those, **64** lack a usable expanded Fandom description. The speaker IDs link directly to the Cornell tables. The lines come from screenplay drafts and can differ from what the actors say in the released films. [Speaker index with line and word counts](cornell_speakers.csv) · [Cornell corpus and citation](https://www.cs.cornell.edu/~cristian/Cornell_Movie-Dialogs_Corpus.html)

The 109 credits include seven roles in *Memento* and ten in *Insomnia*. Only Al Pacino and Robin Williams also have three earlier dialogue roles and an eligible co-star in the same Nolan film. The dialogue is therefore most useful for reading examples and comparing how a character speaks with how fans describe them. It has limited coverage for estimating Nolan-wide casting patterns. [Cornell dataset documentation](https://convokit.cornell.edu/documentation/movie.html)

## Other passages found in the project archive

The older Fandom archive links 61 distinct credits on this study’s roster to character pages. All 61 already have usable Fandom descriptions. The separate role archive yielded **157 candidate passages** for credits where both the expanded Fandom collection and the paper’s original Wikipedia dataset had fewer than 25 masked words. Of these, 154 come from the CMU Movie Summary Corpus and three use Wikipedia’s cast and plot sections. Examples include Morgan Freeman as Hoke Colburn in *Driving Miss Daisy* and Josh Hartnett as Ernest Lawrence in *Oppenheimer*. Eleven of the 157 also have at least 25 words of Cornell dialogue. The other 146 fill a gap across all three existing datasets. [Supplemental passages and source locations](archived_passages.csv)

The table requires a matching actor, film title and release year, a character name that matches the source label, and at least 25 words after the paper’s name masking. For plot sentences the extraction also checks that a credited name appears in the sentence. Each row gives the source version, the location of each excerpt, the original text and the masked text. These are candidates for human review because a sentence mentioning a character can describe someone else’s actions. The reported Fandom comparison uses the 367 Fandom descriptions. The CMU passages are extracts from Wikipedia’s November 2012 snapshot, compiled by David Bamman, Brendan O’Connor and Noah A. Smith. Text is credited to the source article contributors under the applicable Attribution-ShareAlike license. [CMU Movie Summary Corpus and attribution](https://www.cs.cmu.edu/~ark/personas/)

## Reproduction

From the `Final project` directory, install the tested dependencies with `python3 -m pip install -r requirements-project.txt`. The build command verifies the selected Fandom revisions. Add `--offline` to use cached responses. The comparison uses the paper’s existing scoring code and the pinned Week 7 encoder. Supply `--model-dir /path/to/model` for offline inference.

```sh
python3 fandom/expanded/build.py
python3 fandom/expanded/compare.py
python3 fandom/expanded/cornell.py data/nolan/raw/cornell-dialogs --output-text data/nolan/raw/cornell-dialogs/matched_dialogue.csv
```

The local Cornell data directory holds the three original tables and the joined dialogue. The script checks the hashes of all three inputs. To reproduce the index elsewhere, place `movie_titles_metadata.txt`, `movie_characters_metadata.txt` and `movie_lines.txt` from the pinned mirror in that directory. The CSV index can also be used independently of the local cache. [Pinned Cornell data mirror](https://huggingface.co/datasets/spawn99/CornellMovieDialogCorpus/tree/2bba5d7a7c57f8fdf2c65bd6c068d68e71a10af6)

The supplemental passages are included as a standalone CSV. To rebuild that table from the local role archive, run `python3 fandom/expanded/archived_passages.py data/nolan/character_descriptions.jsonl`. [Export script](archived_passages.py)
