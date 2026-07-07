#!/usr/bin/env node
/* Replay interactions and write JSONL traces with semantic state. */
const fs=require('fs'); const path=require('path');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
function toUrl(p){if(/^https?:\/\//.test(p)||/^file:/.test(p))return p; return 'file://' + path.resolve(p);}
async function state(page, selector){
  return await page.evaluate((selector)=>{
    const el=document.querySelector(selector); const body=getComputedStyle(document.body);
    if(!el) return {exists:false, url:location.href, active:null, body_overflow:body.overflow};
    const r=el.getBoundingClientRect(); const cs=getComputedStyle(el); const expanded=el.getAttribute('aria-expanded');
    let controlledVisible=null; const controls=el.getAttribute('aria-controls');
    if(controls){ const p=document.getElementById(controls); if(p){ const pr=p.getBoundingClientRect(); const pcs=getComputedStyle(p); controlledVisible=pr.width>0&&pr.height>0&&pcs.display!=='none'&&pcs.visibility!=='hidden'&&Number(pcs.opacity)>0.001; }}
    return {exists:true, url:location.href, active:document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null, rect:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}, display:cs.display, visibility:cs.visibility, opacity:Number(cs.opacity), aria_expanded:expanded, className:String(el.className||''), controlled_visible:controlledVisible, body_overflow:body.overflow};
  }, selector);
}
async function main(){
  const url=arg('url'), matrixPath=arg('matrix'), out=arg('out'), side=arg('side','original');
  if(!url||!matrixPath||!out) throw new Error('Usage: --url url --matrix interaction_matrix.json --side original|candidate --out traces.jsonl');
  const {chromium}=require('playwright'); const matrix=JSON.parse(fs.readFileSync(matrixPath,'utf8')); const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:Number(arg('viewport','390')),height:Number(arg('height','1400'))}});
  const traces=[]; const screenshotDir=path.join(path.dirname(path.dirname(out)),'screenshots','behavior'); fs.mkdirSync(screenshotDir,{recursive:true});
  for(const it of matrix.interactions||[]){
    await page.goto(toUrl(url),{waitUntil:'networkidle'});
    const before=await state(page,it.selector); let error=null; let safe_boundary_applied=false;
    try{
      if(it.action==='hover') await page.hover(it.selector,{timeout:2000});
      else if(it.action==='focus') await page.focus(it.selector,{timeout:2000});
      else if(it.action==='click') await page.click(it.selector,{timeout:2000});
      else if(it.action==='keyboard-enter'){ await page.focus(it.selector,{timeout:2000}); await page.keyboard.press('Enter'); }
      else if(it.action==='keyboard-space'){ await page.focus(it.selector,{timeout:2000}); await page.keyboard.press('Space'); }
      else if(it.action==='escape') await page.keyboard.press('Escape');
      else if(it.action==='outside-click') await page.mouse.click(5,5);
      else if(it.action==='scroll') await page.mouse.wheel(0,600);
      await page.waitForTimeout(Number(arg('settle-ms','250')));
    }catch(e){ error=String(e).slice(0,300); }
    const after=await state(page,it.selector); const shot=`${side}_${it.interaction_id.replace(/[^a-z0-9_.-]/gi,'_')}.png`; await page.screenshot({path:path.join(screenshotDir,shot), fullPage:false});
    traces.push({side, interaction_id:it.interaction_id, component_id:it.component_id, selector:it.selector, action:it.action, criticality:it.criticality||'normal', before, after, screenshot:path.join('screenshots','behavior',shot), error, safe_boundary_applied});
  }
  await browser.close(); fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,traces.map(t=>JSON.stringify(t)).join('\n')+'\n'); console.log(`traces=${traces.length} out=${out}`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
