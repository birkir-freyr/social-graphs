(async function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const fmt = n => n.toLocaleString('en-US');
  const colors = ['#a44427', '#826ba4', '#196b61', '#85641b', '#356c9a', '#b35070', '#527332', '#a95315', '#66578c'];
  const labels = ['Kant / Hegel', 'Aquinas / Augustine', 'Marx / Locke', 'Aristotle / Plato',
    'Russell / Husserl', 'Leibniz / Descartes', 'Madhva / Buddha', 'Avicenna / Averroes', 'Confucius / Mencius'];
  try {
    const response = await fetch('../data/week4.json?v=1', {cache: 'no-cache'});
    if (!response.ok) throw new Error(`Data request returned ${response.status}`);
    const data = await response.json();
    const byId = new Map(data.nodes.map(n => [n.id, n]));
    const critical = data.critical;
    const detailNodes = new Set(critical.fragments.flatMap(f => f.nodes));
    const fragment = new Map(critical.fragments.flatMap((f, i) => f.nodes.map(n => [n, i])));
    const fragmentColors = ['#a8c9ae', '#c9b8f0', '#ffc47c'];
    const detailBefore = Week4.analyze(data, critical.score, true);
    const detailAfter = Week4.analyze(data, critical.score);
    const special = new Set(['Augustine_of_Hippo', 'Erasmus', 'Nicolas_Malebranche',
      'Aristotle', 'Friedrich_Nietzsche', 'Ambrose', 'Pope_Gregory_I']);
    let cut = false, alpha = .2, selected = 'Augustine_of_Hippo';
    let view = Week4.analyze(data, alpha);
    const hitTargets = new Map();
    const observer = new ResizeObserver(() => drawAll());
    const radius = (n, detail) => Math.max(detail ? 2.5 : 1.5, Math.sqrt(n.strength) * (detail ? .48 : .24));

    function paint(canvas, nodes, edges, positions, color, dark, labelIds, chosen) {
      const width = canvas.clientWidth, height = canvas.clientHeight;
      if (!width || !height) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);
      const px = 38, py = 45;
      const values = Object.values(positions);
      const xmin = Math.min(...values.map(p => p[0])), xmax = Math.max(...values.map(p => p[0]));
      const ymin = Math.min(...values.map(p => p[1])), ymax = Math.max(...values.map(p => p[1]));
      const scale = Math.min((width - 2 * px) / (xmax - xmin || 1), (height - 2 * py) / (ymax - ymin || 1));
      const point = id => [width / 2 + (positions[id][0] - (xmin + xmax) / 2) * scale,
        height / 2 + (positions[id][1] - (ymin + ymax) / 2) * scale];
      ctx.strokeStyle = dark ? 'rgba(182,204,190,.28)' : 'rgba(61,88,69,.17)';
      ctx.lineWidth = dark ? 1 : .6;
      ctx.beginPath();
      for (const e of edges) {
        if (!positions[e.source] || !positions[e.target]) continue;
        ctx.moveTo(...point(e.source)); ctx.lineTo(...point(e.target));
      }
      ctx.stroke();
      if (dark && !cut) {
        ctx.strokeStyle = '#ff8757'; ctx.lineWidth = 3; ctx.setLineDash([6, 4]);
        ctx.beginPath();
        for (const e of critical.removed) {
          ctx.moveTo(...point(e.source)); ctx.lineTo(...point(e.target));
        }
        ctx.stroke(); ctx.setLineDash([]);
      }
      const hits = [];
      for (const n of [...nodes].sort((a, b) => a.strength - b.strength)) {
        const [x, y] = point(n.id), r = radius(n, dark);
        ctx.fillStyle = color(n);
        ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fill();
        if (n.id === chosen) {
          ctx.strokeStyle = dark ? '#fff' : '#17312d'; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.arc(x, y, r + 3, 0, 2 * Math.PI); ctx.stroke();
        }
        hits.push({id: n.id, x, y, r});
      }
      hitTargets.set(canvas.id, hits);
      const boxes = [];
      ctx.font = `${dark ? 12 : 10}px system-ui`;
      // Keep labels legible; skip lower-priority labels when their boxes collide.
      for (const n of [...nodes].sort((a, b) => (b.id === chosen) - (a.id === chosen) || b.strength - a.strength)) {
        if (!labelIds.has(n.id) && n.id !== chosen) continue;
        const [x, y] = point(n.id), w = ctx.measureText(n.name).width;
        const tx = Math.max(5, Math.min(width - w - 5, x + radius(n, dark) + 5));
        let ty = y - 7;
        if (boxes.some(b => tx < b.x + b.w && tx + w > b.x && ty - 12 < b.y + 4 && ty + 4 > b.y - 12)) ty = y + 19;
        if (boxes.some(b => tx < b.x + b.w && tx + w > b.x && ty - 12 < b.y + 4 && ty + 4 > b.y - 12)) continue;
        boxes.push({x: tx, y: ty, w});
        ctx.lineWidth = 4; ctx.strokeStyle = dark ? '#122c29' : '#e7ece3';
        ctx.strokeText(n.name, tx, ty); ctx.fillStyle = dark ? '#f0f3e9' : '#17312d'; ctx.fillText(n.name, tx, ty);
      }
    }
    const overviewPositions = Object.fromEntries(data.nodes.map(n => [n.id, [n.x, n.y]]));
    function drawAll() {
      const dview = cut ? detailAfter : detailBefore;
      paint($('fracture-map'), data.nodes.filter(n => detailNodes.has(n.id)),
        dview.edges.filter(e => detailNodes.has(e.source) && detailNodes.has(e.target)), critical.positions,
        n => fragmentColors[fragment.get(n.id)], true, special, null);
      const visible = data.nodes.filter(n => view.active.has(n.id) || $('show-isolates').checked);
      const top = new Set(visible.filter(n => view.active.has(n.id)).sort((a, b) => b.strength - a.strength).slice(0, 10).map(n => n.id));
      paint($('backbone-map'), visible, view.edges, overviewPositions,
        n => view.active.has(n.id) ? colors[n.community] : '#aab5a5', false, top, selected);
    }
    function selectNode(id) {
      selected = id;
      const n = byId.get(id);
      $('philosopher').value = id;
      const retained = view.edges.filter(e => e.source === id || e.target === id).length;
      const area = $('node-selection'); area.replaceChildren();
      const link = document.createElement('a'); link.href = n.url; link.textContent = n.name;
      area.append(link, document.createElement('br'),
        `${fmt(retained)} / ${fmt(n.degree)} links remain. Original strength: ${fmt(n.strength)}.`,
        document.createElement('br'), `Community: ${labels[n.community]}.`);
      if (!retained) area.append(document.createElement('br'), 'Isolated at this setting; use “Show isolated nodes” to locate it.');
      drawAll();
    }
    function update() {
      view = Week4.analyze(data, alpha);
      $('alpha').value = String(alpha); $('alpha-value').textContent = alpha.toFixed(2);
      $('retained-links').textContent = fmt(view.edges.length);
      $('active-nodes').textContent = fmt(view.active.size);
      $('giant-nodes').textContent = fmt(view.giant);
      $('isolated-nodes').textContent = fmt(view.isolates);
      $('backbone-map').setAttribute('aria-label', `Backbone at alpha ${alpha.toFixed(2)}: ${view.edges.length} links, ${view.active.size} active philosophers, largest component ${view.giant}, ${view.isolates} isolates.`);
      document.querySelectorAll('[data-alpha]').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.alpha) === alpha)));
      renderChart(); selectNode(selected);
    }
    function renderChart() {
      const width = 1000, height = 230, l = 55, r = 20, top = 18, bottom = 40;
      const x = a => l + a * (width - l - r);
      const y = n => height - bottom - (n / data.nodes.length) * (height - top - bottom);
      let path = `M${x(0)},${y(1)}`;
      for (const e of data.curve) path += `H${x(e.score)}V${y(e.above)}`;
      path += `H${x(1)}`;
      const ticks = [0, 500, 1000, 1374].map(n => `<path d="M${l},${y(n)}H${width-r}" stroke="#cbd2c9"/><text x="${l-9}" y="${y(n)+4}" text-anchor="end">${fmt(n)}</text>`).join('');
      const xticks = [0, .2, .4, .6, .8, 1].map(a => `<text x="${x(a)}" y="${height-18}" text-anchor="middle">${a.toFixed(1)}</text>`).join('');
      $('sweep-chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Largest component rises from one to 1374 as filtering is relaxed. Largest single drop on tightening is 108 to 65 near alpha 0.0471." style="font:12px system-ui;fill:#596761">${ticks}${xticks}<path d="${path}" fill="none" stroke="#17312d" stroke-width="2"/><path d="M${x(critical.score)},${y(critical.below)}V${y(critical.above)}" stroke="#dc532e" stroke-width="5"/><circle cx="${x(critical.score)}" cy="${y(critical.above)}" r="5" fill="#dc532e"/><path d="M${x(critical.score)},${y(critical.above)-9}v-25h90" stroke="#dc532e" fill="none"/><text x="${x(critical.score)+96}" y="${y(critical.above)-31}" fill="#a63d1f">108 → 65</text><path d="M${x(alpha)},${top}V${height-bottom}" stroke="#146e61" stroke-dasharray="3 4"/><circle cx="${x(alpha)}" cy="${y(view.giant)}" r="5" fill="#146e61"/><text x="${width-r}" y="${height-2}" text-anchor="end">α → more links retained</text></svg>`;
    }
    for (const [i, label] of labels.entries()) {
      const span = document.createElement('span'), dot = document.createElement('i');
      dot.style.background = colors[i]; span.append(dot, `${label} · ${data.communities[i].size}`); $('community-legend').append(span);
    }
    $('philosopher').replaceChildren(...[...data.nodes].sort((a, b) => a.name.localeCompare(b.name)).map(n => {
      const option = document.createElement('option'); option.value = n.id; option.textContent = n.name; return option;
    }));
    $('philosopher').addEventListener('change', e => selectNode(e.target.value));
    $('cut-links').addEventListener('click', () => {
      cut = !cut;
      $('cut-links').textContent = cut ? 'Restore the two links' : 'Cut the two links';
      $('cut-links').setAttribute('aria-pressed', String(cut));
      $('fracture-largest').textContent = cut ? '65' : '108';
      $('fracture-reading').textContent = cut ? 'Largest of three fragments: 65 + 40 + 3.' : 'One connected group before the cut.';
      $('fracture-state').textContent = cut ? 'AT THE THRESHOLD · THREE COMPONENTS' : 'JUST ABOVE THE THRESHOLD · 108 CONNECTED';
      $('fracture-map').setAttribute('aria-label', cut ? 'The former 108-person component has split into fragments of 65, 40 and 3.' : '108 philosophers in one connected component, with Augustine’s two bridge links highlighted.');
      drawAll();
    });
    $('alpha').addEventListener('input', e => {alpha = Number(e.target.value); update();});
    document.querySelectorAll('[data-alpha]').forEach(b => b.addEventListener('click', () => {alpha = Number(b.dataset.alpha); update();}));
    $('show-isolates').addEventListener('change', drawAll);
    for (const id of ['fracture-map', 'backbone-map']) {
      $(id).addEventListener('click', event => {
        const bounds = $(id).getBoundingClientRect();
        const x = event.clientX - bounds.left, y = event.clientY - bounds.top;
        const hit = (hitTargets.get(id) || []).map(n => ({...n, distance: Math.hypot(n.x - x, n.y - y)}))
          .filter(n => n.distance < n.r + 8).sort((a, b) => a.distance - b.distance)[0];
        if (!hit) return;
        if (id === 'backbone-map') selectNode(hit.id);
        else {
          const n = byId.get(hit.id);
          $('detail-selection').textContent = `${n.name} · original degree ${n.degree} · strength ${n.strength} · eventual fragment: ${critical.fragments[fragment.get(n.id)].size} people.`;
        }
      });
      observer.observe($(id));
    }
    $('cut-links').disabled = false; $('alpha').disabled = false; $('philosopher').disabled = false;
    document.querySelectorAll('[data-alpha]').forEach(b => {b.disabled = false;});
    update();
  } catch (error) {
    $('week4-error').hidden = false;
    $('week4-error').textContent = 'The interactive data could not load. Try reloading, or use the figure and downloads below. For local previews, serve this folder over HTTP.';
    console.error(error);
  }
})();
