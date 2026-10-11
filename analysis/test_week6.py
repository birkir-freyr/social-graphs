"""Independent checks of exported Week 6 counts, rankings and raw spans."""
import csv
import gzip
import hashlib
import json
import math
import re
import unittest
from collections import Counter

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import CountVectorizer

from build_week6 import DATA, load, name_candidates, nearest, weights


class Week6Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((DATA / 'week6.json').read_text(encoding='utf-8'))
        cls.roster, cls.pages = load()
        # Independently tokenize and calculate DF and normalized coordinates.
        cls.counts = {n: Counter(re.findall(r'(?u)\b\w\w+\b', text.lower()))
                      for n, text in cls.pages.items()}
        cls.df = Counter(word for counts in cls.counts.values() for word in counts)
        uses, uppercase = Counter(), Counter()
        for raw in cls.pages.values():
            for word in re.findall('[A-Za-z]+', raw):
                uses[word.lower()] += 1
                if 'A' <= word[0] <= 'Z':
                    uppercase[word.lower()] += 1
        cls.removed = {w for w in cls.df if 2 * uppercase[w] > uses[w]}
        cls.uses, cls.uppercase = uses, uppercase
        cls.vectors = {}
        for mode in ('original', 'filtered'):
            vectors = {}
            for name, counts in cls.counts.items():
                kept = {w: c for w, c in counts.items() if mode == 'original' or w not in cls.removed}
                size = sum(kept.values())
                values = {w: c / size * math.log(303 / cls.df[w]) for w, c in kept.items()}
                norm = math.sqrt(sum(v * v for v in values.values()))
                vectors[name] = {w: v / norm for w, v in values.items() if v}
            cls.vectors[mode] = vectors
        cls.nodes = {n['id']: n for n in cls.data['nodes']}

    def test_inputs_and_compressed_copy(self):
        self.assertEqual(set(self.nodes), set(self.roster))
        self.assertEqual(len(self.nodes), 303)
        for name, digest in self.data['meta']['hashes'].items():
            self.assertEqual(hashlib.sha256((DATA / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(gzip.decompress((DATA / 'week6.json.gz').read_bytes()), (DATA / 'week6.json').read_bytes())

    def test_independent_rankings(self):
        cases = ('Storm_(Marvel_Comics)', 'Emma_Frost', 'Wolverine_(character)', 'Jean_Grey')
        for mode, vectors in self.vectors.items():
            for name in cases:
                source = vectors[name]
                scores = {other: sum(v * vectors[other].get(w, 0) for w, v in source.items())
                          for other in vectors if other != name}
                order = sorted(scores, key=lambda other: (-scores[other], other))[:5]
                exported = self.nodes[name][mode]
                self.assertEqual(order, [r['target'] for r in exported])
                for row in exported:
                    self.assertAlmostEqual(scores[row['target']], row['cosine'], places=12)

    def test_every_pair_decomposition(self):
        for pair in self.data['pairs']:
            for mode, vectors in self.vectors.items():
                a, b = vectors[pair['source']], vectors[pair['target']]
                products = {w: v * b[w] for w, v in a.items() if w in b}
                total = sum(products.values())
                terms = pair[mode]['terms']
                self.assertAlmostEqual(total, pair[mode]['cosine'], places=12)
                # Independent summation/norm order can swap numerical ties.
                # Verify the ordered values and that no materially larger
                # contribution is omitted, rather than requiring tied labels.
                expected = sorted(products.values(), reverse=True)[:5]
                self.assertEqual(len(expected), len(terms))
                for value, term in zip(expected, terms):
                    self.assertAlmostEqual(value, term['contribution'], places=12)
                for term in terms:
                    self.assertAlmostEqual(products[term['term']], term['contribution'], places=12)
                    self.assertAlmostEqual(products[term['term']] / total, term['share'], places=12)
                    self.assertEqual(term['removed'], term['term'] in self.removed)
                    for side in ('source', 'target'):
                        excerpt = self.data['excerpts'][term[f'{side}_excerpt']]
                        self.assertEqual((excerpt['node'], excerpt['term']), (pair[side], term['term']))

    def test_every_excerpt_is_first_raw_occurrence(self):
        first = {}
        for name, raw in self.pages.items():
            first[name] = {}
            for match in re.finditer(r'(?u)\b\w\w+\b', raw):
                first[name].setdefault(match.group().lower(), match.start())
        keys = set()
        for span in self.data['excerpts']:
            key = span['node'], span['term']
            self.assertNotIn(key, keys)
            keys.add(key)
            raw = self.pages[span['node']]
            self.assertEqual(raw[span['start']:span['end']], span['text'])
            start = span['start'] + span['match_start']
            end = span['start'] + span['match_end']
            self.assertEqual(raw[start:end].lower(), span['term'])
            self.assertEqual(start, first[span['node']][span['term']])

    def test_filter_and_audit(self):
        self.assertEqual(set(t['term'] for t in self.data['removed_terms']), self.removed)
        self.assertEqual(len(self.df), 26279)
        self.assertEqual(len(self.removed), 8972)
        for term in self.data['removed_terms']:
            word = term['term']
            self.assertEqual(term['uses'], self.uses[word])
            self.assertEqual(term['capitalized_uses'], self.uppercase[word])
            self.assertAlmostEqual(term['capitalized_fraction'], self.uppercase[word] / self.uses[word])
        self.assertNotIn('she', self.removed)
        self.assertNotIn('her', self.removed)
        self.assertIn('storm', self.removed)
        self.assertEqual(name_candidates({'a': 'Hero hero Beta BETA beta'})[0], {'beta'})

    def test_csv_rankings_and_links(self):
        with (DATA / 'week1_edges.tsv').open(encoding='utf-8') as stream:
            linked = {tuple(sorted(line.strip().split('\t'))) for line in stream
                      if line.strip() and not line.startswith('#')}
        for pair in self.data['pairs']:
            self.assertEqual(pair['linked'], tuple(sorted((pair['source'], pair['target']))) in linked)
        with (DATA / 'week6-neighbors.csv').open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 3030)
        for row in rows:
            item = self.nodes[row['source']][row['mode']][int(row['rank']) - 1]
            self.assertEqual(row['target'], item['target'])
            self.assertEqual(float(row['cosine']), item['cosine'])
            self.assertEqual(row['linked'], str(self.data['pairs'][item['pair']]['linked']))

    def test_claims(self):
        nodes = list(self.nodes.values())
        changed = sum(n['original'][0]['target'] != n['filtered'][0]['target'] for n in nodes)
        overlap = [len({r['target'] for r in n['original']} & {r['target'] for r in n['filtered']}) for n in nodes]
        self.assertEqual(changed, 223)
        self.assertEqual(self.data['summary']['changed_first'], changed)
        self.assertEqual(self.data['summary']['retained_histogram'], [overlap.count(k) for k in range(6)])
        self.assertAlmostEqual(self.data['summary']['mean_retained_top5'], sum(overlap) / 303)
        for mode in ('original', 'filtered'):
            count = sum(self.data['pairs'][r['pair']]['linked'] for n in nodes for r in n[mode])
            self.assertAlmostEqual(self.data['summary']['mean_linked_top5'][mode], count / 303)
        for name, target, word, percentage in [
                ('Storm_(Marvel_Comics)', 'Human_Torch', 'storm', 86.9),
                ('Emma_Frost', 'Jack_Frost_(Marvel_Comics)', 'frost', 96.1)]:
            match = self.nodes[name]['original'][0]
            self.assertEqual(match['target'], target)
            term = self.data['pairs'][match['pair']]['original']['terms'][0]
            self.assertEqual(term['term'], word)
            self.assertEqual(round(term['share'] * 100, 1), percentage)
        for source, target, mode, words, percentage in [
                ('Storm_(Marvel_Comics)', 'Jean_Grey', 'filtered', {'her', 'she'}, 34.0),
                ('Storm_(Marvel_Comics)', 'She-Hulk', 'filtered', {'her', 'she'}, 58.2),
                ('Jean_Grey', 'Phoenix_Force', 'original', {'phoenix', 'jean', 'grey'}, 87.4)]:
            pair = next(p for p in self.data['pairs'] if {p['source'], p['target']} == {source, target})
            share = sum(t['share'] for t in pair[mode]['terms'] if t['term'] in words)
            self.assertEqual(round(share * 100, 1), percentage)

    def test_ubiquitous_terms_zero_rows_and_ties(self):
        vectorizer = CountVectorizer()
        matrix = weights(vectorizer.fit_transform(['same rare', 'same', 'same']).astype(float))
        self.assertEqual(matrix[:, list(vectorizer.get_feature_names_out()).index('same')].nnz, 0)
        self.assertEqual(matrix[1:].nnz, 0)
        matrix = weights(csr_matrix([[1., 1.], [0., 0.], [1., 0.]]))
        self.assertTrue(np.isfinite(matrix.data).all())
        self.assertEqual(matrix[1].nnz, 0)
        scores, order = nearest(csr_matrix((3, 2)), ['z', 'b', 'a'], n=2)
        self.assertEqual(order, [[2, 1], [2, 0], [1, 0]])
        self.assertEqual(scores[0, 0], -1)


if __name__ == '__main__':
    unittest.main()
