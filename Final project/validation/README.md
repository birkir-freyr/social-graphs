# Validation sample

Checks whether the text similarity score tracks what a reader would call "the same kind of character"
(paper section "Human ratings do not follow the measure").

| File | What it is |
|---|---|
| `make_sheet.py` | Draws the 24 pairs: 18 within-actor pairs (6 per cosine tercile), 5 same-film pairs of different characters, 1 case pair (Heath Ledger's Joker vs Ned Kelly). |
| `validation_sheet.md` | What we read: the two masked passages of each pair and the 1-5 scale. |
| `validation_key.csv` | Cosine and pair type of each pair, kept hidden while rating. |
| `validation_ratings.csv` | Our rating of each pair, rated once, without seeing the key. |
| `analyse_ratings.py` | Spearman between cosine and rating (permutation p) and mean rating per pair type. |
| `validation_results.json` | Output of `analyse_ratings.py`; the numbers in the paper. |

Run from `Final project`:

```bash
python3 validation/analyse_ratings.py
```

`make_sheet.py` rebuilds the sheet and key and never overwrites existing ratings.
