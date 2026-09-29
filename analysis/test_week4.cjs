const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'site/data/week4.json')));
const {analyze} = require('../site/week4-core.js');

// Independent breadth-first traversal, deliberately separate from union-find.
function components(edges) {
  const neighbors = new Map(data.nodes.map(n => [n.id, []]));
  for (const e of edges) {neighbors.get(e.source).push(e.target); neighbors.get(e.target).push(e.source);}
  const unseen = new Set(neighbors.keys()), groups = [];
  while (unseen.size) {
    const queue = [unseen.values().next().value]; unseen.delete(queue[0]);
    for (let i = 0; i < queue.length; i++) {
      for (const n of neighbors.get(queue[i])) if (unseen.delete(n)) queue.push(n);
    }
    groups.push(queue.sort());
  }
  return groups.sort((a, b) => b.length - a.length || a[0].localeCompare(b[0]));
}

test('original directed weights, degrees, strengths and endpoint scores reproduce the export', () => {
  const pairs = new Map();
  const lines = fs.readFileSync(path.join(root, 'site/data/week4_philosophers_edges.tsv'), 'utf8').trim().split('\n').filter(l => !l.startsWith('#')).slice(1);
  for (const line of lines) {
    const [u, v, w] = line.split('\t');
    const key = [u, v].sort().join('\t'); pairs.set(key, (pairs.get(key) || 0) + Number(w));
  }
  assert.equal(pairs.size, 9140);
  const nodes = new Set(data.nodes.map(n => n.id));
  const degrees = new Map(data.nodes.map(n => [n.id, 0])), strengths = new Map(degrees);
  for (const [key, weight] of pairs) {
    const ends = key.split('\t');
    if (!ends.every(n => nodes.has(n))) continue;
    for (const n of ends) {degrees.set(n, degrees.get(n) + 1); strengths.set(n, strengths.get(n) + weight);}
  }
  for (const n of data.nodes) {assert.equal(n.degree, degrees.get(n.id)); assert.equal(n.strength, strengths.get(n.id));}
  for (const e of data.edges) {
    assert.equal(e.weight, pairs.get([e.source, e.target].sort().join('\t')));
    const scores = [e.source, e.target].map(n => (1 - e.weight / strengths.get(n)) ** (degrees.get(n) - 1));
    assert.ok(Math.abs(e.score - Math.min(...scores)) < 1e-14);
  }
  for (const [name, hash] of Object.entries(data.meta.hashes)) {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'site/data', name))).digest('hex'), hash);
  }
});

test('all slider settings agree with independent traversal and preserve isolated nodes', () => {
  let prev = 1;
  for (let i = 0; i <= 100; i++) {
    const alpha = i / 100, result = analyze(data, alpha);
    const groups = components(data.edges.filter(e => e.score < alpha));
    assert.equal(result.giant, groups[0].length);
    assert.equal(result.components.length, groups.length);
    assert.equal(result.isolates, groups.filter(g => g.length === 1).length);
    assert.ok(result.giant >= prev); prev = result.giant;
    assert.equal(result.components.reduce((sum, g) => sum + g.length, 0), 1374);
  }
  assert.equal(analyze(data, 0).edges.length, 0);
  assert.equal(analyze(data, 1).giant, 1374);
});

test('course reference snapshots match the browser calculations', () => {
  for (const s of data.snapshots) {
    const v = analyze(data, s.alpha);
    assert.deepEqual([v.edges.length, v.active.size, v.giant, v.isolates], [s.links, s.active, s.giant, s.isolates]);
  }
});

test('critical boundary, tied removals, fragment memberships and counterfactuals', () => {
  const c = data.critical;
  assert.equal(c.score, 0.04712622658232835);
  assert.equal(Math.max(...data.curve.map(e => e.drop)), 43);
  assert.equal(data.curve.filter(e => e.drop === 43).length, 1);
  const before = analyze(data, c.score, true), after = analyze(data, c.score);
  assert.deepEqual([before.edges.length, after.edges.length, before.giant, after.giant, after.isolates], [273, 271, 108, 65, 1046]);
  assert.deepEqual(data.edges.filter(e => e.score === c.score), c.removed);
  const original = new Set(components(before.edges)[0]);
  const fragments = components(after.edges).filter(g => original.has(g[0]));
  assert.deepEqual(fragments, c.fragments.map(f => [...f.nodes].sort()));
  assert.deepEqual(fragments.map(f => f.length), [65, 40, 3]);
  for (const e of c.single_link_removals) {
    const remaining = before.edges.filter(edge => !(edge.source === e.source && edge.target === e.target));
    assert.equal(components(remaining)[0].length, e.giant);
  }
});

test('sweep covers every edge score and sampled event sides match traversal', () => {
  const scores = [...new Set(data.edges.map(e => e.score))].sort((a, b) => a - b);
  assert.deepEqual(data.curve.map(e => e.score), scores);
  let previous = 1;
  for (const e of data.curve) {
    assert.equal(e.below, previous); assert.equal(e.drop, e.above - e.below); previous = e.above;
  }
  for (let i = 0; i < data.curve.length; i += 101) {
    const e = data.curve[i];
    assert.equal(components(data.edges.filter(d => d.score < e.score))[0].length, e.below);
    assert.equal(components(data.edges.filter(d => d.score <= e.score))[0].length, e.above);
  }
});
