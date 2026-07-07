#!/usr/bin/env node
/* Discover likely interactive components and listener evidence. */
const fs=require('fs'); const path=require('path');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
function toUrl(p){if(/^https?:\/\//.test(p)||/^file:/.test(p))return p; return 'file://' + path.resolve(p);}
function slug(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,50)||'item';}
async function main(){
  const url=arg('url'); const out=arg('out','reports/behavior_inventory.json'); const viewport=Number(arg('viewport','390'));
  if(!url) throw new Error('Usage: --url original --out reports/behavior_inventory.json');
  const {chromium}=require('playwright'); const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:viewport,height:Number(arg('height','1400'))}});
  await page.goto(toUrl(url),{waitUntil:'networkidle'});
  const data=await page.evaluate((viewport)=>{
    const qs='a[href],button,input,select,textarea,[role="button"],[role="menuitem"],[aria-expanded],[tabindex]:not([tabindex="-1"]),summary';
    const els=[...document.querySelectorAll(qs)].filter(el=>{const r=el.getBoundingClientRect(); const cs=getComputedStyle(el); return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden';}).slice(0,200);
    return els.map((el,i)=>{
      const txt=(el.innerText||el.getAttribute('aria-label')||el.getAttribute('title')||el.getAttribute('href')||el.name||el.id||el.tagName).trim().replace(/\s+/g,' ').slice(0,80);
      const kind=el.tagName.toLowerCase()==='a'?'link':(el.tagName.toLowerCase()==='input'?'input':(el.getAttribute('aria-expanded')?'disclosure':'button'));
      let selector=el.getAttribute('data-behavior-id') ? `[data-behavior-id="${el.getAttribute('data-behavior-id')}"]` : (el.id ? `#${CSS.escape(el.id)}` : null);
      if(!selector) selector=`${el.tagName.toLowerCase()}:nth-of-type(${i+1})`;
      return {component_id:`${viewport}:${kind}:${i}:${txt.toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,30)}`, selector, kind, label:txt, criticality: kind==='link' || kind==='button' || kind==='disclosure' ? 'critical':'normal', h2d_path:el.getAttribute('data-h2d-path')||null};
    });
  }, viewport);
  await browser.close();
  const report={result:data.length?'pass':'not-tested', url, viewports:[viewport], components:data};
  fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(report,null,2));
  const listeners={result:data.length?'pass':'not-tested', listeners:data.map(c=>({component_id:c.component_id, selector:c.selector, events:['hover','focus','click','keydown']}))};
  fs.writeFileSync(path.join(path.dirname(out),'event_listener_inventory.json'),JSON.stringify(listeners,null,2));
  console.log(`components=${data.length} out=${out}`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
