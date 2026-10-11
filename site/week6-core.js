(function (root) {
  'use strict';
  function inspect(data, nodeId, pairId, mode) {
    if (!['original', 'filtered'].includes(mode)) throw new Error('Unknown vocabulary');
    const node = data.nodes.find(n => n.id === nodeId);
    const pair = data.pairs[pairId];
    if (!node || !pair || ![pair.source, pair.target].includes(nodeId)) throw new Error('Unknown match');
    const reversed = pair.target === nodeId;
    const targetId = reversed ? pair.source : pair.target;
    return {
      source: node, target: data.nodes.find(n => n.id === targetId),
      linked: pair.linked, cosine: pair[mode].cosine,
      terms: pair[mode].terms.map(term => ({...term,
        source_excerpt: data.excerpts[reversed ? term.target_excerpt : term.source_excerpt],
        target_excerpt: data.excerpts[reversed ? term.source_excerpt : term.target_excerpt]})),
      rank: node[mode].findIndex(n => n.pair === pairId) + 1
    };
  }
  function summarize(data) {
    return {
      changed_first: data.nodes.filter(n => n.original[0].target !== n.filtered[0].target).length,
      mean_retained_top5: data.nodes.reduce((sum, node) => sum + node.original.filter(
        a => node.filtered.some(b => a.target === b.target)).length, 0) / data.nodes.length,
      mean_linked_top5: Object.fromEntries(['original', 'filtered'].map(mode => [mode,
        data.nodes.reduce((sum, node) => sum + node[mode].filter(n => data.pairs[n.pair].linked).length, 0) / data.nodes.length]))
    };
  }
  const api = {inspect, summarize};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Week6 = api;
})(typeof window === 'undefined' ? globalThis : window);
