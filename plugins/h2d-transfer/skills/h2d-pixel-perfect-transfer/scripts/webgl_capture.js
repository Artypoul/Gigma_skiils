#!/usr/bin/env node
/* Capture generated WebGL frame evidence without accepting hand-authored placeholders. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { launchChromium, contextOptions, installNetworkSandbox, installRuntimeInstrumentation, isExpectedSandboxConsole } = require('./browser');

function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function loadJson(value, fallback) { return value ? JSON.parse(fs.readFileSync(value, 'utf8')) : fallback; }
function toUrl(value) { if (/^https?:\/\//.test(value) || /^file:/.test(value)) return value; return 'file://' + path.resolve(value).replace(/\\/g, '/'); }
function sha(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function sampleTimeline(value) {
  const rows = String(value).split(',').map(item => Number(item.trim()));
  if (rows.length < 3 || rows.some(item => !Number.isFinite(item) || item < 0) || rows[0] !== 0 || rows.some((item, index) => index > 0 && item <= rows[index - 1])) throw new Error('--sample-ms requires at least three finite, strictly increasing offsets starting at 0');
  return rows;
}
async function replayPrerequisites(page, sequence) {
  for (const step of sequence || []) {
    const locator = page.locator(step.selector);
    if (await locator.count() !== 1) throw new Error(`WebGL prerequisite selector is not unique: ${step.selector}`);
    if (step.action === 'click') await locator.click();
    else if (step.action === 'hover') await locator.hover();
    else if (step.action === 'focus') await locator.focus();
    else throw new Error(`unsupported WebGL prerequisite action: ${step.action}`);
  }
}

async function main() {
  const url = arg('url'); const inventoryPath = arg('inventory'); const out = path.resolve(arg('out') || 'reports/webgl_capture_report.json');
  if (!url || !inventoryPath) throw new Error('Usage: --url page --inventory liveness_inventory.json --out webgl_capture_report.json');
  const inventory = loadJson(inventoryPath, null);
  if (!inventory || inventory.result !== 'pass' || inventory.coverage_complete !== true) throw new Error('WebGL capture requires a passing complete liveness inventory');
  const surfaces = (inventory.surfaces || []).filter(row => ['webgl', 'webgl2'].includes(String(row.kind).toLowerCase()));
  const profile = loadJson(arg('profile'), { id:'default', headless:true, device_scale_factor:1, is_mobile:false, has_touch:false, locale:'en-US', timezone:'UTC', reduced_motion:'reduce' });
  const viewport = { width:Number(arg('viewport','390')), height:Number(arg('height','1400')) }; const samples = sampleTimeline(arg('sample-ms','0,250,500'));
  const contexts = []; const issues = [];
  for (const surface of surfaces) {
    const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
    const context = await browser.newContext(contextOptions(profile, viewport)); await installNetworkSandbox(context, loadJson(arg('request-allowlist'), [])); await installRuntimeInstrumentation(context);
    const page = await context.newPage(); const runtimeErrors = [];
    page.on('pageerror', error => runtimeErrors.push(String(error.message || error).slice(0,500)));
    page.on('console', message => { if (message.type() === 'error' && !isExpectedSandboxConsole(message)) runtimeErrors.push(message.text().slice(0,500)); });
    try {
      await page.goto(toUrl(url), { waitUntil:'networkidle' }); await replayPrerequisites(page, surface.prerequisite_sequence);
      const frameHashes = []; let nonBlank = 0; let metadata = null; let previous = 0;
      for (const offset of samples) {
        const wait = offset - previous; if (wait) await page.waitForTimeout(wait); previous = offset;
        const sample = await page.evaluate(async ({ selector, contextType }) => {
          const canvas = document.querySelector(selector);
          if (!(canvas instanceof HTMLCanvasElement)) throw new Error(`WebGL selector is not a canvas: ${selector}`);
          const observed = canvas.getAttribute('data-h2d-canvas-context');
          if (observed !== contextType) throw new Error(`expected ${contextType}, observed ${observed || 'none'}`);
          const gl = canvas.getContext(contextType);
          if (!gl) throw new Error(`${contextType} context is unavailable`);
          gl.finish(); const pixels = new Uint8Array(canvas.width * canvas.height * 4);
          gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
          const digest = await crypto.subtle.digest('SHA-256', pixels); const frameHash = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2,'0')).join('');
          let nonBlank = false; for (let index = 0; index < pixels.length; index += 4) if (pixels[index] || pixels[index+1] || pixels[index+2] || pixels[index+3]) { nonBlank = true; break; }
          const extension = gl.getExtension('WEBGL_debug_renderer_info'); const rect = canvas.getBoundingClientRect();
          return { frame_hash:frameHash, non_blank:nonBlank, rect:{x:rect.x+scrollX,y:rect.y+scrollY,width:rect.width,height:rect.height}, context_attributes:gl.getContextAttributes(), vendor:extension?gl.getParameter(extension.UNMASKED_VENDOR_WEBGL):gl.getParameter(gl.VENDOR), renderer:extension?gl.getParameter(extension.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER) };
        }, { selector:surface.selector, contextType:String(surface.kind).toLowerCase() });
        frameHashes.push(sample.frame_hash); if (sample.non_blank) nonBlank++; metadata = sample;
      }
      contexts.push({ canvas_selector:surface.selector, context_type:String(surface.kind).toLowerCase(), rect:metadata.rect, context_attributes:metadata.context_attributes, vendor:String(metadata.vendor || 'masked-or-unavailable'), renderer:String(metadata.renderer || 'masked-or-unavailable'), frame_hashes:frameHashes, pixels_change_over_time:new Set(frameHashes).size > 1, non_blank_samples:nonBlank });
      for (const message of runtimeErrors) issues.push({ type:'runtime-error', canvas_selector:surface.selector, message });
      if (frameHashes.length < 3 || nonBlank < 1) issues.push({ type:'invalid-webgl-samples', canvas_selector:surface.selector, frame_hashes:frameHashes.length, non_blank_samples:nonBlank });
    } catch (error) { issues.push({ type:'capture-error', canvas_selector:surface.selector, message:String(error.message || error).slice(0,500) }); }
    finally { await context.close(); await browser.close(); }
  }
  const result = !surfaces.length ? 'not-present' : (issues.length ? 'fail' : 'pass');
  const report = { schema_version:'2.0', result, coverage_complete:result === 'pass' || result === 'not-present', generator_sha256:sha(fs.readFileSync(__filename)), contexts, issues };
  fs.mkdirSync(path.dirname(out), { recursive:true }); fs.writeFileSync(out, JSON.stringify(report,null,2));
  console.log(`result=${result} contexts=${contexts.length} out=${out}`); if (result === 'fail') process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
