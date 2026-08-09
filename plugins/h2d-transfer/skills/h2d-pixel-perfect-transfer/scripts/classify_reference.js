#!/usr/bin/env node
/* Generate fail-closed behavior/liveness classification across reachable donor states. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {
  launchChromium, contextOptions, installNetworkSandbox,
  installRuntimeInstrumentation, stableSelectorScript, isExpectedSandboxConsole,
} = require('./browser');

function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function load(value, label) { if (!value) throw new Error(`${label} is required`); return JSON.parse(fs.readFileSync(path.resolve(value), 'utf8')); }
function sha(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function toUrl(value) { if (/^file:/.test(value)) return value; if (/^https?:/.test(value)) throw new Error('classification requires a pinned local donor'); return 'file://' + path.resolve(value).replace(/\\/g, '/'); }
function verifyDonorClosure(visual, donorRoot) {
  if (!Array.isArray(visual.donor_closure) || !visual.donor_closure.length) throw new Error('visual manifest has no donor closure');
  const current = visual.donor_closure.map((entry, index) => {
    if (!entry || typeof entry.path !== 'string' || !entry.path || path.isAbsolute(entry.path)) throw new Error(`invalid donor closure path at ${index}`);
    const file = path.resolve(donorRoot, entry.path);
    const relative = path.relative(donorRoot, file);
    if (relative.startsWith('..') || path.isAbsolute(relative) || !fs.statSync(file).isFile()) throw new Error(`donor closure path is missing or escapes root: ${entry.path}`);
    return { path: entry.path.replace(/\\/g, '/'), sha256: sha(fs.readFileSync(file)), size: fs.statSync(file).size };
  }).sort((a, b) => a.path.localeCompare(b.path));
  const identity = `sha256:${sha(Buffer.from(JSON.stringify(current)))}`;
  if (identity !== visual.donor_identity) throw new Error('donor closure changed between visual freeze and classification');
  return { identity, current };
}

async function scan(page, maxElements) {
  return page.evaluate(({ maxElements, selectorSource }) => {
    const stable = (0, eval)(selectorSource);
    const all = [...document.querySelectorAll('*')];
    const visible = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity) > 0.001; };
    const eventProps = ['onclick','onpointerdown','onpointerup','ontouchstart','ontouchend','onkeydown','oninput','onchange','onsubmit'];
    const controls = [];
    const surfaces = [];
    for (const el of all.slice(0, maxElements)) {
      if (!visible(el)) continue;
      const listeners = String(el.getAttribute('data-h2d-listener-events') || '').split(',').filter(Boolean);
      const semantic = el.matches('a[href],button,input,select,textarea,summary,[role],[aria-expanded],[tabindex]:not([tabindex="-1"])');
      const propertyBacked = eventProps.some(name => typeof el[name] === 'function') || eventProps.some(name => el.hasAttribute(name));
      if (semantic || listeners.length || propertyBacked) {
        const selector = stable(el); const count = selector ? document.querySelectorAll(selector).length : 0;
        controls.push({ selector, selector_count: count, tag: el.tagName.toLowerCase(), role: el.getAttribute('role'), listeners });
      }
      const cs = getComputedStyle(el);
      const animated = cs.animationName && cs.animationName !== 'none' && cs.animationDuration !== '0s';
      const transitioned = cs.transitionProperty && cs.transitionDuration && cs.transitionDuration !== '0s';
      if (animated || transitioned || el instanceof HTMLCanvasElement || el instanceof HTMLVideoElement) {
        surfaces.push({ selector: stable(el), kind: animated ? 'css-animation' : transitioned ? 'css-transition' : el instanceof HTMLCanvasElement ? `canvas-${el.getAttribute('data-h2d-canvas-context') || 'unobserved'}` : 'video' });
      }
    }
    const actionable = controls.filter(row => ['button','summary'].includes(row.tag) || ['button','menuitem','tab'].includes(row.role) || document.querySelector(row.selector)?.hasAttribute('aria-expanded') || document.querySelector(row.selector)?.matches('input[type="checkbox"],input[type="radio"]'));
    const fingerprint = JSON.stringify({ controls: controls.map(row => [row.selector,row.tag,row.role]), surfaces, text: document.body.innerText.slice(0, 20000) });
    return { controls, actionable, surfaces, truncated: all.length > maxElements, discovered: all.length, fingerprint };
  }, { maxElements, selectorSource: stableSelectorScript() });
}

async function inspectMatrixRow(browser, donor, profile, viewport, requestRules, projectRoot) {
  const maxStates = Number(arg('max-states', '80'));
  const maxDepth = Number(arg('max-depth', '4'));
  const maxElements = Number(arg('max-elements', '5000'));
  const queue = [[]]; const seenSequences = new Set(['']); const seenStates = new Set(); const states = []; const errors = [];
  while (queue.length && states.length < maxStates) {
    const sequence = queue.shift();
    const context = await browser.newContext(contextOptions(profile, viewport));
    await installNetworkSandbox(context, requestRules); await installRuntimeInstrumentation(context);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error.message || error).slice(0, 500)));
    page.on('console', message => { if (message.type() === 'error' && !isExpectedSandboxConsole(message)) errors.push(message.text().slice(0, 500)); });
    try {
      await page.goto(toUrl(donor), { waitUntil: 'networkidle' });
      for (const selector of sequence) {
        if (await page.locator(selector).count() !== 1) throw new Error(`reachable-state selector is not unique: ${selector}`);
        await page.locator(selector).click(); await page.waitForTimeout(60);
      }
      const state = await scan(page, maxElements);
      const stateHash = sha(Buffer.from(state.fingerprint));
      if (!seenStates.has(stateHash)) {
        seenStates.add(stateHash);
        states.push({ sequence, state_sha256: stateHash, controls: state.controls, surfaces: state.surfaces, truncated: state.truncated, discovered: state.discovered });
        if (sequence.length < maxDepth) {
          for (const control of state.actionable) {
            if (control.selector_count !== 1) { errors.push(`non-unique donor selector: ${control.selector}`); continue; }
            const next = [...sequence, control.selector]; const key = JSON.stringify(next);
            if (!seenSequences.has(key)) { seenSequences.add(key); queue.push(next); }
          }
        }
      }
    } catch (error) { errors.push(String(error.message || error).slice(0, 500)); }
    finally { await context.close(); }
  }
  return { states, errors, exhausted: queue.length > 0, behavior_required: states.some(state => state.controls.length > 0), liveness_required: states.some(state => state.surfaces.length > 0) };
}

async function main() {
  const donor = arg('donor'); const h2d = arg('h2d'); const out = path.resolve(arg('out') || 'reference_classification.json');
  if (!donor || !h2d) throw new Error('--donor and --h2d are required');
  const matrix = load(arg('matrix'), '--matrix'); const profiles = load(arg('profiles'), '--profiles'); const visual = load(arg('visual-manifest'), '--visual-manifest');
  const donorRoot = path.resolve(arg('donor-root') || path.dirname(path.resolve(donor)));
  const donorClosure = verifyDonorClosure(visual, donorRoot);
  const requestRules = arg('request-allowlist') ? load(arg('request-allowlist'), '--request-allowlist') : [];
  const expected = [...matrix.flatMap(viewport => profiles.map(profile => `${viewport.width}x${viewport.height}@${profile.id}`))].sort();
  if (JSON.stringify([...(visual.matrix_keys || [])].sort()) !== JSON.stringify(expected)) throw new Error('visual manifest does not cover classification matrix');
  const rows = [];
  for (const profile of profiles) {
    const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
    try { for (const viewport of matrix) rows.push({ matrix_key: `${viewport.width}x${viewport.height}@${profile.id}`, ...(await inspectMatrixRow(browser, donor, profile, viewport, requestRules)) }); }
    finally { await browser.close(); }
  }
  const issues = rows.flatMap(row => [...row.errors.map(message => ({ matrix_key: row.matrix_key, type: 'runtime-or-action-error', message })), ...(row.exhausted ? [{ matrix_key: row.matrix_key, type: 'state-budget-exhausted' }] : []), ...row.states.filter(state => state.truncated).map(() => ({ matrix_key: row.matrix_key, type: 'element-limit' }))]);
  const result = issues.length ? 'fail' : 'pass';
  const report = { schema_version: '2.0', result, coverage_complete: result === 'pass', generator_sha256: sha(fs.readFileSync(__filename)), source_sha256: sha(fs.readFileSync(path.resolve(h2d))), donor_identity: donorClosure.identity, donor_closure: donorClosure.current, matrix_keys: expected, behavior_required: rows.some(row => row.behavior_required), liveness_required: rows.some(row => row.liveness_required), rows, issues };
  fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(report, null, 2));
  console.log(`result=${result} matrix=${rows.length} behavior=${report.behavior_required} liveness=${report.liveness_required}`);
  if (result !== 'pass') process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
