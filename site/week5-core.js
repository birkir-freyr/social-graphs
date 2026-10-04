(function (root) {
  'use strict';
  function analyze(data, threshold) {
    const edges = data.edges.filter(edge => edge.length >= threshold);
    const active = new Set(edges.flatMap(edge => [edge.source, edge.target]));
    return {edges, active, nodes: data.nodes.filter(node => active.has(node.id))};
  }
  const api = {analyze};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Week5 = api;
})(typeof window === 'undefined' ? globalThis : window);
