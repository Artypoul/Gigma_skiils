#!/usr/bin/env node
/* Discover semantic and listener-backed controls without silently truncating coverage. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { launchChromium, contextOptions, installNetworkSandbox, installRuntimeInstrumentation } = require('./browser');

function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function toUrl(value) { if (/^https?:\/\//.test(value) || /^file:/.test(value)) return value; return 'file://' + path.resolve(value).replace(/\\/g, '/'); }
function loadJson(value, fallback) { return value ? JSON.parse(fs.readFileSync(value, 'utf8')) : fallback; }
function sha(value) { return crypto.createHash('sha256').update(value).digest('hex'); }

async function main() {
  const url = arg('url');
  const out = arg('out', 'reports/behavior_inventory.json');
  if (!url) throw new Error('Usage: --url original --out reports/behavior_inventory.json');
  const viewport = { width: Number(arg('viewport', '390')), height: Number(arg('height', '1400')) };
  const profile = loadJson(arg('profile'), { id: 'default', headless: true, device_scale_factor: Number(arg('dpr', '1')), is_mobile: false, has_touch: false, locale: 'en-US', timezone: 'UTC', reduced_motion: 'reduce' });
  const maxElements = Number(arg('max-elements', '5000'));
  const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
  const context = await browser.newContext(contextOptions(profile, viewport));
  const network = await installNetworkSandbox(context, loadJson(arg('request-allowlist'), []));
  await installRuntimeInstrumentation(context);
  const page = await context.newPage();
  await page.goto(toUrl(url), { waitUntil: 'networkidle' });
  const data = await page.evaluate(({ maxElements, viewportWidth }) => {
    const eventProps = ['onclick','ondblclick','onpointerdown','onpointerup','onpointermove','onmousedown','onmouseup','onmousemove','ontouchstart','ontouchend','onkeydown','onkeyup','oninput','onchange','onsubmit','ondragstart','ondragend','ondrop'];
    const actionableRoles = new Set(['button','link','menuitem','menuitemcheckbox','menuitemradio','tab','checkbox','radio','switch','option','combobox','textbox','searchbox','slider','spinbutton','treeitem','gridcell']);
    function visible(el) { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity) > 0.001; }
    function stable(el) {
      if (el.id) return '#' + CSS.escape(el.id);
      for (const name of ['data-h2d-path','data-behavior-id']) { const value = el.getAttribute(name); if (value) return `[${name}=${JSON.stringify(value)}]`; }
      const parts = []; let node = el;
      while (node && node.nodeType === 1 && node !== document.documentElement) {
        let part = node.tagName.toLowerCase();
        const siblings = node.parentElement ? [...node.parentElement.children].filter(item => item.tagName === node.tagName) : [];
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        parts.unshift(part); node = node.parentElement;
      }
      return 'html > ' + parts.join(' > ');
    }
    const seen = new Set(); const rows = []; const boundaries = [];
    function inspectDocument(doc, framePath = 'main') {
      const all = [...doc.querySelectorAll('*')];
      if (all.length > maxElements) boundaries.push({ type: 'element-limit', frame_path: framePath, discovered: all.length, limit: maxElements });
      for (const el of all.slice(0, maxElements)) {
        if (!visible(el)) continue;
        const semantic = el.matches('a[href],button,input,select,textarea,[aria-expanded],[tabindex]:not([tabindex="-1"]),summary') || actionableRoles.has(el.getAttribute('role'));
        const registered = String(el.getAttribute('data-h2d-listener-events') || '').split(',').filter(Boolean);
        const properties = eventProps.filter(name => typeof el[name] === 'function' || el.hasAttribute(name));
        if (!semantic && !registered.length && !properties.length) continue;
        const selector = stable(el); const key = `${framePath}|${selector}`;
        if (seen.has(key)) continue; seen.add(key);
        let count = 0; try { count = doc.querySelectorAll(selector).length; } catch {}
        const tag = el.tagName.toLowerCase();
        const label = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('href') || el.name || el.id || tag).trim().replace(/\s+/g, ' ').slice(0, 120);
        let kind = 'listener-surface';
        if (tag === 'a') kind = 'link'; else if (tag === 'input' || tag === 'textarea') kind = 'input'; else if (tag === 'select') kind = 'select'; else if (tag === 'form') kind = 'form'; else if (el.hasAttribute('aria-expanded')) kind = 'disclosure'; else if (tag === 'button' || el.getAttribute('role') === 'button') kind = 'button';
        rows.push({ component_id: `${viewportWidth}:${framePath}:${rows.length}`, selector, frame_path: framePath, selector_count: count, kind, label, criticality: 'critical', listeners: [...new Set([...registered, ...properties.map(name => name.slice(2))])].sort(), h2d_path: el.getAttribute('data-h2d-path') || null });
        if (el.shadowRoot) inspectShadow(el.shadowRoot, `${framePath}>>>${selector}`);
      }
      for (const frame of [...doc.querySelectorAll('iframe')]) {
        const selector = stable(frame);
        try { if (frame.contentDocument) inspectDocument(frame.contentDocument, `${framePath}||${selector}`); else boundaries.push({ type: 'cross-origin-frame', frame_path: `${framePath}||${selector}` }); }
        catch { boundaries.push({ type: 'cross-origin-frame', frame_path: `${framePath}||${selector}` }); }
      }
    }
    function inspectShadow(root, rootPath) {
      const all = [...root.querySelectorAll('*')];
      if (all.length > maxElements) boundaries.push({ type: 'element-limit', frame_path: rootPath, discovered: all.length, limit: maxElements });
      for (const el of all.slice(0, maxElements)) {
        if (!visible(el)) continue;
        const semantic = el.matches('a[href],button,input,select,textarea,[aria-expanded],[tabindex]:not([tabindex="-1"]),summary') || actionableRoles.has(el.getAttribute('role'));
        const registered = String(el.getAttribute('data-h2d-listener-events') || '').split(',').filter(Boolean);
        const properties = eventProps.filter(name => typeof el[name] === 'function' || el.hasAttribute(name));
        if (!semantic && !registered.length && !properties.length) continue;
        const selector = stable(el);
        rows.push({ component_id: `${viewportWidth}:${rootPath}:${rows.length}`, selector, frame_path: rootPath, selector_count: 1, kind: 'shadow-control', label: (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0,120), criticality: 'critical', listeners: [...new Set([...registered, ...properties.map(name=>name.slice(2))])].sort() });
      }
    }
    inspectDocument(document);
    for (const listener of (window.__h2dRuntime || {}).global_listeners || []) boundaries.push({ type: 'delegated-listener', target: listener.target, event: listener.type });
    for (const [target, value] of [['window', window], ['document', document]]) for (const name of eventProps) if (typeof value[name] === 'function') boundaries.push({ type: 'delegated-property-handler', target, event: name.slice(2) });
    return { rows, boundaries };
  }, { maxElements, viewportWidth: viewport.width });
  await browser.close();
  const classificationPath = arg('classification');
  let classification = null; let classificationRow = null;
  if (classificationPath) {
    classification = loadJson(classificationPath, null);
    if (!classification || classification.result !== 'pass' || classification.coverage_complete !== true) throw new Error('Behavior inventory requires a complete generated classification');
    const matrixKey = `${viewport.width}x${viewport.height}@${profile.id}`;
    classificationRow = (classification.rows || []).find(row => row.matrix_key === matrixKey);
    if (!classificationRow) throw new Error(`Classification is missing ${matrixKey}`);
    const byStateSelector = new Map();
    for (const state of classificationRow.states || []) {
      const prerequisite = (state.sequence || []).map(selector => ({ action: 'click', selector }));
      for (const control of state.controls || []) {
        const framePath = control.frame_path || 'main'; const key = `${state.state_sha256}|${framePath}|${control.selector}`;
        const candidate = {
          selector: control.selector, frame_path: framePath, selector_count: control.selector_count,
          kind: control.kind || 'listener-surface', label: control.label || control.selector,
          criticality: 'critical', listeners: control.listeners || [], h2d_path: control.h2d_path || null,
          state_sha256: state.state_sha256, prerequisite_sequence: prerequisite,
        };
        byStateSelector.set(key, candidate);
      }
    }
    data.rows = [...byStateSelector.values()].sort((a,b) => `${a.prerequisite_sequence.length}|${a.state_sha256}|${a.frame_path}|${a.selector}`.localeCompare(`${b.prerequisite_sequence.length}|${b.state_sha256}|${b.frame_path}|${b.selector}`));
  }
  data.rows.forEach((row, index) => { row.component_id = `${viewport.width}:${profile.id}:${index}`; });
  const unresolved = data.rows.filter(row => row.selector_count !== 1);
  const truncated = data.boundaries.some(item => item.type === 'element-limit');
  const unsupported = data.boundaries.some(item => ['cross-origin-frame','delegated-listener','delegated-property-handler'].includes(item.type));
  const complete = Boolean(classificationRow) && !unresolved.length && !truncated && !unsupported;
  const result = unresolved.length || truncated || unsupported ? 'fail' : (data.rows.length ? (complete ? 'pass' : 'partial') : 'not-tested');
  const generator_sha256 = sha(fs.readFileSync(__filename));
  const report = { result, coverage_complete: complete, reachable_states_complete: complete, generator_sha256, classification_sha256: classificationPath ? sha(fs.readFileSync(classificationPath)) : null, truncated, url, viewports: [viewport.width], profile_id: profile.id, components: data.rows, boundaries: data.boundaries, issues: unresolved.map(row => ({ type: 'selector-not-unique', component_id: row.component_id, count: row.selector_count })), blocked_requests: network.filter(row => row.action === 'blocked').length };
  fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(path.dirname(out), 'event_listener_inventory.json'), JSON.stringify({ result, coverage_complete: report.coverage_complete, generator_sha256, listeners: data.rows.map(row => ({ component_id: row.component_id, selector: row.selector, events: row.listeners })) }, null, 2));
  console.log(`result=${result} components=${data.rows.length} boundaries=${data.boundaries.length} out=${out}`);
  if (result === 'fail') process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
