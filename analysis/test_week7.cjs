const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const api=require('../site/week7-core.js');const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../site/data/week7.json'),'utf8'));
test('every saved result exposes the correct page, source text and target status',()=>{
 for(const q of data.queries)for(const method of api.methods){const r=q.results[method];for(const h of [...r.top5,...(r.target?[r.target]:[])]){const v=api.inspect(data,q.id,method,h.page);assert.equal(v.hit.page,h.page);assert.equal(v.excerpt.page,h.page);assert.equal(v.isTarget,h.page===q.target);assert.equal(v.outsideTop5,h.rank>5);}}
 assert.throws(()=>api.query(data,'missing'));assert.throws(()=>api.inspect(data,'surgeon','bad','Doctor_Strange'));assert.throws(()=>api.inspect(data,'surgeon','tfidf','missing'));
});
test('ranks preserve an absent target and an intended page outside top five',()=>{
 const ranks=api.targetRanks(data);assert.equal(ranks.length,8);assert.deepEqual(ranks.find(q=>q.id==='blind_lawyer'),{id:'blind_lawyer',present:false,tfidf:null,dense_page:null,dense_180:null,dense_60:null});
 const v=api.inspect(data,'russian_spy','dense_page','Black_Widow_(Natasha_Romanova)');assert.equal(v.hit.rank,20);assert.equal(v.outsideTop5,true);assert.equal(v.isTarget,true);
});
class Element{
 constructor(dataset={}){this.dataset=dataset;this.children=[];this.events={};this.attributes={};this.disabled=false;this.hidden=true;this.value='';this.checked=false;this.textContent='';}
 setAttribute(k,v){this.attributes[k]=v;}addEventListener(k,v){this.events[k]=v;}replaceChildren(...x){this.children=x;}append(...x){this.children.push(...x);}click(){if(!this.disabled)this.events.click();}
}
async function start(failed=false){
 const html=fs.readFileSync(path.join(__dirname,'../site/weeks/week7.html'),'utf8');const els=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));const presets=[0,1,2,3].map(i=>new Element({preset:String(i)}));for(const e of [...presets,...['query-select','left-mode','right-mode','left-target','right-target','left-context','right-context'].map(id=>els.get(id))])e.disabled=true;
 const errors=[];const document={getElementById:id=>{assert.ok(els.has(id),id);return els.get(id);},querySelectorAll:()=>presets,createElement:()=>new Element()};const context=vm.createContext({document,Week7:api,fetch:async()=>({ok:!failed,json:async()=>data}),console:{error:e=>errors.push(e)}});await vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/week7.js'),'utf8'),context);return {els,presets,errors};
}
test('preset comparisons, outside-top-five inspection and source-context toggle work',async()=>{
 const {els,presets,errors}=await start();assert.equal(errors.length,0);assert.equal(els.get('query-select').children.length,8);assert.equal(els.get('left-target-rank').textContent,'#3');assert.equal(els.get('right-target-rank').textContent,'#1');assert.equal(els.get('left-source-title').textContent,'Coldblood');
 presets[0].click();assert.equal(els.get('left-target-rank').textContent,'#20');els.get('left-target').click();assert.match(els.get('left-source-title').textContent,/Black Widow/);assert.match(els.get('left-source-note').textContent,/outside the shown top five/);
 presets[2].click();assert.equal(els.get('left-target-rank').textContent,'#6');assert.equal(els.get('right-target-rank').textContent,'#1');assert.match(els.get('left-source-title').textContent,/John Jameson/);
 presets[3].click();assert.match(els.get('right-source').textContent,/not extraterrestrial/);els.get('right-mode').value='dense_60';els.get('right-mode').events.change();assert.doesNotMatch(els.get('right-source').textContent,/not extraterrestrial/);els.get('right-context').checked=true;els.get('right-context').events.change();assert.match(els.get('right-source').textContent,/not extraterrestrial/);
});
test('absent target disables target inspection while returned results remain inspectable',async()=>{
 const {els}=await start();els.get('query-select').value='blind_lawyer';els.get('query-select').events.change();assert.equal(els.get('left-target-rank').textContent,'Absent');assert.equal(els.get('left-target').disabled,true);assert.equal(els.get('right-target').disabled,true);assert.equal(els.get('right-list').children.length,5);assert.match(els.get('query-note').textContent,/absent/);
});
test('data failure preserves static evidence and disables the controls',async()=>{
 const {els,presets,errors}=await start(true);assert.equal(errors.length,1);assert.equal(els.get('week7-error').hidden,false);assert.match(els.get('week7-error').textContent,/rank table/);assert.ok(presets.every(x=>x.disabled));assert.equal(els.get('query-select').disabled,true);
});
