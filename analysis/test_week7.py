"""Independent audits of Week7 search scores, source evidence and claims."""
import csv,hashlib,html,json,math,re,unittest,zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote,urlsplit
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
METHODS=['tfidf','dense_page','dense_180','dense_60']
class Week7Audit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=json.loads((ROOT/'site/data/week7.json').read_text());cls.meta=json.loads((ROOT/'analysis/data/week7-search-embeddings.json').read_text());cls.names=cls.meta['names'];cls.ix={n:i for i,n in enumerate(cls.names)}
  with np.load(ROOT/'analysis/data/week7-search-embeddings.npz') as v:cls.v={k:v[k] for k in v.files}
  cls.pages={}
  with zipfile.ZipFile(ROOT/'site/data/marvel_pages.zip') as z:
   for n in z.namelist():
    if n.endswith('.txt') and not n.endswith('README.txt'):cls.pages[unquote(Path(n).stem)]=z.read(n).decode()
  cls.by_page={words:{n:[k for k,c in enumerate(cls.meta[f'passages_{words}']) if c['page']==n] for n in cls.names} for words in [180,60]}
  with (ROOT/'site/data/week7-rankings.csv').open() as f:cls.rows=list(csv.DictReader(f))
 def test_unit_vectors_full_source_coverage_and_page_means(self):
  for key,vectors in self.v.items():self.assertEqual(vectors.shape[1],384);self.assertTrue(np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-6),key)
  for words in [180,60]:
   for n in self.names:
    segments=[self.meta[f'passages_{words}'][k] for k in self.by_page[words][n]]
    self.assertEqual(''.join(''.join(self.pages[n][c['start']:c['end']].split()) for c in segments),''.join(self.pages[n].split()))
    self.assertTrue(all(len(self.pages[n][c['start']:c['end']].split())<=words for c in segments))
  for i,n in enumerate(self.names):
   v=self.v['passages_180'][self.by_page[180][n]].mean(0);self.assertTrue(np.allclose(v/np.linalg.norm(v),self.v['documents'][i],atol=1e-6))
 def test_keyword_scores_with_independent_counter_arithmetic(self):
  # Count terms directly, avoiding the builder's sklearn sparse operations.
  analyze=lambda s:re.findall(r'(?u)\b\w\w+\b',s.lower())
  counts={n:Counter(analyze(self.pages[n])) for n in self.names};df=Counter(w for c in counts.values() for w in c);idf={w:math.log(303/n) for w,n in df.items()}
  norms={n:math.sqrt(sum((count*idf[w])**2 for w,count in c.items())) for n,c in counts.items()}
  for q in self.data['queries']:
   qc=Counter(w for w in analyze(q['query']) if w in idf);qn=math.sqrt(sum((count*idf[w])**2 for w,count in qc.items()));expected={n:sum(qcount*counts[n][w]*idf[w]**2 for w,qcount in qc.items())/(qn*norms[n]) for n in self.names};saved=[r for r in self.rows if r['query_id']==q['id'] and r['method']=='tfidf']
   for row in saved:self.assertAlmostEqual(float(row['score']),expected[row['page']],places=12)
   self.assertEqual([r['page'] for r in saved],sorted(self.names,key=lambda n:(-expected[n],n)))
 def test_all_dense_scores_and_rankings_from_original_vectors(self):
  for qi,q in enumerate(self.data['queries']):
   for method in METHODS[1:]:
    query=self.v['queries'][qi]
    if method=='dense_page':scores=self.v['documents']@query
    else:
     words=180 if method=='dense_180' else 60
     scores=np.array([np.max(self.v[f'passages_{words}'][self.by_page[words][n]]@query) for n in self.names])
    saved=[r for r in self.rows if r['query_id']==q['id'] and r['method']==method]
    self.assertEqual([r['page'] for r in saved],sorted(self.names,key=lambda n:(-float(scores[self.ix[n]]),n)))
    for row in saved:self.assertAlmostEqual(float(row['score']),float(scores[self.ix[row['page']]]),places=5)
 def test_top_five_targets_absent_page_and_reported_examples(self):
  expected={'russian_spy':[1,20,3,5],'blind_lawyer':[None]*4,'surgeon':[3,5,1,1],'weather':[1]*4,'alien_suit':[1,17,1,1],'radioactive_spider':[3,4,6,1],'iron_fist':[1,2,2,1],'ghost_rider':[1,1,2,1]}
  self.assertEqual(len(self.rows),9696)
  for q in self.data['queries']:
   self.assertEqual([q['results'][m]['target_rank'] for m in METHODS],expected[q['id']])
   for m in METHODS:
    rows=[r for r in self.rows if r['query_id']==q['id'] and r['method']==m];self.assertEqual(len(rows),303);self.assertEqual([h['page'] for h in q['results'][m]['top5']],[r['page'] for r in rows[:5]])
    if q['target_present']:
     target=q['results'][m]['target'];self.assertEqual(rows[target['rank']-1]['page'],q['target']);self.assertEqual(target['rank'],q['results'][m]['target_rank'])
    else:self.assertNotIn(q['target'],self.names);self.assertIsNone(q['results'][m]['target']);self.assertIsNone(q['results'][m]['target_rank'])
 def test_every_returned_span_and_max_passage_score(self):
  for e in self.data['excerpts'].values():
   self.assertEqual(e['text'],self.pages[e['page']][e['start']:e['end']]);c=e['context'];self.assertEqual(c['text'],self.pages[e['page']][c['start']:c['end']]);self.assertLessEqual(c['start'],e['start']);self.assertGreaterEqual(c['end'],e['end'])
  for qi,q in enumerate(self.data['queries']):
   for m in METHODS:
    r=q['results'][m]
    for hit in r['top5']+([r['target']] if r['target'] else []):
     e=self.data['excerpts'][hit['excerpt']];self.assertEqual(e['page'],hit['page'])
     if m in ['dense_180','dense_60']:
      words,k=map(int,hit['excerpt'].split(':'));self.assertEqual(words,180 if m=='dense_180' else 60);self.assertAlmostEqual(float(self.v[f'passages_{words}'][k]@self.v['queries'][qi]),hit['score'],places=5)
 def test_context_reveals_negation_and_source_interpretations(self):
  q=next(q for q in self.data['queries'] if q['id']=='alien_suit');a=self.data['excerpts'][q['results']['dense_180']['target']['excerpt']];b=self.data['excerpts'][q['results']['dense_60']['target']['excerpt']]
  self.assertIn('not extraterrestrial',a['text']);self.assertNotIn('not extraterrestrial',b['text']);self.assertIn('not extraterrestrial',b['context']['text'])
  spider=next(q for q in self.data['queries'] if q['id']=='radioactive_spider');winner=spider['results']['dense_180']['top5'][0];self.assertEqual(winner['page'],'John_Jameson_(character)');self.assertIn('What If',self.data['excerpts'][winner['excerpt']]['text'])
 def test_input_hashes_and_static_page(self):
  for file,digest in self.data['methods']['source_hashes'].items():self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),digest)
  from html.parser import HTMLParser
  class Parser(HTMLParser):
   def __init__(self):super().__init__();self.links=[];self.ids=[];self.pre=None;self.texts={}
   def handle_starttag(self,tag,attrs):
    a=dict(attrs)
    if 'id' in a:self.ids.append(a['id'])
    for k in ['src','href']:
     if k in a:self.links.append(a[k])
    if tag=='pre':self.pre=a.get('id');self.texts[self.pre]=''
   def handle_data(self,data):
    if self.pre is not None:self.texts[self.pre]+=data
   def handle_endtag(self,tag):
    if tag=='pre':self.pre=None
  page=ROOT/'site/weeks/week7.html';raw=page.read_text();p=Parser();p.feed(raw);self.assertEqual(len(p.ids),len(set(p.ids)))
  for link in p.links:
   target=urlsplit(link).path
   if target.endswith(('.css','.js','.svg')) or target.startswith('../data/week7'):self.assertTrue((page.parent/target).exists(),link)
  q=next(q for q in self.data['queries'] if q['id']=='surgeon')
  for side,m in [('left','tfidf'),('right','dense_180')]:self.assertEqual(p.texts[side+'-source'],self.data['excerpts'][q['results'][m]['top5'][0]['excerpt']]['text'])
  self.assertIn('9,696',raw);self.assertIn('target rank into an accuracy claim',raw);self.assertNotIn('Black Fox',raw)
if __name__=='__main__':unittest.main()
