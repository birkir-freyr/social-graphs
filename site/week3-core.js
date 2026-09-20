/* Shared component calculations for the Week 3 explorable and Node tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RemovalLab = api;
})(globalThis, function () {
  "use strict";

  function prepare(payload) {
    const nodes = payload.graph.nodes;
    const index = new Map(nodes.map((node, i) => [node.id, i]));
    const adjacency = nodes.map(() => []);
    const seen = new Set();
    for (const [source, target] of payload.graph.edges) {
      const a = index.get(source), b = index.get(target);
      if (a === undefined || b === undefined || a === b) throw new Error("Invalid edge");
      const key = a < b ? `${a}:${b}` : `${b}:${a}`;
      if (seen.has(key)) throw new Error("Duplicate edge");
      seen.add(key);
      adjacency[a].push(b);
      adjacency[b].push(a);
    }
    nodes.forEach((node, i) => {
      if (node.degree !== adjacency[i].length) throw new Error(`Degree mismatch for ${node.id}`);
    });
    return { payload, nodes, index, adjacency };
  }

  function componentState(model, order, removedCount) {
    if (!Number.isInteger(removedCount) || removedCount < 0 || removedCount > order.length) {
      throw new Error("Invalid removal count");
    }
    const removed = new Set(order.slice(0, removedCount).map(id => model.index.get(id)));
    if (removed.has(undefined) || removed.size !== removedCount) throw new Error("Invalid removal order");
    const component = new Int16Array(model.nodes.length).fill(-2);
    removed.forEach(i => { component[i] = -1; });
    const groups = [];
    for (let start = 0; start < model.nodes.length; start++) {
      if (component[start] !== -2) continue;
      const id = groups.length, queue = [start], members = [];
      component[start] = id;
      for (let cursor = 0; cursor < queue.length; cursor++) {
        const node = queue[cursor];
        members.push(node);
        for (const neighbor of model.adjacency[node]) {
          if (component[neighbor] === -2) {
            component[neighbor] = id;
            queue.push(neighbor);
          }
        }
      }
      groups.push(members);
    }
    groups.sort((a, b) => b.length - a.length || a[0] - b[0]);
    const ranked = new Int16Array(model.nodes.length).fill(-1);
    groups.forEach((group, rank) => group.forEach(i => { ranked[i] = rank; }));
    return {
      removed,
      component: ranked,
      sizes: groups.map(group => group.length),
      giantSize: groups[0]?.length || 0,
      outsideGiant: model.nodes.length - removedCount - (groups[0]?.length || 0),
    };
  }

  return { prepare, componentState };
});
