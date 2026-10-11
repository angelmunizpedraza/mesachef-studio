#!/usr/bin/env python3
"""Read Alcampo's public category pages; delivery zone remains unconfirmed."""
import argparse, concurrent.futures, html, json, re, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('catalogs',Path(__file__).with_name('refresh-catalogs.py'));c=module_from_spec(spec);spec.loader.exec_module(c)
ORIGIN='https://www.compraonline.alcampo.es'
c.ORIGINS['alcampo']=ORIGIN
def parse_page(text,fetched):
 marker='window.__INITIAL_STATE__='
 if marker not in text:raise ValueError('La página no publicó productos verificables')
 # Only public product entities are retained. Session/account/cart state is discarded.
 state=json.JSONDecoder().raw_decode(text.split(marker,1)[1])[0]
 entities=state['data']['products']['productEntities'];urls={}
 for link in re.findall(r'href="([^\"]+)"',text):
  u=urlparse(urljoin(ORIGIN,html.unescape(link)))
  if u.scheme=='https'and u.netloc=='www.compraonline.alcampo.es'and re.search(r'^/products/[^/]+/[0-9]+$',u.path):urls[u.path.rsplit('/',1)[1]]=u._replace(query='',fragment='').geturl()
 products=[]
 for raw in entities.values():
  pid=str(raw.get('retailerProductId',''));price=raw.get('price',{});current=price.get('current',{})
  if pid not in urls or current.get('currency')!='EUR' or not isinstance(raw.get('name'),str):continue
  row=c.product('alcampo',pid,raw['name'],urls[pid],current.get('amount'),fetched)
  unit=price.get('unit',{});label=unit.get('label','');reference=unit.get('current',{})
  row.update(brand=raw.get('brand',''),image=raw.get('image',{}).get('src',''),categories=raw.get('categoryPath',[]),format=raw.get('size',{}).get('value',''),available=raw.get('available')if type(raw.get('available'))is bool else None,referenceCents=c.cents(reference.get('amount'))if reference.get('currency')=='EUR'else None,referenceUnit={'fop.price.per.litre':'L','fop.price.per.kg':'kg','fop.price.per.kilogram':'kg'}.get(label,'ud'if label=='fop.price.per.unit'else ''),variable=bool(price.get('estimated')or price.get('typical')or raw.get('isVariableWeight')),conditionalPrice=bool(price.get('loyalty')))
  products.append(row)
 if not products:raise ValueError('Página sin fichas con URL, identidad y precio verificables')
 return products
def categories(text):
 urls=[n.text for n in ET.fromstring(text).iter()if n.tag.endswith('loc')and n.text]
 eligible=[u for u in urls if urlparse(u).netloc=='www.compraonline.alcampo.es'and '/categories/'in u and '/folletos-y-promociones/'not in u and '/campañas/'not in u]
 # Prefer broad public categories. Different paths to one retailer category are deduplicated.
 result={}
 for u in sorted(eligible,key=lambda u:(len(u.split('/')),u)):
  result.setdefault(u.rsplit('/',1)[1],u)
 return list(result.values())
def collect(resume=False,maximum=100,captured=None):
 text=captured.read_text()if captured else c.request(ORIGIN+'/sitemaps/sitemap-categories-part1.xml')[0]
 urls=categories(text)
 if not urls:raise ValueError('Índice sin categorías públicas')
 target=c.TARGET/'alcampo.json';rows={};checked=[];errors={};cursor=None
 if target.exists():
  old=json.loads(target.read_text());rows={p['id']:p for p in old['products']}
  if resume:checked=[u for u in old.get('checkedCategoryUrls',[])if u in urls];errors=old.get('errors',{});cursor=old.get('lastAttemptUrl')
 start=(urls.index(cursor)+1)%len(urls)if cursor in urls else 0
 pending=(urls[start:]+urls[:start])[:maximum]
 def snapshot():return dict(schemaVersion=1,retailer='alcampo',fetchedAt=c.now(),postcode=None,warehouse=None,scope='Primeras páginas públicas de categorías Alcampo, zona de entrega sin confirmar; surtido de hipermercado y supermercado',coverage='partial',expectedCategories=len(urls),checkedCategories=len(checked),checkedCategoryUrls=checked,lastAttemptUrl=cursor,pageCoverage='first-public-page-only',errors=errors,products=list(rows.values()))
 def one(url):
  try:text,_=c.request(quote(url,safe=':/'));return url,parse_page(text,c.now()),None
  except Exception as e:return url,[],str(e)[:250]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  failures=0
  for url,products,error in pool.map(one,pending):
   cursor=url
   for p in products:
    old=rows.get(p['id']);p['categories']=list(dict.fromkeys((old['categories']if old else [])+p['categories']));rows[p['id']]=p
   if error:errors[url]=error;failures+=1
   else:
    errors.pop(url,None);failures=0
    if url not in checked:checked.append(url)
   if rows:c.TARGET.mkdir(exist_ok=True,parents=True);c.atomic(target,snapshot())
   print(f'Alcampo: {len(checked)}/{len(urls)} primeras páginas, {len(rows)} fichas',flush=True)
   if (failures>=3 and error and ('403'in error or '401'in error or 'timed out'in error)) or failures>=10:
    pool.shutdown(wait=False,cancel_futures=True);break
 if not rows:raise ValueError('No se obtuvieron fichas verificables')
 return snapshot()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--max-categories',type=int,default=100);p.add_argument('--captured-index',type=Path);a=p.parse_args();c.atomic(c.TARGET/'alcampo.json',collect(a.resume,a.max_categories,a.captured_index))
