const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../site/week3-core.js');
const data = require('../site/data/week3.json');

test('saved graph and attack sequences are internally consistent', () => {
  const model = core.prepare(data);
  assert.equal(model.nodes.length, 277);
  assert.equal(data.graph.edges.length, 1421);
  for (const strategy of Object.values(data.strategies)) {
    assert.equal(strategy.order.length, 100);
    assert.equal(new Set(strategy.order).size, 100);
    assert.equal(strategy.curve.length, 101);
    strategy.curve.forEach((expected, removed) => {
      assert.equal(core.componentState(model, strategy.order, removed).giantSize, expected);
    });
  }
});

test('Spider-Man removal creates exactly five isolated fragments', () => {
  const model = core.prepare(data);
  const order = data.strategies.betweenness.order;
  assert.equal(order[0], 'Spider-Man');
  const state = core.componentState(model, order, 1);
  assert.deepEqual(state.sizes, [271, 1, 1, 1, 1, 1]);
  assert.equal(state.outsideGiant, 5);
  assert.equal(data.singleRemoval[0].detachedCount, 5);
});

test('attack findings and random envelope retain their promised coverage', () => {
  assert.equal(data.findings.betweennessFirstBelowHalf, 63);
  assert.equal(data.findings.degreeFirstBelowHalf, 74);
  assert.equal(data.findings.betweennessAt80, 42);
  assert.equal(data.findings.degreeAt80, 107);
  assert.equal(data.findings.randomMedianAt80, 191);
  assert.equal(data.random.summary.length, 101);
  data.random.summary.forEach((point, removed) => {
    assert.equal(point.removed, removed);
    assert.ok(point.q05 <= point.median && point.median <= point.q95);
    assert.ok(point.q05 <= point.mean && point.mean <= point.q95);
  });
});

test('the Week 3 page exposes the tested results and interactive hooks', () => {
  const html = fs.readFileSync(path.join(__dirname, '../site/weeks/week3.html'), 'utf8');
  for (const id of ['removal-map', 'removal-count', 'attack-chart', 'giant-size', 'week3-error']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /after <strong>63 removals<\/strong>/);
  assert.match(html, /<strong>42<\/strong>/);
  assert.match(html, /<strong>107<\/strong>/);
  assert.match(html, /<strong>191<\/strong>/);
});

test('invalid component requests and malformed graphs fail clearly', () => {
  const model = core.prepare(data);
  assert.throws(() => core.componentState(model, data.strategies.degree.order, -1));
  assert.throws(() => core.componentState(model, ['missing'], 1));
  assert.throws(() => core.prepare({graph:{nodes:[{id:'a',degree:0}],edges:[['a','a']]}}));
});
