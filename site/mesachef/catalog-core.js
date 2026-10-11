(function(root){'use strict';
const origins={mercadona:'https://tienda.mercadona.es',dia:'https://www.dia.es',carrefour:'https://www.carrefour.es',mas:'https://www.supermercadosmas.com'};
const C={origins};
C.text=x=>String(x??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
C.unit=x=>({kilo:'kg',kilogramo:'kg',kg:'kg',l:'L',litro:'L',litros:'L',ud:'ud',unidad:'ud',unidades:'ud'}[C.text(x)]||String(x||''));
C.safeURL=(retailer,value)=>{const u=new URL(value);if(u.protocol!=='https:'||u.username||u.password||u.origin!==origins[retailer])throw Error('Ficha fuera de la tienda oficial');return u.href;};
C.product=p=>{
 if(!p||!origins[p.retailer]||typeof p.sourceId!=='string'||!p.sourceId||p.id!==p.retailer+':'+p.sourceId||typeof p.name!=='string'||!p.name.trim()||p.name.length>300)throw Error('Producto no válido');
 for(const field of ['priceCents','referenceCents'])if(p[field]!==null&&(!Number.isSafeInteger(p[field])||p[field]<0||p[field]>1000000))throw Error('Precio no válido');
 const date=Date.parse(p.fetchedAt);if(!Number.isFinite(date)||date>Date.now()+300000)throw Error('Fecha de fuente no válida');
 if(typeof p.zoneConfirmed!=='boolean'||typeof p.variable!=='boolean'||!(p.available===null||typeof p.available==='boolean'))throw Error('Estado de producto no válido');
 if(p.zoneConfirmed&&(!/^\d{5}$/.test(p.postcode)||typeof p.warehouse!=='string'||!p.warehouse))throw Error('Zona sin confirmar');
 const imageOrigins=['https://prod-mercadona.imgix.net','https://www.dia.es','https://static.carrefour.es','https://assets.supermercadosmas.com','https://www.supermercadosmas.com'];let image='';
 try{const u=new URL(p.image);if(imageOrigins.includes(u.origin)&&!u.username&&!u.password)image=u.href;}catch{}
 return {id:p.id,retailer:p.retailer,sourceId:p.sourceId,name:p.name,url:C.safeURL(p.retailer,p.url),priceCents:p.priceCents,referenceCents:p.referenceCents,referenceUnit:C.unit(p.referenceUnit),format:String(p.format||'').slice(0,180),categories:Array.isArray(p.categories)?p.categories.filter(x=>typeof x==='string').map(x=>x.slice(0,150)):[],brand:String(p.brand||'').slice(0,150),image,fetchedAt:p.fetchedAt,postcode:p.postcode||null,warehouse:p.warehouse||null,zoneConfirmed:p.zoneConfirmed,variable:p.variable,available:p.available,conditionalPrice:p.conditionalPrice===true,needsRefresh:p.needsRefresh===true};
};
C.catalog=(data,retailer,postcode)=>{
 if(!data||data.schemaVersion!==1||data.retailer!==retailer||!Array.isArray(data.products)||!['partial','categories-checked'].includes(data.coverage))throw Error('Catálogo no válido');
 if(retailer==='mercadona'&&data.postcode!==postcode)throw Error('Catálogo de otra zona');
 const seen=new Set();const products=data.products.map(p=>{const v=C.product(p);if(v.retailer!==retailer||seen.has(v.id))throw Error('Identidad duplicada');if(v.zoneConfirmed&&(v.postcode!==data.postcode||v.warehouse!==data.warehouse))throw Error('Ficha de otra zona');seen.add(v.id);return v;});
 if(data.coverage==='categories-checked'&&(!Number.isSafeInteger(data.expectedCategories)||data.expectedCategories<1||data.checkedCategories!==data.expectedCategories||Object.keys(data.errors||{}).length))throw Error('Cobertura completa sin verificar');
 return {...data,products};
};
C.status=(p,postcode,time=Date.now())=>{
 if(p.needsRefresh)return 'imported';if(p.available===false)return 'unavailable';if(p.conditionalPrice)return 'conditional';
 const age=time-Date.parse(p.fetchedAt);if(age < -300000||age>86400000)return 'stale';
 if(!p.zoneConfirmed||p.postcode!==postcode)return 'area';if(p.variable)return 'weight';if(p.priceCents===null)return 'missing';return 'current';
};
C.search=(products,{query='',retailer='all',category='all',sort='name',postcode='41011',usable=false}={})=>{
 const words=C.text(query).trim().split(/\s+/).filter(Boolean);
 const referenceUnit=sort==='per-kg'?'kg':sort==='per-L'?'L':null;
 const list=products.filter(p=>(!referenceUnit||(p.referenceUnit===referenceUnit&&p.referenceCents!==null))&&(retailer==='all'||p.retailer===retailer)&&(category==='all'||p.categories.includes(category))&&(!usable||C.status(p,postcode)==='current')&&words.every(w=>C.text([p.name,p.sourceId,p.brand,...p.categories].join(' ')).includes(w)));
 return list.sort((a,b)=>referenceUnit?a.referenceCents-b.referenceCents||a.name.localeCompare(b.name,'es'):sort==='price'?(a.priceCents??Infinity)-(b.priceCents??Infinity)||a.name.localeCompare(b.name,'es'):a.name.localeCompare(b.name,'es'));
};
C.basket=(rows,postcode,time=Date.now())=>{
 let totalCents=0,pending=0,quantity=0;const stores={};
 for(const row of rows){const p=C.product(row.product);if(!Number.isSafeInteger(row.qty)||row.qty<1)throw Error('Cantidad no válida');const state=C.status(p,postcode,time);const amount=state==='current'?p.priceCents*row.qty:null;if(amount!==null&&!Number.isSafeInteger(amount))throw Error('Importe demasiado grande');const group=stores[p.retailer]||(stores[p.retailer]={cents:0,pending:0,quantity:0});quantity+=row.qty;group.quantity+=row.qty;if(amount===null){pending++;group.pending++;}else{totalCents+=amount;group.cents+=amount;}if(!Number.isSafeInteger(totalCents)||!Number.isSafeInteger(quantity))throw Error('Total demasiado grande');}
 return {totalCents,pending,quantity,complete:pending===0,stores};
};
C.restore=(data,{requireRefresh=false}={})=>{
 if(!data||data.schemaVersion!==1||data.kind!=='mesachef-catalog-basket'||!Array.isArray(data.rows))throw Error('Copia de compra no válida');
 const ids=new Set();const rows=data.rows.map(r=>{const p=C.product(r.product);p.needsRefresh=requireRefresh||r.product.needsRefresh===true;if(ids.has(p.id)||!Number.isSafeInteger(r.qty)||r.qty<1)throw Error('Compra duplicada o cantidad no válida');ids.add(p.id);return {product:p,qty:r.qty};});const sum=C.basket(rows,'00000');if(!Number.isSafeInteger(sum.quantity*1000000))throw Error('Cantidades fuera de la precisión numérica admitida');return rows;
};
root.MesaCatalogCore=C;
})(typeof window==='undefined'?globalThis:window);
