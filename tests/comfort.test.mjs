import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM,VirtualConsole} from 'jsdom';
import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
const read=p=>readFileSync(p,'utf8');
function environment(){
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(read('site/index.html'),{url:'https://mesa.test/mi-repo/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window;
 w.scrollTo=()=>{};Object.defineProperty(w.crypto,'randomUUID',{value:()=>webcrypto.randomUUID()});w.MesaStore={save:async()=>{}};
 for(const f of ['data','market-data','market','engine','app','comfort'])w.eval(read('site/mesachef/'+f+'.js'));
 const click=s=>{const b=w.document.querySelector(s);assert(b,s);b.click();};
 const submit=id=>w.document.getElementById(id).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 return{dom,w,click,submit,errors};
}
test('vista fácil conserva todas las funciones y preferencias en las copias',()=>{
 const {dom,w,click,submit,errors}=environment();assert.equal(w.document.querySelectorAll('.start-grid button').length,3);
 click('[data-comfort="easy"]');assert(w.document.body.classList.contains('easy-view'));assert.equal(w.document.querySelectorAll('#nav button').length,4);
 click('#nav [data-comfort="more"]');assert.equal(w.document.querySelectorAll('.easy-menu [data-comfort="navigate"]').length,9);
 click('.easy-menu [data-page="history"]');assert.equal(w.MesaApp.getPage(),'history');assert.equal(w.document.activeElement.id,'main');
 click('[data-comfort="help"]');click('[data-comfort="appearance"]');w.document.getElementById('comfort-size').value='largest';w.document.getElementById('comfort-contrast').checked=true;submit('comfort-form');
 assert.equal(w.document.documentElement.dataset.textSize,'largest');assert(w.document.body.classList.contains('high-contrast'));
 const copy=w.MesaEngine.validate(JSON.parse(JSON.stringify(w.MesaApp.getState())));assert.equal(copy.comfort.textSize,'largest');assert(copy.comfort.easy);assert(copy.comfort.contrast);
 const invalid=JSON.parse(JSON.stringify(copy));invalid.comfort.textSize='<script>';assert.throws(()=>w.MesaEngine.validate(invalid));
 assert.deepEqual(errors,[]);dom.window.close();
});
test('el asistente valida comidas, conserva alérgenos y no aplica hasta revisar',()=>{
 const {dom,w,click,submit,errors}=environment();const state=w.MesaApp.getState();state.prefs.allergens=['leche'];
 click('[data-comfort="guide"]');w.document.getElementById('guide-people').value='3';w.document.getElementById('guide-days').value='2';
 for(const b of w.document.querySelectorAll('[name="meals"]'))b.checked=false;submit('guide-form');assert.equal(w.document.querySelector('.guide-progress b').textContent,'Paso 1 de 3');assert(!w.document.getElementById('guide-error').hidden);
 w.document.getElementById('guide-lunch').checked=true;submit('guide-form');assert(w.document.getElementById('guide-allergen-leche').checked);assert.equal(w.MesaApp.getState().prefs.people,2);
 submit('guide-form');assert(w.document.querySelector('.guide-review'));assert.equal(Object.keys(state.plan).length,0);submit('guide-form');
 assert.equal(w.MesaApp.getState().prefs.people,3);assert.equal(Object.keys(w.MesaApp.getState().plan).length,2);assert.equal(w.MesaApp.getPage(),'plan');assert.deepEqual([...w.MesaApp.getState().prefs.allergens],['leche']);
 assert.deepEqual(errors,[]);dom.window.close();
});
test('un menú guiado puede deshacerse conservando menú, datos y apariencia anteriores',()=>{
 const {dom,w,click,submit,errors}=environment();w.MesaApp.generate();const original=JSON.stringify(w.MesaApp.getState().plan),originalPeople=w.MesaApp.getState().prefs.people;
 w.MesaApp.goto('home');click('[data-comfort="guide"]');w.document.getElementById('guide-people').value='4';submit('guide-form');submit('guide-form');assert(w.document.querySelector('#guide-form .warn').textContent.includes('reemplazará'));submit('guide-form');
 click('[data-action="undo"]');assert.equal(JSON.stringify(w.MesaApp.getState().plan),original);assert.equal(w.MesaApp.getState().prefs.people,originalPeople);
 assert.deepEqual(errors,[]);dom.window.close();
});
test('pantallas principales no tienen botones sin nombre ni campos sin etiqueta',()=>{
 const {dom,w,errors}=environment();const failures=[];
 for(const page of ['home','plan','shop','explore','pantry','lab','history','settings']){
  w.MesaApp.goto(page);
  for(const b of w.document.querySelectorAll('#app button'))if(!b.textContent.trim()&&!b.getAttribute('aria-label')&&!b.getAttribute('aria-labelledby'))failures.push(page+': botón '+b.dataset.action);
  for(const i of w.document.querySelectorAll('#main input:not([type=hidden]),#main select,#main textarea'))if(!i.getAttribute('aria-label')&&!i.getAttribute('aria-labelledby')&&!i.labels?.length)failures.push(page+': campo '+i.id);
 }
 assert.deepEqual(failures,[]);assert.deepEqual(errors,[]);dom.window.close();
});
test('tokens de texto y contraste no dependen de un tamaño fijo en píxeles',()=>{
 const css=read('site/mesachef/style.css')+read('site/mesachef/catalog.css');assert(!/font-size:[0-9]+px/.test(css));
 function luminance(hex){const values=hex.match(/[a-f\d]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return values[0]*.2126+values[1]*.7152+values[2]*.0722;}
 for(const [fg,bg] of [['526159','f6f5ef'],['173d33','ffffff'],['bed0c4','202925'],['ffffff','234f3d'],['b84c24','f6f5ef']]){
  const a=luminance(fg),b=luminance(bg);assert((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,fg+' / '+bg);
 }
});
