#!/usr/bin/env node
/* Detect motion without creating canvas contexts or silently truncating the DOM. */
const fs = require('fs'); const path = require('path');
const { launchChromium, contextOptions, installNetworkSandbox, installRuntimeInstrumentation } = require('./browser');
function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function toUrl(value) { if (/^https?:\/\//.test(value) || /^file:/.test(value)) return value; return 'file://' + path.resolve(value).replace(/\\/g, '/'); }
function loadJson(value, fallback) { return value ? JSON.parse(fs.readFileSync(value, 'utf8')) : fallback; }
async function main() {
  const url = arg('url'), out = arg('out', 'reports/liveness_inventory.json'); if (!url) throw new Error('Usage: --url original --out report.json');
  const viewport = { width:Number(arg('viewport','390')), height:Number(arg('height','1400')) };
  const profile = loadJson(arg('profile'), { id:'default', headless:true, device_scale_factor:Number(arg('dpr','1')), is_mobile:false, has_touch:false, locale:'en-US', timezone:'UTC', reduced_motion:'reduce' });
  const maxElements = Number(arg('max-elements','5000'));
  const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
  const context = await browser.newContext(contextOptions(profile, viewport)); await installNetworkSandbox(context, loadJson(arg('request-allowlist'), [])); await installRuntimeInstrumentation(context);
  const page = await context.newPage(); await page.addInitScript(() => { window.__h2dRaf = { requested:0, fired:0 }; const native = requestAnimationFrame; window.requestAnimationFrame = function(cb){ window.__h2dRaf.requested++; return native.call(window, ts => { window.__h2dRaf.fired++; return cb(ts); }); }; });
  await page.goto(toUrl(url), { waitUntil:'networkidle' }); await page.waitForTimeout(Number(arg('settle-ms','600')));
  const data = await page.evaluate(({ maxElements, viewportWidth }) => {
    function visible(el) { const r=el.getBoundingClientRect(); const cs=getComputedStyle(el); return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden'&&Number(cs.opacity)>0.001; }
    function stable(el) { if(el.id) return '#'+CSS.escape(el.id); for(const name of ['data-h2d-path','data-behavior-id']){const value=el.getAttribute(name);if(value)return `[${name}=${JSON.stringify(value)}]`;} const parts=[];let node=el;while(node&&node.nodeType===1&&node!==document.documentElement){let part=node.tagName.toLowerCase();const siblings=node.parentElement?[...node.parentElement.children].filter(item=>item.tagName===node.tagName):[];if(siblings.length>1)part+=`:nth-of-type(${siblings.indexOf(node)+1})`;parts.unshift(part);node=node.parentElement;}return 'html > '+parts.join(' > '); }
    function triggers(el, cs) { const result=['load']; if(cs.transitionDuration && cs.transitionDuration!=='0s'){result.push('hover','focus'); if(el.matches('input[type="checkbox"],input[type="radio"]'))result.push('checked');} return [...new Set(result)]; }
    const all=[...document.querySelectorAll('*')]; const truncated=all.length>maxElements; const surfaces=[];
    for(const [index,el] of all.slice(0,maxElements).entries()){
      if(!visible(el))continue;const cs=getComputedStyle(el);const animated=cs.animationName&&cs.animationName!=='none'&&cs.animationDuration!=='0s';const transitioned=cs.transitionProperty&&cs.transitionDuration&&cs.transitionDuration!=='0s';
      if(animated||transitioned)surfaces.push({surface_id:`${viewportWidth}:${animated?'css-animation':'css-transition'}:${index}`,kind:animated?'css-animation':'css-transition',selector:stable(el),criticality:'critical',triggers:triggers(el,cs),timing:{animationName:cs.animationName,animationDuration:cs.animationDuration,animationDelay:cs.animationDelay,transitionProperty:cs.transitionProperty,transitionDuration:cs.transitionDuration,transitionDelay:cs.transitionDelay}});
      if(el instanceof HTMLCanvasElement){const actual=el.getAttribute('data-h2d-canvas-context');surfaces.push({surface_id:`${viewportWidth}:canvas:${index}`,kind:actual?`canvas-${actual}`:'canvas-unobserved',selector:stable(el),criticality:'critical',triggers:['load','resize'],context_observed:actual||null});}
      if(el instanceof HTMLVideoElement)surfaces.push({surface_id:`${viewportWidth}:video:${index}`,kind:'video',selector:stable(el),criticality:'critical',triggers:['load','playback'],autoplay:el.autoplay,muted:el.muted,loop:el.loop});
    }
    if((window.__h2dRaf||{}).fired>0)surfaces.push({surface_id:`${viewportWidth}:requestAnimationFrame:document`,kind:'requestAnimationFrame',selector:'html',criticality:'critical',triggers:['load'],raf:window.__h2dRaf});
    return { surfaces, truncated, discovered:all.length, raf:window.__h2dRaf||{} };
  }, { maxElements, viewportWidth:viewport.width });
  await browser.close();
  const unobserved = data.surfaces.filter(row => row.kind === 'canvas-unobserved');
  const result = data.truncated || unobserved.length ? 'fail' : (data.surfaces.length ? 'pass' : 'not-tested');
  const report = { result, coverage_complete: result !== 'fail', truncated:data.truncated, discovered_elements:data.discovered, liveness_required:data.surfaces.length>0, url, viewports:[viewport.width], profile_id:profile.id, raf:data.raf, surfaces:data.surfaces, issues:unobserved.map(row=>({type:'canvas-context-unobserved',surface_id:row.surface_id})) };
  fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2));
  fs.writeFileSync(path.join(path.dirname(out),'webgl_capture_report.json'),JSON.stringify({result:unobserved.length?'fail':(data.surfaces.some(row=>row.kind.includes('webgl'))?'pass':'not-present'),contexts:data.surfaces.filter(row=>row.kind.startsWith('canvas-')).map(row=>({canvas_selector:row.selector,context_type:row.kind.replace('canvas-',''),frame_hashes:[],pixels_change_over_time:false,non_blank_samples:0})),issues:report.issues},null,2));
  console.log(`result=${result} surfaces=${data.surfaces.length} truncated=${data.truncated} out=${out}`);if(result==='fail')process.exitCode=2;
}
main().catch(error=>{console.error(error.stack||error);process.exit(1);});
