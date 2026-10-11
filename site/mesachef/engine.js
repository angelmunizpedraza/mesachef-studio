(function(root){
 'use strict';
 const E={}; const ingredient=()=>root.INGREDIENTS, recipes=()=>root.RECIPES;
 E.localDate=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
 E.dateAt=(iso,offset)=>{const d=new Date(iso+'T12:00:00');d.setDate(d.getDate()+offset);return d;};
 E.recipe=id=>recipes().find(r=>r.id===id);
 E.defaults=()=>({version:3,comfort:{easy:false,textSize:'normal',contrast:false,motion:'system'},customRecipes:[],history:[],batchChecks:{},market:root.MesaMarket.snapshot(),receipts:{},prefs:{name:'',people:2,budget:75,days:7,meals:['lunch','dinner'],diet:'all',allergens:[],maxTime:30,protein:false,start:E.localDate(),theme:'light'},plan:{},pantry:{},prices:{},packs:{},favorites:[],checks:{},extras:[],cooked:[],generation:0});
 E.product=(s,id)=>{const receipt=s.receipts[id];if(receipt)return {...receipt,status:'manual',source:'manual',variable:false};const pid=s.market.selection[id],p=s.market.products[pid];if(!p)return null;return {...p,status:p.postcode!==s.market.postcode||p.warehouse!==s.market.warehouse?'area':!p.available?'unavailable':s.market.errors[pid]?'failed':!root.MesaMarket.fresh(p)?'stale':'current'};};
 E.priced=p=>p&&['current','manual'].includes(p.status);
 E.pack=(s,id)=>{const p=E.product(s,id);return E.priced(p)?(p.source==='manual'?p.usableG:root.MesaMarket.usableG(p,id)):null;};
 E.price=(s,id)=>{const p=E.product(s,id),g=E.pack(s,id);if(!E.priced(p)||!g||p.variable)return null;return p.unitPriceCents*10/g;};
 E.recipeCost=(s,r,people=1)=>{let sum=0;for(const i of r.ingredients){const price=E.price(s,i.id);if(price===null)return null;sum+=price*i.g*people/1000;}return sum;};
 E.valid=(r,p,kind)=>Boolean(r && (kind==='breakfast'?r.kind==='breakfast':r.kind==='main') && r.time<=p.maxTime && (p.diet==='all'||(p.diet==='vegetarian'?r.vegetarian:r.vegan)) && !r.allergens.some(a=>p.allergens.includes(a)) && (!p.protein||r.protein>=(kind==='breakfast'?10:25)));
 E.pantryQty=(s,id)=>{const p=s.pantry[id];return p && (!p.expiry||p.expiry>=E.localDate())?p.qty:0;};
 E.required=s=>{const req={};Object.entries(s.plan).forEach(([key,slot])=>{if(s.cooked.includes(key))return;const r=E.recipe(slot.id);if(!r)return;r.ingredients.forEach(i=>req[i.id]=(req[i.id]||0)+i.g*slot.servings);});return req;};
 E.shopping=s=>Object.entries(E.required(s)).map(([id,g])=>{const owned=E.pantryQty(s,id),need=Math.max(0,g-owned),product=E.product(s,id),pack=E.pack(s,id),known=E.priced(product)&&pack>0,variable=known&&product.variable,packs=known&&!variable?Math.ceil(Math.max(0,need-0.001)/pack):null,costCents=packs!==null?packs*product.unitPriceCents:null;return {id,name:ingredient()[id].name,aisle:ingredient()[id].aisle,required:g,owned,need,product,pack,packs,buy:packs!==null?packs*pack:null,costCents,cost:costCents!==null?costCents/100:null,unknown:!known,variable};}).filter(i=>i.need>0.001).sort((a,b)=>a.aisle.localeCompare(b.aisle,'es')||a.name.localeCompare(b.name,'es'));
 E.summary=s=>{const rows=E.shopping(s),knownCents=rows.reduce((n,x)=>n+(x.costCents??0),0)+s.extras.reduce((n,x)=>n+Math.round(x.cost*100),0),missing=rows.filter(x=>x.unknown).length,variable=rows.filter(x=>x.variable).length;return {knownTotal:knownCents/100,total:missing||variable?null:knownCents/100,missing,variable,complete:!missing&&!variable};};
 E.total=s=>E.summary(s).total;
 E.consumedCost=s=>{const costs=Object.values(s.plan).map(x=>E.recipeCost(s,E.recipe(x.id),x.servings));return costs.some(x=>x===null)?null:costs.reduce((a,b)=>a+b,0);};
 E.seeded=seed=>()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
 E.generate=s=>{
  const p=s.prefs,pools={}; for(const kind of p.meals){pools[kind]=recipes().filter(r=>E.valid(r,p,kind));if(!pools[kind].length)return {error:`No hay recetas para ${kind==='breakfast'?'el desayuno':kind==='lunch'?'la comida':'la cena'} con estos filtros. Amplía el tiempo o cambia las preferencias.`};}
  for(const [key,slot] of Object.entries(s.plan)){if(slot.locked && !E.valid(E.recipe(slot.id),p,key.split('-')[1]))return {error:'Hay una receta fijada que no cumple los filtros. Desfíjala para continuar.'};}
  let best=null,bestScore=Infinity;const rand=E.seeded(20261010+s.generation*937+Date.now()%100000);
  for(let trial=0;trial<(p.days*p.meals.length>100?12:80);trial++){
   const plan={},uses={};const dayIds={};
   for(let day=0;day<p.days;day++){dayIds[day]=[];for(const kind of p.meals){const key=day+'-'+kind,old=s.plan[key];if(old?.locked){plan[key]={...old};uses[old.id]=(uses[old.id]||0)+1;dayIds[day].push(old.id);continue;}
    const pool=pools[kind]; const ranked=pool.map(r=>{const overlap=r.ingredients.filter(i=>E.pantryQty(s,i.id)>0).length/r.ingredients.length;const sameDay=dayIds[day].includes(r.id)?100:0;return {r,score:(uses[r.id]||0)*5+sameDay+(E.recipeCost(s,r)??20)*(trial%3===0?1.4:0.3)-overlap*2+rand()*3};}).sort((a,b)=>a.score-b.score);
    const r=ranked[0].r;plan[key]={id:r.id,servings:p.people,locked:false};uses[r.id]=(uses[r.id]||0)+1;dayIds[day].push(r.id);
   }}
   const candidate={...s,plan,cooked:[]};const summary=E.summary(candidate),cost=summary.knownTotal;const duplicate=Object.values(uses).reduce((x,n)=>x+Math.max(0,n-1),0);const over=Math.max(0,cost-p.budget);
   const mains=Object.values(plan).map(x=>E.recipe(x.id)).filter(r=>r.kind==='main');
   const hasMeat=mains.some(r=>r.ingredients.some(i=>['pollo','pavo','ternera'].includes(i.id)));
   const hasFish=mains.some(r=>r.ingredients.some(i=>['salmon','atun','merluza','gambas'].includes(i.id)));
   const varietyPenalty=p.diet==='all'&&mains.length>=4?(!hasMeat?5:0)+(!hasFish?4:0):0;
   const score=summary.missing*10000+over*100+duplicate*2+cost*0.08+varietyPenalty;
   if(score<bestScore){bestScore=score;best={plan,cost:summary.total,over,duplicate,missing:summary.missing,variable:summary.variable};}
  }
  return best;
 };
 E.consume=(s,slot,key)=>{
  if(s.cooked.includes(key))return {error:'Esta comida ya está marcada como cocinada.'};
  const r=E.recipe(slot.id),missing=[];r.ingredients.forEach(i=>{const p=s.pantry[i.id];const needed=i.g*slot.servings,have=E.pantryQty(s,i.id);if(have<needed)missing.push(ingredient()[i.id].name);if(p&&have>0){p.qty=Math.max(0,p.qty-needed);if(p.qty===0)delete s.pantry[i.id];}});s.cooked.push(key);return {missing};
 };
 E.validate=raw=>{
  if(!raw||typeof raw!=='object'||![1,2].includes(raw.version))throw Error('Formato de copia incompatible');
  const s=E.defaults(), p=raw.prefs;
  const num=(n,min,max)=>typeof n==='number'&&Number.isFinite(n)&&n>=min&&n<=max;
  const short=(v,max)=>typeof v==='string'&&v.length<=max;
  const iso=v=>short(v,10)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&E.localDate(E.dateAt(v,0))===v;
  const allergens=['gluten','crustaceos','huevo','pescado','cacahuetes','soja','leche','frutos','apio','mostaza','sesamo','sulfitos','altramuz','moluscos'];
  if(!p||!short(p.name,40)||!num(p.people,1,Number.MAX_SAFE_INTEGER)||!Number.isInteger(p.people)||!num(p.budget,0,Number.MAX_SAFE_INTEGER)||!num(p.days,1,Number.MAX_SAFE_INTEGER)||!Number.isInteger(p.days)||!Array.isArray(p.meals)||!p.meals.length||p.meals.length>3||new Set(p.meals).size!==p.meals.length||!p.meals.every(x=>['breakfast','lunch','dinner'].includes(x))||!['all','vegetarian','vegan'].includes(p.diet)||!num(p.maxTime,1,Number.MAX_SAFE_INTEGER)||!Array.isArray(p.allergens)||p.allergens.length>14||!p.allergens.every(x=>allergens.includes(x))||!iso(p.start)||!['light','dark'].includes(p.theme)||typeof p.protein!=='boolean')throw Error('Preferencias no válidas');
  s.prefs={name:p.name,people:p.people,budget:p.budget,days:p.days,meals:[...p.meals],diet:p.diet,allergens:[...new Set(p.allergens)],maxTime:p.maxTime,protein:p.protein,start:p.start,theme:p.theme};
  const obj=v=>v&&typeof v==='object'&&!Array.isArray(v);
  if(!obj(raw.plan)||false)throw Error('Plan no válido');
  for(const [key,v] of Object.entries(raw.plan)){const [day,kind]=key.split('-');if(!/^\d+-(breakfast|lunch|dinner)$/.test(key)||Number(day)>=p.days||!p.meals.includes(kind)||!v||!E.valid(E.recipe(v.id),p,kind)||!num(v.servings,1,Number.MAX_SAFE_INTEGER)||!Number.isInteger(v.servings)||typeof v.locked!=='boolean')throw Error('Receta del plan no válida');s.plan[key]={id:v.id,servings:v.servings,locked:v.locked};}
  if(!obj(raw.pantry)||!obj(raw.prices)||!obj(raw.packs))throw Error('Datos de despensa no válidos');
  for(const [id,v] of Object.entries(raw.pantry)){if(!Object.hasOwn(ingredient(),id)||!v||!num(v.qty,0,Number.MAX_SAFE_INTEGER)||!short(v.expiry,10)||(v.expiry&&!iso(v.expiry)))throw Error('Alimento de despensa no válido');s.pantry[id]={qty:v.qty,expiry:v.expiry};}
  for(const field of ['prices','packs'])for(const [id,n]of Object.entries(raw[field])){if(!Object.hasOwn(ingredient(),id)||!num(n,field==='packs'?1:0,Number.MAX_SAFE_INTEGER))throw Error('Precio o envase no válido');s[field][id]=n;}
  if(!Array.isArray(raw.favorites)||false||!raw.favorites.every(id=>E.recipe(id)))throw Error('Favoritos no válidos');s.favorites=[...new Set(raw.favorites)];
  if(!obj(raw.checks)||false)throw Error('Lista no válida');
  for(const [id,v]of Object.entries(raw.checks)){if(typeof v!=='boolean'||(!Object.hasOwn(ingredient(),id)&&!/^x\d{1,20}$/.test(id)))throw Error('Elemento de lista no válido');s.checks[id]=v;}
  if(!Array.isArray(raw.extras)||false)throw Error('Demasiados extras');
  s.extras=raw.extras.map(v=>{if(!v||!/^x\d{1,20}$/.test(v.id)||!short(v.name,80)||!v.name.trim()||!short(v.qty,40)||!num(v.cost,0,Number.MAX_SAFE_INTEGER))throw Error('Extra no válido');return {id:v.id,name:v.name,qty:v.qty,cost:v.cost};});
  if(new Set(s.extras.map(x=>x.id)).size!==s.extras.length)throw Error('Extras duplicados');
  if(!Array.isArray(raw.cooked)||false||!raw.cooked.every(x=>Object.hasOwn(s.plan,x)))throw Error('Registro de comidas no válido');s.cooked=[...new Set(raw.cooked)];
  s.prices={};s.packs={};
  if(raw.version===2){
   const m=raw.market,allowed=root.MesaMarket.allowedIds();
   if(!obj(m)||!/^\d{5}$/.test(m.postcode)||!/^\w{1,12}$/.test(m.warehouse)||!obj(m.selection)||!obj(m.products)||!obj(m.errors)||Object.keys(m.products).length>150)throw Error('Catálogo no válido');
   const selection={},products={},errors={};
   for(const id of Object.keys(ingredient())){const pid=m.selection[id];if(!root.PRODUCT_OPTIONS[id]?.includes(pid))throw Error('Selección de producto no válida');selection[id]=pid;}
   for(const [id,p]of Object.entries(m.products)){if(id!==p.id)throw Error('Identidad de precio no válida');products[id]=root.MesaMarket.validProduct(p);}
   for(const [id,e]of Object.entries(m.errors)){if(!allowed.has(id)||!short(e,300))throw Error('Error de catálogo no válido');errors[id]=e;}
   if(!short(m.fetchedAt,50)||(m.fetchedAt&&!Number.isFinite(Date.parse(m.fetchedAt))))throw Error('Fecha de catálogo no válida');
   s.market={postcode:m.postcode,warehouse:m.warehouse,fetchedAt:m.fetchedAt,selection,products,errors};
   if(!obj(raw.receipts))throw Error('Precios manuales no válidos');
   for(const [id,p]of Object.entries(raw.receipts)){if(!Object.hasOwn(ingredient(),id)||!p||!Number.isInteger(p.unitPriceCents)||!num(p.unitPriceCents,0,1000000)||!num(p.usableG,1,Number.MAX_SAFE_INTEGER)||!short(p.name,200)||!Number.isFinite(Date.parse(p.fetchedAt)))throw Error('Ticket no válido');s.receipts[id]={unitPriceCents:p.unitPriceCents,usableG:p.usableG,name:p.name,fetchedAt:p.fetchedAt};}
  }
  s.generation=num(raw.generation,0,1000000)?Math.floor(raw.generation):0;return s;
 };

 const seedRecipes=[...recipes()];
 E.setCustom=list=>{root.RECIPES.splice(0,root.RECIPES.length,...seedRecipes,...list);};
 E.normalizeRecipe=raw=>{
  const num=n=>typeof n==='number'&&Number.isFinite(n)&&n>0&&n<=Number.MAX_SAFE_INTEGER;
  if(!raw||!/^u[a-zA-Z0-9-]+$/.test(raw.id)||typeof raw.title!=='string'||!raw.title.trim()||raw.title.length>200||!num(raw.time)||!['main','breakfast'].includes(raw.kind)||!Array.isArray(raw.ingredients)||!raw.ingredients.length||!Array.isArray(raw.steps)||!raw.steps.length)throw Error('Receta propia no válida');
  const items=raw.ingredients.map(i=>{if(!i||!Object.hasOwn(ingredient(),i.id)||!num(i.g))throw Error('Ingrediente de receta no válido');return{id:i.id,g:i.g};});
  if(new Set(items.map(i=>i.id)).size!==items.length)throw Error('Combina los ingredientes repetidos');
  const steps=raw.steps.map(v=>{if(typeof v!=='string'||!v.trim()||v.length>5000)throw Error('Paso no válido');return v.trim();});
  const all=[...new Set(items.flatMap(i=>ingredient()[i.id].allergens))];
  const vegan=items.every(i=>ingredient()[i.id].vegan),vegetarian=!items.some(i=>['pollo','pavo','ternera','salmon','atun','merluza','gambas'].includes(i.id));
  const macros={};for(const k of ['kcal','protein','carbs','fat'])macros[k]=Math.round(items.reduce((n,i)=>n+ingredient()[i.id][k]*i.g/100,0));
  return{id:raw.id,title:raw.title.trim(),time:raw.time,kind:raw.kind,image:['bowl','pasta','salad','breakfast','pizza','soup'].includes(raw.image)?raw.image:'bowl',ingredients:items,steps,spices:typeof raw.spices==='string'?raw.spices.slice(0,500):'Condimentos, al gusto',equipment:typeof raw.equipment==='string'?raw.equipment.slice(0,500):'Según preparación',note:typeof raw.note==='string'?raw.note.slice(0,2000):'',allergens:all,vegan,vegetarian,...macros,custom:true};
 };
 const legacyValidate=E.validate;
 E.validate=raw=>{
  if(!raw||![1,2,3].includes(raw.version))throw Error('Copia incompatible');
  let customs=[];if(raw.version===3){if(!Array.isArray(raw.customRecipes))throw Error('Recetas no válidas');customs=raw.customRecipes.map(E.normalizeRecipe);if(new Set(customs.map(r=>r.id)).size!==customs.length)throw Error('Recetas duplicadas');}
  const before=recipes().slice(seedRecipes.length);E.setCustom(customs);
  try{const s=legacyValidate({...raw,version:raw.version===1?1:2});s.version=3;s.customRecipes=customs;s.history=[];s.batchChecks={};
   if(raw.version===3){if(!Array.isArray(raw.history))throw Error('Historial no válido');s.history=raw.history.map(h=>{if(!h||typeof h.id!=='string'||!/^h[a-zA-Z0-9-]+$/.test(h.id)||typeof h.title!=='string'||h.title.length>200||!Number.isFinite(Date.parse(h.createdAt)))throw Error('Menú guardado no válido');const historical={...s,prefs:h.prefs,plan:h.plan,checks:{},cooked:[],history:[],customRecipes:h.customRecipes||customs};const past=E.validate(historical);return{id:h.id,title:h.title,createdAt:h.createdAt,prefs:past.prefs,plan:past.plan,customRecipes:past.customRecipes};});if(new Set(s.history.map(h=>h.id)).size!==s.history.length)throw Error('Menús repetidos');if(raw.batchChecks&&typeof raw.batchChecks==='object')for(const [key,value]of Object.entries(raw.batchChecks))if(typeof value==='boolean'&&/^\d+-(breakfast|lunch|dinner)-\d+$/.test(key))s.batchChecks[key]=value;}
   if(raw.comfort!==undefined){const c=raw.comfort;if(!c||typeof c.easy!=='boolean'||typeof c.contrast!=='boolean'||!['normal','large','largest'].includes(c.textSize)||!['system','reduce'].includes(c.motion))throw Error('Apariencia no válida');s.comfort={easy:c.easy,contrast:c.contrast,textSize:c.textSize,motion:c.motion};}
   return s;
  }finally{E.setCustom(before);}
 };
 E.coverage=(s,r,servings=s.prefs.people)=>{let covered=0,total=0;for(const i of r.ingredients){const need=i.g*servings;total+=need;covered+=Math.min(need,E.pantryQty(s,i.id));}return total?covered/total:0;};
 E.rescue=s=>{const today=E.localDate(),soon=E.localDate(E.dateAt(today,3));return recipes().filter(r=>E.valid(r,s.prefs,r.kind==='breakfast'?'breakfast':'lunch')).map(r=>{const coverage=E.coverage(s,r),urgent=r.ingredients.filter(i=>{const p=s.pantry[i.id];return p&&p.qty>0&&p.expiry&&p.expiry>=today&&p.expiry<=soon;}).map(i=>i.id);const missing=r.ingredients.filter(i=>E.pantryQty(s,i.id)<i.g*s.prefs.people).map(i=>({id:i.id,g:i.g*s.prefs.people-E.pantryQty(s,i.id)}));return{recipe:r,coverage,urgent,missing,score:urgent.length*3+coverage};}).filter(x=>x.coverage>0).sort((a,b)=>b.score-a.score);};
 E.packOptions=(s,row)=>(root.PRODUCT_OPTIONS[row.id]||[]).map(pid=>{const p=s.market.products[pid];if(!p||!p.available||p.variable||!root.MesaMarket.fresh(p)||s.market.errors[pid]||p.postcode!==s.market.postcode||p.warehouse!==s.market.warehouse)return null;const pack=root.MesaMarket.usableG(p,row.id);if(!pack)return null;const count=Math.ceil(Math.max(0,row.need-0.001)/pack);return{product:p,packs:count,usableG:pack,remaining:count*pack-row.need,costCents:count*p.unitPriceCents};}).filter(Boolean).sort((a,b)=>a.costCents-b.costCents||a.remaining-b.remaining);
 E.packSuggestions=s=>E.shopping(s).map(row=>{if(s.receipts[row.id]||row.unknown||row.variable)return null;const options=E.packOptions(s,row),best=options[0];if(!best||best.product.id===row.product.id)return null;const saving=row.costCents-best.costCents;return saving>0||best.remaining<row.buy-row.need?{...best,ingredient:row.id,savingCents:saving,currentCents:row.costCents,currentRemaining:row.buy-row.need}:null;}).filter(Boolean);
 E.batch=(s,day)=>s.prefs.meals.map(kind=>{const key=day+'-'+kind,slot=s.plan[key];if(!slot||s.cooked.includes(key))return null;const r=E.recipe(slot.id);return{key,recipe:r,servings:slot.servings,steps:r.steps};}).filter(Boolean);
 root.MesaEngine=E;if(typeof module!=='undefined')module.exports=E;
})(typeof window!=='undefined'?window:globalThis);
