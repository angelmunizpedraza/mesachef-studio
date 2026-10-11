import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {JSDOM,VirtualConsole} from 'jsdom';import {indexedDB} from 'fake-indexeddb';
test('catálogo funciona en subruta, busca, guarda compra y excluye zonas desconocidas',async()=>{
 const warnings=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>warnings.push(e.message));
 const dom=new JSDOM('<div id="catalog"></div>',{url:'https://mesa.test/mi-repo/',runScripts:'outside-only',virtualConsole:vc});const w=dom.window;w.indexedDB=indexedDB;w.MesaBase='https://mesa.test/mi-repo/';w.HTMLElement.prototype.scrollIntoView=()=>{};
 const calls=[];w.fetch=async url=>{calls.push(String(url));const path=new URL(url).pathname.replace('/mi-repo/','site/');const text=readFileSync(path,'utf8');return {ok:true,json:async()=>JSON.parse(text)};};
 w.eval(readFileSync('site/mesachef/catalog-core.js','utf8'));w.eval(readFileSync('site/mesachef/catalog.js','utf8'));w.MesaCatalog.mount(w.document.querySelector('#catalog'),'41011');
 for(let i=0;i<60&&!w.document.querySelector('.catalog-product');i++)await new Promise(resolve=>setTimeout(resolve,10));
 assert(w.document.querySelector('.catalog-product'));assert(calls.every(u=>u.startsWith('https://mesa.test/mi-repo/catalogs/')));
 const target=w.document.querySelector('.catalog-product-open').dataset.id;const product=w.MesaCatalog.products.find(p=>p.id===target);const input=w.document.querySelector('#catalog-search');input.focus();input.value=product.name;input.dispatchEvent(new w.Event('input',{bubbles:true}));assert([...w.document.querySelectorAll('.catalog-product-open')].some(p=>p.dataset.id===target));
 w.document.querySelector('[data-cat="add"]').click();w.document.querySelector('[data-view="basket"]').click();assert(w.document.querySelector('.catalog-basket-row'));
 w.document.querySelector('[data-view="coverage"]').click();assert.equal(w.document.querySelectorAll('.catalog-store').length,JSON.parse(readFileSync('site/catalogs/retailers.json','utf8')).retailers.length);assert(w.document.querySelector('.catalog-warning').textContent.length>10);
 assert.deepEqual(warnings,[]);dom.window.close();
});

test('una copia local conserva productos y fechas cuando falla la red sin confirmar sus importes',async()=>{
 const namespace='https://mesa.test/cache-repo/';const first=new JSDOM('<div id="catalog"></div>',{url:namespace,runScripts:'outside-only'});const w=first.window;w.indexedDB=indexedDB;w.MesaBase=namespace;
 w.fetch=async url=>({ok:true,json:async()=>JSON.parse(readFileSync(new URL(url).pathname.replace('/cache-repo/','site/'),'utf8'))});
 for(const name of ['catalog-core','catalog'])w.eval(readFileSync('site/mesachef/'+name+'.js','utf8'));w.MesaCatalog.mount(w.document.querySelector('#catalog'),'41011');
 for(let i=0;i<100&&!w.MesaCatalog.products.length;i++)await new Promise(r=>setTimeout(r,10));await new Promise(r=>setTimeout(r,100));
 const product=w.MesaCatalog.products[0],date=product.fetchedAt;assert(product);first.window.close();
 const second=new JSDOM('<div id="catalog"></div>',{url:namespace,runScripts:'outside-only'}),v=second.window;v.indexedDB=indexedDB;v.MesaBase=namespace;v.fetch=async()=>{throw Error('Sin conexión');};
 for(const name of ['catalog-core','catalog'])v.eval(readFileSync('site/mesachef/'+name+'.js','utf8'));v.MesaCatalog.mount(v.document.querySelector('#catalog'),'41011');
 for(let i=0;i<100&&!v.MesaCatalog.products.length;i++)await new Promise(r=>setTimeout(r,10));
 const restored=v.MesaCatalog.products.find(p=>p.id===product.id);assert(restored);assert.equal(restored.fetchedAt,date);assert.equal(restored.needsRefresh,true);assert.equal(v.MesaCatalogCore.status(restored,'41011'),'imported');assert(v.document.querySelector('.notice').textContent.length);second.window.close();
});
