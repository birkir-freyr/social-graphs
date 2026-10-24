"""Optional fresh inference for Week7 search. First run downloads pinned weights.
Install requirements-week7-encoder.txt, run this file, then build_week7.py.
"""
import os,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
if Path('/etc/ssl/cert.pem').exists():
 os.environ.setdefault('SSL_CERT_FILE','/etc/ssl/cert.pem');os.environ.setdefault('REQUESTS_CA_BUNDLE','/etc/ssl/cert.pem')
import numpy as np,torch
from sentence_transformers import SentenceTransformer
from importlib.metadata import version
from build_week7 import load,normalized,sha,INPUT

def chunks(text,tokenizer,max_words):
 words=list(re.finditer(r'\S+',text));out=[];a=0
 while a<len(words):
  b=min(a+max_words,len(words))
  while True:
   start,end=words[a].start(),words[b-1].end();part=text[start:end];tokens=tokenizer(part,add_special_tokens=False)['input_ids']
   if len(tokens)<=254:break
   b=a+max(1,int((b-a)*254/len(tokens))-1)
   if b==a+1:raise ValueError('Unexpected single overlong token; inspect before changing the frozen rule')
  out.append({'start':start,'end':end});a=b
 return out

def main():
 _,pages,meta,query_spec,_=load();torch.set_num_threads(4)
 model=SentenceTransformer(meta['encoder']['repo'],revision=meta['encoder']['revision'],cache_folder=str(ROOT/'.cache/week7-model'),device='cpu');assert model.max_seq_length==256
 vectors={}
 for words in [180,60]:
  passages=[]
  for i,n in enumerate(meta['names']):passages.extend(dict(c,page=n,index=i) for c in chunks(pages[n],model.tokenizer,words))
  assert passages==meta[f'passages_{words}'],'Chunk rule changed; inspect before overwriting the reference'
  vectors[f'passages_{words}']=model.encode([pages[c['page']][c['start']:c['end']] for c in passages],normalize_embeddings=True,batch_size=64,show_progress_bar=True)
 vectors['documents']=np.vstack([normalized(vectors['passages_180'][[k for k,c in enumerate(meta['passages_180']) if c['index']==i]].mean(0)) for i in range(303)])
 vectors['queries']=model.encode([q['query'] for q in query_spec['items']],normalize_embeddings=True,batch_size=64)
 destination=INPUT/'week7-search-embeddings.npz';np.savez_compressed(destination,**vectors);meta['vectors_sha256']=sha(destination);meta['versions']={n:version(n) for n in ['numpy','torch','transformers','sentence-transformers']};(INPUT/'week7-search-embeddings.json').write_text(json.dumps(meta,indent=2))
 print('Re-encoded. Rebuild and inspect changed scores/rankings before updating the article.')
if __name__=='__main__':main()
