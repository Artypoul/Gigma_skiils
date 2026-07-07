#!/usr/bin/env node
/* Capture start/mid/end frame evidence for dynamic surfaces. */
const fs=require('fs'); const path=require('path'); const crypto=require('crypto');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
function toUrl(p){if(/^https?:\/\//.test(p)||/^file:/.test(p))return p; return 'file://' + path.resolve(p);}
function sha(buf){return 'sha256:'+crypto.createHash('sha256').update(buf).digest('hex');}
async function main(){
  const url=arg('url'), inventoryPath=arg('inventory'), out=arg('out'), side=arg('side','original');
  if(!url||!inventoryPath||!out) throw new Error('Usage: --url url --inventory liveness_inventory.json --side original|candidate --out trace.jsonl');
  const {chromium}=require('playwright'); const inventory=JSON.parse(fs.readFileSync(inventoryPath,'utf8'));
  const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:Number(arg('viewport','390')),height:Number(arg('height','1400'))}, deviceScaleFactor:Number(arg('dpr','1'))});
  await page.goto(toUrl(url),{waitUntil:'networkidle'});
  const screenshotDir=path.join(path.dirname(path.dirname(out)),'screenshots','liveness'); fs.mkdirSync(screenshotDir,{recursive:true});
  const traces=[]; const sampleMs=(arg('sample-ms','0,250,500,1000')).split(',').map(Number).filter(n=>!Number.isNaN(n));
  for(const s of inventory.surfaces||[]){
    const samples=[]; const traceId=`${side}:${s.surface_id}`.replace(/[^a-z0-9_.:-]/gi,'_'); let prev=0;
    for(const t of sampleMs){
      const wait=Math.max(0,t-prev); if(wait) await page.waitForTimeout(wait); prev=t;
      const shotName=`${traceId}_${String(t).padStart(4,'0')}.png`.replace(/[^a-z0-9_.-]/gi,'_');
      const fullPath=path.join(screenshotDir,shotName); const buf=await page.screenshot({path:fullPath, fullPage:false});
      const state=await page.evaluate((selector)=>{
        const el=selector==='document'?document.documentElement:document.querySelector(selector); if(!el) return {exists:false};
        const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
        let canvasData=null;
        if(el instanceof HTMLCanvasElement){
          try{ canvasData={width:el.width,height:el.height,data_url_len:el.toDataURL('image/png').length}; } catch(e){ canvasData={error:String(e).slice(0,120)}; }
        }
        return {exists:true, rect:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}, computed:{opacity:cs.opacity, transform:cs.transform, filter:cs.filter, clipPath:cs.clipPath, animationName:cs.animationName, animationDuration:cs.animationDuration, transitionProperty:cs.transitionProperty, transitionDuration:cs.transitionDuration}, canvas:canvasData};
      }, s.selector);
      samples.push({t_ms:t, screenshot:path.join('screenshots','liveness',shotName), frame_hash:sha(buf), computed:state.computed||{}, rect:state.rect||{}, canvas:state.canvas||null});
    }
    traces.push({trace_id:traceId, side, surface_id:s.surface_id, selector:s.selector, kind:s.kind, viewport:inventory.viewports&&inventory.viewports[0]||null, timing:{sample_ms:sampleMs}, samples, errors:[]});
  }
  await browser.close(); fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,traces.map(t=>JSON.stringify(t)).join('\n')+'\n'); console.log(`traces=${traces.length} out=${out}`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
