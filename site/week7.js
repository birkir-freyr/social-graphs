(async function(){
  'use strict';
  const $=id=>document.getElementById(id),presets=[...document.querySelectorAll('[data-preset]')];
  let data,current='surgeon',selected={left:null,right:null};
  const text=(id,value)=>{$(id).textContent=value;};
  function renderSide(side){
    const method=$(side+'-mode').value,q=Week7.query(data,current),r=q.results[method];
    if(!selected[side]||![...r.top5,r.target].filter(Boolean).some(h=>h.page===selected[side]))selected[side]=r.top5[0].page;
    text(side+'-target-rank',r.target_rank===null?'Absent':'#'+r.target_rank);
    text(side+'-target-note',q.target_present?'rank of '+q.target_name:'The intended page is not in this corpus.');
    const list=$(side+'-list');list.replaceChildren();
    for(const hit of r.top5){
      const li=document.createElement('li'),button=document.createElement('button'),name=document.createElement('span'),score=document.createElement('span');
      button.type='button';button.className='result-button';button.setAttribute('aria-pressed',String(selected[side]===hit.page));name.className='result-name';name.textContent=hit.rank+'. '+hit.name+(hit.page===q.target?' · intended page':'');score.className='result-score';score.textContent=hit.score.toFixed(3);button.append(name,score);button.addEventListener('click',()=>{selected[side]=hit.page;renderSide(side);});li.append(button);list.append(li);
    }
    const targetButton=$(side+'-target');targetButton.disabled=!r.target;targetButton.textContent=r.target?'Inspect intended page (#'+r.target_rank+')':'Intended page is absent';
    const v=Week7.inspect(data,current,method,selected[side]),expanded=$(side+'-context').checked,source=expanded?v.excerpt.context:v.excerpt;
    text(side+'-source-title',v.hit.name);text(side+'-source-note',`Examining rank ${v.hit.rank}${v.outsideTop5?' · outside the shown top five':''}${v.isTarget?' · predeclared intended page':''}. Cosine ${v.hit.score.toFixed(3)}.`);
    text(side+'-offset',`Frozen page · characters ${source.start}–${source.end} · end excluded`);text(side+'-source',source.text);$(side+'-link').href=v.hit.url;
    text(side+'-evidence-rule',method==='dense_page'?'This is the page’s best 180-word passage for this query, shown for inspection. Its displayed ranking score comes from the full page mean.':method==='tfidf'?'This is the page’s lexically closest 180-word passage for inspection. Its ranking score uses the full page.':`The original ${method==='dense_60'?'60':'180'}-word passage defines this page’s max-passage score. Expanded context does not change the score.`);
  }
  function render(){
    const q=Week7.query(data,current);text('query-text',q.query);text('target-name',q.target_name);text('query-note',q.target_present?'The intended page was recorded before the original search run. It is a diagnostic target; other pages may also be relevant.':'The intended Daredevil page is absent. These results cannot establish that the corpus contains the answer.');
    $('query-select').value=current;renderSide('left');renderSide('right');
    for(const b of presets){const p=data.presets[Number(b.dataset.preset)];b.setAttribute('aria-pressed',String(p.id===current&&p.left===$('left-mode').value&&p.right===$('right-mode').value));}
  }
  function resetSelection(){selected={left:null,right:null};$('left-context').checked=false;$('right-context').checked=false;}
  try{
    let response;
    if(typeof DecompressionStream!=='undefined'){
      try{const r=await fetch('../data/week7.json.gz');if(!r.ok)throw Error('gzip unavailable');data=await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).json();}
      catch{response=await fetch('../data/week7.json');}
    }else response=await fetch('../data/week7.json');
    if(response){if(!response.ok)throw Error('Data request failed');data=await response.json();}
    const select=$('query-select');select.replaceChildren();for(const q of data.queries){const option=document.createElement('option');option.value=q.id;option.textContent=q.query;select.append(option);}
    for(const side of ['left','right']){
      const menu=$(side+'-mode');menu.replaceChildren();for(const method of Week7.methods){const option=document.createElement('option');option.value=method;option.textContent=data.methods.labels[method];menu.append(option);}
      menu.value=side==='left'?'tfidf':'dense_180';menu.addEventListener('change',()=>{selected[side]=null;render();});
      $(side+'-target').addEventListener('click',()=>{const q=Week7.query(data,current);selected[side]=q.target;renderSide(side);});
      $(side+'-context').addEventListener('change',()=>renderSide(side));
    }
    select.addEventListener('change',()=>{current=select.value;resetSelection();render();});
    for(const b of presets)b.addEventListener('click',()=>{const p=data.presets[Number(b.dataset.preset)];current=p.id;$('left-mode').value=p.left;$('right-mode').value=p.right;resetSelection();render();});
    for(const e of [...presets,select,$('left-mode'),$('right-mode'),$('left-context'),$('right-context')])e.disabled=false;
    render();
  }catch(error){text('week7-error','The comparison data could not load. The article, rank table, standalone figure and downloads preserve the results.');$('week7-error').hidden=false;console.error(error);}
})();
