(function(root){
 'use strict';const M={},refs=['kg','L','l','ud','dc','100 g','100g'];
 M.allowedIds=()=>new Set(Object.values(root.PRODUCT_OPTIONS||{}).flat());
 M.defaultSelection=()=>Object.fromEntries(Object.entries(root.PRODUCT_OPTIONS||{}).map(([ingredient,ids])=>[ingredient,ids[0]]));
 M.normalize=(raw,context)=>{
  if(!raw||typeof raw!=='object'||!/^\d{1,9}$/.test(String(raw.id))||!M.allowedIds().has(String(raw.id)))throw Error('Producto no autorizado');
  const p=raw.price_instructions,id=String(raw.id);if(!p||!['kg','l','ud'].includes(p.size_format))throw Error('Formato de producto no compatible');
  const cash=value=>{if(!/^[0-9]+(?:\.[0-9]{1,3})?$/.test(String(value)))throw Error('Precio inválido');const n=Number(value);if(!Number.isFinite(n)||n<0||n>10000)throw Error('Precio inválido');return n;};
  const amount=value=>{if(value===null||value===undefined)return null;const n=Number(value);if(!Number.isFinite(n)||n<=0||n>1000)throw Error('Cantidad no válida');return n;};
  const fixedCents=Math.round(cash(p.unit_price)*100),reference=cash(p.reference_price??p.bulk_price);
  const net=amount(p.unit_size),drained=amount(p.drained_weight);const variable=raw.is_variable_weight===true||p.approx_size===true;
  if(!context||!/^\d{5}$/.test(context.postcode)||!/^\w{1,12}$/.test(context.warehouse)||!Number.isFinite(Date.parse(context.fetchedAt)))throw Error('Contexto del precio no válido');
  const referenceFormat=String(p.reference_format||p.size_format);if(!refs.includes(referenceFormat))throw Error('Unidad de referencia no válida');
  const name=String(raw.display_name||'').slice(0,200);if(!name)throw Error('Producto sin nombre');
  const url=String(raw.share_url||'');if(!url.startsWith('https://tienda.mercadona.es/product/'+id+'/'))throw Error('Fuente de producto no válida');
  const available=raw.published!==false&&(!raw.unavailable_from||Date.parse(raw.unavailable_from)>Date.now());
  return {id,name,source:'mercadona',url,unitPriceCents:fixedCents,referencePrice:reference,referenceFormat,sizeFormat:p.size_format,netAmount:net,drainedAmount:drained,variable,available,postcode:context.postcode,warehouse:context.warehouse,fetchedAt:context.fetchedAt};
 };
 M.snapshot=()=>{const snapshot=root.MERCADONA_SNAPSHOT||{},products={};for(const [id,record]of Object.entries(snapshot.records||{})){try{products[id]=M.normalize(record.raw,record.context);}catch(e){}}
 return {postcode:snapshot.postcode||'41011',warehouse:snapshot.warehouse||'svq1',fetchedAt:snapshot.fetchedAt||'',selection:M.defaultSelection(),products,errors:{...snapshot.errors}};};
 M.validProduct=(p)=>{
  if(!p||!M.allowedIds().has(p.id)||p.source!=='mercadona'||typeof p.name!=='string'||p.name.length>200||!p.url?.startsWith('https://tienda.mercadona.es/product/'+p.id+'/')||!Number.isInteger(p.unitPriceCents)||p.unitPriceCents<0||p.unitPriceCents>1000000||!Number.isFinite(p.referencePrice)||p.referencePrice<0||p.referencePrice>10000||!refs.includes(p.referenceFormat)||!['kg','l','ud'].includes(p.sizeFormat)||typeof p.variable!=='boolean'||typeof p.available!=='boolean'||!/^\d{5}$/.test(p.postcode)||!/^\w{1,12}$/.test(p.warehouse)||!Number.isFinite(Date.parse(p.fetchedAt))||Date.parse(p.fetchedAt)>Date.now()+300000)throw Error('Precio guardado no válido');
  for(const v of [p.netAmount,p.drainedAmount])if(v!==null&&(!Number.isFinite(v)||v<=0||v>1000))throw Error('Formato guardado no válido');
  return {id:p.id,name:p.name,source:'mercadona',url:p.url,unitPriceCents:p.unitPriceCents,referencePrice:p.referencePrice,referenceFormat:String(p.referenceFormat).slice(0,20),sizeFormat:p.sizeFormat,netAmount:p.netAmount,drainedAmount:p.drainedAmount,variable:p.variable,available:p.available,postcode:p.postcode,warehouse:p.warehouse,fetchedAt:p.fetchedAt};
 };
 M.usableG=(p,ingredient)=>{
  if(!p)return null;const n=p.drainedAmount??p.netAmount;if(n===null)return null;
  if(p.sizeFormat==='kg'||p.sizeFormat==='l')return n*1000;
  if(p.sizeFormat==='ud'&&ingredient==='huevo')return n*55;
  return null;
 };
 M.format=(p)=>{
  if(!p)return 'Formato sin verificar';const fmt=n=>new Intl.NumberFormat('es-ES',{maximumFractionDigits:3}).format(n);
  let result=p.netAmount!==null?`${fmt(p.netAmount)} ${p.sizeFormat==='l'?'L':p.sizeFormat==='ud'?'ud.':'kg'}`:'Peso neto no informado';
  if(p.drainedAmount!==null)result+=` · ${fmt(p.drainedAmount*1000)} g útiles/escurridos`;
  if(p.variable)result+=' · peso variable';return result;
 };
 M.fresh=p=>{const age=Date.now()-Date.parse(p.fetchedAt);return age>=-300000&&age<=24*3600000;};
 root.MesaMarket=M;if(typeof module!=='undefined')module.exports=M;
})(typeof window!=='undefined'?window:globalThis);
