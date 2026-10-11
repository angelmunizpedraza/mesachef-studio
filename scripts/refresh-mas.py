#!/usr/bin/env python3
"""Read first public category pages from MAS. Query pagination stays excluded."""
import argparse,concurrent.futures,json,re
from html.parser import HTMLParser
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
from urllib.parse import urlparse
spec=spec_from_file_location('catalogs',Path(__file__).with_name('refresh-catalogs.py'));c=module_from_spec(spec);spec.loader.exec_module(c)
class Menu(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='nav':self.stack.append('data-top-nav'in a or(bool(self.stack)and self.stack[-1]))
  if tag=='a' and self.stack and self.stack[-1] and a.get('href'):self.links.append(a['href'])
 def handle_endtag(self,tag):
  if tag=='nav' and self.stack:self.stack.pop()
def categories(text):
 menu=Menu();menu.feed(text)
 urls=list(dict.fromkeys(u for u in menu.links if urlparse(u).scheme=='https'and urlparse(u).netloc=='www.supermercadosmas.com'and not urlparse(u).fragment and not urlparse(u).query and urlparse(u).path.endswith('/')and not re.search('/(?:marca-|etiqueta-|customer/)',urlparse(u).path)))
 return [u for u in urls if not any(v!=u and v.startswith(u)for v in urls)]
def collect(resume=False,maximum=None,captured=None):
 text=captured.read_text()if captured else c.request('https://www.supermercadosmas.com/')[0];urls=categories(text)
 if not urls:raise ValueError('Menú sin categorías públicas')
 target=c.TARGET/'mas.json';rows={};checked=[];errors={}
 if target.exists():
  old=json.loads(target.read_text());rows={p['id']:p for p in old['products']}
  if resume:checked=[u for u in old.get('checkedCategoryUrls',[])if u in urls];errors=old.get('errors',{})
 pending=[u for u in urls if u not in checked]
 if maximum:pending=pending[:maximum]
 def snapshot():return dict(schemaVersion=1,retailer='mas',fetchedAt=c.now(),postcode=None,warehouse=None,scope='Primera página pública de categorías del menú MAS; sin paginación por consulta ni zona de entrega confirmada',coverage='partial',expectedCategories=len(urls),checkedCategories=len(checked),checkedCategoryUrls=checked,pageCoverage='first-public-page-only',errors=errors,products=list(rows.values()))
 def one(url):
  try:
   text,_=c.request(url);products=c.page_catalog('mas',source=(text,c.now()))['products']
   for p in products:p['categories']=urlparse(url).path.strip('/').split('/')
   return url,products,None
  except Exception as e:return url,[],str(e)[:250]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  failures=0
  for url,products,error in pool.map(one,pending):
   for p in products:
    old=rows.get(p['id']);p['categories']=list(dict.fromkeys((old['categories']if old else [])+p['categories']));rows[p['id']]=p
   if error:errors[url]=error;failures+=1
   else:errors.pop(url,None);checked.append(url);failures=0
   if rows:c.TARGET.mkdir(exist_ok=True,parents=True);c.atomic(target,snapshot())
   print(f'MAS: {len(checked)}/{len(urls)} primeras páginas, {len(rows)} fichas',flush=True)
   if failures>=3 and error and ('403'in error or '401'in error or 'timed out'in error):
    pool.shutdown(wait=False,cancel_futures=True);break
 if not rows:raise ValueError('Sin fichas verificables')
 return snapshot()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--max-categories',type=int);p.add_argument('--captured-menu',type=Path);a=p.parse_args();c.atomic(c.TARGET/'mas.json',collect(a.resume,a.max_categories,a.captured_menu))
