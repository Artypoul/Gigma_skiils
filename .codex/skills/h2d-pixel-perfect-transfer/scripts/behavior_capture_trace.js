#!/usr/bin/env node
/* Replay isolated action sequences under a deny-by-default network sandbox. */
const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const { launchChromium, contextOptions, installNetworkSandbox, installRuntimeInstrumentation, redactUrl, isExpectedSandboxConsole } = require('./browser');
function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function toUrl(value) { if (/^https?:\/\//.test(value) || /^file:/.test(value)) return value; return 'file://' + path.resolve(value).replace(/\\/g, '/'); }
function loadJson(value, fallback) { return value ? JSON.parse(fs.readFileSync(value, 'utf8')) : fallback; }
function sha(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function locatorFor(page, step, interaction) {
  const framePath = interaction.frame_path || 'main';
  if (framePath.includes('||')) {
    const parts = framePath.split('||').slice(1);
    let frame = page;
    for (const selector of parts) frame = frame.frameLocator(selector);
    return frame.locator(step.selector);
  }
  return page.locator(step.selector);
}
async function semanticState(page, selector) {
  return page.evaluate((selector) => {
    const el = document.querySelector(selector); const body = getComputedStyle(document.body);
    if (!el) return { exists: false, url_hash: null, active: null, body_overflow: body.overflow };
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); const controls = el.getAttribute('aria-controls');
    let controlledVisible = null;
    if (controls) { const controlled = document.getElementById(controls); if (controlled) { const cr = controlled.getBoundingClientRect(); const ccs = getComputedStyle(controlled); controlledVisible = cr.width > 0 && cr.height > 0 && ccs.display !== 'none' && ccs.visibility !== 'hidden' && Number(ccs.opacity) > 0.001; } }
    const accessibility = [...document.querySelectorAll('[role],button,a[href],input,select,textarea,main,nav,header,footer')].slice(0, 1000).map(node => ({ role: node.getAttribute('role') || node.tagName.toLowerCase(), name: node.getAttribute('aria-label') || node.innerText || node.getAttribute('alt') || '', expanded: node.getAttribute('aria-expanded'), checked: node.getAttribute('aria-checked'), disabled: node.hasAttribute('disabled') || node.getAttribute('aria-disabled') }));
    return { exists: true, rect: { x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height }, display: cs.display, visibility: cs.visibility, opacity: Number(cs.opacity), transform: cs.transform, aria_expanded: el.getAttribute('aria-expanded'), aria_checked: el.getAttribute('aria-checked'), value: 'value' in el ? el.value : null, active: document.activeElement ? (document.activeElement.id || document.activeElement.getAttribute('aria-label') || document.activeElement.tagName) : null, controlled_visible: controlledVisible, body_overflow: body.overflow, accessibility_sha256_source: JSON.stringify(accessibility) };
  }, selector);
}
async function intent(locator, kind) {
  return locator.evaluate((el, kind) => {
    if (kind === 'submit-intent' || el.tagName === 'FORM') return { kind: 'submit', method: String(el.method || 'get').toUpperCase(), destination: el.action || location.href, target: el.target || '_self' };
    const link = el.closest && el.closest('a[href]');
    if (link) return { kind: link.hasAttribute('download') ? 'download' : 'navigation', method: 'GET', destination: link.href, target: link.target || '_self', download: link.getAttribute('download') || null };
    return null;
  }, kind);
}
async function perform(page, interaction, step, intents) {
  const locator = locatorFor(page, step, interaction);
  if (step.action === 'escape') return page.keyboard.press('Escape');
  if (step.action === 'outside-click') return page.mouse.click(5, 5);
  if (step.action === 'tab') return page.keyboard.press('Tab');
  if (step.action === 'shift-tab') return page.keyboard.press('Shift+Tab');
  if (step.action === 'focus') return locator.focus({ timeout: 3000 });
  if (step.action === 'blur') return locator.evaluate(el => el.blur());
  if (step.action === 'keyboard-enter') { await locator.focus(); return page.keyboard.press('Enter'); }
  if (step.action === 'keyboard-space') { await locator.focus(); return page.keyboard.press('Space'); }
  if (step.action === 'input') return locator.fill(String(step.value ?? 'h2d-probe'));
  if (step.action === 'select-next') return locator.evaluate(el => { if (!el.options || el.options.length < 2) throw new Error('select has no alternative option'); el.selectedIndex = (el.selectedIndex + 1) % el.options.length; el.dispatchEvent(new Event('change', { bubbles: true })); });
  if (step.action === 'submit-intent') { const observed = await intent(locator, step.action); if (observed) intents.push(observed); return; }
  if (step.action === 'pointer-drag') {
    const box = await locator.boundingBox(); if (!box) throw new Error('pointer target has no box');
    const value = step.value || {}; const start = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
    await page.mouse.move(start.x, start.y); await page.mouse.down({ button: value.button || 'left' });
    await page.mouse.move(start.x + Number(value.dx || 0), start.y + Number(value.dy || 0), { steps: 6 }); return page.mouse.up({ button: value.button || 'left' });
  }
  if (step.action === 'click') { const observed = await intent(locator, step.action); if (observed) intents.push(observed); return locator.click({ timeout: 3000, noWaitAfter: true }); }
  throw new Error(`unsupported action ${step.action}`);
}
async function main() {
  const url = arg('url'), matrixPath = arg('matrix'), out = arg('out'), side = arg('side', 'original');
  if (!url || !matrixPath || !out) throw new Error('Usage: --url url --matrix matrix.json --side original|candidate --out traces.jsonl');
  const matrix = loadJson(matrixPath, {}); const profile = loadJson(arg('profile'), { id:'default', headless:true, device_scale_factor:1, is_mobile:false, has_touch:false, locale:'en-US', timezone:'UTC', reduced_motion:'reduce' });
  const implementation = side === 'candidate' ? loadJson(arg('implementation-map'), null) : null;
  if (side === 'candidate' && (!implementation || implementation.result !== 'pass')) throw new Error('candidate capture requires a passing --implementation-map');
  const mappings = implementation ? implementation.mappings || [] : [];
  const mappedSelectors = mappings.map(row => row.candidate_selector);
  if (new Set(mappedSelectors).size !== mappedSelectors.length) throw new Error('candidate selector mapping must be injective');
  const byComponent = new Map(mappings.map(row => [row.component_id, row.candidate_selector]));
  const byOriginal = new Map(mappings.map(row => [row.original_selector, row.candidate_selector]));
  const candidateSelector = (selector, componentId = null) => side === 'candidate' ? (byComponent.get(componentId) || byOriginal.get(selector) || null) : selector;
  const viewport = { width: Number(arg('viewport', '390')), height: Number(arg('height', '1400')) };
  const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
  const traces = []; const screenshotDir = path.join(path.dirname(path.dirname(out)), 'screenshots', 'behavior'); fs.mkdirSync(screenshotDir, { recursive: true });
  for (const interaction of matrix.interactions || []) {
    const context = await browser.newContext(contextOptions(profile, viewport)); const network = await installNetworkSandbox(context, loadJson(arg('request-allowlist'), [])); await installRuntimeInstrumentation(context);
    const page = await context.newPage(); const runtimeErrors = []; const intents = [];
    page.on('pageerror', error => runtimeErrors.push({ type:'pageerror', message:String(error.message || error).slice(0,500) }));
    page.on('console', message => { if (message.type() === 'error' && !isExpectedSandboxConsole(message)) runtimeErrors.push({ type:'console-error', message:message.text().slice(0,500) }); });
    await page.goto(toUrl(url), { waitUntil: 'networkidle' });
    const primarySelector = candidateSelector(interaction.selector, interaction.component_id);
    if (!primarySelector) throw new Error(`candidate mapping is missing for ${interaction.component_id}`);
    const errors = []; const sequence = interaction.sequence || [{ action: interaction.action, selector: interaction.selector }];
    const prerequisiteCount = Number(interaction.prerequisite_count || 0);
    if (!Number.isInteger(prerequisiteCount) || prerequisiteCount < 0 || prerequisiteCount > sequence.length) throw new Error(`invalid prerequisite_count for ${interaction.interaction_id}`);
    const replay = async (steps, observedIntents) => {
      for (const step of steps) {
        const resolved = candidateSelector(step.selector, step.selector === interaction.selector ? interaction.component_id : null);
        try { if (!resolved) throw new Error(`candidate mapping is missing for step ${step.selector}`); await perform(page, interaction, { ...step, selector: resolved }, observedIntents); await page.waitForTimeout(Number(arg('settle-ms', '250'))); }
        catch (error) { errors.push({ action: step.action, message: String(error.message || error).slice(0,500) }); break; }
      }
    };
    await replay(sequence.slice(0, prerequisiteCount), []);
    const before = await semanticState(page, primarySelector); const actionNetworkStart = network.length;
    const actionTransportStart = await page.evaluate(() => (window.__h2dBlockedTransports || []).length);
    if (!errors.length) await replay(sequence.slice(prerequisiteCount), intents);
    const after = await semanticState(page, primarySelector);
    const shot = `${side}_${interaction.interaction_id.replace(/[^a-z0-9_.-]/gi, '_')}.png`; const absolute = path.join(screenshotDir, shot); const buffer = await page.screenshot({ path: absolute, fullPage: false });
    const beforeComparable = JSON.stringify({ ...before, accessibility_sha256_source: undefined }); const afterComparable = JSON.stringify({ ...after, accessibility_sha256_source: undefined });
    const transports = await page.evaluate(() => window.__h2dBlockedTransports || []);
    const actionNetwork = network.slice(actionNetworkStart);
    const actionTransports = transports.slice(actionTransportStart);
    const changed = beforeComparable !== afterComparable || intents.length > 0 || actionNetwork.length > 0 || actionTransports.length > 0;
    if (interaction.expected_transition && !changed) errors.push({ action: 'expected-transition', message: 'declared transition produced no observed state, intent, request, or transport outcome' });
    const { accessibility_sha256_source: beforeAccessibility, ...beforePublic } = before;
    const { accessibility_sha256_source: afterAccessibility, ...afterPublic } = after;
    traces.push({ generator_sha256: sha(fs.readFileSync(__filename)), side, interaction_id: interaction.interaction_id, component_id: interaction.component_id, selector: interaction.selector, resolved_selector: primarySelector, frame_path: interaction.frame_path || 'main', prerequisite_count: prerequisiteCount, sequence, expected_transition: Boolean(interaction.expected_transition), criticality: interaction.criticality || 'critical', before: { ...beforePublic, accessibility_sha256: sha(beforeAccessibility || '') }, after: { ...afterPublic, accessibility_sha256: sha(afterAccessibility || '') }, intents: intents.map(item => item.destination ? { ...item, destination: redactUrl(item.destination) } : item), screenshot: path.join('screenshots','behavior',shot).replace(/\\/g,'/'), screenshot_sha256: sha(buffer), errors, runtime_errors: runtimeErrors, blocked_requests: actionNetwork.filter(row => row.action === 'blocked'), blocked_transports: actionTransports });
    await context.close();
  }
  await browser.close(); fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, traces.map(row => JSON.stringify(row)).join('\n') + '\n');
  const invalidReference = side === 'original' && traces.some(row => row.errors.length || row.runtime_errors.length);
  console.log(`traces=${traces.length} invalid_reference=${invalidReference} out=${out}`); if (invalidReference) process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
