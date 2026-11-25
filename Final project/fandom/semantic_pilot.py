"""Week 7 embedding pilot. Run from Final project with python3 fandom/semantic_pilot.py.

Supply --model-dir for an offline copy of the pinned Hugging Face model.
The review sheet contains no model scores. Its key is in the results JSON.
"""
import argparse
import csv
import json
import random
import re
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import torch
from scipy.stats import rankdata
from torch.nn.functional import normalize
from transformers import AutoModel, AutoTokenizer

from analyze import HERE, ROOT, RESULTS, estimate
from common import T, load_rows, vectorise
from film_confound import placebo, scored_roles
import within_nolan as W

SEED = 2805
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def credit(row):
    return row["actor"], row["film"], row["character"]


def encode(texts, model_dir):
    location = model_dir or MODEL
    options = {"local_files_only": True} if model_dir else {"revision": REVISION}
    tokenizer = AutoTokenizer.from_pretrained(location, **options)
    model = AutoModel.from_pretrained(location, **options).eval()
    torch.set_num_threads(4)
    texts = list(dict.fromkeys(texts))
    owners, chunks = [], []
    for owner, text in enumerate(texts):
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + 180, len(words))
            while True:
                chunk = " ".join(words[start:end])
                count = len(tokenizer.encode(chunk, add_special_tokens=False, verbose=False))
                if count <= 254:
                    break
                if end == start + 1:
                    raise ValueError(f"A word in document {owner} exceeds the tokenizer budget")
                end = start + max(1, int((end - start) * 254 / count) - 1)
            chunks.append(chunk)
            owners.append(owner)
            start = end

    vectors = np.zeros((len(texts), 384), dtype=np.float64)
    with torch.inference_mode():
        for start in range(0, len(chunks), 16):
            batch = tokenizer(chunks[start:start+16], padding=True, return_tensors="pt")
            if batch.input_ids.shape[1] > 256:
                raise ValueError("Chunk exceeds the course encoder limit")
            hidden = model(**batch).last_hidden_state
            mask = batch.attention_mask.unsqueeze(-1)
            means = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
            np.add.at(vectors, owners[start:start+len(means)], normalize(means).numpy())
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(vectors).all():
        raise ValueError("Empty or invalid passage vector")
    return dict(zip(texts, vectors)), len(chunks)


def rating_agreement(pairs):
    """Fixed 18-pair primary benchmark and the paper's 23-pair secondary benchmark."""
    result = {}
    for label, sample in (("within_actor", [p for p in pairs if p["kind"] == "within_actor"]),
                          ("all_except_case", [p for p in pairs if p["kind"] != "case"])):
        y = rankdata([p["rating"] for p in sample])
        y = (y - y.mean()) / np.linalg.norm(y - y.mean())
        result[label] = {"n": len(y)}
        rng = np.random.default_rng(SEED)
        permuted = np.array([rng.permutation(y) for _ in range(10000)])
        for method in ("reported_tfidf", "tfidf", "minilm"):
            x = rankdata([p[method] for p in sample])
            x = (x - x.mean()) / np.linalg.norm(x - x.mean())
            rho = float(x @ y)
            hits = np.count_nonzero(np.abs(permuted @ x) >= abs(rho) - 1e-12)
            result[label][method] = {"spearman": rho, "permutation_p": (1 + int(hits)) / 10001}
    return result


def excerpt(text, limit=120):
    """Prefer a complete sentence for reading, hard-cap an unusually long first sentence."""
    words = text.split()
    if len(words) <= limit:
        return " ".join(words)
    head = " ".join(words[:limit])
    ends = list(re.finditer(r'[.!?]["”\']?(?=\s|$)', head))
    return head[:ends[-1].end()] if ends and len(head[:ends[-1].end()].split()) >= 40 else head


def review_sample(rows, metadata):
    """One random estimate-eligible target per actor. Sampling never reads a model score."""
    rng = random.Random(SEED)
    by_actor = defaultdict(list)
    by_film = defaultdict(list)
    for row in rows:
        by_actor[row["actor"]].append(row)
        by_film[row["film"], row["year"]].append(row)

    items = []
    for actor, roles in sorted(by_actor.items()):
        targets = []
        for target in roles:
            if not target["is_nolan"]:
                continue
            earlier = [r for r in roles if not r["is_nolan"] and r["year"] < target["year"]]
            if len(earlier) < 3:
                continue
            own = W.char_tokens(target["character"])
            mates = [m for m in by_film[target["film"], target["year"]]
                     if m["actor"] != actor and not own.intersection(W.char_tokens(m["character"]))
                     and m["text"] != target["text"]]
            # All three passages must come from separate articles.
            options = []
            for mate in mates:
                urls = {metadata[credit(r)]["source_url"] for r in (target, mate)}
                priors = [r for r in earlier if metadata[credit(r)]["source_url"] not in urls]
                if len(urls) == 2 and priors:
                    options.append((mate, priors))
            if options:
                targets.append((target, options))
        if targets:
            target, options = rng.choice(targets)
            mate, priors = rng.choice(options)
            candidates = [target, mate]
            rng.shuffle(candidates)
            items.append({"anchor": rng.choice(priors), "A": candidates[0], "B": candidates[1],
                          "own_side": "A" if candidates[0] is target else "B"})
    rng.shuffle(items)
    return items


def write_review(items, embeddings, sparse):
    lines = ["# Which character is more like the earlier role?", "",
             "Work independently. For each item read the reference, then compare A and B on the character’s goals, conduct and relationships. Both candidates appear in the same film. Record A, B, tie, or insufficient evidence, and a short reason. Leave the key closed until both reviewers finish.", "",
             "Names and film titles have been masked automatically. Each extract uses up to 120 words. Every item has one earlier reference role. The task measures agreement about character similarity.", ""]
    key = []
    for index, item in enumerate(items, 1):
        item_id = f"F{index:02}"
        texts = {side: excerpt(item[side]["text"]) for side in ("anchor", "A", "B")}
        lines += [f"## {item_id}", ""]
        for side, text in texts.items():
            label = "Earlier reference role" if side == "anchor" else side
            lines += [f"**{label}**", "", text, ""]
        lines += ["**Choice and reason**", "", "_____ ", ""]
        record = {"item": item_id, "own_side": item["own_side"],
                  "credits": {side: credit(item[side]) for side in texts}}
        for name, vecs in (("minilm", embeddings), ("tfidf", sparse)):
            anchor = vecs[texts["anchor"]]
            scores = {side: float(np.dot(anchor, vecs[texts[side]])) if name == "minilm"
                      else T.cos(anchor, vecs[texts[side]]) for side in ("A", "B")}
            record[name] = scores
        key.append(record)
    sheet = HERE / "blind_character_comparisons.md"
    content = "\n".join(lines)
    if sheet.exists() and sheet.read_text(encoding="utf-8") != content:
        raise ValueError(f"{sheet.name} has been edited. Preserve your responses before regenerating it.")
    if not sheet.exists():
        sheet.write_text(content, encoding="utf-8")
    return key


def paired_estimate(pairs):
    groups = defaultdict(list)
    for pair in pairs:
        groups[pair["actor"]].append(pair["diff"] - pair["placebo"])
    return estimate(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    fandom = load_rows(path=str(HERE / "passages.csv"))
    metadata = {credit(r): r for r in read_csv(HERE / "passages.csv") if r["status"] == "usable"}
    wiki = {credit(r): r for r in vectorise(load_rows())}
    ratings = {r["pair_id"]: int(r["rating"]) for r in read_csv(ROOT / "validation/validation_ratings.csv")}
    pairs = read_csv(ROOT / "validation/validation_key.csv")
    pair_keys = {p["pair_id"]: [tuple(p[f"{field}_{side}"] for field in ("actor", "film", "character"))
                                for side in ("a", "b")] for p in pairs}
    items = review_sample(fandom, metadata)
    clips = [excerpt(r["text"]) for r in fandom]
    texts = [r["text"] for r in fandom] + [wiki[k]["text"] for ks in pair_keys.values() for k in ks]
    dense, chunk_count = encode(texts + clips, args.model_dir)
    judged = []
    for p in pairs:
        left, right = (wiki[k] for k in pair_keys[p["pair_id"]])
        tfidf = T.cos(left["v"], right["v"])
        if abs(tfidf - float(p["cosine"])) > 0.000051:
            raise ValueError(f"TF-IDF baseline mismatch in {p['pair_id']}")
        judged.append({"pair_id": p["pair_id"], "kind": p["kind"], "rating": ratings[p["pair_id"]],
                       "reported_tfidf": float(p["cosine"]), "tfidf": tfidf,
                       "minilm": float(dense[left["text"]] @ dense[right["text"]])})

    for r in fandom:
        r["v"] = dict(enumerate(dense[r["text"]].tolist()))
    scored = scored_roles(fandom)
    paired = [s for s in placebo(fandom, scored) if s["is_nolan"]]
    # Sensitivity to the editorial community of each target and its co-stars.
    # Keep the same embeddings, priors and scoring. Restrict only the co-stars.
    def community(row):
        return urlparse(metadata[credit(row)]["source_url"]).hostname

    same_wiki = []
    for wiki_name in sorted({community(r) for r in fandom}):
        candidates = [r for r in fandom if r["is_nolan"] and community(r) == wiki_name]
        targets = [s for s in scored if s["is_nolan"] and community(s) == wiki_name]
        same_wiki.extend(placebo(candidates, targets))
    clip_vectors = T.tfidf_vectors([{"text": text} for text in clips])
    key = write_review(items, dense, dict(zip(clips, clip_vectors)))
    out = {"model": MODEL, "revision": REVISION, "versions": {p: version(p) for p in
           ("torch", "transformers", "numpy", "scipy")}, "unique_texts": len(dense), "chunks": chunk_count,
           "rated_wikipedia_pairs": judged, "agreement_with_readers": rating_agreement(judged),
           "rated_within_actor_pairs_available_in_fandom": sum(p["kind"] == "within_actor" and
           all(k in metadata for k in pair_keys[p["pair_id"]]) for p in pairs),
           "fandom_own_minus_costar": paired_estimate(paired),
           "exploratory_same_wiki_costars": paired_estimate(same_wiki), "fandom_review_key": key}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "semantic_pilot.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("agreement_with_readers", "fandom_own_minus_costar")}, indent=2))
    print(f"{len(items)} blinded Fandom comparisons")


if __name__ == "__main__":
    main()
