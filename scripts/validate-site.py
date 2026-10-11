#!/usr/bin/env python3
import json,re
from pathlib import Path
from datetime import datetime
BASE=Path(__file__).resolve().parents[1];SITE=BASE/'site'
html=(SITE/'index.html').read_text()
for path in re.findall(r'(?:src|href)="(\./[^"]+)"',html):
 assert(SITE/path[2:]).is_file(),f'Recurso ausente: {path}'
for script in ['data','market-data','market','engine','store','catalog-core','catalog','web-bridge','app','comfort','offline-boot']:
 assert(SITE/'mesachef'/(script+'.js')).is_file()
manifest=json.loads((SITE/'mesachef/manifest.webmanifest').read_text());assert manifest['scope']=='../'and manifest['start_url']=='../'
for icon in manifest['icons']:assert(SITE/'mesachef'/icon['src']).is_file()
assert 'window.PRODUCT_OPTIONS='in(SITE/'mesachef/market-data.js').read_text(),'Falta el mapa de productos del cliente'
app=(SITE/'mesachef/app.js').read_text();assert 'src="/mesachef/'not in app and 'Acceso privado con ChatGPT'not in app
bridge=(SITE/'mesachef/web-bridge.js').read_text();assert '/api/market/'not in bridge and "cache:'no-store'"in bridge
allowed=set(i for v in json.loads((BASE/'scripts/product-map.json').read_text()).values()for i in v)
for path in(SITE/'market').glob('*.json'):
 data=json.loads(path.read_text());assert path.stem==data['postcode'];datetime.fromisoformat(data['fetchedAt']);assert set(data['records']).issubset(allowed)and set(data['errors']).issubset(allowed)
 for pid,record in data['records'].items():
  assert str(record['raw']['id'])==pid and record['context']['postcode']==path.stem and record['context']['warehouse']==data['warehouse']
  assert record['raw']['share_url'].startswith('https://tienda.mercadona.es/product/'+pid+'/');datetime.fromisoformat(record['context']['fetchedAt'])
registry=json.loads((SITE/'catalogs/retailers.json').read_text());assert registry['schemaVersion']==1
origins={'mercadona':'https://tienda.mercadona.es/','dia':'https://www.dia.es/','carrefour':'https://www.carrefour.es/','mas':'https://www.supermercadosmas.com/','alcampo':'https://www.compraonline.alcampo.es/','aldi':'https://www.aldi.es/','elcorteingles':'https://www.elcorteingles.es/'}
for path in (SITE/'catalogs').glob('*.json'):
 if path.name=='retailers.json':continue
 data=json.loads(path.read_text());assert data['schemaVersion']==1;ids=set();datetime.fromisoformat(data['fetchedAt'])
 if data['coverage']=='categories-checked':assert data['expectedCategories']==data['checkedCategories'] and not data['errors']
 for product in data['products']:
  assert product['id'] not in ids;ids.add(product['id']);assert product['retailer']==data['retailer'];assert product['url'].startswith(origins[data['retailer']]);datetime.fromisoformat(product['fetchedAt'])
  assert product['priceCents'] is None or type(product['priceCents']) is int and 0<=product['priceCents']<=1000000
  if product['zoneConfirmed']:assert product['postcode']==data['postcode'] and product['warehouse']==data['warehouse']
print('OK: archivos, rutas relativas, PWA, transporte estático y catálogos con fuente y cobertura.')
