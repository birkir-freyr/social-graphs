/* Week 2: an independent sampler and an honest comparison with saved nulls. */
(function () {
  'use strict';
  const byId = id => document.getElementById(id);
  const controls = [...document.querySelectorAll('[data-model], [data-null], .sample-actions button')];
  const number = n => n.toFixed(2);
  const percent = n => `${(100*n).toFixed(1)}%`;
  let data, models, modelKey = 'real', activeSampler;

  function showSample(summary) {
    const graph = models[modelKey].graph;
    byId('sample-count').textContent = summary.count.toLocaleString();
    byId('sample-person').textContent = summary.count ? number(summary.personMean) : '—';
    byId('sample-friend').textContent = summary.count ? number(summary.friendMean) : '—';
    byId('sample-fraction').textContent = summary.count ? percent(summary.fraction) : '—';
    const person = summary.last ? graph.nodes[summary.last.person] : null;
    const friend = summary.last ? graph.nodes[summary.last.friend] : null;
    byId('person-name').textContent = person ? person.name : 'Who will you be?';
    byId('friend-name').textContent = friend ? friend.name : 'Who will you meet?';
    byId('person-degree').textContent = person ? person.degree : '—';
    byId('friend-degree').textContent = friend ? friend.degree : '—';
    byId('sample-verdict').textContent = !person ? 'Every person gets an equal chance. Every friend does not.'
      : friend.degree > person.degree ? `This pair: the friend has ${friend.degree-person.degree} more connections. The names above show the latest draw.`
      : friend.degree === person.degree ? 'This pair is a tie. Ties count in “friend ≥ person.”'
      : `This pair: the person has ${person.degree-friend.degree} more connections. A population average is not a promise about every pair.`;
  }

  function switchModel(key) {
    modelKey = key; activeSampler = FriendshipSampling.sampler(models[key]);
    document.querySelectorAll('[data-model]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.model === key)));
    const stats = models[key].graph.stats;
    byId('expected-person').textContent = number(stats.personMean);
    byId('expected-friend').textContent = number(stats.friendMean);
    // A fixed 0–40 scale keeps comparisons stable across model changes.
    byId('person-bar').style.width = `${stats.personMean/40*100}%`;
    byId('friend-bar').style.width = `${stats.friendMean/40*100}%`;
    const intro = key === 'real' ? 'Observed Marvel network.'
      : key === 'shuffle' ? 'One saved degree-preserving shuffle. Every character keeps their degree; their neighbors change.'
      : 'One saved random graph with the same 303 nodes and 1,434 edges. Names are labels; these are synthetic connections.';
    byId('model-note').textContent = `${intro} ${stats.eligible} eligible people; ${stats.isolates} isolates excluded. Bars show exact expectations on a fixed 0–40 scale. Switching networks resets the tally.`;
    showSample(activeSampler.summary());
  }

  const ns = 'http://www.w3.org/2000/svg';
  function svgElement(tag, attributes, text) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, String(value));
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function drawNull(key) {
    document.querySelectorAll('[data-null]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.null === key)));
    const bins = FriendshipSampling.histogram(data.ensembles[key].values);
    const otherKey = key === 'shuffle' ? 'random' : 'shuffle';
    const otherBins = FriendshipSampling.histogram(data.ensembles[otherKey].values);
    const maxCount = Math.ceil(Math.max(...bins.map(b => b.count), ...otherBins.map(b => b.count))/10)*10;
    const svg = svgElement('svg', { viewBox: '0 0 960 340', 'aria-hidden': 'true' });
    const left = 60, right = 930, top = 48, bottom = 270;
    const x = v => left + (v-8)/20*(right-left), y = v => bottom-v/maxCount*(bottom-top);
    for (let tick=0; tick<=maxCount; tick+=20) {
      svg.append(svgElement('line', {x1:left,x2:right,y1:y(tick),y2:y(tick),stroke:'#cbd2c9'}));
      svg.append(svgElement('text', {x:left-12,y:y(tick)+5,'text-anchor':'end',fill:'#596761','font-size':14},tick));
    }
    const color = key === 'shuffle' ? '#146e61' : '#dc532e';
    for (const bin of bins) if (bin.count) {
      const rect = svgElement('rect', {x:x(bin.lo)+1,y:y(bin.count),width:x(bin.hi)-x(bin.lo)-2,height:bottom-y(bin.count),fill:color,rx:2});
      rect.append(svgElement('title', {},`${bin.lo}–${bin.hi}: ${bin.count} null graphs`)); svg.append(rect);
    }
    for (let tick=8;tick<=28;tick+=2) svg.append(svgElement('text',{x:x(tick),y:bottom+26,'text-anchor':'middle',fill:'#596761','font-size':14},tick));
    const observed = data.graphs.real.stats.friendMean;
    svg.append(svgElement('line',{x1:x(observed),x2:x(observed),y1:top-5,y2:bottom,stroke:'#17312d','stroke-width':3,'stroke-dasharray':'5 4'}));
    svg.append(svgElement('text',{x:x(observed),y:26,'text-anchor':'middle',fill:'#17312d','font-size':16,'font-weight':600},`Marvel: ${number(observed)}`));
    svg.append(svgElement('text',{x:left,y:24,fill:'#596761','font-size':14},'Number of null graphs'));
    svg.append(svgElement('text',{x:(left+right)/2,y:325,'text-anchor':'middle',fill:'#17312d','font-size':16},'Exact mean degree of a person’s random friend'));
    byId('null-chart').replaceChildren(svg);
    const e = data.ensembles[key];
    byId('null-chart').setAttribute('aria-label',`Histogram of 100 ${key === 'shuffle' ? 'degree-preserving shuffles' : 'random graphs'}. Null mean ${number(e.mean)}, standard deviation ${number(e.sd)}. Observed Marvel mean ${number(observed)}. The horizontal scale is unchanged when switching nulls.`);
    byId('null-kicker').textContent = key === 'shuffle' ? 'ORDINARY UNDER THIS NULL' : 'EXTREME UNDER THIS NULL';
    byId('null-reading').textContent = key === 'shuffle'
      ? `Marvel: ${number(observed)}. Degree-preserving shuffles: ${number(e.mean)} ± ${number(e.sd)}. The observed result sits comfortably inside this null distribution (two-sided empirical p = ${e.pTwoSided.toFixed(3)}).`
      : `Marvel: ${number(observed)}. Random graphs: ${number(e.mean)} ± ${number(e.sd)}. None of the 100 random graphs reaches Marvel’s value (two-sided empirical p = ${e.pTwoSided.toFixed(4)}). This null also removes Marvel’s heavy-tailed degrees.`;
  }

  async function init() {
    try {
      const response = await fetch('../data/week2.json');
      if (!response.ok) throw new Error('Unable to load graph data');
      data = await response.json();
      models = Object.fromEntries(Object.entries(data.graphs).map(([key, graph]) => [key, FriendshipSampling.prepare(graph)]));
      switchModel('real'); drawNull('shuffle');
      document.querySelectorAll('[data-model]').forEach(b => b.addEventListener('click', () => switchModel(b.dataset.model)));
      document.querySelectorAll('[data-null]').forEach(b => b.addEventListener('click', () => drawNull(b.dataset.null)));
      byId('sample-one').addEventListener('click', () => showSample(activeSampler.draw()));
      byId('sample-many').addEventListener('click', () => showSample(activeSampler.draw(1000)));
      byId('reset-samples').addEventListener('click', () => showSample(activeSampler.reset()));
      controls.forEach(b => { b.disabled = false; });
    } catch (error) {
      byId('week2-error').hidden = false;
      byId('week2-error').textContent = 'The interactive data could not be loaded. Reload to try again. The article and tables below still contain the complete results.';
      console.error('Week 2 data:', error);
    }
  }
  init();
})();
