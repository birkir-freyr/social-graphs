/* Mathematical and UI-state checks without browser automation. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const core = require('../site/week2-core.js');
const data = require('../site/data/week2.json');
const close = (a, b) => assert.ok(Math.abs(a-b) < 1e-9, `${a} != ${b}`);

test('all saved graph statistics agree with the edges consumed by the sampler', () => {
  for (const graph of Object.values(data.graphs)) {
    const m = core.prepare(graph), degree = i => graph.nodes[i].degree;
    const n = m.eligible.length;
    const person = m.eligible.reduce((s,i) => s+degree(i),0)/n;
    const friend = m.eligible.reduce((s,i) => s+m.adjacency[i].reduce((sum,j)=>sum+degree(j),0)/degree(i),0)/n;
    const fraction = m.eligible.reduce((s,i) => s+m.adjacency[i].filter(j=>degree(j)>=degree(i)).length/degree(i),0)/n;
    const endpoint = graph.nodes.reduce((s,v)=>s+v.degree*v.degree,0)/(2*graph.edges.length);
    close(person,graph.stats.personMean); close(friend,graph.stats.friendMean);
    close(fraction,graph.stats.fractionGE); close(endpoint,graph.stats.endpointMean);
    graph.nodes.forEach((node,i) => close(node.friendProbability,m.adjacency[i].reduce((s,j)=>s+1/degree(j),0)/n));
  }
  assert.deepEqual(data.graphs.real.nodes.map(n=>[n.id,n.degree]),data.graphs.shuffle.nodes.map(n=>[n.id,n.degree]));
});

test('exhaustive star sampling distinguishes person-first from edge endpoints and excludes isolates', () => {
  const graph = {nodes:[3,1,1,1,0].map(degree=>({degree})),edges:[[0,1],[0,2],[0,3]]};
  const model = core.prepare(graph);
  const draws = [0.01,0.1, 0.26,0.1, 0.51,0.1, 0.76,0.1];
  const sampler = core.sampler(model,()=>draws.shift());
  const s = sampler.draw(4);
  close(s.personMean,1.5); close(s.friendMean,2.5); close(s.fraction,.75);
  assert.deepEqual(s.last,{person:3,friend:0}); assert.equal(s.count,4);
  const before = JSON.stringify(graph);
  assert.deepEqual(sampler.reset(),{count:0,personMean:null,friendMean:null,fraction:null,last:null});
  assert.equal(JSON.stringify(graph),before);
  assert.throws(()=>sampler.draw(0)); assert.throws(()=>core.prepare({nodes:[{degree:0}],edges:[]}));
});

test('regular-graph pairs are ties and invalid saved graphs fail clearly', () => {
  const sampler = core.sampler(core.prepare({nodes:[{degree:1},{degree:1}],edges:[[0,1]]}),()=>0);
  const s = sampler.draw(1000); assert.equal(s.fraction,1); assert.equal(s.personMean,s.friendMean);
  assert.throws(()=>core.prepare({nodes:[{degree:2}],edges:[[0,0]]}));
  assert.throws(()=>core.prepare({nodes:[{degree:2},{degree:2}],edges:[[0,1],[1,0]]}));
});

test('histograms retain all 100 trials and include their upper boundary', () => {
  for (const e of Object.values(data.ensembles)) {
    assert.equal(e.values.length,100);
    assert.equal(core.histogram(e.values).reduce((sum,b)=>sum+b.count,0),100);
    close(e.values.reduce((a,b)=>a+b,0)/100,e.mean);
  }
  assert.equal(core.histogram([28]).at(-1).count,1);
  assert.throws(()=>core.histogram([29]));
});

// A small DOM substitute checks event wiring and error recovery, not layout.
class Element {
  constructor(dataset={}) {this.dataset=dataset;this.attributes={};this.style={};this.events={};this.children=[];this.disabled=true;this.hidden=true;this.textContent='';}
  setAttribute(k,v){this.attributes[k]=String(v);}
  addEventListener(k,fn){this.events[k]=fn;}
  append(...els){this.children.push(...els);}
  replaceChildren(...els){this.children=els;}
  click(){if (!this.disabled) this.events.click();}
}
async function startUI(fail=false){
  const html=fs.readFileSync(path.join(__dirname,'../site/weeks/week2.html'),'utf8');
  const els=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const modelButtons=['real','shuffle','random'].map(model=>new Element({model}));
  const nullButtons=['shuffle','random'].map(value=>new Element({null:value}));
  const actions=['sample-one','sample-many','reset-samples'].map(id=>els.get(id));
  const errors=[];
  const document={getElementById:id=>{assert.ok(els.has(id),`Missing element ${id}`);return els.get(id);},
    querySelectorAll:q=>q==='[data-model]'?modelButtons:q==='[data-null]'?nullButtons:[...modelButtons,...nullButtons,...actions],
    createElementNS:()=>new Element()};
  const context=vm.createContext({document,FriendshipSampling:core,fetch:async()=>({ok:!fail,json:async()=>data}),console:{error:(...v)=>errors.push(v)}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/week2.js'),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return {els,modelButtons,nullButtons,errors};
}

test('UI sampling, reset, model switch, and null switch use separate state correctly',async()=>{
  const {els,modelButtons,nullButtons,errors}=await startUI();
  assert.equal(errors.length,0);
  els.get('sample-many').click(); assert.equal(els.get('sample-count').textContent,'1,000');
  els.get('sample-one').click(); assert.equal(els.get('sample-count').textContent,'1,001');
  nullButtons[1].click(); assert.equal(els.get('null-kicker').textContent,'EXTREME UNDER THIS NULL');
  assert.equal(els.get('sample-count').textContent,'1,001');
  modelButtons[2].click(); assert.equal(els.get('sample-count').textContent,'0');
  assert.equal(els.get('expected-friend').textContent,data.graphs.random.stats.friendMean.toFixed(2));
  assert.equal(modelButtons[2].attributes['aria-pressed'],'true');
  els.get('sample-one').click(); els.get('reset-samples').click();
  assert.equal(els.get('friend-degree').textContent,'—');
  assert.equal(els.get('sample-fraction').textContent,'—');
});

test('failed data loading leaves controls disabled and displays a readable fallback',async()=>{
  const {els,modelButtons,errors}=await startUI(true);
  assert.equal(errors.length,1); assert.equal(els.get('week2-error').hidden,false);
  assert.match(els.get('week2-error').textContent,/article and tables/);
  assert.ok(modelButtons.every(b=>b.disabled)); assert.equal(els.get('sample-many').disabled,true);
});
