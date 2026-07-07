#!/usr/bin/env node
/* Detect dynamic runtime surfaces: CSS motion, requestAnimationFrame evidence, canvas/WebGL, video and common animation libs. */
const fs=require('fs'); const path=require('path');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
function toUrl(p){if(/^https?:\/\//.test(p)||/^file:/.test(p))return p; return 'file://' + path.resolve(p);}
async function main(){
  const url=arg('url'); const out=arg('out','reports/liveness_inventory.json'); const viewport=Number(arg('viewport','390'));
  if(!url) throw new Error('Usage: --url original --out reports/liveness_inventory.json');
  const {chromium}=require('playwright');
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:viewport,height:Number(arg('height','1400'))}, deviceScaleFactor:Number(arg('dpr','1'))});
  await page.addInitScript(()=>{
    window.__h2d_liveness={raf_count:0, raf_callbacks:0};
    const origRAF=window.requestAnimationFrame;
    window.requestAnimationFrame=function(cb){ window.__h2d_liveness.raf_callbacks++; return origRAF.call(window,function(ts){ window.__h2d_liveness.raf_count++; return cb(ts); }); };
  });
  await page.goto(toUrl(url),{waitUntil:'networkidle'});
  await page.waitForTimeout(Number(arg('settle-ms','600')));
  const data=await page.evaluate((viewport)=>{
    const surfaces=[];
    function vis(el){const r=el.getBoundingClientRect(); const cs=getComputedStyle(el); return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden'&&Number(cs.opacity)>0.001;}
    function selector(el,i){return el.id ? `#${CSS.escape(el.id)}` : (el.getAttribute('data-h2d-path') ? `[data-h2d-path="${el.getAttribute('data-h2d-path')}"]` : `${el.tagName.toLowerCase()}:nth-of-type(${i+1})`);}
    [...document.querySelectorAll('*')].slice(0,1500).forEach((el,i)=>{
      if(!vis(el)) return;
      const cs=getComputedStyle(el);
      const anim=cs.animationName && cs.animationName !== 'none';
      const trans=cs.transitionProperty && cs.transitionProperty !== 'all 0s ease 0s' && cs.transitionDuration !== '0s';
      if(anim || trans){
        surfaces.push({surface_id:`${viewport}:${anim?'css-animation':'css-transition'}:${i}`, kind:anim?'css-animation':'css-transition', selector:selector(el,i), criticality:'normal', triggers:['load','state-change'], evidence_required:['computed_styles','start_mid_end_screenshots'], timing:{animationName:cs.animationName, animationDuration:cs.animationDuration, transitionProperty:cs.transitionProperty, transitionDuration:cs.transitionDuration}});
      }
    });
    [...document.querySelectorAll('canvas')].forEach((el,i)=>{
      if(!vis(el)) return;
      let kind='canvas-2d'; let attrs={};
      try { const gl=el.getContext('webgl2') || el.getContext('webgl'); if(gl){kind=gl instanceof WebGL2RenderingContext?'webgl2':'webgl'; attrs=gl.getContextAttributes()||{};} }
      catch(e){}
      surfaces.push({surface_id:`${viewport}:${kind}:${i}`, kind, selector:selector(el,i), criticality:'critical', triggers:['load','resize'], evidence_required:['context','frame_hashes','non_blank_pixels'], context_attributes:attrs});
    });
    [...document.querySelectorAll('video')].forEach((el,i)=>{ if(vis(el)) surfaces.push({surface_id:`${viewport}:video:${i}`, kind:'video', selector:selector(el,i), criticality:'normal', triggers:['load','playback'], evidence_required:['poster','playback_state','frame_samples'], autoplay:el.autoplay, muted:el.muted, loop:el.loop, controls:el.controls}); });
    const libs=[]; const text=[...document.scripts].map(s=>s.src||'').join(' ').toLowerCase();
    for(const lib of ['three','pixi','gsap','lottie','rive','spline','swiper','framer-motion','anime']) if(text.includes(lib)) libs.push(lib);
    const raf=window.__h2d_liveness||{};
    if((raf.raf_count||0)>0){surfaces.push({surface_id:`${viewport}:requestAnimationFrame:document`, kind:'requestAnimationFrame', selector:'document', criticality:'normal', triggers:['load'], evidence_required:['raf_count','frame_samples'], raf_count:raf.raf_count, raf_callbacks:raf.raf_callbacks});}
    return {surfaces, libs, raf};
  }, viewport);
  await browser.close();
  const report={result:data.surfaces.length?'pass':'not-tested', liveness_required:data.surfaces.some(s=>s.criticality==='critical'||['webgl','webgl2','canvas-2d','video','requestAnimationFrame'].includes(s.kind)), url, viewports:[viewport], detected_libraries:data.libs, raf:data.raf, surfaces:data.surfaces};
  fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(report,null,2));
  const webgl={result:data.surfaces.some(s=>['webgl','webgl2'].includes(s.kind))?'pass':'not-present', contexts:data.surfaces.filter(s=>['webgl','webgl2','canvas-2d'].includes(s.kind)).map(s=>({canvas_selector:s.selector, context_type:s.kind==='canvas-2d'?'2d':s.kind, context_attributes:s.context_attributes||{}, frame_hashes:[], pixels_change_over_time:false, non_blank_samples:0})), issues:[]};
  fs.writeFileSync(path.join(path.dirname(out),'webgl_capture_report.json'), JSON.stringify(webgl,null,2));
  console.log(`surfaces=${report.surfaces.length} liveness_required=${report.liveness_required} out=${out}`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
