(function(root){
  'use strict';
  const methods=['tfidf','dense_page','dense_180','dense_60'];
  function query(data,id){const q=data.queries.find(q=>q.id===id);if(!q)throw Error('Unknown query');return q;}
  function inspect(data,id,method,page){
    if(!methods.includes(method))throw Error('Unknown retrieval method');
    const q=query(data,id),r=q.results[method];
    const hit=r.top5.find(h=>h.page===page)||(r.target?.page===page?r.target:null);
    if(!hit)throw Error('Unknown result');
    return {query:q,result:r,hit,excerpt:data.excerpts[hit.excerpt],isTarget:hit.page===q.target,outsideTop5:hit.rank>5};
  }
  function targetRanks(data){return data.queries.map(q=>({id:q.id,present:q.target_present,...Object.fromEntries(methods.map(m=>[m,q.results[m].target_rank]))}));}
  const api={methods,query,inspect,targetRanks};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Week7=api;
})(typeof window==='undefined'?globalThis:window);
