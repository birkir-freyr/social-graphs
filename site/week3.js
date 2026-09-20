(function () {
  "use strict";

  const byId = id => document.getElementById(id);
  const canvas = byId("removal-map");
  const context = canvas.getContext("2d");
  const slider = byId("removal-count");
  const strategyButtons = [...document.querySelectorAll("[data-strategy]")];
  const controls = [...strategyButtons, slider, byId("play-removals"), byId("reset-removals")];
  let data, model, strategy = "betweenness", removedCount = 1, timer = null;

  function svgElement(name, attrs = {}, content) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    if (content !== undefined) element.textContent = content;
    return element;
  }

  function setPressed(key) {
    strategyButtons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.strategy === key)));
  }

  function formatName(id) {
    return model.nodes[model.index.get(id)].name;
  }

  function state() {
    return RemovalLab.componentState(model, data.strategies[strategy].order, removedCount);
  }

  function drawMap(current) {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    const xs = model.nodes.map(node => node.x), ys = model.nodes.map(node => node.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const points = model.nodes.map(node => ({
      x: 28 + (node.x - minX) / (maxX - minX) * (width - 56),
      y: 28 + (node.y - minY) / (maxY - minY) * (height - 56),
      r: 1.8 + Math.sqrt(node.degree) * 0.45,
    }));

    context.beginPath();
    for (const [source, target] of data.graph.edges) {
      const a = model.index.get(source), b = model.index.get(target);
      if (current.component[a] < 0 || current.component[b] < 0) continue;
      context.moveTo(points[a].x, points[a].y);
      context.lineTo(points[b].x, points[b].y);
    }
    context.strokeStyle = "rgba(186, 211, 198, .13)";
    context.lineWidth = 0.65;
    context.stroke();

    points.forEach((point, i) => {
      context.beginPath();
      context.arc(point.x, point.y, point.r, 0, Math.PI * 2);
      if (current.component[i] === -1) context.fillStyle = "rgba(129, 149, 140, .16)";
      else if (current.component[i] === 0) context.fillStyle = "#9fc9b7";
      else context.fillStyle = "#f5c263";
      context.fill();
    });

    if (removedCount) {
      const lastId = data.strategies[strategy].order[removedCount - 1];
      const last = model.index.get(lastId), point = points[last];
      context.beginPath();
      context.arc(point.x, point.y, point.r + 6, 0, Math.PI * 2);
      context.strokeStyle = "#ff8055";
      context.lineWidth = 2;
      context.stroke();
    }
  }

  function linePath(values, x, y) {
    return values.map((value, i) => `${i ? "L" : "M"}${x(i)},${y(value)}`).join(" ");
  }

  function drawChart() {
    const width = 960, height = 360, left = 60, right = 30, top = 34, bottom = 56;
    const x = value => left + value / data.maxRemovals * (width - left - right);
    const y = value => height - bottom - value / data.graph.stats.nodes * (height - top - bottom);
    const svg = svgElement("svg", {viewBox: `0 0 ${width} ${height}`, role: "img", "aria-labelledby": "attack-title attack-desc"});
    svg.append(svgElement("title", {id: "attack-title"}, "Largest connected component under character removal"));
    svg.append(svgElement("desc", {id: "attack-desc"}, `After ${removedCount} adaptive ${strategy} removals, the largest component has ${data.strategies[strategy].curve[removedCount]} characters.`));

    [0, 50, 100, 150, 200, 250, 277].forEach(tick => {
      svg.append(svgElement("line", {x1: left, x2: width - right, y1: y(tick), y2: y(tick), stroke: "#c7d0c7"}));
      svg.append(svgElement("text", {x: left - 10, y: y(tick) + 5, "text-anchor": "end", fill: "#596761", "font-size": 13}, tick));
    });
    [0, 20, 40, 60, 80, 100].forEach(tick => {
      svg.append(svgElement("text", {x: x(tick), y: height - bottom + 25, "text-anchor": "middle", fill: "#596761", "font-size": 13}, tick));
    });

    const random = data.random.summary;
    const band = [...random.map(point => `${x(point.removed)},${y(point.q95)}`), ...random.slice().reverse().map(point => `${x(point.removed)},${y(point.q05)}`)].join(" ");
    svg.append(svgElement("polygon", {points: band, fill: "#cbd8cc", opacity: .72}));
    svg.append(svgElement("path", {d: linePath(random.map(point => point.median), x, y), fill: "none", stroke: "#718079", "stroke-width": 2, "stroke-dasharray": "6 5"}));

    const series = [
      ["degree", "#146e61"],
      ["betweenness", "#dc532e"],
    ];
    for (const [key, color] of series) {
      svg.append(svgElement("path", {d: linePath(data.strategies[key].curve, x, y), fill: "none", stroke: color, "stroke-width": key === strategy ? 4 : 2.5, opacity: key === strategy ? 1 : .55}));
      svg.append(svgElement("circle", {cx: x(removedCount), cy: y(data.strategies[key].curve[removedCount]), r: key === strategy ? 6 : 4, fill: color, stroke: "#f4f5f1", "stroke-width": 2}));
    }
    svg.append(svgElement("line", {x1: x(removedCount), x2: x(removedCount), y1: top, y2: height - bottom, stroke: "#17312d", "stroke-width": 1.5, "stroke-dasharray": "3 4"}));
    svg.append(svgElement("text", {x: (left + width - right) / 2, y: height - 8, "text-anchor": "middle", fill: "#17312d", "font-size": 15}, "Characters removed"));
    svg.append(svgElement("text", {x: 17, y: (top + height - bottom) / 2, transform: `rotate(-90 17 ${(top + height - bottom) / 2})`, "text-anchor": "middle", fill: "#17312d", "font-size": 14}, "Largest component"));
    byId("attack-chart").replaceChildren(svg);
  }

  function update() {
    const current = state();
    const attack = data.strategies[strategy];
    const last = removedCount ? attack.order[removedCount - 1] : null;
    const next = removedCount < attack.order.length ? attack.order[removedCount] : null;
    slider.value = removedCount;
    byId("removed-output").value = removedCount;
    byId("giant-size").textContent = current.giantSize;
    byId("fragment-count").textContent = current.sizes.length;
    byId("outside-count").textContent = current.outsideGiant;
    byId("last-removed").textContent = last ? formatName(last) : "Nobody yet";
    byId("last-removed-detail").textContent = last ? formatName(last) : "Nobody yet";
    byId("next-target").textContent = next ? formatName(next) : "End of sequence";
    byId("strategy-note").textContent = attack.description;
    byId("step-reading").textContent = removedCount
      ? `${formatName(last)} was removed at step ${removedCount}. ${current.giantSize} of the ${data.graph.stats.nodes - removedCount} remaining characters are still in the largest component; ${current.outsideGiant} sit outside it.`
      : `All ${data.graph.stats.nodes} characters begin in one connected component.`;
    drawMap(current);
    drawChart();
  }

  function stop() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    byId("play-removals").textContent = "▶";
    byId("play-removals").setAttribute("aria-label", "Play removals");
    byId("play-removals").title = "Play removals";
  }

  function play() {
    if (timer !== null) {
      stop();
      return;
    }
    if (removedCount >= data.maxRemovals) removedCount = 0;
    byId("play-removals").textContent = "Ⅱ";
    byId("play-removals").setAttribute("aria-label", "Pause removals");
    byId("play-removals").title = "Pause removals";
    timer = window.setInterval(() => {
      removedCount += 1;
      update();
      if (removedCount >= data.maxRemovals) stop();
    }, 260);
  }

  async function init() {
    try {
      const response = await fetch("../data/week3.json");
      if (!response.ok) throw new Error("Unable to load Week 3 data");
      data = await response.json();
      model = RemovalLab.prepare(data);
      slider.max = data.maxRemovals;
      strategyButtons.forEach(button => button.addEventListener("click", () => {
        stop();
        strategy = button.dataset.strategy;
        setPressed(strategy);
        update();
      }));
      slider.addEventListener("input", () => {
        stop();
        removedCount = Number(slider.value);
        update();
      });
      byId("play-removals").addEventListener("click", play);
      byId("reset-removals").addEventListener("click", () => { stop(); removedCount = 0; update(); });
      window.addEventListener("resize", () => drawMap(state()));
      controls.forEach(control => { control.disabled = false; });
      update();
    } catch (error) {
      byId("week3-error").hidden = false;
      byId("week3-error").textContent = "The interactive data could not be loaded. Reload to try again; the article and tables below still contain the results.";
      console.error("Week 3 data:", error);
    }
  }

  init();
})();
