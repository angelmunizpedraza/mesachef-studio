#!/usr/bin/env python3
"""Traverse official indexed categories and their public pagination (pages 1–5)."""
import argparse, concurrent.futures, json, re, sys, xml.etree.ElementTree as ET
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
from urllib.parse import urljoin,urlparse
spec=spec_from_file_location('catalogs',Path(__file__).with_name('refresh-catalogs.py'));c=module_from_spec(spec);spec.loader.exec_module(c)


def read_category(category):
    found={};visited=set();queue=[category];expected=None
    try:
        while queue:
            url=queue.pop(0)
            if url in visited:continue
            visited.add(url);text,_=c.request(url);fetched=c.now()
            data=c.page_catalog('dia',source=(text,fetched))
            for p in data['products']:
                p['categories']=category.split('www.dia.es/',1)[1].split('/c/')[0].split('/')
                found[p['id']]=p
            match=re.search(r'<script[^>]*id="vike_pageContext"[^>]*>(.*?)</script>',text,re.S)
            state=json.loads(match[1])['INITIAL_STATE'];pagination=state.get('pagination',{}).get('pagination',{})
            count=pagination.get('total_pages',1)
            if not isinstance(count,int) or count<1:raise ValueError('Paginación no válida')
            expected=max(expected or 1,count)
            cid=category.rsplit('/',1)[1]
            for href in re.findall(r'href="([^\"]*pag-[^\"]*)"',text):
                candidate=urljoin(category,href)
                if urlparse(candidate).netloc=='www.dia.es' and re.search(r'/pag-[1-5]/c/'+re.escape(cid)+r'$',candidate) and candidate not in visited:queue.append(candidate)
        if expected and expected>5:raise ValueError('La categoría tiene más de cinco páginas; solo se consultaron las páginas públicas 1–5')
        if len(visited)!=(expected or 1):raise ValueError('Faltan páginas enlazadas')
        return category,list(found.values()),None
    except Exception as e:return category,list(found.values()),str(e)[:250]

def collect(resume=False,maximum=None):
    raw,_=c.request('https://www.dia.es/sitemap.xml');tree=ET.fromstring(raw)
    urls=list(dict.fromkeys(node.text for node in tree.iter() if node.tag.endswith('loc') and node.text))
    categories=[u for u in urls if re.search(r'/c/L\d+$',u) and urlparse(u).netloc=='www.dia.es']
    indexed={u.rsplit('/p/',1)[1] for u in urls if re.search(r'/p/\d+$',u)}
    if not categories or not indexed:raise ValueError('Índice oficial sin categorías o productos')
    target=c.TARGET/'dia.json';rows={};checked=[];category_products={};errors={}
    if target.exists():
        previous=json.loads(target.read_text());rows={p['id']:p for p in previous.get('products',[])}
        if resume:
            errors={u:e for u,e in previous.get('errors',{}).items() if u in categories}
            checked=[u for u in previous.get('checkedCategoryUrls',[]) if u in categories]
            category_products={u:ids for u,ids in previous.get('categoryProducts',{}).items() if u in checked}
    pending=[u for u in categories if u not in checked]
    if maximum:pending=pending[:maximum]
    def snapshot():
        missing=indexed-{p['sourceId'] for p in rows.values()}
        complete=len(checked)==len(categories) and not errors and not missing
        return dict(schemaVersion=1,retailer='dia',fetchedAt=c.now(),postcode=None,warehouse=None,
            scope='Categorías y páginas públicas de Día; zona de entrega sin confirmar',
            coverage='categories-checked' if complete else 'partial',expectedCategories=len(categories),checkedCategories=len(checked),
            checkedCategoryUrls=checked,categoryProducts=category_products,listedProducts=len(indexed),missingIndexedProducts=len(missing),
            indexSource='https://www.dia.es/sitemap.xml',errors=errors,products=list(rows.values()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for url,products,error in pool.map(read_category,pending):
            for p in products:
                old=rows.get(p['id']);p['categories']=list(dict.fromkeys((old['categories'] if old else [])+p['categories']));rows[p['id']]=p
            if error:errors[url]=error
            else:
                errors.pop(url,None);checked.append(url);category_products[url]=[p['id'] for p in products]
            if rows:c.TARGET.mkdir(exist_ok=True,parents=True);c.atomic(target,snapshot())
            print(f'Día: {len(checked)}/{len(categories)} categorías, {len(rows)} fichas',flush=True)
    if not rows:raise ValueError('No se recibió ninguna ficha')
    if len(checked)==len(categories) and not errors:
        current_ids={pid for ids in category_products.values() for pid in ids}
        rows={pid:p for pid,p in rows.items() if pid in current_ids}
    return snapshot()

def main():
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--max-categories',type=int);args=p.parse_args()
    result=collect(args.resume,args.max_categories);c.TARGET.mkdir(exist_ok=True,parents=True);c.atomic(c.TARGET/'dia.json',result)
    print(f'Día: {len(result["products"])} fichas; {result["missingIndexedProducts"]} referencias indexadas sin ficha consultada',flush=True)
if __name__=='__main__':main()
