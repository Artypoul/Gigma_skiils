#!/usr/bin/env node
/* Capture original/candidate screenshots and calculate live visual diff metrics. */
const fs=require('fs'); const path=require('path'); const {spawnSync}=require('child_process');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
function toUrl(p){if(/^https?:\/\//.test(p)||/^file:/.test(p))return p; return 'file://' + path.resolve(p);}
function toBool(v, d=true){
  if(v == null) return d;
  const s=String(v).trim().toLowerCase();
  if(['1','true','yes','y','on'].includes(s)) return true;
  if(['0','false','no','n','off'].includes(s)) return false;
  return d;
}
async function main(){
  const original=arg('original'); const candidate=arg('candidate'); const outDir=arg('out-dir','h2d-transfer-output'); const viewports=String(arg('viewports','390')).split(',').map(Number).filter(v=>!Number.isNaN(v));
  const heightMapRaw=arg('height-map');
  const heightMap=heightMapRaw ? JSON.parse(heightMapRaw) : {};
  const hideOriginalSelector=arg('hide-original-selector');
  const maxMismatchRatio=Number(arg('max-pixel-mismatch-ratio','0.005'));
  const pythonBin=arg('python','python');
  if(!candidate) throw new Error('Usage: --candidate file --original url optional --viewports 390,768 --out-dir dir');
  const {chromium}=require('playwright'); const browser=await chromium.launch({headless:true});
  fs.mkdirSync(path.join(outDir,'screenshots'),{recursive:true}); const rowsByViewport=new Map();
  for(const vp of viewports){
    const row={viewport:vp};
    for(const side of ['candidate','original']){
      const url = side==='candidate' ? candidate : original;
      if(!url) continue;
      const page=await browser.newPage({viewport:{width:vp,height:Number(heightMap[vp] || arg('height','1600'))}, deviceScaleFactor:1, locale:arg('locale','en-US'), timezoneId:arg('timezone','Europe/Berlin')});
      await page.emulateMedia({reducedMotion: arg('reduced-motion','reduce')});
      await page.goto(toUrl(url),{waitUntil:'networkidle'});
      if(side==='original' && hideOriginalSelector){
        await page.addStyleTag({content:`${hideOriginalSelector}{display:none!important}`});
        await page.locator(hideOriginalSelector).evaluateAll(nodes => nodes.forEach(node => node.remove()));
      }
      const finalUrl=page.url(); const file=path.join(outDir,'screenshots',`${side}_${vp}.png`);
      await page.screenshot({path:file, fullPage:toBool(arg('full-page','true'), true)});
      row[side]=path.relative(outDir,file);
      row[`${side}_url`]=url;
      row[`${side}_final_url`]=finalUrl;
      await page.close();
    }
    rowsByViewport.set(vp, row);
  }
  await browser.close();
  const rows=[...rowsByViewport.values()];
  const issues=[]; let result='not-tested';
  if(original){
    result='pass';
    for(const row of rows){
      if(!row.original || !row.candidate){
        row.verdict='fail';
        issues.push(`viewport ${row.viewport}: missing original or candidate screenshot`);
        result='fail';
        continue;
      }
      const diffRel=path.join('screenshots',`diff_${row.viewport}.png`);
      const diffAbs=path.join(outDir,diffRel);
      const metricsScript=path.join(__dirname,'image_diff_metrics.py');
      const metricsOut=spawnSync(
        pythonBin,
        [
          metricsScript,
          path.join(outDir,row.original),
          path.join(outDir,row.candidate),
          '--diff',
          diffAbs,
        ],
        {encoding:'utf8'}
      );
      if(metricsOut.status !== 0){
        row.verdict='manual-review';
        row.diff=diffRel;
        row.diff_error=((metricsOut.stdout || '') + '\n' + (metricsOut.stderr || '')).trim();
        issues.push(`viewport ${row.viewport}: diff metrics failed`);
        result='fail';
        continue;
      }
      const metrics=JSON.parse(metricsOut.stdout);
      row.diff=diffRel;
      row.pixel_mismatch_ratio=metrics.pixel_mismatch_ratio;
      row.different_pixels=metrics.different_pixels;
      row.total_pixels=metrics.total_pixels;
      row.diff_bbox=metrics.diff_bbox;
      row.verdict=metrics.pixel_mismatch_ratio <= maxMismatchRatio ? 'pass' : 'fail';
      if(hideOriginalSelector){
        // Оригинал был изменён перед сравнением: чистый pass недопустим — нужен ручной разбор.
        row.original_normalized=true;
        row.hide_original_selector=hideOriginalSelector;
        if(row.verdict === 'pass'){ row.verdict='pass-with-normalization'; }
      }
      if(row.verdict === 'fail'){
        issues.push(`viewport ${row.viewport}: pixel mismatch ratio ${metrics.pixel_mismatch_ratio} exceeds ${maxMismatchRatio}`);
        result='fail';
      }
    }
  }
  if(hideOriginalSelector){
    issues.push(`original page was normalized before capture via --hide-original-selector='${hideOriginalSelector}'; the live-diff gate requires manual confirmation that the hidden element is an approved deviation`);
    if(result === 'pass'){ result='manual-review'; }
  }
  const report={result, environment:{locale:arg('locale','en-US'),timezone:arg('timezone','Europe/Berlin'),reducedMotion:arg('reduced-motion','reduce'),maxPixelMismatchRatio:maxMismatchRatio,hideOriginalSelector:hideOriginalSelector||null,originalNormalized:Boolean(hideOriginalSelector)}, viewports: rows, issues};
  fs.mkdirSync(path.join(outDir,'reports'),{recursive:true}); fs.writeFileSync(path.join(outDir,'reports','diff_summary.json'),JSON.stringify(report,null,2));
  console.log(`screenshots=${rows.length} report=reports/diff_summary.json`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
