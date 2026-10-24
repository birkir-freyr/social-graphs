"""Exercise 7.13: same query, different results.

Run python analysis/build_week7.py. All model vectors are bundled, so the
measurement build is offline. Optional encode_week7.py reruns model inference.
"""
import csv,gzip,hashlib,html,json,zipfile
from pathlib import Path
from urllib.parse import unquote
import numpy as np
import scipy,sklearn
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'site/data';INPUT=ROOT/'analysis/data'
METHODS=['tfidf','dense_page','dense_180','dense_60']
METHOD_LABELS={'tfidf':'TF-IDF · full page','dense_page':'MiniLM · page mean','dense_180':'MiniLM · 180-word max','dense_60':'MiniLM · 60-word max'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def normalized(x):
 norm=np.linalg.norm(x,axis=-1,keepdims=True)
 if np.any(norm==0):raise ValueError('Zero vector')
 return x/norm

def load():
 with (DATA/'week1_nodes.tsv').open() as f:
  roster={r['node_id']:r for r in csv.DictReader((x for x in f if not x.startswith('#')),delimiter='\t',quoting=csv.QUOTE_NONE)}
 pages={}
 with zipfile.ZipFile(DATA/'marvel_pages.zip') as z:
  for f in sorted(z.namelist()):
   if f.endswith('.txt') and not f.endswith('README.txt'):pages[unquote(Path(f).stem)]=z.read(f).decode()
 meta=json.loads((INPUT/'week7-search-embeddings.json').read_text());queries=json.loads((INPUT/'week7-queries.json').read_text());names=meta['names']
 assert set(names)==set(pages)==set(roster) and len(names)==303
 assert sha(DATA/'marvel_pages.zip')==meta['corpus_sha256']
 assert sha(INPUT/'week7-search-embeddings.npz')==meta['vectors_sha256']
 assert meta['queries']==[q['query'] for q in queries['items']]
 with np.load(INPUT/'week7-search-embeddings.npz') as v:vectors={k:v[k] for k in v.files}
 for key,expected in [('documents',303),('queries',len(queries['items'])),('passages_180',len(meta['passages_180'])),('passages_60',len(meta['passages_60']))]:
  assert vectors[key].shape==(expected,384)
  assert np.allclose(np.linalg.norm(vectors[key],axis=1),1,atol=1e-6)
 return roster,pages,meta,queries,vectors

def sparse_representation(texts):
 """Week6 definition: IDF ln(N/DF), no smoothing/+1; keep stopwords.
 Raw TF and relative TF yield identical cosine after L2 normalization.
 """
 vectorizer=CountVectorizer();counts=vectorizer.fit_transform(texts);df=np.asarray((counts>0).sum(0)).ravel();idf=np.log(len(texts)/df)
 return vectorizer,idf,normalize(counts.multiply(idf).tocsr())

def order(scores,names):return sorted(range(len(names)),key=lambda i:(-float(scores[i]),names[i]))

def figure(result):
 esc=html.escape
 svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 750" role="img" aria-labelledby="title desc">','<title id="title">The intended page changes rank when we change how text is searched</title>','<desc id="desc">Eight saved queries, four retrieval methods. Numbers give the rank of each predeclared target page. Black Widow ranks1,20,3,5. Doctor Strange ranks3,5,1,1. Spider-Man ranks3,4,6,1. Daredevil is absent from the corpus. Smaller ranks are better for locating that target; this is not complete relevance ground truth.</desc>','<rect width="1100" height="750" fill="#122c29"/>','<text x="35" y="48" fill="#edf2e8" font-family="sans-serif" font-size="29">The same query does not guarantee the same result.</text>','<text x="35" y="78" fill="#b9cdc2" font-family="sans-serif" font-size="14">Rank of the predeclared target page · lower is better for finding that page</text>']
 headers=[['TF-IDF','full page'],['MiniLM','page mean'],['MiniLM','180-word max'],['MiniLM','60-word max']]
 for i,(a,b) in enumerate(headers):
  x=504+i*140;svg.extend([f'<text x="{x}" y="114" text-anchor="middle" fill="#edf2e8" font-family="sans-serif" font-size="15">{a}</text>',f'<text x="{x}" y="134" text-anchor="middle" fill="#b9cdc2" font-family="sans-serif" font-size="13">{b}</text>'])
 labels={'russian_spy':'Russian spy → Avenger','blind_lawyer':'Blind lawyer → crime fighter','surgeon':'Surgeon → sorcery after a crash','weather':'Woman → weather control','alien_suit':'Living alien suit → host','radioactive_spider':'Young hero → radioactive spider','iron_fist':'Iron Fist / martial arts / K’un-Lun','ghost_rider':'Johnny Blaze / Ghost Rider / motorcycle'}
 for row,q in enumerate(result['queries']):
  y=151+60*row
  svg.extend([f'<text x="35" y="{y+22}" fill="#edf2e8" font-size="17" font-family="sans-serif">{esc(q["target_name"])}</text>',f'<text x="35" y="{y+43}" fill="#a8c5b9" font-size="12" font-family="sans-serif">{esc(labels[q["id"]])}</text>'])
  for col,method in enumerate(METHODS):
   rank=q['results'][method]['target_rank'];fill='#c8e2ca' if rank==1 else ('#96bbae' if rank is not None and rank<=5 else ('#fa784d' if rank is not None else '#203e35'));ink='#122c29' if rank is not None else '#b9cdc2';x=445+col*140
   svg.extend([f'<rect x="{x}" y="{y}" width="118" height="48" rx="3" fill="{fill}"/>',f'<text x="{x+59}" y="{y+33}" text-anchor="middle" fill="{ink}" font-family="sans-serif" font-size="26">{rank if rank is not None else "—"}</text>'])
 svg.extend(['<text x="35" y="664" fill="#b9cdc2" font-family="sans-serif" font-size="14">Orange: target outside the first five. Dash: target absent from the 303-page corpus.</text>','<text x="35" y="692" fill="#b9cdc2" font-family="sans-serif" font-size="14">Page mean → max passage changes pooling; 180 → 60 changes window size with max pooling fixed.</text>','<text x="35" y="720" fill="#b9cdc2" font-family="sans-serif" font-size="14">Some queries fit multiple incarnations or pages. Inspect the returned text before judging relevance.</text>','</svg>'])
 assets=ROOT/'site/assets';assets.mkdir(exist_ok=True);(assets/'week7-search-ranks.svg').write_text('\n'.join(svg))

def build():
 roster,pages,meta,query_spec,v=load();names=meta['names'];texts=[pages[n] for n in names];N=len(names);cv,idf,x=sparse_representation(texts)
 qx=normalize(cv.transform([q['query'] for q in query_spec['items']]).multiply(idf).tocsr());sparse=(x@qx.T).toarray().T
 page_scores=v['queries']@v['documents'].T
 chunk_scores={words:v['queries']@v[f'passages_{words}'].T for words in [180,60]}
 by_page={words:{n:[] for n in names} for words in [180,60]}
 for words in [180,60]:
  for k,c in enumerate(meta[f'passages_{words}']):
   assert c['page']==names[c['index']];assert 0<=c['start']<c['end']<=len(pages[c['page']]);by_page[words][c['page']].append(k)
 for i,n in enumerate(names):assert np.allclose(normalized(v['passages_180'][by_page[180][n]].mean(0)),v['documents'][i],atol=1e-6)
 excerpts={}
 def excerpt(words,k):
  key=f'{words}:{k}'
  if key not in excerpts:
   c=meta[f'passages_{words}'][k];raw=pages[c['page']];start,end=c['start'],c['end'];a,b=max(0,start-800),min(len(raw),end+1200)
   excerpts[key]={**c,'words_limit':words,'text':raw[start:end],'context':{'start':a,'end':b,'text':raw[a:b]}}
  return key
 outputs=[];rank_rows=[];target_rows=[]
 for qi,spec in enumerate(query_spec['items']):
  target_index=names.index(spec['target']) if spec['target'] in names else None
  target_name=roster[spec['target']]['name'] if target_index is not None else 'Daredevil (absent)'
  result={**spec,'target_name':target_name,'target_present':target_index is not None,'results':{}}
  best={}
  for words in [180,60]:
   best[words]=[min(by_page[words][n],key=lambda k:(-float(chunk_scores[words][qi,k]),meta[f'passages_{words}'][k]['start'])) for n in names]
  scores={'tfidf':sparse[qi],'dense_page':page_scores[qi],**{f'dense_{words}':chunk_scores[words][qi,best[words]] for words in [180,60]}}
  for method in METHODS:
   ranking=order(scores[method],names);rank_of={i:k+1 for k,i in enumerate(ranking)};target_rank=rank_of[target_index] if target_index is not None else None;words=60 if method=='dense_60' else 180
   def evidence_index(i):
    if method!='tfidf':return best[words][i]
    ids=by_page[180][names[i]];cx=normalize(cv.transform([pages[names[i]][meta['passages_180'][k]['start']:meta['passages_180'][k]['end']] for k in ids]).multiply(idf).tocsr());cs=(cx@qx[qi].T).toarray().ravel()
    return ids[min(range(len(ids)),key=lambda j:(-float(cs[j]),meta['passages_180'][ids[j]]['start']))]
   def hit(i):
    k=evidence_index(i)
    return {'page':names[i],'name':roster[names[i]]['name'],'url':roster[names[i]]['url'],'rank':rank_of[i],'score':float(scores[method][i]),'excerpt':excerpt(words,k)}
   result['results'][method]={'target_rank':target_rank,'top5':[hit(i) for i in ranking[:5]],'target':hit(target_index) if target_index is not None else None}
   target_rows.append({'query_id':spec['id'],'query':spec['query'],'target':spec['target'],'present':target_index is not None,'method':method,'rank':target_rank})
   for i in ranking:rank_rows.append({'query_id':spec['id'],'query':spec['query'],'method':method,'rank':rank_of[i],'page':names[i],'score':float(scores[method][i]),'is_intended_target':i==target_index})
  outputs.append(result)
 source_files=['site/data/week1_nodes.tsv','site/data/marvel_pages.zip','analysis/data/week7-search-embeddings.npz','analysis/data/week7-search-embeddings.json','analysis/data/week7-queries.json','analysis/data/week7-reading-notes.json']
 result={'methods':{'labels':METHOD_LABELS,'encoder':meta['encoder'],'encoding':meta['settings'],'versions':{**meta['versions'],'numpy':np.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__},'tfidf':'CountVectorizer default lowercase tokens >=2 word characters; retain English stopwords and numbers; IDF ln(303/DF), no smoothing or added1; L2-normalize corpus and query with corpus IDF. Raw versus relative TF gives identical cosine.','dense_page':'Query cosine with normalized mean of normalized180-word passage vectors. The whole page is represented, not just its truncated beginning.','dense_passages':'For each page, maximum query cosine across its180- or60-word passage vectors. Encoder, queries and corpus fixed. Chunk cap254 wordpieces leaves two special tokens. Long pages have more candidate passages.','ties':'Exact score ties break alphabetically by node ID; tied passages use earliest source offset.','evidence':'Max-passage modes show the passage defining the score. Page-mean mode shows its best180-word passage for inspection, not a decomposition of the page score. TF-IDF shows the lexically closest180-word chunk from the ranked page; full-page score unchanged.','context':'Optional source context adds up to800 characters before and1200 after the returned passage; retrieval scores and ranks remain unchanged.','query_provenance':query_spec['provenance'],'evaluation':'Rank of the assistant-predeclared intended page, not complete relevance ground truth. Multiple incarnations/umbrella pages may be valid. One target is absent. No accuracy, calibrated probability or significance claim.','source_hashes':{p:sha(ROOT/p) for p in source_files}},'summary':{'pages':N,'queries':len(outputs),'present_targets':sum(q['target_present'] for q in outputs),'passages_180':len(meta['passages_180']),'passages_60':len(meta['passages_60']),'ranking_rows':len(rank_rows)},'queries':outputs,'excerpts':excerpts,'presets':[{'id':'russian_spy','left':'dense_page','right':'dense_180'},{'id':'surgeon','left':'tfidf','right':'dense_180'},{'id':'radioactive_spider','left':'dense_180','right':'dense_60'},{'id':'alien_suit','left':'dense_page','right':'dense_180'}]}
 DATA.mkdir(exist_ok=True);encoded=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode();(DATA/'week7.json').write_bytes(encoded)
 with (DATA/'week7.json.gz').open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write(encoded)
 for filename,rows in [('week7-rankings.csv',rank_rows),('week7-target-ranks.csv',target_rows)]:
  with (DATA/filename).open('w',newline='',encoding='utf-8') as f:
   writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 figure(result)
 print(json.dumps(result['summary'],indent=2))
 for q in outputs:print(q['id'],[q['results'][m]['target_rank'] for m in METHODS])
 return result
if __name__=='__main__':build()
