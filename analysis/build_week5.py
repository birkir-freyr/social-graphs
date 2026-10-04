"""Week 5 / exercise 5.9: longest shared token runs in the Marvel corpus.

Python 3.10+, NetworkX 3.4.2 and NumPy 1.26.0. All inputs are bundled;
no NLP models or network access needed. Run: python3 analysis/build_week5.py
"""
import csv
import hashlib
import html
import itertools
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'site/data'
TOKEN = re.compile(r"\w+(?:[-'’]\w+)*", re.UNICODE)
MINIMUM = 8


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


def longest_runs(token_lists, minimum=MINIMUM):
    """Exact exhaustive search for maximal cross-document runs >= minimum.

    The inverted index supplies every possible starting match. If the previous
    tokens match, this alignment has already been visited at an earlier start.
    Extending each remaining seed finds a maximal run, including repeated
    occurrences. Ties prefer the earliest (source, target) token offsets.
    """
    index = defaultdict(list)
    for document, tokens in enumerate(token_lists):
        for offset in range(len(tokens) - minimum + 1):
            index[tuple(tokens[offset:offset + minimum])].append((document, offset))
    best = {}
    for hits in index.values():
        if len(hits) < 2:
            continue
        for (a, i), (b, j) in itertools.combinations(hits, 2):
            if a == b:
                continue
            ta, tb = token_lists[a], token_lists[b]
            if i and j and ta[i - 1] == tb[j - 1]:
                continue
            length = minimum
            while i + length < len(ta) and j + length < len(tb) and ta[i + length] == tb[j + length]:
                length += 1
            old = best.get((a, b))
            if old is None or (-length, i, j) < (-old[0], old[1], old[2]):
                best[a, b] = (length, i, j)
    return best


def counts(names, edges, threshold):
    graph = nx.Graph()
    graph.add_nodes_from(names)
    graph.add_edges_from((e['source'], e['target']) for e in edges if e['length'] >= threshold)
    groups = sorted(nx.connected_components(graph), key=lambda g: (-len(g), min(g)))
    return {'threshold': threshold, 'pairs': graph.number_of_edges(),
            'active_pages': len(graph) - nx.number_of_isolates(graph),
            'largest_group': len(groups[0]),
            'groups_with_links': sum(len(g) > 1 for g in groups)}


def positions(names, edges):
    """Fixed layout of the >=20 graph, arranged by its connected groups."""
    graph = nx.Graph()
    graph.add_edges_from((e['source'], e['target']) for e in edges)
    groups = sorted(nx.connected_components(graph), key=lambda g: (-len(g), min(g)))
    output = {}
    columns = 4
    rows = (len(groups) + columns - 1) // columns
    for group_index, group in enumerate(groups):
        subgraph = nx.Graph()
        subgraph.add_nodes_from(sorted(group))
        subgraph.add_edges_from(sorted((min(a, b), max(a, b)) for a, b in graph.subgraph(group).edges()))
        layout = nx.spring_layout(subgraph, seed=509, weight=None, iterations=180)
        cx = (group_index % columns + 0.5) / columns
        cy = (group_index // columns + 0.5) / rows
        for name, point in layout.items():
            output[name] = {'x': round(cx + float(point[0]) * .09, 6),
                            'y': round(cy + float(point[1]) * .35 / rows, 6),
                            'group': group_index}
    return output


def raw_span(raw, matches, offset, length):
    start, end = matches[offset].start(), matches[offset + length - 1].end()
    return {'start': start, 'end': end, 'text': raw[start:end]}


def static_figure(nodes, edges, stats):
    """An accessible, standalone SVG of the same threshold-30 network."""
    name_map = {n['id']: n for n in nodes}
    selected = [e for e in edges if e['length'] >= 30]
    active = {n for e in selected for n in (e['source'], e['target'])}
    colors = ['#fa784d', '#96bbae', '#bea7e4', '#e7cb85', '#83bbd1']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 780" role="img" aria-labelledby="title desc">',
           '<title id="title">Marvel pages sharing at least 30 consecutive tokens</title>',
           f'<desc id="desc">{len(selected)} undirected pairs among {len(active)} active pages. Links mean shared normalized text, not hyperlinks or proven copying.</desc>',
           '<rect width="1100" height="780" fill="#122c29"/>',
           '<text x="36" y="45" fill="#edf2e8" font-family="sans-serif" font-size="25">Same universe. Same sentences.</text>',
           f'<text x="36" y="74" fill="#a8c5b9" font-family="sans-serif" font-size="14">30-token minimum · {len(selected)} shared-text pairs · {len(active)} of 303 pages</text>']
    xy = lambda n: (name_map[n]['x'] * 1020 + 40, name_map[n]['y'] * 580 + 115)
    for edge in selected:
        a, b = xy(edge['source']), xy(edge['target'])
        svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#78968a" stroke-width="{1 + edge["length"] / 70}" opacity=".7"/>')
    occupied = []
    for name in sorted(active, key=lambda name: (-max(e['length'] for e in selected if name in (e['source'], e['target'])), name)):
        n = name_map[name]
        x, y = xy(name)
        color = colors[n['group'] % len(colors)]
        svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"><title>{html.escape(n["name"])}</title></circle>')
        label = n['name'] if len(n['name']) <= 22 else n['name'][:21] + '…'
        width = len(label) * 6
        left = x + 9 if x + 9 + width < 1060 else x - 9 - width
        box = (left, y - 9, left + width, y + 6)
        if not any(box[0] < old[2] and box[2] > old[0] and box[1] < old[3] and box[3] > old[1] for old in occupied):
            occupied.append(box)
            svg.append(f'<text x="{left}" y="{y + 4}" fill="#edf2e8" font-family="sans-serif" font-size="11">{html.escape(label)}</text>')
    svg.append('<text x="36" y="748" fill="#a8c5b9" font-family="sans-serif" font-size="13">Fixed layout from the 20-token graph. Colors identify its connected groups; distance has no meaning.</text></svg>')
    (ROOT / 'site/assets/week5-shared-text.svg').write_text('\n'.join(svg), encoding='utf-8')


def build():
    (ROOT / 'site/assets').mkdir(parents=True, exist_ok=True)
    roster, pages = load()
    names = sorted(pages)
    matches = [[*TOKEN.finditer(pages[name])] for name in names]
    tokens = [[m.group().lower() for m in document] for document in matches]
    best = longest_runs(tokens)
    boilerplate = tuple('in american comic books published by marvel comics'.split())
    boilerplate_pages = sum(any(tuple(document[i:i + 8]) == boilerplate
                               for i in range(len(document) - 7)) for document in tokens)
    all_edges = []
    browser_edges = []
    for (a, b), (length, i, j) in best.items():
        edge = {'source': names[a], 'target': names[b], 'length': length,
                'source_token': i, 'target_token': j}
        all_edges.append(edge)
        if length >= 20:
            span_a = raw_span(pages[names[a]], matches[a], i, length)
            span_b = raw_span(pages[names[b]], matches[b], j, length)
            assert [m.group().lower() for m in TOKEN.finditer(span_a['text'])] == tokens[b][j:j + length]
            assert [m.group().lower() for m in TOKEN.finditer(span_b['text'])] == tokens[a][i:i + length]
            browser_edges.append({**edge, 'source_excerpt': span_a, 'target_excerpt': span_b,
                                  'raw_equal': span_a['text'] == span_b['text']})
    all_edges.sort(key=lambda e: (-e['length'], e['source'], e['target']))
    browser_edges.sort(key=lambda e: (-e['length'], e['source'], e['target']))
    thresholds = [counts(names, all_edges, threshold) for threshold in [8, 12, 20, 25, 30, 40, 50, 75, 100, 125, 150]]
    layout = positions(names, browser_edges)
    nodes = [{'id': name, 'name': roster[name]['name'], 'url': roster[name]['url'],
              'tokens': len(tokens[i]), **layout[name]} for i, name in enumerate(names) if name in layout]
    examples = [('Mayday_Parker', 'Spider-Woman', 'plot'),
                ('Cyclops_(Marvel_Comics)', 'Jean_Grey', 'editorial history'),
                ('Spitfire_(character)', 'Union_Jack_(Joseph_Chapman)', 'bibliography'),
                ('Spider-Woman', 'Spider-Woman_(Jessica_Drew)', 'quotation')]
    case_studies = []
    for source, target, category in examples:
        edge_index = next(i for i, e in enumerate(browser_edges) if {source, target} == {e['source'], e['target']})
        case_studies.append({'edge_index': edge_index, 'category': category})
    results = {'meta': {'exercise': '5.9', 'snapshot': '2026-08-26',
                        'hashes': {file: hashlib.sha256((DATA / file).read_bytes()).hexdigest()
                                   for file in ['marvel_pages.zip', 'week1_nodes.tsv']},
                        'documents': len(names), 'tokens': sum(map(len, tokens)),
                        'possible_pairs': len(names) * (len(names) - 1) // 2,
                        'token_pattern': TOKEN.pattern, 'normalization': 'lowercase only; keep numbers, stopwords, internal apostrophes and hyphens; punctuation and whitespace delimit tokens',
                        'minimum_indexed_run': MINIMUM, 'browser_minimum': 20,
                        'layout_seed': 509, 'networkx': nx.__version__},
               'boilerplate': {'phrase': ' '.join(boilerplate), 'pages': boilerplate_pages,
                               'pairs': boilerplate_pages * (boilerplate_pages - 1) // 2},
               'thresholds': thresholds, 'nodes': nodes, 'edges': browser_edges, 'case_studies': case_studies}
    (DATA / 'week5.json').write_text(json.dumps(results, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    with (DATA / 'week5-pairs.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['source', 'target', 'length', 'source_token', 'target_token'])
        writer.writeheader()
        writer.writerows(all_edges)
    with (DATA / 'week5-thresholds.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(thresholds[0]))
        writer.writeheader()
        writer.writerows(thresholds)
    static_figure(nodes, browser_edges, thresholds)
    print(json.dumps({'meta': results['meta'], 'thresholds': thresholds,
                      'cases': [{'pair': [browser_edges[e['edge_index']]['source'], browser_edges[e['edge_index']]['target']],
                                 'length': browser_edges[e['edge_index']]['length'], 'category': e['category']} for e in case_studies]}, indent=2))


if __name__ == '__main__':
    build()
