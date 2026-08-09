#!/usr/bin/env node
/* Capture scoped motion samples after the inventory-declared trigger sequence. */
const fs=require('fs');const path=require('path');const crypto=require('crypto');
const {launchChromium,contextOptions,installNetworkSandbox,installRuntimeInstrumentation,isExpectedSandboxConsole}=require('./browser');
function arg(name,fallback=null){const i=process.argv.indexOf(`--${name}`);return i>=0?process.argv[i+1]:fallback;}
function toUrl(value){if(/^https?:\/\//.test(value)||/^file:/.test(value))return value;return 'file://'+path.resolve(value).replace(/\\/g,'/');}
function loadJson(value,fallback){return value?JSON.parse(fs.readFileSync(value,'utf8')):fallback;}
function sha(value){return crypto.createHash('sha256').update(value).digest('hex');}
async function applyTrigger(page,surface,trigger){const locator=page.locator(surface.selector);if(trigger==='hover')await locator.hover();else if(trigger==='focus')await locator.focus();else if(trigger==='checked')await locator.check();else if(trigger==='resize')await page.setViewportSize({width:page.viewportSize().width-1,height:page.viewportSize().height});else if(trigger==='playback')await locator.evaluate(el=>el.play().catch(()=>{}));}
async function main(){
  const url=arg('url'),inventoryPath=arg('inventory'),out=arg('out'),side=arg('side','original');if(!url||!inventoryPath||!out)throw new Error('Usage: --url --inventory --out');
  const inventory=loadJson(inventoryPath,{});if(inventory.result==='fail'||inventory.coverage_complete===false)throw new Error('Cannot capture from incomplete liveness inventory');
  const profile=loadJson(arg('profile'),{id:'default',headless:true,device_scale_factor:Number(arg('dpr','1')),is_mobile:false,has_touch:false,locale:'en-US',timezone:'UTC',reduced_motion:'reduce'});
  const viewport={width:Number(arg('viewport','390')),height:Number(arg('height','1400'))};const sampleMs=String(arg('sample-ms','0,250,500,1000')).split(',').map(Number).filter(Number.isFinite);
  const browser=await launchChromium({headless:profile.headless!==false,projectRoot:arg('project-root')||process.cwd()});const traces=[];const screenshotDir=path.join(path.dirname(path.dirname(out)),'screenshots','liveness');fs.mkdirSync(screenshotDir,{recursive:true});
  for(const surface of inventory.surfaces||[]){for(const trigger of surface.triggers||['load']){
    const context=await browser.newContext(contextOptions(profile,viewport));await installNetworkSandbox(context,loadJson(arg('request-allowlist'),[]));await installRuntimeInstrumentation(context);const page=await context.newPage();const errors=[];page.on('pageerror',error=>errors.push({type:'pageerror',message:String(error.message||error).slice(0,500)}));page.on('console',message=>{if(message.type()==='error'&&!isExpectedSandboxConsole(message))errors.push({type:'console-error',message:message.text().slice(0,500)});});
    await page.goto(toUrl(url),{waitUntil:'networkidle'});if(trigger!=='load')await applyTrigger(page,surface,trigger);const locator=page.locator(surface.selector);if(await locator.count()!==1)errors.push({type:'selector-count',message:`expected 1, got ${await locator.count()}`});
    const samples=[];let previous=0;for(const t of sampleMs){const wait=Math.max(0,t-previous);if(wait)await page.waitForTimeout(wait);previous=t;const shotName=`${side}_${surface.surface_id}_${trigger}_${t}.png`.replace(/[^a-z0-9_.-]/gi,'_');const absolute=path.join(screenshotDir,shotName);let buffer;
      if(await locator.count()===1)buffer=await locator.screenshot({path:absolute});else buffer=await page.screenshot({path:absolute,fullPage:false});
      const state=await page.evaluate(selector=>{const el=document.querySelector(selector);if(!el)return{exists:false};const r=el.getBoundingClientRect();const cs=getComputedStyle(el);let canvas=null;if(el instanceof HTMLCanvasElement){try{canvas={width:el.width,height:el.height,data_url_sha_source:el.toDataURL('image/png')};}catch(error){canvas={error:String(error).slice(0,120)};}}return{exists:true,rect:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height},computed:{opacity:cs.opacity,transform:cs.transform,filter:cs.filter,clipPath:cs.clipPath,animationName:cs.animationName,animationDuration:cs.animationDuration,animationDelay:cs.animationDelay,transitionProperty:cs.transitionProperty,transitionDuration:cs.transitionDuration,transitionDelay:cs.transitionDelay},canvas};},surface.selector);
      if(state.canvas&&state.canvas.data_url_sha_source){state.canvas.frame_sha256=sha(state.canvas.data_url_sha_source);delete state.canvas.data_url_sha_source;}
      samples.push({t_ms:t,screenshot:path.join('screenshots','liveness',shotName).replace(/\\/g,'/'),frame_hash:sha(buffer),computed:state.computed||{},rect:state.rect||{},canvas:state.canvas||null});}
    traces.push({trace_id:`${surface.surface_id}@${trigger}`,side,surface_id:surface.surface_id,selector:surface.selector,kind:surface.kind,trigger,viewport:viewport.width,profile_id:profile.id,timing:{sample_ms:sampleMs},samples,errors});await context.close();
  }}
  await browser.close();fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,traces.map(row=>JSON.stringify(row)).join('\n')+'\n');const invalid=side==='original'&&traces.some(row=>row.errors.length);console.log(`traces=${traces.length} invalid_reference=${invalid} out=${out}`);if(invalid)process.exitCode=2;
}
main().catch(error=>{console.error(error.stack||error);process.exit(1);});
