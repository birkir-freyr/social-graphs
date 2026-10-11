"""Exercise 6.11: how sensitive are Marvel lookalikes to removing names?

Python 3.10+, NumPy 1.26.0, SciPy 1.13.1, scikit-learn 1.6.1.
Inputs are bundled; no model downloads or network access are required.
Run: python analysis/build_week6.py
"""
import csv
import gzip
import hashlib
import html
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'site/data'
TOKEN = re.compile(r'(?u)\b\w\w+\b')
TOP_N = 5


def load():
    with (DATA / 'week1_nodes.tsv').open(encoding='utf-8') as stream:
        roster = {r['node_id']: r for r in csv.DictReader(
            (line for line in stream if not line.startswith('#')),
            delimiter='\t', quoting=csv.QUOTE_NONE)}
    pages = {}
    with zipfile.ZipFile(DATA / 'marvel_pages.zip') as archive:
        for name in sorted(archive.namelist()):
            if name.endswith('.txt') and not name.endswith('README.txt'):
                pages[unquote(Path(name).stem)] = archive.read(name).decode('utf-8')
    assert set(pages) == set(roster) and len(pages) == 303
    return roster, pages


def weights(counts):
    """The course's unsmoothed TF-IDF; ubiquitous terms receive zero weight."""
    df = np.asarray((counts > 0).sum(axis=0)).ravel()
    lengths = np.asarray(counts.sum(axis=1)).ravel()
    tf = counts.multiply(np.divide(1., lengths, out=np.zeros_like(lengths, dtype=float), where=lengths > 0)[:, None])
    idf = np.log(counts.shape[0] / df)
    result = normalize(tf.multiply(idf), norm='l2').tocsr()
    result.eliminate_zeros()
    return result


def name_candidates(pages):
    """Course heuristic: alphabetic terms capitalized in >50% of uses.

    This is a type-level heuristic, not named entity recognition. It also
    removes some sentence-initial/common words and misses lowercase names.
    """
    seen, caps = Counter(), Counter()
    for text in pages.values():
        for word in re.findall(r'[A-Za-z]+', text):
            seen[word.lower()] += 1
            caps[word.lower()] += word[0].isupper()
    removed = {word for word in seen if caps[word] > seen[word] / 2}
    return removed, seen, caps


def nearest(matrix, names, n=TOP_N):
    scores = (matrix @ matrix.T).toarray()
    np.fill_diagonal(scores, -1)
    # Explicit, deterministic alphabetical tie-break, including zero matches.
    order = [sorted(range(len(names)), key=lambda j: (-scores[i, j], names[j]))[:n]
             for i in range(len(names))]
    return scores, order


def raw_excerpt(raw, match):
    if match is None:
        return None
    start, end = max(0, match.start() - 100), min(len(raw), match.end() + 160)
    return {'start': start, 'end': end, 'text': raw[start:end],
            'match_start': match.start() - start, 'match_end': match.end() - start}


def contributors(a, b, vocab, removed, excerpt, names, i, j):
    row = a.multiply(b)
    positions = sorted(range(row.nnz), key=lambda k: (-row.data[k], vocab[row.indices[k]]))[:5]
    total = float(row.sum())
    output = []
    for k in positions:
        term = str(vocab[row.indices[k]])
        output.append({'term': term, 'contribution': float(row.data[k]),
                       'share': float(row.data[k]) / total if total else 0,
                       'removed': term in removed,
                       'source_excerpt': excerpt(names[i], term),
                       'target_excerpt': excerpt(names[j], term)})
    return output


def standalone(result):
    """Readable exported figure showing Storm's nearest three in each view."""
    storm = next(n for n in result['nodes'] if n['id'] == 'Storm_(Marvel_Comics)')
    by_id = {n['id']: n for n in result['nodes']}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 520" role="img" aria-labelledby="title desc">',
           '<title id="title">Storm’s closest pages before and after filtering mostly capitalized terms</title>',
           '<desc id="desc">Two independently ranked cosine similarity lists. The filter changes vocabulary, so scores from the two spaces are not directly comparable.</desc>',
           '<rect width="1100" height="520" fill="#122c29"/>',
           '<text x="35" y="47" fill="#edf2e8" font-family="sans-serif" font-size="27">Who is Storm’s closest match?</text>']
    for column, mode in enumerate(['original', 'filtered']):
        x = 35 + 550 * column
        title = 'All terms kept' if mode == 'original' else 'Mostly capitalized terms removed'
        svg.append(f'<text x="{x}" y="102" fill="#a8c5b9" font-family="sans-serif" font-size="18">{title}</text>')
        for rank, item in enumerate(storm[mode][:3]):
            pair = result['pairs'][item['pair']][mode]
            terms = ', '.join(t['term'] for t in pair['terms'][:3])
            y = 155 + rank * 93
            svg += [f'<text x="{x}" y="{y}" fill="#edf2e8" font-family="sans-serif" font-size="18">{rank + 1}. {html.escape(by_id[item["target"]]["name"])}</text>',
                    f'<rect x="{x}" y="{y+14}" width="{item["cosine"] * 450:.2f}" height="9" fill="{"#fa784d" if mode == "original" else "#96bbae"}"/>',
                    f'<text x="{x}" y="{y+48}" fill="#a8c5b9" font-family="sans-serif" font-size="13">cosine {item["cosine"]:.3f} · {html.escape(terms)}</text>']
    svg += ['<text x="35" y="466" fill="#a8c5b9" font-family="sans-serif" font-size="14">Same 303 pages; same TF-IDF formula. One capitalization heuristic changes the vocabulary.</text>',
            '<text x="35" y="490" fill="#a8c5b9" font-family="sans-serif" font-size="13">Scores are within-view measurements, not a calibrated scale of character meaning.</text></svg>']
    (ROOT / 'site/assets/week6-lookalikes.svg').write_text('\n'.join(svg), encoding='utf-8')


def build():
    DATA.mkdir(parents=True, exist_ok=True)
    (ROOT / 'site/assets').mkdir(parents=True, exist_ok=True)
    roster, pages = load()
    names = sorted(pages)
    vectorizer = CountVectorizer()
    counts = vectorizer.fit_transform([pages[name] for name in names]).astype(float).tocsr()
    vocab = vectorizer.get_feature_names_out()
    removed, seen, caps = name_candidates(pages)
    keep = np.array([word not in removed for word in vocab])
    original = weights(counts)
    filtered = weights(counts[:, keep])
    filtered_vocab = vocab[keep]
    original_scores, original_order = nearest(original, names)
    filtered_scores, filtered_order = nearest(filtered, names)

    linked = set()
    with (DATA / 'week1_edges.tsv').open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('#') or not line.strip():
                continue
            a, b = line.strip().split('\t')
            linked.add(tuple(sorted((a, b))))

    selected_pairs = sorted({tuple(sorted((i, j))) for orders in [original_order, filtered_order]
                             for i, row in enumerate(orders) for j in row})
    pair_index = {pair: i for i, pair in enumerate(selected_pairs)}
    # Store each page/word passage once; pairs refer to this compact registry.
    first_matches = {}
    for name, raw in pages.items():
        first_matches[name] = {}
        for match in TOKEN.finditer(raw):
            first_matches[name].setdefault(match.group().lower(), match)
    excerpts, excerpt_ids = [], {}

    def excerpt(name, word):
        key = (name, word)
        if key not in excerpt_ids:
            span = raw_excerpt(pages[name], first_matches[name].get(word))
            assert span is not None, f'Missing source token: {key}'
            excerpt_ids[key] = len(excerpts)
            excerpts.append({'node': name, 'term': word, **span})
        return excerpt_ids[key]

    pairs = []
    for i, j in selected_pairs:
        pair = {'source': names[i], 'target': names[j], 'linked': (names[i], names[j]) in linked}
        for mode, matrix, terms_vocab, scores in [
                ('original', original, vocab, original_scores),
                ('filtered', filtered, filtered_vocab, filtered_scores)]:
            pair[mode] = {'cosine': float(scores[i, j]),
                          'terms': contributors(matrix[i], matrix[j], terms_vocab, removed, excerpt, names, i, j)}
        pairs.append(pair)

    nodes, csv_rows = [], []
    changed = 0
    retained = []
    links_in_lists = {'original': 0, 'filtered': 0}
    for i, name in enumerate(names):
        label = 'Phoenix Force' if name == 'Phoenix_Force' else roster[name]['name']
        node = {'id': name, 'name': label, 'url': roster[name]['url']}
        for mode, order, scores in [('original', original_order, original_scores),
                                     ('filtered', filtered_order, filtered_scores)]:
            node[mode] = []
            for rank, j in enumerate(order[i], 1):
                pair_id = pair_index[tuple(sorted((i, j)))]
                node[mode].append({'target': names[j], 'cosine': float(scores[i, j]), 'pair': pair_id})
                links_in_lists[mode] += pairs[pair_id]['linked']
                csv_rows.append({'source': name, 'mode': mode, 'rank': rank, 'target': names[j],
                                 'cosine': float(scores[i, j]), 'linked': pairs[pair_id]['linked']})
        node['changed_first'] = original_order[i][0] != filtered_order[i][0]
        node['retained_top5'] = len(set(original_order[i]) & set(filtered_order[i]))
        changed += node['changed_first']
        retained.append(node['retained_top5'])
        nodes.append(node)

    results = {'meta': {
        'exercise': '6.11', 'snapshot': '2026-08-26', 'documents': len(names), 'top_n': TOP_N,
        'hashes': {f: hashlib.sha256((DATA / f).read_bytes()).hexdigest()
                   for f in ['marvel_pages.zip', 'week1_nodes.tsv', 'week1_edges.tsv']},
        'versions': {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__},
        'token_pattern': TOKEN.pattern,
        'weighting': 'TF=count/retained document length; IDF=ln(N/DF); L2 normalize before cosine; no IDF smoothing or +1; no English stopword removal',
        'filter': 'Course heuristic: count [A-Za-z]+ occurrences in raw case-sensitive text; remove a term type if its first letter is uppercase in strictly more than half its uses; intersect this set with the CountVectorizer vocabulary',
        'vocabulary_original': len(vocab), 'vocabulary_filtered': len(filtered_vocab),
        'removed_features': int((~keep).sum()),
        'zero_vectors_original': int((np.diff(original.indptr) == 0).sum()),
        'zero_vectors_filtered': int((np.diff(filtered.indptr) == 0).sum()),
        'tie_break': 'alphabetical node_id; self excluded',
        'labels': 'Frozen roster display names except Phoenix_Force, corrected to Phoenix Force; its roster label incorrectly names Phoenix (Guardians of the Galaxy). IDs and URLs unchanged',
        'excerpts': 'Deduplicated first raw occurrence of each inspected page/term; pair terms reference array indices. Character offsets are zero-based Python Unicode-codepoint offsets; end is exclusive'},
        'summary': {'changed_first': changed, 'unchanged_first': len(names) - changed,
                    'mean_retained_top5': float(np.mean(retained)),
                    'retained_histogram': [retained.count(k) for k in range(6)],
                    'mean_linked_top5': {mode: value / len(names) for mode, value in links_in_lists.items()}},
        'nodes': nodes, 'pairs': pairs, 'excerpts': excerpts,
        'removed_terms': [{'term': str(word), 'uses': seen[word], 'capitalized_uses': caps[word],
                           'capitalized_fraction': caps[word] / seen[word]}
                          for word in vocab if word in removed]}
    payload = (json.dumps(results, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    (DATA / 'week6.json').write_bytes(payload)
    (DATA / 'week6.json.gz').write_bytes(gzip.compress(payload, mtime=0))
    with (DATA / 'week6-neighbors.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
        writer.writeheader(); writer.writerows(csv_rows)
    with (DATA / 'week6-removed-terms.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results['removed_terms'][0]))
        writer.writeheader(); writer.writerows(results['removed_terms'])
    standalone(results)
    print(json.dumps({'meta': results['meta'], 'summary': results['summary'],
                      'cases': [n for n in nodes if n['id'] in ['Storm_(Marvel_Comics)', 'Emma_Frost',
                                                                'Wolverine_(character)', 'Jean_Grey']]}, indent=2))


if __name__ == '__main__':
    build()
