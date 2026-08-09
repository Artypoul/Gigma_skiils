#!/usr/bin/env node
/* Generate fail-closed behavior/liveness classification across reachable donor states. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { fileURLToPath } = require('url');
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

function extendDonorClosure(baseClosure, resourceUrls, donorRoot) {
  const files = new Map(baseClosure.map(entry => [entry.path, entry]));
  for (const value of resourceUrls) {
    let parsed; try { parsed = new URL(value); } catch { continue; }
    if (parsed.protocol !== 'file:') continue;
    const file = path.resolve(fileURLToPath(parsed));
    const relative = path.relative(donorRoot, file);
    if (relative.startsWith('..') || path.isAbsolute(relative) || !fs.statSync(file).isFile()) throw new Error(`interaction resource escapes donor root or is missing: ${value}`);
    const key = relative.replace(/\\/g, '/');
    files.set(key, { path: key, sha256: sha(fs.readFileSync(file)), size: fs.statSync(file).size });
  }
  const current = [...files.values()].sort((a, b) => a.path.localeCompare(b.path));
  return { identity: `sha256:${sha(Buffer.from(JSON.stringify(current)))}`, current };
}

async function scan(page, maxElements) {
  return page.evaluate(({ maxElements, selectorSource }) => {
    const stable = (0, eval)(selectorSource);
    const all = [...document.querySelectorAll('*')];
    const visible = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity) > 0.001; };
    const eventProps = ['onclick','onpointerdown','onpointerup','ontouchstart','ontouchend','onkeydown','oninput','onchange','onsubmit'];
    const actionableRoles = new Set(['button','link','menuitem','menuitemcheckbox','menuitemradio','tab','checkbox','radio','switch','option','combobox','textbox','searchbox','slider','spinbutton','treeitem','gridcell']);
    const controls = [];
    const surfaces = [];
    for (const el of all.slice(0, maxElements)) {
      if (!visible(el)) continue;
      const registered = String(el.getAttribute('data-h2d-listener-events') || '').split(',').filter(Boolean);
      const properties = eventProps.filter(name => typeof el[name] === 'function' || el.hasAttribute(name));
      const listeners = [...new Set([...registered, ...properties.map(name => name.slice(2))])].sort();
      const role = el.getAttribute('role');
      const semantic = el.matches('a[href],button,input,select,textarea,summary,[aria-expanded],[tabindex]:not([tabindex="-1"])') || actionableRoles.has(role);
      const propertyBacked = properties.length > 0;
      if (semantic || listeners.length || propertyBacked) {
        const selector = stable(el); const count = selector ? document.querySelectorAll(selector).length : 0;
        const tag = el.tagName.toLowerCase();
        let kind = 'listener-surface';
        if (tag === 'a' || role === 'link') kind = 'link'; else if (tag === 'input' || tag === 'textarea' || ['textbox','searchbox'].includes(role)) kind = 'input'; else if (tag === 'select' || role === 'combobox') kind = 'select'; else if (tag === 'form') kind = 'form'; else if (el.hasAttribute('aria-expanded')) kind = 'disclosure'; else if (tag === 'button' || role === 'button') kind = 'button';
        const label = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('href') || el.getAttribute('name') || el.id || tag).trim().replace(/\s+/g, ' ').slice(0, 120);
        controls.push({ selector, selector_count: count, tag, role, kind, label, frame_path: 'main', listeners, h2d_path: el.getAttribute('data-h2d-path') || null });
      }
      const cs = getComputedStyle(el);
      const animated = cs.animationName && cs.animationName !== 'none' && cs.animationDuration !== '0s';
      const transitioned = cs.transitionProperty && cs.transitionDuration && cs.transitionDuration !== '0s';
      if (animated || transitioned || el instanceof HTMLCanvasElement || el instanceof HTMLVideoElement) {
        surfaces.push({ selector: stable(el), kind: animated ? 'css-animation' : transitioned ? 'css-transition' : el instanceof HTMLCanvasElement ? `canvas-${el.getAttribute('data-h2d-canvas-context') || 'unobserved'}` : 'video' });
      }
    }
    const runtime = window.__h2dRuntime || {};
    const globalPropertyBoundaries = [];
    for (const [target, value] of [['window', window], ['document', document]]) for (const name of eventProps) if (typeof value[name] === 'function') globalPropertyBoundaries.push({ key: `${target}:${name.slice(2)}:property`, target, type: name.slice(2), property: true });
    if ((runtime.timers || []).length) surfaces.push({ selector: 'body', kind: 'unknown-runtime', timer_registrations: runtime.timers.slice(0, 200) });
    const breakpoints = new Set(); const breakpointIssues = [];
    const collectQuery = query => {
      const value = String(query || ''); let matched = false;
      const add = (amount, unit) => { const factor = String(unit).toLowerCase() === 'px' ? 1 : 16; breakpoints.add(Math.round(Number(amount) * factor)); matched = true; };
      for (const match of value.matchAll(/(?:min|max)-(?:width|inline-size)\s*:\s*(\d+(?:\.\d+)?)\s*(px|r?em)\b/gi)) add(match[1], match[2]);
      for (const match of value.matchAll(/(?:width|inline-size)\s*(?:>=|>|<=|<)\s*(\d+(?:\.\d+)?)\s*(px|r?em)\b/gi)) add(match[1], match[2]);
      for (const match of value.matchAll(/(\d+(?:\.\d+)?)\s*(px|r?em)\s*(?:>=|>|<=|<)\s*(?:width|inline-size)\b/gi)) add(match[1], match[2]);
      if (/(?:width|inline-size)/i.test(value) && !matched) breakpointIssues.push(value.slice(0, 300));
    };
    const walkRules = rules => { for (const rule of [...(rules || [])]) { collectQuery(rule.conditionText); try { if (rule.cssRules) walkRules(rule.cssRules); } catch {} } };
    for (const sheet of [...document.styleSheets]) { try { walkRules(sheet.cssRules); } catch {} }
    for (const query of runtime.media_queries || []) collectQuery(query);
    const actionable = controls.filter(row => ['button','summary'].includes(row.tag) || actionableRoles.has(row.role) || document.querySelector(row.selector)?.hasAttribute('aria-expanded') || document.querySelector(row.selector)?.matches('input[type="checkbox"],input[type="radio"]'));
    const fingerprint = JSON.stringify({ controls: controls.map(row => [row.selector,row.tag,row.role]), surfaces, text: document.body.innerText.slice(0, 20000), dom: [...document.querySelectorAll('*')].slice(0, maxElements).map(el => [stable(el), el.className, el.getAttribute('style'), el.getAttribute('aria-expanded'), el.getAttribute('aria-checked')]) });
    const delegatedBoundaries = [...(runtime.global_listeners || []), ...globalPropertyBoundaries].filter((row,index,all) => all.findIndex(item => item.key === row.key) === index);
    return { controls, actionable, surfaces, breakpoints: [...breakpoints].sort((a,b)=>a-b), breakpoint_issues: [...new Set(breakpointIssues)], delegated_boundaries: delegatedBoundaries, truncated: all.length > maxElements, discovered: all.length, fingerprint };
  }, { maxElements, selectorSource: stableSelectorScript() });
}

async function inspectMatrixRow(browser, donor, profile, viewport, requestRules, projectRoot) {
  const maxStates = Number(arg('max-states', '80'));
  const maxDepth = Number(arg('max-depth', '4'));
  const maxElements = Number(arg('max-elements', '5000'));
  const queue = [[]]; const seenSequences = new Set(['']); const seenStates = new Set(); const states = []; const errors = []; const resourceUrls = new Set();
  while (queue.length && states.length < maxStates) {
    const sequence = queue.shift();
    const context = await browser.newContext(contextOptions(profile, viewport));
    const network = await installNetworkSandbox(context, requestRules); await installRuntimeInstrumentation(context);
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
        states.push({ sequence, state_sha256: stateHash, controls: state.controls, surfaces: state.surfaces, breakpoints: state.breakpoints, breakpoint_issues: state.breakpoint_issues, delegated_boundaries: state.delegated_boundaries, truncated: state.truncated, discovered: state.discovered });
        if (sequence.length < maxDepth) {
          for (const control of state.actionable) {
            if (control.selector_count !== 1) { errors.push(`non-unique donor selector: ${control.selector}`); continue; }
            const next = [...sequence, control.selector]; const key = JSON.stringify(next);
            if (!seenSequences.has(key)) { seenSequences.add(key); queue.push(next); }
          }
        }
      }
      for (const boundary of state.delegated_boundaries || []) errors.push(`unresolved delegated listener: ${boundary.target}:${boundary.type}`);
      for (const query of state.breakpoint_issues || []) errors.push(`unsupported responsive breakpoint query: ${query}`);
    } catch (error) { errors.push(String(error.message || error).slice(0, 500)); }
    finally { await context.close(); }
    for (const event of network.filter(row => row.action === 'allowed')) if (String(event.safe_url || '').startsWith('file:')) resourceUrls.add(event.safe_url);
  }
  return { states, errors, resource_urls: [...resourceUrls], exhausted: queue.length > 0, behavior_required: states.some(state => state.controls.length > 0) || states.some(state => state.delegated_boundaries.length > 0), liveness_required: states.some(state => state.surfaces.length > 0) };
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
  const finalClosure = extendDonorClosure(donorClosure.current, rows.flatMap(row => row.resource_urls || []), donorRoot);
  const breakpoints = [...new Set(rows.flatMap(row => row.states || []).flatMap(state => state.breakpoints || []))].sort((a,b)=>a-b);
  const publicRows = rows.map(({ resource_urls, ...row }) => row);
  const issues = rows.flatMap(row => [...row.errors.map(message => ({ matrix_key: row.matrix_key, type: 'runtime-or-action-error', message })), ...(row.exhausted ? [{ matrix_key: row.matrix_key, type: 'state-budget-exhausted' }] : []), ...row.states.filter(state => state.truncated).map(() => ({ matrix_key: row.matrix_key, type: 'element-limit' }))]);
  const result = issues.length ? 'fail' : 'pass';
  const report = { schema_version: '2.0', result, coverage_complete: result === 'pass', generator_sha256: sha(fs.readFileSync(__filename)), source_sha256: sha(fs.readFileSync(path.resolve(h2d))), donor_identity: finalClosure.identity, donor_closure: finalClosure.current, breakpoints, matrix_keys: expected, behavior_required: rows.some(row => row.behavior_required), liveness_required: rows.some(row => row.liveness_required), rows: publicRows, issues };
  fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(report, null, 2));
  console.log(`result=${result} matrix=${rows.length} behavior=${report.behavior_required} liveness=${report.liveness_required}`);
  if (result !== 'pass') process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
