#!/usr/bin/env python3
"""Public catalogues only. Counts, dates and missing categories stay explicit."""
import argparse, concurrent.futures, html, json, re, sys, urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parents[1]
TARGET = BASE / 'site/catalogs'
ORIGINS = {'mercadona':'https://tienda.mercadona.es', 'dia':'https://www.dia.es',
           'carrefour':'https://www.carrefour.es', 'mas':'https://www.supermercadosmas.com'}

def now(): return datetime.now(timezone.utc).isoformat()
def cents(value):
    if isinstance(value, bool) or value is None: return None
    s = str(value).strip().replace('€','').replace('\xa0','').strip()
    if ',' in s: s = s.replace('.','').replace(',','.')
    if not re.fullmatch(r'\d+(?:\.\d{1,4})?',s): return None
    try: n = Decimal(s)
    except InvalidOperation: return None
    if n < 0 or n > 10000: return None
    return int((n*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def request(url, body=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
        method=method, headers={'User-Agent':'MesaChef/3.0 public catalogue', 'Accept':'application/json,text/html',
        'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as response:
        data = response.read(6000001)
        if len(data)>6000000: raise ValueError('Respuesta demasiado grande')
        return data.decode('utf-8'), response.headers

def safe_url(retailer, value):
    u = urljoin(ORIGINS[retailer]+'/',str(value))
    if urlparse(u).netloc != urlparse(ORIGINS[retailer]).netloc or urlparse(u).scheme!='https':
        raise ValueError('Fuente fuera de la tienda oficial')
    return u

def product(retailer, pid, name, url, price, fetched, **kw):
    if not str(pid) or not str(name).strip(): raise ValueError('Ficha sin identidad')
    return dict(id=retailer+':'+str(pid), retailer=retailer, sourceId=str(pid),
        name=html.unescape(str(name)).strip()[:300], url=safe_url(retailer,url),
        priceCents=cents(price), fetchedAt=fetched, postcode=None, warehouse=None,
        zoneConfirmed=False, variable=False, available=None, referenceCents=None,
        referenceUnit='', format='', categories=[], brand='', image='', **kw)

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)

def mercadona(postcode, resume=False, maximum=None):
    _, headers = request(ORIGINS['mercadona']+'/api/postal-codes/actions/change-pc/',
                         {'new_postal_code':postcode},'PUT')
    warehouse = headers.get('x-customer-wh','')
    if headers.get('x-customer-pc')!=postcode or not re.fullmatch(r'\w{1,12}',warehouse):
        raise ValueError('Mercadona no confirmó la zona')
    taxonomy = json.loads(request(ORIGINS['mercadona']+'/api/categories/?lang=es&wh='+warehouse)[0])
    if taxonomy.get('next'): raise ValueError('Taxonomía paginada sin recorrer')
    leaves = {str(c['id']):[top['name'],c['name']] for top in taxonomy['results']
              for c in top.get('categories',[]) if c.get('published',True)}
    if not leaves: raise ValueError('Sin categorías publicadas')
    records, errors, checked, category_products = {}, {}, [], {}
    saved=TARGET/('mercadona-'+postcode+'.json')
    if resume and saved.exists():
        previous=json.loads(saved.read_text())
        if previous.get('warehouse')==warehouse and previous.get('postcode')==postcode:
            records={p['id']:p for p in previous.get('products',[])}
            checked=[cid for cid in previous.get('checkedCategoryIds',[]) if cid in leaves]
            category_products={cid:ids for cid,ids in previous.get('categoryProducts',{}).items() if cid in checked}
    pending=[(cid,names) for cid,names in leaves.items() if cid not in checked]
    if maximum: pending=pending[:maximum]
    def category(item):
        cid, names = item
        try:
            data = json.loads(request(ORIGINS['mercadona']+'/api/categories/'+cid+'/?lang=es&wh='+warehouse)[0])
            if str(data.get('id'))!=cid: raise ValueError('Categoría incorrecta')
            fetched = now(); products=[]
            for raw in walk(data):
                if 'price_instructions' not in raw or not raw.get('display_name'): continue
                p=raw['price_instructions']; pid=str(raw['id'])
                row=product('mercadona',pid,raw['display_name'],raw['share_url'],p.get('unit_price'),fetched)
                row.update(postcode=postcode,warehouse=warehouse,zoneConfirmed=True,
                    variable=bool(raw.get('is_variable_weight') or p.get('approx_size')),
                    available=raw.get('published') is not False and not raw.get('unavailable_from'),
                    referenceCents=cents(p.get('reference_price',p.get('bulk_price'))),
                    referenceUnit=str(p.get('reference_format') or p.get('size_format') or ''),
                    format=' '.join(str(v) for v in [raw.get('packaging'),p.get('unit_size'),p.get('size_format')] if v is not None),
                    categories=names, image=raw.get('thumbnail',''))
                products.append(row)
            return cid,products,None
        except Exception as e: return cid,[],str(e)[:250]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for cid,rows,error in pool.map(category,pending):
            if error: errors[cid]=error
            else:
                checked.append(cid)
                category_products[cid]=[row['id'] for row in rows]
                for row in rows:
                    if row['id'] in records:
                        row['categories']=list(dict.fromkeys(records[row['id']]['categories']+row['categories']))
                    records[row['id']]=row
            print(f'Mercadona {postcode}: {len(checked)+len(errors)}/{len(leaves)} categorías, {len(records)} productos',flush=True)
    if not records: raise ValueError('No se recibió ningún producto')
    complete=len(checked)==len(leaves) and not errors
    if complete:
        current_ids={pid for ids in category_products.values() for pid in ids}
        records={pid:p for pid,p in records.items() if pid in current_ids}
    return dict(schemaVersion=1,retailer='mercadona',fetchedAt=now(),postcode=postcode,
        warehouse=warehouse, scope='Catálogo online publicado para CP '+postcode,
        coverage='categories-checked' if complete else 'partial',
        expectedCategories=len(leaves),checkedCategories=len(checked),checkedCategoryIds=checked,
        categoryProducts=category_products,errors=errors,
        products=list(records.values()))

def page_catalog(retailer, captured=None, source=None):
    url=ORIGINS[retailer] + ('/supermercado/' if retailer=='carrefour' else '/')
    if source:
        text,fetched=source
    elif captured:
        text=captured.read_text(); fetched=datetime.fromtimestamp(captured.stat().st_mtime,timezone.utc).isoformat()
    else:
        text,_=request(url); fetched=now()
    rows={}
    if retailer=='dia':
        match=re.search(r'<script[^>]*id="vike_pageContext"[^>]*>(.*?)</script>',text,re.S)
        if not match: raise ValueError('Día no expuso su catálogo en esta página')
        state=json.loads(match[1])['INITIAL_STATE']
        for raw in walk(state):
            if 'sku_id' not in raw or 'display_name' not in raw or not isinstance(raw.get('prices'),dict): continue
            p=raw['prices']
            if p.get('currency')!='EUR': continue
            row=product(retailer,raw['sku_id'],raw['display_name'],raw['url'],p.get('price'),fetched)
            row.update(brand=raw.get('brand',''),image=urljoin(url,raw.get('image','')),
                referenceCents=cents(p.get('price_per_unit')),referenceUnit=p.get('measure_unit',''),
                available=raw.get('units_in_stock',0)>0,
                conditionalPrice=bool(p.get('is_club_price')))
            rows[row['id']]=row
    elif retailer=='carrefour':
        if 'window.__INITIAL_STATE__=' not in text: raise ValueError('Carrefour no expuso sus fichas')
        state=json.JSONDecoder().raw_decode(text.split('window.__INITIAL_STATE__=',1)[1])[0]
        for raw in walk(state):
            if not all(k in raw for k in ['sku_id','name','price','url']): continue
            row=product(retailer,raw['sku_id'],raw['name'],raw['url'],raw['price'],fetched)
            row.update(referenceCents=cents(raw.get('price_per_unit')),referenceUnit=raw.get('measure_unit',''),
                image=raw.get('images',{}).get('desktop',''),available=raw.get('units_in_stock',0)>0)
            rows[row['id']]=row
    elif retailer=='mas':
        # Public product-card attributes; exclude hidden form keys and account/cart data.
        cards=list(re.finditer(r'data-id="(\d+)"\s+data-sku="([^\"]+)"[^>]*data-url="([^\"]+)"\s+data-name="([^\"]+)"',text))
        for i,card in enumerate(cards):
            chunk=text[card.start():cards[i+1].start() if i+1<len(cards) else card.start()+18000]
            price=re.search(r'data-price-amount="([^\"]+)"\s+data-price-type="finalPrice"',chunk)
            if not price: continue
            row=product(retailer,card[2],card[4],html.unescape(card[3]),price[1],fetched)
            image=re.search(r'<img[^>]*src="([^\"]+)"',chunk)
            row.update(image=html.unescape(image[1]) if image else '')
            rows[row['id']]=row
    if not rows: raise ValueError('Página sin productos verificables')
    return dict(schemaVersion=1,retailer=retailer,fetchedAt=fetched,postcode=None,warehouse=None,
        scope='Productos publicados en la portada online; zona de entrega sin confirmar',coverage='partial',
        expectedCategories=None,checkedCategories=None,errors={},products=list(rows.values()))

def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')));tmp.replace(path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--retailers',nargs='+',default=list(ORIGINS));parser.add_argument('--postcode',default='41011');parser.add_argument('--captured-dir',type=Path);parser.add_argument('--resume',action='store_true');parser.add_argument('--max-categories',type=int);args=parser.parse_args()
    if not re.fullmatch(r'\d{5}',args.postcode): raise ValueError('Código postal no válido')
    if any(r not in ORIGINS for r in args.retailers): raise ValueError('Supermercado no configurado')
    TARGET.mkdir(parents=True,exist_ok=True);failed=[]
    for retailer in args.retailers:
        try:
            result=mercadona(args.postcode,args.resume,args.max_categories) if retailer=='mercadona' else page_catalog(retailer,args.captured_dir/(retailer+'.txt') if args.captured_dir else None)
            filename=retailer+'-'+args.postcode+'.json' if retailer=='mercadona' else retailer+'.json'
            atomic(TARGET/filename,result)
            print(f'{retailer}: {len(result["products"])} fichas; cobertura {result["coverage"]}',flush=True)
        except Exception as e:
            failed.append(retailer);print(f'{retailer}: {e}; no se cambia la consulta anterior',file=sys.stderr,flush=True)
    if failed: sys.exit(1)

if __name__=='__main__':main()
