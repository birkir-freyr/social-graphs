"""Independent checks of exact matches and the public source excerpts."""
import csv
import hashlib
import json
import random
import unittest
from pathlib import Path

from build_week5 import DATA, TOKEN, load, longest_runs


def reference_longest(a, b):
    # Dynamic programming for longest common contiguous substring. It is
    # independent of the builder's seed index and maximal-run extension.
    previous = [0] * (len(b) + 1)
    best = (0, 0, 0)
    for i, token in enumerate(a):
        current = [0] * (len(b) + 1)
        for j, other in enumerate(b):
            if token == other:
                current[j + 1] = previous[j] + 1
                candidate = (current[j + 1], i - current[j + 1] + 1, j - current[j + 1] + 1)
                if (-candidate[0], candidate[1], candidate[2]) < (-best[0], best[1], best[2]):
                    best = candidate
        previous = current
    return best


class SharedRuns(unittest.TestCase):
    def test_exact_search_against_independent_dynamic_programming(self):
        rng = random.Random(509)
        cases = [
            (list('ababcababc'), list('zzababczzababc')),
            (list('abcxyz'), list('xyzabc')),
            (['same'] * 12, ['same'] * 15),
            (list('abcdef'), list('uvwxyz')),
        ]
        for _ in range(100):
            a = [rng.choice('abcd') for _ in range(24)]
            b = [rng.choice('abcd') for _ in range(27)]
            start = rng.randrange(15)
            b[7:15] = a[start:start + 8]
            cases.append((a, b))
        for a, b in cases:
            for minimum in [1, 3, 8]:
                with self.subTest(a=a, b=b, minimum=minimum):
                    actual = longest_runs([a, b], minimum).get((0, 1))
                    expected = reference_longest(a, b)
                    self.assertEqual(actual, expected if expected[0] >= minimum else None)

    def test_document_boundaries_do_not_make_phrases(self):
        self.assertFalse(longest_runs([list('abcd'), list('efgh'), list('abcdefgh')], minimum=8))

    def test_boilerplate_claim_against_raw_pages(self):
        result = json.loads((DATA / 'week5.json').read_text())
        _, pages = load()
        phrase = 'in american comic books published by marvel comics'
        count = sum(phrase in ' '.join(m.group().lower() for m in TOKEN.finditer(text))
                    for text in pages.values())
        self.assertEqual(count, 282)
        self.assertEqual(result['boilerplate'], {'phrase': phrase, 'pages': count, 'pairs': 39621})

    def test_every_public_excerpt_matches_both_frozen_sources(self):
        result = json.loads((DATA / 'week5.json').read_text())
        _, pages = load()
        for file, digest in result['meta']['hashes'].items():
            self.assertEqual(hashlib.sha256((DATA / file).read_bytes()).hexdigest(), digest)
        for edge in result['edges']:
            passages = []
            for side in ['source', 'target']:
                text = pages[edge[side]]
                excerpt = edge[side + '_excerpt']
                self.assertEqual(excerpt['text'], text[excerpt['start']:excerpt['end']])
                all_tokens = [m.group().lower() for m in TOKEN.finditer(text)]
                offset = edge[side + '_token']
                match_tokens = [m.group().lower() for m in TOKEN.finditer(excerpt['text'])]
                self.assertEqual(len(match_tokens), edge['length'])
                self.assertEqual(match_tokens, all_tokens[offset:offset + edge['length']])
                passages.append(match_tokens)
            self.assertEqual(passages[0], passages[1])
            self.assertEqual(edge['raw_equal'], edge['source_excerpt']['text'] == edge['target_excerpt']['text'])

    def test_threshold_counts_against_csv_and_saved_claims(self):
        result = json.loads((DATA / 'week5.json').read_text())
        with (DATA / 'week5-pairs.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 40550)
        self.assertEqual(max(int(r['length']) for r in rows), 164)
        self.assertEqual(len({(r['source'], r['target']) for r in rows}), len(rows))
        for threshold in result['thresholds']:
            included = [r for r in rows if int(r['length']) >= threshold['threshold']]
            nodes = {r[s] for r in included for s in ['source', 'target']}
            self.assertEqual(len(included), threshold['pairs'])
            self.assertEqual(len(nodes), threshold['active_pages'])
        self.assertEqual(result['meta']['possible_pairs'], 303 * 302 // 2)


if __name__ == '__main__':
    unittest.main()
