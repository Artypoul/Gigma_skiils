#!/usr/bin/env node
/* Asset paint audit: map -> DOM/load -> visibility chain -> crop pixel proof. */
const fs = require('fs');
const path = require('path');

function arg(name, def=null){ const i=process.argv.indexOf(`--${name}`); return i>=0 ? process.argv[i+1] : def; }
function toFileUrl(p){ if(/^https?:\/\//.test(p)||/^file:/.test(p)) return p; return 'file://' + path.resolve(p); }
function ensureDir(p){ fs.mkdirSync(p,{recursive:true}); }

function pixelStatsPng(buffer){
  try {
    const { PNG } = require('pngjs');
    const png = PNG.sync.read(buffer);
    let nonTransparent=0, minX=Infinity, minY=Infinity, maxX=-1, maxY=-1;
    for(let y=0;y<png.height;y++){
      for(let x=0;x<png.width;x++){
        const idx=(png.width*y+x)*4; const a=png.data[idx+3];
        if(a>5){ nonTransparent++; if(x<minX)minX=x; if(y<minY)minY=y; if(x>maxX)maxX=x; if(y>maxY)maxY=y; }
      }
    }
    return {width:png.width,height:png.height,non_transparent_pixels:nonTransparent,total_pixels:png.width*png.height,non_transparent_ratio: png.width*png.height ? nonTransparent/(png.width*png.height) : 0, content_bbox: nonTransparent ? [minX,minY,maxX+1,maxY+1] : null, pixel_result: nonTransparent ? 'pass' : 'fail'};
  } catch(err) {
    return {pixel_result:'manual-review', pixel_error:String(err).slice(0,300)};
  }
}

async function main(){
  const html=arg('html'); const assetMapPath=arg('asset-map'); const outDir=arg('out-dir','h2d-transfer-output');
  if(!html || !assetMapPath) throw new Error('Usage: --html file --asset-map reports/asset_map.json --out-dir h2d-transfer-output');
  const { chromium } = require('playwright');
  const rawMap = JSON.parse(fs.readFileSync(assetMapPath,'utf8'));
  const assets = Array.isArray(rawMap) ? rawMap : (rawMap.assets || []);
  const reportDir = path.join(outDir,'reports'); const cropDir = path.join(outDir,'screenshots','painted_asset_crops');
  ensureDir(reportDir); ensureDir(cropDir);
  const browser = await chromium.launch({headless:true});
  const broken = []; const allRequests=[];
  const paintRows=[]; const visRows=[];
  const viewports = [...new Set(assets.flatMap(a => a.viewports || [Number(arg('viewport','390'))]))];
  for(const viewport of viewports){
    const page = await browser.newPage({viewport:{width:Number(viewport), height:Number(arg('height','1600'))}, deviceScaleFactor:1});
    page.on('requestfailed', req => { const rec={url:req.url(), failure:req.failure()?.errorText || 'requestfailed'}; broken.push(rec); allRequests.push({...rec,status:'failed'}); });
    page.on('response', res => { const u=res.url(); if(/\.(png|jpe?g|webp|gif|svg|woff2?|css)(\?|$)/i.test(u)){ const rec={url:u,status:res.status()}; allRequests.push(rec); if(res.status()>=400) broken.push(rec); } });
    await page.goto(toFileUrl(html), {waitUntil:'networkidle'});
    for(const asset of assets.filter(a => (a.viewports||[]).includes(Number(viewport)))){
      const selectors = asset.target?.selectors || (asset.target?.h2d_paths || []).map(p => `[data-h2d-path="${p}"]`);
      const selector = selectors[0];
      const rowBase = {asset_id:asset.asset_id, viewport:Number(viewport), selector: selector || '', criticality: asset.criticality || 'unknown'};
      if(!selector){ paintRows.push({...rowBase, dom_result:'fail', pixel_result:'not-tested', visibility_result:'fail', result:'fail', reason:'no selector'}); continue; }
      const el = await page.$(selector);
      if(!el){ paintRows.push({...rowBase, dom_result:'fail', pixel_result:'not-tested', visibility_result:'fail', result: asset.criticality==='critical'?'fail':'partial', reason:'element not found'}); continue; }
      const data = await el.evaluate((node) => {
        const chain=[]; let cur=node;
        while(cur && cur.nodeType===1){
          const cs=getComputedStyle(cur); const r=cur.getBoundingClientRect();
          chain.push({tag:cur.tagName, id:cur.id||null, className:String(cur.className||'').slice(0,120), display:cs.display, visibility:cs.visibility, opacity:Number(cs.opacity), overflow:cs.overflow, zIndex:cs.zIndex, rect:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}});
          cur=cur.parentElement;
        }
        const r=node.getBoundingClientRect();
        const cs=getComputedStyle(node);
        let loaded=true;
        if(node.tagName==='IMG') loaded = Boolean(node.complete && node.naturalWidth > 0);
        const visible = r.width>0 && r.height>0 && chain.every(c => c.display !== 'none' && c.visibility !== 'hidden' && c.opacity > 0.001);
        return {bbox:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}, display:cs.display, visibility:cs.visibility, opacity:Number(cs.opacity), loaded, visible, chain};
      });
      const visResult = data.visible ? 'pass' : 'fail';
      visRows.push({...rowBase, bbox:data.bbox, chain:data.chain, result:visResult});
      let cropFile=null, pixel = {pixel_result:'not-tested'};
      if(data.bbox && data.bbox.width>0 && data.bbox.height>0){
        const safeId = String(asset.asset_id).replace(/[^a-z0-9_.-]/gi,'_');
        cropFile = path.join('screenshots','painted_asset_crops',`${viewport}_${safeId}.png`);
        const clip={x:Math.max(0,data.bbox.x), y:Math.max(0,data.bbox.y), width:Math.max(1,Math.min(data.bbox.width, Number(arg('max-crop-width','1400')))), height:Math.max(1,Math.min(data.bbox.height, Number(arg('max-crop-height','1400'))))};
        const buffer = await page.screenshot({clip});
        fs.writeFileSync(path.join(outDir,cropFile), buffer);
        pixel = pixelStatsPng(buffer);
      }
      const domResult = data.loaded && data.bbox && data.bbox.width>0 && data.bbox.height>0 ? 'pass' : 'fail';
      const critical = asset.criticality === 'critical';
      const result = (domResult==='pass' && visResult==='pass' && pixel.pixel_result==='pass') ? 'pass' : (critical ? 'fail' : 'partial');
      paintRows.push({...rowBase, bbox:data.bbox, crop_file:cropFile, dom_result:domResult, visibility_result:visResult, loaded:data.loaded, ...pixel, result});
    }
    await page.close();
  }
  await browser.close();
  const brokenReport={result: broken.length ? 'fail':'pass', broken, all: allRequests};
  const visReport={result: visRows.every(r=>r.result==='pass') ? 'pass' : 'fail', items: visRows};
  const issues = paintRows.filter(r=>r.result!=='pass').map(r=>({asset_id:r.asset_id, viewport:r.viewport, result:r.result, reason:r.reason || 'paint proof failed'}));
  const paintReport={result: issues.some(i=>i.result==='fail') ? 'fail' : (issues.length?'partial':'pass'), assets: paintRows, issues};
  fs.writeFileSync(path.join(reportDir,'broken_asset_requests.json'), JSON.stringify(brokenReport,null,2));
  fs.writeFileSync(path.join(reportDir,'asset_visibility_chain.json'), JSON.stringify(visReport,null,2));
  fs.writeFileSync(path.join(reportDir,'asset_paint_validation.json'), JSON.stringify(paintReport,null,2));
  console.log(`asset_paint=${paintReport.result} assets=${paintRows.length} broken=${broken.length}`);
  process.exit(paintReport.result==='pass' && brokenReport.result==='pass' ? 0 : 2);
}
main().catch(e=>{ console.error(e.stack || e); process.exit(1); });
