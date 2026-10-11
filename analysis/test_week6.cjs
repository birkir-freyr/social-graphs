const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {inspect, summarize} = require('../site/week6-core.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../site/data/week6.json'), 'utf8'));

test('all exported pairs orient names, passages and ranks correctly in both directions', () => {
  for (let id = 0; id < data.pairs.length; id++) {
    const pair = data.pairs[id];
    for (const mode of ['original', 'filtered']) {
      const forward = inspect(data, pair.source, id, mode);
      const backward = inspect(data, pair.target, id, mode);
      assert.equal(forward.source.id, backward.target.id);
      assert.equal(forward.target.id, backward.source.id);
      assert.equal(forward.cosine, backward.cosine);
      for (let k = 0; k < forward.terms.length; k++) {
        assert.equal(forward.terms[k].source_excerpt, backward.terms[k].target_excerpt);
        assert.equal(forward.terms[k].target_excerpt, backward.terms[k].source_excerpt);
        assert.equal(forward.terms[k].source_excerpt.node, forward.source.id);
        assert.equal(forward.terms[k].target_excerpt.node, forward.target.id);
        assert.ok(forward.terms[k].contribution > 0);
        assert.ok(Math.abs(forward.terms[k].share * forward.cosine - forward.terms[k].contribution) < 1e-12);
        if (mode === 'filtered') assert.equal(forward.terms[k].removed, false);
      }
      for (const view of [forward, backward]) {
        const expected = view.source[mode].findIndex(r => r.pair === id) + 1;
        assert.equal(view.rank, expected);
      }
    }
  }
});

test('summary is calculated from actual ranks and links, not stored flags', () => {
  const summary = summarize(data);
  assert.equal(summary.changed_first, 223);
  assert.equal(summary.changed_first, data.summary.changed_first);
  assert.equal(summary.mean_retained_top5, data.summary.mean_retained_top5);
  assert.deepEqual(summary.mean_linked_top5, data.summary.mean_linked_top5);
  for (const node of data.nodes) {
    assert.equal(node.changed_first, node.original[0].target !== node.filtered[0].target);
    for (const mode of ['original', 'filtered']) {
      assert.equal(node[mode].length, 5);
      assert.equal(new Set(node[mode].map(r => r.target)).size, 5);
      assert.ok(node[mode].every(r => r.target !== node.id && r.cosine >= 0 && r.cosine <= 1 + 1e-12));
      assert.ok(node[mode].every((r, i, list) => !i || list[i - 1].cosine >= r.cosine));
    }
  }
});

test('changing vocabulary preserves the chosen pair even outside the other top five', () => {
  const storm = data.nodes.find(n => n.id === 'Storm_(Marvel_Comics)');
  const pair = storm.original[0].pair;
  assert.equal(inspect(data, storm.id, pair, 'original').rank, 1);
  const after = inspect(data, storm.id, pair, 'filtered');
  assert.equal(after.target.id, 'Human_Torch');
  assert.equal(after.rank, 0);
  assert.ok(!after.terms.some(t => t.term === 'storm'));
});

test('invalid vocabulary, node and pair selections are rejected', () => {
  assert.throws(() => inspect(data, data.nodes[0].id, 0, 'bogus'));
  assert.throws(() => inspect(data, 'missing', 0, 'original'));
  assert.throws(() => inspect(data, data.nodes[0].id, -1, 'original'));
});

// Exercise event wiring and the uncompressed fallback without a DOM package.
class Element {
  constructor(dataset = {}) {
    this.dataset = dataset; this.attributes = {}; this.style = {};
    this.children = []; this.events = {}; this.disabled = false;
    this.hidden = true; this.textContent = '';
  }
  setAttribute(k, value) {this.attributes[k] = String(value);}
  addEventListener(k, fn) {this.events[k] = fn;}
  append(...items) {this.children.push(...items);}
  replaceChildren(...items) {this.children = items;}
  querySelectorAll() {return this.children;}
  click() {if (!this.disabled) this.events.click();}
}
async function startUI(failed = false) {
  const html = fs.readFileSync(path.join(__dirname, '../site/weeks/week6.html'), 'utf8');
  const els = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element()]));
  const characters = [...html.matchAll(/data-character="([^"]+)"/g)].map(m => new Element({character:m[1]}));
  const vocabularies = ['original', 'filtered'].map(vocabulary => new Element({vocabulary}));
  [...characters, ...vocabularies, els.get('character')].forEach(el => {el.disabled = true;});
  const errors = [], requests = [];
  const document = {
    getElementById: id => {assert.ok(els.has(id), `Missing HTML hook ${id}`); return els.get(id);},
    querySelectorAll: q => q === '[data-character]' ? characters : vocabularies,
    createElement: () => new Element(),
    createTextNode: text => ({textContent:text})
  };
  const context = vm.createContext({document, Week6:{inspect, summarize},
    fetch: async url => {requests.push(url); return {ok:!failed, status:503, json:async()=>data};},
    console:{error:e=>errors.push(e)}});
  await vm.runInContext(fs.readFileSync(path.join(__dirname, '../site/week6.js'), 'utf8'), context);
  return {els, characters, vocabularies, errors, requests};
}

test('UI plain-JSON fallback, preset selection, term highlighting and full roster are wired', async () => {
  const {els, characters, vocabularies, errors, requests} = await startUI();
  assert.equal(errors.length, 0);
  assert.deepEqual(requests, ['../data/week6.json']);
  assert.equal(els.get('character').children.length, 303);
  assert.equal(els.get('source-passage').children[1].textContent, 'Storm');
  assert.equal(els.get('target-passage').children[1].textContent, 'Storm');
  vocabularies[1].click();
  assert.match(els.get('pair-caption').textContent, /outside this view’s top five/);
  assert.match(els.get('term-note').textContent, /relationship/);
  characters[1].click();
  assert.equal(els.get('chosen-name').textContent, 'Emma Frost');
  assert.equal(vocabularies[0].attributes['aria-pressed'], 'true');
  assert.match(els.get('pair-title').textContent, /Jack Frost/);
  els.get('term-buttons').children[1].click();
  assert.equal(els.get('term-buttons').children[1].attributes['aria-pressed'], 'true');
  els.get('character').events.change({target:{value:'Jean_Grey'}});
  assert.equal(els.get('chosen-name').textContent, 'Jean Grey');
  assert.match(els.get('pair-title').textContent, /Phoenix Force/);
});

test('failed data load keeps controls disabled and preserves readable static results', async () => {
  const {els, characters, vocabularies, errors} = await startUI(true);
  assert.equal(errors.length, 1);
  assert.equal(els.get('week6-error').hidden, false);
  assert.match(els.get('week6-error').textContent, /article, results table and downloadable figure/);
  assert.ok([...characters, ...vocabularies, els.get('character')].every(el => el.disabled));
  const html = fs.readFileSync(path.join(__dirname, '../site/weeks/week6.html'), 'utf8');
  assert.match(html, /Human Torch · 0.329/);
  assert.match(html, /Jean Grey · 0.416/);
  assert.match(html, /week6-lookalikes.svg/);
});
