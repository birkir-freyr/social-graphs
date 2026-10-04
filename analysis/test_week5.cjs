const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../site/data/week5.json')));
const {analyze} = require('../site/week5-core.js');

function groups(edges) {
  const adjacency = new Map();
  for (const edge of edges) {
    for (const [a, b] of [[edge.source, edge.target], [edge.target, edge.source]]) {
      if (!adjacency.has(a)) adjacency.set(a, []);
      adjacency.get(a).push(b);
    }
  }
  const unseen = new Set(adjacency.keys()), sizes = [];
  while (unseen.size) {
    const queue = [unseen.values().next().value]; unseen.delete(queue[0]);
    for (let i = 0; i < queue.length; i++) {
      for (const neighbor of adjacency.get(queue[i])) if (unseen.delete(neighbor)) queue.push(neighbor);
    }
    sizes.push(queue.length);
  }
  return sizes;
}

test('all slider settings retain exactly the eligible pairs and their endpoints', () => {
  for (let threshold = 20; threshold <= 150; threshold++) {
    const result = analyze(data, threshold);
    const expected = data.edges.filter(edge => edge.length >= threshold);
    assert.deepEqual(result.edges, expected);
    assert.deepEqual(new Set(result.nodes.map(node => node.id)), result.active);
    assert.equal(result.nodes.length, result.active.size);
    const samePair = new Set(expected.map(edge => `${edge.source}\t${edge.target}`));
    assert.equal(samePair.size, expected.length);
  }
});

test('saved component sizes match independent graph traversal', () => {
  for (const record of data.thresholds.filter(record => record.threshold >= 20)) {
    const result = analyze(data, record.threshold), sizes = groups(result.edges);
    assert.equal(result.edges.length, record.pairs);
    assert.equal(result.active.size, record.active_pages);
    assert.equal(Math.max(...sizes), record.largest_group);
    assert.equal(sizes.length, record.groups_with_links);
  }
});

test('four inspected examples retain their measured lengths and raw-match distinctions', () => {
  const cases = data.case_studies.map(item => data.edges[item.edge_index]);
  assert.deepEqual(cases.map(edge => edge.length), [164, 99, 123, 128]);
  assert.deepEqual(cases.map(edge => edge.raw_equal), [true, false, false, false]);
  assert.equal(data.nodes.length, 81);
  for (const node of data.nodes) {
    assert.ok(node.x >= 0 && node.x <= 1 && node.y >= 0 && node.y <= 1);
  }
});
