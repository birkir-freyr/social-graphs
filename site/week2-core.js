/* Shared sampling mathematics; browser UI and Node checks use the same code. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FriendshipSampling = api;
})(globalThis, function () {
  'use strict';

  function prepare(graph) {
    const adjacency = graph.nodes.map(() => []);
    const seen = new Set();
    for (const [u, v] of graph.edges) {
      if (!Number.isInteger(u) || !Number.isInteger(v) || !adjacency[u] || !adjacency[v] || u === v) throw new Error('Invalid edge');
      const key = [Math.min(u, v), Math.max(u, v)].join(':');
      if (seen.has(key)) throw new Error('Duplicate edge');
      seen.add(key); adjacency[u].push(v); adjacency[v].push(u);
    }
    graph.nodes.forEach((node, i) => {
      if (node.degree !== adjacency[i].length) throw new Error('Degree does not match edges');
    });
    const eligible = graph.nodes.map((_, i) => i).filter(i => adjacency[i].length > 0);
    if (!eligible.length) throw new Error('No eligible people');
    return { graph, adjacency, eligible };
  }

  function sampler(model, rng = Math.random) {
    let count, personSum, friendSum, wins, last;
    function reset() { count = personSum = friendSum = wins = 0; last = null; return summary(); }
    function summary() {
      return { count, personMean: count ? personSum / count : null, friendMean: count ? friendSum / count : null,
        fraction: count ? wins / count : null, last };
    }
    function draw(amount = 1) {
      if (!Number.isInteger(amount) || amount < 1 || amount > 10000) throw new Error('Invalid sample count');
      for (let i = 0; i < amount; i++) {
        const person = model.eligible[Math.floor(rng() * model.eligible.length)];
        const choices = model.adjacency[person];
        const friend = choices[Math.floor(rng() * choices.length)];
        const a = model.graph.nodes[person].degree, b = model.graph.nodes[friend].degree;
        personSum += a; friendSum += b; wins += Number(b >= a); count++;
        last = { person, friend };
      }
      return summary();
    }
    reset();
    return { draw, reset, summary };
  }

  function histogram(values, lo = 8, hi = 28, width = 0.5) {
    const bins = Array.from({ length: Math.ceil((hi - lo) / width) }, (_, i) => ({ lo: lo + i*width, hi: Math.min(hi, lo + (i+1)*width), count: 0 }));
    for (const value of values) {
      if (!Number.isFinite(value) || value < lo || value > hi) throw new Error('Histogram value outside domain');
      bins[Math.min(bins.length - 1, Math.floor((value - lo) / width))].count++;
    }
    return bins;
  }

  return { prepare, sampler, histogram };
});
