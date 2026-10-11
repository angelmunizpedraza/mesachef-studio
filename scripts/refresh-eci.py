#!/usr/bin/env python3
"""Only public El Corte Inglés category HTML; no API, filters or postcode query."""
import argparse,concurrent.futures,json,re
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('catalogs',Path(__file__).with_name('refresh-catalogs.py'));c=module_from_spec(spec);spec.loader.exec_module(c)
ORIGIN='https://www.elcorteingles.es';c.ORIGINS['elcorteingles']=ORIGIN
CATEGORIES=['alimentacion-general','desayunos-dulces-y-pan','lacteos','congelados','bebidas','frescos','bebes','cuidado-personal-y-belleza','drogueria-y-limpieza','mascotas']
def parse_page(text,fetched):
 marker='window.__MOONSHINE_STATE__ = '
 if marker not in text:raise ValueError('Sin estado público de productos')
 state=json.JSONDecoder().raw_decode(text.split(marker,1)[1])[0]['viewData']['plp'];rows=[]
 for raw in state.get('products',[]):
  pid=raw.get('id','');url=raw.get('url','');price=raw.get('priceSpecification',{})
  if not re.fullmatch(r'B[0-9]+',pid)or not url.startswith('/supermercado/'+pid+'-')or not price:continue
  row=c.product('elcorteingles',pid,raw.get('description',''),url,price.get('salePrice')or price.get('price'),fetched)
  if row['priceCents']is None:continue
  cats=[d['name']for d in c.walk(raw.get('categories',[]))if isinstance(d.get('name'),str)]
  row.update(brand=raw.get('brand',{}).get('name',''),image=raw.get('image',''),categories=list(dict.fromkeys(cats)),format=' '.join(str(raw.get(k,''))for k in ['presentation_detail_description','presentation_detail_quantity']).strip(),referenceCents=c.cents(price.get('measurementUnitPrice')),referenceUnit=price.get('pum_description',''),variable=raw.get('sale_type',{}).get('identifier')not in ['U',None],available=None,conditionalPrice=bool(raw.get('promotional_actions')))
  rows.append(row)
 if not rows:raise ValueError('Sin fichas con precio e identidad verificables')
 pagination=state.get('pagination',{});next_path=pagination.get('path_next')if pagination.get('page',1)<pagination.get('totalPages',1)else None
 if next_path and not re.fullmatch(r'/supermercado/[a-z-]+/[0-9]+/',next_path):next_path=None
 return rows,next_path,pagination.get('count')
def collect(maximum=100,resume=False):
 target=c.TARGET/'elcorteingles.json';rows={};checked=[];errors={};queue=[ORIGIN+'/supermercado/'+cat+'/'for cat in CATEGORIES];counts={}
 if target.exists():
  old=json.loads(target.read_text());rows={p['id']:p for p in old['products']}
  if resume:
   checked=old.get('checkedPageUrls',[]);queue=old.get('pendingPageUrls',queue);errors=old.get('errors',{});counts=old.get('categoryCounts',{})
   if not queue:queue=[ORIGIN+'/supermercado/'+cat+'/'for cat in CATEGORIES];checked=[];counts={}
 def snapshot():return dict(schemaVersion=1,retailer='elcorteingles',fetchedAt=c.now(),postcode=None,warehouse=None,scope='Páginas públicas del supermercado El Corte Inglés; zona sin confirmar. No acredita el catálogo de Supercor',coverage='partial',expectedCategories=len(CATEGORIES),checkedCategories=len({u.split('/')[4]for u in checked}),checkedPageUrls=checked,pendingPageUrls=queue,categoryCounts=counts,errors=errors,products=list(rows.values()))
 def one(url):
  try:return url,parse_page(c.request(url)[0],c.now()),None
  except Exception as e:return url,None,str(e)[:250]
 failures=0;attempted=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  while queue and attempted<maximum:
   batch=queue[:min(2,maximum-attempted)];queue=queue[len(batch):]
   for url,result,error in pool.map(one,batch):
    attempted+=1
    if error:errors[url]=error;failures+=1
    else:
     failures=0;errors.pop(url,None);checked.append(url);products,next_path,count=result
     for p in products:rows[p['id']]=p
     counts[url.split('/')[4]]=count
     if next_path and ORIGIN+next_path not in checked and ORIGIN+next_path not in queue:queue.append(ORIGIN+next_path)
    if rows:c.atomic(target,snapshot())
   print(f'ECI: {len(checked)} páginas, {len(rows)} fichas, {len(queue)} páginas pendientes',flush=True)
   if failures>=4:break
 if not rows:raise ValueError('Sin fichas públicas verificables')
 return snapshot()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--max-pages',type=int,default=100);a=p.parse_args();c.atomic(c.TARGET/'elcorteingles.json',collect(a.max_pages,a.resume))
