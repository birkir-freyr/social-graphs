/* The graph is a view of measured shared-text pairs, not a text-similarity score. */
(async function () {
  'use strict';
  const el = id => document.getElementById(id);
  const canvas = el('shared-map');
  const ctx = canvas.getContext('2d');
  const colors = ['#fa784d', '#96bbae', '#bea7e4', '#e7cb85', '#83bbd1'];
  let data, byId, threshold = 30, selected = 0, view, points = new Map();
  let logicalWidth = 0, logicalHeight = 0;

  function select(index) {
    selected = index;
    const edge = data.edges[index];
    el('pair-select').value = String(index);
    el('passage-title').textContent = `${byId.get(edge.source).name} ↔ ${byId.get(edge.target).name}`;
    el('passage-length').textContent = `${edge.length} consecutive tokens`;
    for (const side of ['source', 'target']) {
      const node = byId.get(edge[side]), excerpt = edge[`${side}_excerpt`];
      el(`${side}-name`).textContent = node.name;
      el(`${side}-text`).textContent = excerpt.text;
      el(`${side}-offset`).textContent = `Frozen page · characters ${excerpt.start.toLocaleString()}–${excerpt.end.toLocaleString()} (zero-based, end exclusive)`;
      el(`${side}-link`).href = node.url;
    }
    el('match-note').textContent = (edge.raw_equal
      ? 'The extracted raw passages are identical, including punctuation and capitalization.'
      : 'The token sequences match after lowercasing. The raw passages retain differences in punctuation, capitalization or whitespace.')
      + ' These excerpts are frozen; live Wikipedia pages may have changed.';
    for (const button of document.querySelectorAll('[data-case]')) {
      button.setAttribute('aria-pressed', String(data.case_studies[Number(button.dataset.case)].edge_index === index));
    }
    draw();
  }

  function update() {
    view = Week5.analyze(data, threshold);
    el('threshold-value').value = String(threshold);
    el('threshold').value = String(threshold);
    el('pair-count').textContent = view.edges.length;
    el('page-count').textContent = view.active.size;
    el('unshown-count').textContent = data.meta.documents - view.active.size;
    canvas.setAttribute('aria-label', `Shared-text network: ${view.edges.length} pairs between ${view.active.size} pages at a ${threshold}-token minimum. Use the pair selector below to inspect every matching passage.`);
    for (const button of document.querySelectorAll('[data-threshold]')) {
      button.setAttribute('aria-pressed', String(Number(button.dataset.threshold) === threshold));
    }
    const selector = el('pair-select');
    selector.replaceChildren();
    for (const edge of view.edges) {
      const index = data.edges.indexOf(edge);
      const option = document.createElement('option');
      option.value = index;
      option.textContent = `${edge.length} tokens · ${byId.get(edge.source).name} ↔ ${byId.get(edge.target).name}`;
      selector.append(option);
    }
    if (!view.edges.includes(data.edges[selected])) selected = data.edges.indexOf(view.edges[0]);
    select(selected);
  }

  function draw() {
    if (!data || !view) return;
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    logicalWidth = rect.width; logicalHeight = rect.height;
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, logicalWidth, logicalHeight);
    points = new Map(view.nodes.map(node => [node.id, {
      x: 12 + node.x * (logicalWidth - 24), y: 20 + node.y * (logicalHeight - 40), node
    }]));
    const chosen = data.edges[selected];
    for (const edge of view.edges) {
      const a = points.get(edge.source), b = points.get(edge.target);
      const emphasized = edge === chosen;
      ctx.strokeStyle = emphasized ? '#ffcba7' : '#668b7b';
      ctx.lineWidth = emphasized ? 3 : Math.min(2.6, .5 + edge.length / 75);
      ctx.globalAlpha = emphasized ? 1 : .6;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (const [id, point] of points) {
      const emphasized = id === chosen.source || id === chosen.target;
      ctx.fillStyle = emphasized ? '#ffcba7' : colors[point.node.group % colors.length];
      ctx.beginPath(); ctx.arc(point.x, point.y, emphasized ? 6 : 4, 0, Math.PI * 2); ctx.fill();
      if (emphasized) {ctx.strokeStyle = '#edf2e8'; ctx.lineWidth = 1; ctx.stroke();}
    }
    // Selected endpoints have first claim on label space; collision checking
    // leaves the graph usable on narrow screens without hiding any data.
    const labels = [], ordered = [...points.entries()].sort(([a], [b]) => {
      const priority = id => id === chosen.source || id === chosen.target ? 0 : 1;
      return priority(a) - priority(b) || a.localeCompare(b);
    });
    ctx.font = '11px sans-serif'; ctx.textBaseline = 'middle';
    for (const [id, point] of ordered) {
      const emphasized = id === chosen.source || id === chosen.target;
      const text = point.node.name.length > 22 ? `${point.node.name.slice(0, 21)}…` : point.node.name;
      const width = ctx.measureText(text).width;
      let x = point.x + 9, y = point.y - 12;
      x = Math.max(3, Math.min(x, logicalWidth - width - 3));
      const box = {left: x - 3, right: x + width + 3, top: y - 9, bottom: y + 9};
      const collision = labels.some(b => box.left < b.right && box.right > b.left && box.top < b.bottom && box.bottom > b.top);
      if (collision && !emphasized) continue;
      if (collision) {y += 25; box.top += 25; box.bottom += 25;}
      ctx.fillStyle = '#122c29'; ctx.fillRect(x - 3, y - 8, width + 6, 16);
      ctx.fillStyle = emphasized ? '#ffcba7' : '#d4e4d8'; ctx.fillText(text, x, y);
      labels.push(box);
    }
  }

  canvas.addEventListener('click', event => {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    let nearest, distance = 18;
    for (const [id, point] of points) {
      const d = Math.hypot(x - point.x, y - point.y);
      if (d < distance) {nearest = id; distance = d;}
    }
    if (nearest) {
      const edge = view.edges.find(edge => edge.source === nearest || edge.target === nearest);
      select(data.edges.indexOf(edge));
    }
  });

  try {
    const response = await fetch('../data/week5.json');
    if (!response.ok) throw new Error(`Data request failed (${response.status})`);
    data = await response.json();
    byId = new Map(data.nodes.map(node => [node.id, node]));
    el('threshold').addEventListener('input', event => {threshold = Number(event.target.value); update();});
    el('pair-select').addEventListener('change', event => select(Number(event.target.value)));
    for (const button of document.querySelectorAll('[data-threshold]')) {
      button.addEventListener('click', () => {threshold = Number(button.dataset.threshold); update();});
      button.disabled = false;
    }
    for (const button of document.querySelectorAll('[data-case]')) {
      button.addEventListener('click', () => {
        const index = data.case_studies[Number(button.dataset.case)].edge_index;
        if (data.edges[index].length < threshold) threshold = 30;
        selected = index; update();
      });
      button.disabled = false;
    }
    el('threshold').disabled = false; el('pair-select').disabled = false;
    new ResizeObserver(draw).observe(canvas);
    update();
  } catch (error) {
    const message = el('week5-error');
    message.hidden = false;
    message.textContent = 'The interactive figure could not load. The article, threshold table and downloadable figure still contain the findings. Please reload the page to try again.';
    console.error(error);
  }
})();
