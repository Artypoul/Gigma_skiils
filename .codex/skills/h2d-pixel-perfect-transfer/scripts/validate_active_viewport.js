#!/usr/bin/env node
/* Viewport-scoped DOM rect validator. Includes active branch root itself. */
const fs = require('fs');
const path = require('path');

function arg(name, def=null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i+1] : def;
}
function toFileUrl(p) {
  if (/^https?:\/\//.test(p) || /^file:/.test(p)) return p;
  return 'file://' + path.resolve(p);
}
function delta(a,b){ return Math.abs(Number(a)-Number(b)); }

async function main() {
  const html = arg('html');
  const rectTargetsPath = arg('rect-targets');
  const outPath = arg('out', 'reports/node_validation.json');
  const threshold = Number(arg('threshold', '0.5'));
  const viewports = String(arg('viewports') || arg('viewport') || '').split(',').filter(Boolean).map(v=>Number(v));
  if (!html || !rectTargetsPath || !viewports.length) throw new Error('Usage: --html file --rect-targets file --viewports 390,768 --out file');
  const { chromium } = require('playwright');
  const targets = JSON.parse(fs.readFileSync(rectTargetsPath, 'utf8'));
  const byViewport = new Map(targets.viewports.map(v => [Number(v.viewport), v]));
  const browser = await chromium.launch({ headless: true });
  const results = [];
  let globalMax = 0;
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport, height: Number(arg('height','1200')) }, deviceScaleFactor: 1 });
    await page.goto(toFileUrl(html), { waitUntil: 'networkidle' });
    const domNodes = await page.evaluate((viewport) => {
      const root = document.querySelector(`[data-h2d-viewport="${viewport}"][data-h2d-branch-root="true"]`) || document.querySelector(`[data-h2d-viewport="${viewport}"]`);
      if (!root) return {error: 'active branch root not found', nodes: []};
      const list = [];
      if (root.hasAttribute('data-h2d-path')) list.push(root);
      list.push(...root.querySelectorAll('[data-h2d-path]'));
      const seen = new Set();
      const nodes = [];
      for (const el of list) {
        const h2dPath = el.getAttribute('data-h2d-path');
        if (!h2dPath || seen.has(h2dPath)) continue;
        seen.add(h2dPath);
        const r = el.getBoundingClientRect();
        nodes.push({data_h2d_path: h2dPath, rect: {x:r.x+scrollX, y:r.y+scrollY, width:r.width, height:r.height}, tag: el.tagName});
      }
      return {nodes};
    }, viewport);
    const targetGroup = byViewport.get(viewport) || {targets: []};
    const domMap = new Map((domNodes.nodes || []).map(n => [n.data_h2d_path, n]));
    const targetMap = new Map(targetGroup.targets.map(t => [t.data_h2d_path, t]));
    const missing = [], extra = [], issues = [];
    let checked = 0, maxDelta = 0;
    for (const [p,t] of targetMap) {
      const n = domMap.get(p);
      if (!n) { missing.push(p); continue; }
      checked += 1;
      const fields = ['x','y','width','height'];
      for (const f of fields) {
        const d = delta(n.rect[f], t.rect[f]);
        maxDelta = Math.max(maxDelta, d); globalMax = Math.max(globalMax, d);
        if (d > threshold) issues.push({type:'delta', path:p, field:f, expected:t.rect[f], actual:n.rect[f], delta:d});
      }
    }
    for (const p of domMap.keys()) if (!targetMap.has(p)) extra.push(p);
    if (domNodes.error) issues.push({type:'branch-root', message: domNodes.error});
    const result = missing.length || issues.length ? 'fail' : 'pass';
    results.push({viewport, result, checked, missing, extra, max_delta: maxDelta, issues});
    await page.close();
  }
  await browser.close();
  const overall = {result: results.every(r=>r.result==='pass') ? 'pass' : 'fail', threshold_px: threshold, global_max_delta: globalMax, viewports: results, issues: results.flatMap(r=>r.issues.map(i=>({...i, viewport:r.viewport})))};
  fs.mkdirSync(path.dirname(outPath), {recursive:true});
  fs.writeFileSync(outPath, JSON.stringify(overall, null, 2));
  console.log(`result=${overall.result} global_max_delta=${globalMax} out=${outPath}`);
  process.exit(overall.result === 'pass' ? 0 : 2);
}
main().catch(err => { console.error(err.stack || err); process.exit(1); });
