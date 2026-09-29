/* Shared filter and connectivity calculations; also exercised by Node tests. */
(function (root) {
  'use strict';
  function analyze(data, alpha, includeBoundary = false) {
    const parent = new Map(data.nodes.map(n => [n.id, n.id]));
    const sizes = new Map(data.nodes.map(n => [n.id, 1]));
    const active = new Set();
    function find(n) {
      while (parent.get(n) !== n) {
        parent.set(n, parent.get(parent.get(n)));
        n = parent.get(n);
      }
      return n;
    }
    const edges = data.edges.filter(e => e.score < alpha || (includeBoundary && e.score === alpha));
    for (const e of edges) {
      active.add(e.source); active.add(e.target);
      let a = find(e.source), b = find(e.target);
      if (a !== b) {
        if (sizes.get(a) < sizes.get(b)) [a, b] = [b, a];
        parent.set(b, a); sizes.set(a, sizes.get(a) + sizes.get(b));
      }
    }
    const groups = new Map();
    for (const n of data.nodes) {
      const id = find(n.id);
      if (!groups.has(id)) groups.set(id, []);
      groups.get(id).push(n.id);
    }
    const components = [...groups.values()].sort((a, b) => b.length - a.length);
    return {edges, active, components, giant: components[0].length,
      isolates: data.nodes.length - active.size};
  }
  const api = {analyze};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Week4 = api;
})(typeof window !== 'undefined' ? window : globalThis);
