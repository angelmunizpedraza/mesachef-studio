#!/usr/bin/env python3
"""Public ALDI product pages. No API calls, accounts or inferred store prices."""
import argparse,concurrent.futures,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('catalogs',Path(__file__).with_name('refresh-catalogs.py'));c=module_from_spec(spec);spec.loader.exec_module(c)
ORIGIN='https://www.aldi.es';c.ORIGINS['aldi']=ORIGIN
INDEX=ORIGIN+'/sitemaps/.aldi-nord-sitemap-products.xml'
def urls(text):
 return list(dict.fromkeys(n.text for n in ET.fromstring(text).iter()if n.tag.endswith('loc')and n.text and re.fullmatch(r'https://www\.aldi\.es/producto/[a-z0-9-]+\.html',n.text)))
def parse_page(text,url,fetched):
 m=re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',text,re.S)
 if not m:raise ValueError('Ficha sin datos públicos verificables')
 state=json.loads(m[1])['props']['pageProps']['apiData'];state=json.loads(state)if isinstance(state,str)else state
 public=dict(state).get('PRODUCT_DETAIL_GET',{}).get('res',{}).get('products',[]);rows=[]
 for raw in public:
  pid=str(raw.get('objectID',''));slug=raw.get('productSlug','')
  if url!=ORIGIN+'/producto/'+slug+'.html' or not pid or not slug.endswith('-'+pid):continue
  price=raw.get('currentPrice',{});base=(price.get('basePrice')or [{}])[0]
  row=c.product('aldi',pid,raw.get('name',''),url,price.get('priceValue'),fetched)
  if row['priceCents']is None:continue
  expiry=price.get('validUntil');start=price.get('validFrom');stamp=datetime.fromisoformat(fetched).timestamp()
  active=(not isinstance(expiry,(int,float))or expiry>=stamp)and(not isinstance(start,(int,float))or start<=stamp)
  row.update(brand=raw.get('brandName',''),format=raw.get('salesUnit',''),image=next((a.get('url','')for a in raw.get('assets',[])if a.get('type')=='primary'),''),categories=raw.get('categoryIDs',[]),available=raw.get('isAvailable')if type(raw.get('isAvailable'))is bool and active else False,referenceCents=c.cents(base.get('basePriceValue')),referenceUnit=base.get('basePriceScale',''))
  rows.append(row)
 if not rows:raise ValueError('Sin producto con identidad, URL y precio verificables')
 return rows
def collect(resume=False,maximum=2768,captured=None):
 index=captured.read_text()if captured else c.request(INDEX)[0];links=urls(index)
 if not links:raise ValueError('Índice oficial vacío')
 target=c.TARGET/'aldi.json';rows={};checked=[];errors={};cursor=None
 if target.exists():
  old=json.loads(target.read_text());rows={p['id']:p for p in old['products']}
  if resume:checked=[u for u in old.get('checkedProductUrls',[])if u in links];errors=old.get('errors',{});cursor=old.get('lastAttemptUrl')
 def snapshot():return dict(schemaVersion=1,retailer='aldi',fetchedAt=c.now(),postcode=None,warehouse=None,scope='Fichas del índice online oficial ALDI, incluye alimentación y bazar; precios publicados sin tienda de Sevilla confirmada',coverage='partial',expectedProducts=len(links),checkedProducts=len(checked),expectedCategories=None,checkedCategories=None,checkedProductUrls=checked,lastAttemptUrl=cursor,errors=errors,products=list(rows.values()))
 def one(url):
  try:return url,parse_page(c.request(url)[0],url,c.now()),None
  except Exception as e:return url,[],str(e)[:250]
 # Bounded batches prevent queued requests from continuing after a source blocks access.
 start=(links.index(cursor)+1)%len(links)if cursor in links else 0
 pending=(links[start:]+links[:start])[:maximum];failures=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  for start in range(0,len(pending),2):
   for url,products,error in pool.map(one,pending[start:start+2]):
    cursor=url
    if error:errors[url]=error;failures+=1
    else:
     if url not in checked:checked.append(url)
     errors.pop(url,None);failures=0
     for p in products:rows[p['id']]=p
    if rows:c.atomic(target,snapshot())
   print(f'ALDI: {len(checked)}/{len(links)} fichas consultadas, {len(rows)} productos',flush=True)
   if failures>=6 and error and any(x in error for x in ['403','401','timed out']):break
 if not rows:raise ValueError('No se recibieron productos verificables')
 return snapshot()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--max-products',type=int,default=2768);p.add_argument('--captured-index',type=Path);a=p.parse_args();c.atomic(c.TARGET/'aldi.json',collect(a.resume,a.max_products,a.captured_index))
