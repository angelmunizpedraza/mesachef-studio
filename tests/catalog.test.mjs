import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const ctx=vm.createContext({URL,Date});vm.runInContext(fs.readFileSync('site/mesachef/catalog-core.js','utf8'),ctx);const C=ctx.MesaCatalogCore;
const row=(patch={})=>({id:'mercadona:1',retailer:'mercadona',sourceId:'1',name:'Leche entera',url:'https://tienda.mercadona.es/product/1/leche',priceCents:109,referenceCents:109,referenceUnit:'L',fetchedAt:new Date().toISOString(),zoneConfirmed:true,postcode:'41011',warehouse:'svq1',variable:false,available:true,categories:['Lácteos'],...patch});
test('no suma precios de otra zona, caducados, condicionados o al peso',()=>{
 const items=[row(),row({id:'mercadona:2',sourceId:'2',zoneConfirmed:false}),row({id:'mercadona:3',sourceId:'3',fetchedAt:new Date(Date.now()-90000000).toISOString()}),row({id:'mercadona:4',sourceId:'4',variable:true}),row({id:'mercadona:5',sourceId:'5',conditionalPrice:true})];
 const sum=C.basket(items.map(product=>({product,qty:3})),'41011');assert.equal(sum.totalCents,327);assert.equal(sum.pending,4);assert.equal(sum.complete,false);assert.equal(C.basket([{product:row(),qty:1}],'28001').totalCents,0);
});
test('céntimos enteros y cantidades verificadas',()=>{assert.equal(C.basket([{product:row(),qty:17}],'41011').totalCents,1853);assert.throws(()=>C.basket([{product:row(),qty:1.2}],'41011'));assert.throws(()=>C.basket([{product:row({priceCents:1000000}),qty:Number.MAX_SAFE_INTEGER}],'41011'));});
test('rechaza fuentes ajenas, fechas futuras y cobertura inventada',()=>{
 assert.throws(()=>C.product(row({url:'https://tienda.mercadona.es.evil.invalid/product/1/leche'})));
 assert.throws(()=>C.product(row({fetchedAt:new Date(Date.now()+3600000).toISOString()})));
 assert.throws(()=>C.catalog({schemaVersion:1,retailer:'mercadona',postcode:'41011',warehouse:'svq1',coverage:'categories-checked',expectedCategories:152,checkedCategories:18,errors:{},products:[row()]},'mercadona','41011'));
});
test('búsqueda con acentos, categorías y precios nulos',()=>{
 const data=[row({name:'Lácteos de Sevilla',priceCents:null}),row({id:'mercadona:2',sourceId:'2',name:'Leche semidesnatada'})];
 assert.equal(C.search(data,{query:'lacteos sevilla'}).length,1);assert.equal(C.search(data,{category:'Lácteos'}).length,2);assert.equal(C.search(data,{sort:'price'})[0].sourceId,'2');
});
test('una copia conserva miles de filas y rechaza duplicados',()=>{
 const rows=Array.from({length:1500},(_,n)=>({product:row({id:'mercadona:'+n,sourceId:String(n)}),qty:1}));assert.equal(C.restore({schemaVersion:1,kind:'mesachef-catalog-basket',rows}).length,1500);assert.throws(()=>C.restore({schemaVersion:1,kind:'mesachef-catalog-basket',rows:[rows[0],rows[0]]}));
});
test('una copia importada no convierte sus precios en confirmados antes de consultar',()=>{
 const data={schemaVersion:1,kind:'mesachef-catalog-basket',rows:[{product:row(),qty:2}]};
 const restored=C.restore(data,{requireRefresh:true});assert.equal(C.status(restored[0].product,'41011'),'imported');assert.equal(C.basket(restored,'41011').totalCents,0);
 assert.equal(C.status(C.restore({schemaVersion:1,kind:data.kind,rows:restored})[0].product,'41011'),'imported');
});
test('las cuatro consultas reales pasan validación con sus fechas y cobertura originales',()=>{
 for(const id of ['mercadona','dia','carrefour','mas']){const filename='site/catalogs/'+id+(id==='mercadona'?'-41011':'')+'.json';const data=JSON.parse(fs.readFileSync(filename));const parsed=C.catalog(data,id,'41011');assert.equal(parsed.products.length,data.products.length);assert.ok(parsed.products.length>0);assert.equal(parsed.products[0].fetchedAt,data.products[0].fetchedAt);if(id!=='mercadona')assert.ok(parsed.products.every(p=>!p.zoneConfirmed));}
});

test('compara precios de referencia sin mezclar kilos con litros',()=>{const data=[row({referenceUnit:'kg',referenceCents:299}),row({id:'mercadona:2',sourceId:'2',referenceUnit:'L',referenceCents:99}),row({id:'mercadona:3',sourceId:'3',referenceUnit:'kg',referenceCents:159})];const result=C.search(data,{sort:'per-kg'});assert.equal(result.length,2);assert.equal(result[0].sourceId,'3');assert.equal(C.search(data,{sort:'per-L'}).length,1);});

test('rechaza una copia con cantidades que desbordarían el total al actualizar precios',()=>{assert.throws(()=>C.restore({schemaVersion:1,kind:'mesachef-catalog-basket',rows:[{product:row(),qty:Number.MAX_SAFE_INTEGER}]}));});
