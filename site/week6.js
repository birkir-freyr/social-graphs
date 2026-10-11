(async function () {
  'use strict';
  const el = id => document.getElementById(id);
  let data, byId, nodeId = 'Storm_(Marvel_Comics)', selectedPair, mode = 'original', selectedTerm = 0;
  const caseNotes = {
    'Storm_(Marvel_Comics)': 'Human Torch shares the word “storm” because he is Johnny Storm. After filtering, inspect what takes the surname’s place.',
    'Emma_Frost': 'Emma Frost and Jack Frost share a rare surname. Compare their words and see how much of the apparent resemblance survives.',
    'Wolverine_(character)': 'A more demanding check: does a recognizable X-Men neighborhood survive after its character names disappear?',
    'Jean_Grey': 'Jean’s history overlaps with the Phoenix Force. The name filter can remove useful story information as well as misleading surnames.'
  };

  function drawRanks() {
    const node = byId.get(nodeId);
    for (const vocabulary of ['original', 'filtered']) {
      const list = el(`${vocabulary}-list`);
      list.replaceChildren();
      node[vocabulary].forEach((neighbor, rank) => {
        const li = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'rank-button';
        button.setAttribute('aria-pressed', String(neighbor.pair === selectedPair && mode === vocabulary));
        const label = document.createElement('span');
        label.className = 'rank-label';
        label.textContent = `${rank + 1}. ${byId.get(neighbor.target).name}`;
        const value = document.createElement('span');
        value.className = 'rank-value';
        value.textContent = neighbor.cosine.toFixed(3);
        const bar = document.createElement('span');
        bar.className = 'rank-bar';
        bar.style.width = `${neighbor.cosine * 100}%`;
        bar.setAttribute('aria-hidden', 'true');
        button.append(label, value, bar);
        button.addEventListener('click', () => {
          selectedPair = neighbor.pair; mode = vocabulary; selectedTerm = 0; render();
        });
        li.append(button); list.append(li);
      });
    }
  }

  function showExcerpt(container, excerpt) {
    container.replaceChildren();
    if (!excerpt) {container.textContent = 'No shared weighted term in this vocabulary.'; return;}
    const characters = Array.from(excerpt.text);
    const before = document.createTextNode(characters.slice(0, excerpt.match_start).join(''));
    const mark = document.createElement('mark');
    mark.textContent = characters.slice(excerpt.match_start, excerpt.match_end).join('');
    const after = document.createTextNode(characters.slice(excerpt.match_end).join(''));
    container.append(before, mark, after);
  }

  function showTerm(term, index) {
    selectedTerm = index;
    for (const button of el('term-buttons').querySelectorAll('button')) {
      button.setAttribute('aria-pressed', String(Number(button.dataset.index) === index));
    }
    for (const side of ['source', 'target']) {
      const excerpt = term?.[`${side}_excerpt`];
      showExcerpt(el(`${side}-passage`), excerpt);
      el(`${side}-offset`).textContent = excerpt
        ? `Frozen page · characters ${excerpt.start.toLocaleString()}–${excerpt.end.toLocaleString()}` : '';
    }
    el('term-note').textContent = term
      ? `“${term.term}” supplies ${(100 * term.share).toFixed(1)}% of this pair’s cosine in the selected vocabulary.${term.removed ? ' The capitalization filter removes this term type from every page.' : ''}`
      : 'This pair has no shared weighted vocabulary after filtering.';
  }

  function render() {
    const node = byId.get(nodeId);
    el('character').value = nodeId;
    el('chosen-name').textContent = node.name;
    el('case-note').textContent = caseNotes[nodeId] || 'Compare both lists, select a match, and inspect the words behind its score. Names and editorial phrasing can both matter.';
    el('retained-note').textContent = `${node.changed_first ? 'The first match changes.' : 'The first match stays.'} ${node.retained_top5} of the original five neighbors remain in the filtered top five.`;
    for (const button of document.querySelectorAll('[data-character]')) {
      button.setAttribute('aria-pressed', String(button.dataset.character === nodeId));
    }
    drawRanks();
    const view = Week6.inspect(data, nodeId, selectedPair, mode);
    el('pair-title').textContent = `${view.source.name} ↔ ${view.target.name}`;
    el('pair-caption').textContent = `${mode === 'original' ? 'All terms kept' : 'Mostly capitalized terms removed'} · cosine ${view.cosine.toFixed(3)} · ${view.rank ? `rank ${view.rank} for ${view.source.name}` : 'outside this view’s top five'} · ${view.linked ? 'Wikipedia link in at least one direction' : 'no direct Wikipedia link in the snapshot'}`;
    for (const button of document.querySelectorAll('[data-vocabulary]')) {
      button.setAttribute('aria-pressed', String(button.dataset.vocabulary === mode));
    }
    for (const side of ['source', 'target']) {
      el(`${side}-name`).textContent = view[side].name;
      el(`${side}-link`).href = view[side].url;
    }
    const terms = el('term-buttons');
    terms.replaceChildren();
    view.terms.forEach((term, index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.dataset.index = index;
      button.textContent = `${term.term} · ${(100 * term.share).toFixed(1)}%${term.removed ? ' · filtered out' : ''}`;
      button.addEventListener('click', () => showTerm(term, index));
      terms.append(button);
    });
    if (selectedTerm >= view.terms.length) selectedTerm = 0;
    showTerm(view.terms[selectedTerm], selectedTerm);
  }

  function choose(id) {
    nodeId = id; mode = 'original'; selectedPair = byId.get(id).original[0].pair; selectedTerm = 0; render();
  }

  try {
    const compressed = typeof DecompressionStream === 'function';
    const response = await fetch(`../data/week6.json${compressed ? '.gz' : ''}`);
    if (!response.ok) throw new Error(`Data request failed (${response.status})`);
    data = await (compressed
      ? new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json()
      : response.json());
    byId = new Map(data.nodes.map(node => [node.id, node]));
    el('character').replaceChildren();
    for (const node of [...data.nodes].sort((a, b) => a.name.localeCompare(b.name))) {
      const option = document.createElement('option');
      option.value = node.id; option.textContent = node.name; el('character').append(option);
    }
    el('character').disabled = false;
    el('character').addEventListener('change', event => choose(event.target.value));
    for (const button of document.querySelectorAll('[data-character]')) {
      button.disabled = false; button.addEventListener('click', () => choose(button.dataset.character));
    }
    for (const button of document.querySelectorAll('[data-vocabulary]')) {
      button.disabled = false;
      button.addEventListener('click', () => {mode = button.dataset.vocabulary; selectedTerm = 0; render();});
    }
    choose(nodeId);
  } catch (error) {
    el('week6-error').hidden = false;
    el('week6-error').textContent = 'The interactive matches could not load. The article, results table and downloadable figure still contain the findings. Reload to try again.';
    console.error(error);
  }
})();
