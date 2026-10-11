#!/usr/bin/env python3
"""Consulta fichas oficiales con zona confirmada y publica datos fechados, nunca ejemplos."""
import json, sys, re, urllib.request, urllib.error, concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
ORIGIN='https://tienda.mercadona.es'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None
opener=urllib.request.build_opener(NoRedirect())
def request(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(ORIGIN+path,data=data,method='GET' if data is None else 'PUT',headers={'Accept':'application/json','Content-Type':'application/json','User-Agent':'MesaChefPersonal/2.0'})
 with opener.open(req,timeout=18)as response:
  content=response.read(1000001)
  if len(content)>1000000:raise ValueError('Respuesta demasiado grande')
  return json.loads(content),response.headers

def area_for(postcode):
 if not isinstance(postcode,str)or not re.fullmatch(r'\d{5}',postcode):raise ValueError('Código postal no válido')
 _,headers=request('/api/postal-codes/actions/change-pc/',{'new_postal_code':postcode})
 warehouse=headers.get('x-customer-wh','')
 if not re.fullmatch(r'\w{1,12}',warehouse)or headers.get('x-customer-pc')!=postcode:raise ValueError('Cobertura no confirmada')
 return warehouse

def fetch_catalog(postcode,ids):
 warehouse=area_for(postcode);records={};errors={}
 def one(pid):
  try:
   raw,_=request('/api/products/'+pid+'/?lang=es&wh='+warehouse)
   if str(raw.get('id'))!=pid or not isinstance(raw.get('price_instructions'),dict):raise ValueError('Ficha no válida')
   url=raw.get('share_url','')
   if not url.startswith(ORIGIN+'/product/'+pid+'/'):raise ValueError('Fuente no válida')
   # Publicamos sólo los campos de ficha usados en cálculos; no cookies ni cabeceras.
   fields=['id','display_name','price_instructions','share_url','published','is_variable_weight','unavailable_from']
   return pid,{'raw':{key:raw[key]for key in fields if key in raw},'context':{'postcode':postcode,'warehouse':warehouse,'fetchedAt':datetime.now(timezone.utc).isoformat()}},None
  except Exception as e:return pid,None,str(e)[:300]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  for pid,record,error in pool.map(one,ids):
   if record:records[pid]=record
   else:errors[pid]=error
 if not records:raise ValueError('Ninguna ficha recibida: no se sobrescribe la consulta anterior')
 return {'postcode':postcode,'warehouse':warehouse,'fetchedAt':datetime.now(timezone.utc).isoformat(),'records':records,'errors':errors}

def main():
 postcodes=json.loads((BASE/'scripts/postcodes.json').read_text());options=json.loads((BASE/'scripts/product-map.json').read_text());ids=sorted(set(pid for value in options.values()for pid in value))
 if not postcodes or any(not isinstance(cp,str)or not re.fullmatch(r'\d{5}',cp)for cp in postcodes):raise ValueError('Configuración de CP no válida')
 if any(not isinstance(pid,str)or not re.fullmatch(r'\d{1,9}',pid)for pid in ids):raise ValueError('Catálogo no válido')
 target=BASE/'site/market';target.mkdir(parents=True,exist_ok=True);failed=[]
 for postcode in dict.fromkeys(postcodes):
  try:
   result=fetch_catalog(postcode,ids);tmp=target/(postcode+'.json.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')));tmp.replace(target/(postcode+'.json'));print(f'{postcode}: {len(result["records"])} fichas, {len(result["errors"])} pendientes',flush=True)
  except Exception as e:failed.append(postcode);print(f'{postcode}: consulta fallida ({e}); se conserva la fecha anterior',file=sys.stderr,flush=True)
 # Cada despliegue debe conservar la carga inicial coherente con el JSON publicado.
 default=target/(postcodes[0]+'.json')
 if default.exists():
  text='window.PRODUCT_OPTIONS='+json.dumps(options,separators=(',',':'))+';\nwindow.MERCADONA_SNAPSHOT='+default.read_text()+';\n';(BASE/'site/mesachef/market-data.js').write_text(text)
 if failed:sys.exit(1)
if __name__=='__main__':main()
