#!/usr/bin/env node
/* Viewport-scoped DOM validator: rects, typography and container constraints.
 *
 * Two candidate modes:
 *   1. marker mode — candidate carries data-h2d-path/data-h2d-viewport attributes;
 *   2. integration mode — candidate is a real project page (file or URL) and a
 *      selector map ties donor node paths to the project's own CSS selectors.
 *
 * Text metrics (size, weight, line-height, letter-spacing) fail the gate: they
 * are what makes a rect match honest. Font family is reported as a substitution
 * instead, because the font_manifest gate owns family identity and a donor face
 * may legitimately lack the candidate's script.
 */
const fs = require('fs');
const path = require('path');

const TEXT_METRIC_PROPS = ['fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'textAlign', 'textTransform', 'color'];
// margin belongs here: a candidate can drop the donor's margin and push the
// element with a parent offset instead, hit the same rect, and silently break
// the structural contract the no-compensation rule exists to protect.
const BOX_PROPS = ['maxWidth', 'padding', 'gap', 'margin'];

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : def;
}
function flag(name) {
  return process.argv.includes(`--${name}`);
}
function toTargetUrl(p) {
  if (/^https?:\/\//.test(p) || /^file:/.test(p)) return p;
  return 'file://' + path.resolve(p);
}
function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}
function delta(a, b) {
  return Math.abs(Number(a) - Number(b));
}

/** Selector map accepts a flat {path: selector} or {viewport: {path: selector}}. */
function selectorsFor(map, viewport) {
  if (!map) return null;
  const scoped = map[String(viewport)];
  const flat = scoped && typeof scoped === 'object' ? scoped : map;
  const out = {};
  for (const [key, value] of Object.entries(flat)) {
    if (typeof value === 'string') out[key] = value;
  }
  return out;
}

/**
 * Owner-approved deltas, e.g. a heading that is taller in another language.
 *
 * Every part is mandatory. A vague entry naming only a node would otherwise
 * suppress unrelated position, typography and colour failures across all
 * viewports under one invented reason — which is precisely the silent
 * self-approval this mechanism is meant to replace.
 */
function buildAcceptedIndex(entries) {
  const index = new Map();
  if (entries && !Array.isArray(entries)) {
    throw new Error('--accepted-deviations must be a JSON array of entries');
  }
  (entries || []).forEach((entry, i) => {
    const at = `accepted-deviations[${i}]`;
    const paths = entry.data_h2d_path ? [entry.data_h2d_path] : (entry.paths || []);
    const viewports = entry.viewport ? [entry.viewport] : (entry.viewports || []);
    const fields = entry.fields || [];
    if (!paths.length) throw new Error(`${at}: "data_h2d_path" (or "paths") is required`);
    if (!viewports.length) throw new Error(`${at}: "viewport" (or "viewports") is required — approve a concrete viewport, not every one`);
    if (!Array.isArray(fields) || !fields.length) throw new Error(`${at}: "fields" is required and must be a non-empty list, e.g. ["height"]`);
    if (fields.includes('*')) throw new Error(`${at}: "*" is not an approval — list the exact fields the owner accepted`);
    if (typeof entry.reason !== 'string' || entry.reason.trim().length < 10) {
      throw new Error(`${at}: "reason" is required and must state what the owner approved and why`);
    }
    for (const p of paths) {
      for (const v of viewports) {
        index.set(`${v}::${p}`, { fields, reason: entry.reason.trim() });
      }
    }
  });
  return index;
}
function acceptedFor(index, viewport, h2dPath, field) {
  const hit = index.get(`${viewport}::${h2dPath}`);
  if (!hit) return null;
  return hit.fields.includes(field) ? hit : null;
}

const PX = /^-?\d+(\.\d+)?px$/;
function normalizeStyleValue(value) {
  return String(value == null ? '' : value).trim().replace(/\s+/g, ' ');
}
/** Compare one computed style value against the donor's. */
function compareStyle(expected, actual, threshold) {
  const e = normalizeStyleValue(expected);
  const a = normalizeStyleValue(actual);
  if (e === a) return {equal: true};
  const bothNumeric = (PX.test(e) || /^-?\d+(\.\d+)?$/.test(e)) && (PX.test(a) || /^-?\d+(\.\d+)?$/.test(a));
  if (bothNumeric) {
    const d = delta(parseFloat(e), parseFloat(a));
    return d <= threshold ? {equal: true} : {equal: false, delta: d};
  }
  return {equal: false};
}
/** First family name, unquoted and lowercased — enough to tell a substitution. */
function primaryFamily(value) {
  return normalizeStyleValue(value).split(',')[0].replace(/["']/g, '').trim().toLowerCase();
}

async function main() {
  const candidate = arg('candidate') || arg('html');
  const rectTargetsPath = arg('rect-targets');
  const outPath = arg('out', 'reports/node_validation.json');
  const selectorMapPath = arg('selector-map');
  const acceptedPath = arg('accepted-deviations');
  const threshold = Number(arg('threshold', '0.5'));
  const styleThreshold = Number(arg('style-threshold', arg('threshold', '0.5')));
  const waitMs = Number(arg('wait-ms', '0'));
  const readyTimeout = Number(arg('ready-timeout-ms', '10000'));
  const strictFontFamily = flag('strict-font-family');
  const lenientBoxStyle = flag('lenient-box-style');
  const viewports = String(arg('viewports') || arg('viewport') || '').split(',').filter(Boolean).map((v) => Number(v));
  if (!candidate || !rectTargetsPath || !viewports.length) {
    throw new Error('Usage: --candidate <file|url> --rect-targets <file> --viewports 390,768 --out <file> [--selector-map <file>] [--accepted-deviations <file>] [--ready-selector <css>] [--ready-timeout-ms 10000] [--wait-ms 0] [--strict-font-family] [--lenient-box-style] [--browser-executable <path>]');
  }

  const { launchChromium } = require('./browser');
  const targets = readJson(rectTargetsPath);
  const selectorMap = selectorMapPath ? readJson(selectorMapPath) : null;
  const accepted = buildAcceptedIndex(acceptedPath ? readJson(acceptedPath) : []);
  const byViewport = new Map(targets.viewports.map((v) => [Number(v.viewport), v]));
  // A viewport with no recorded targets would measure nothing and still report
  // pass, so asking for 375 when the donor recorded 390 must be an error rather
  // than an empty green run.
  const unrecorded = viewports.filter((v) => !byViewport.has(v));
  if (unrecorded.length) {
    throw new Error(`no rect targets recorded for viewport(s) ${unrecorded.join(', ')}; recorded: ${[...byViewport.keys()].join(', ')}`);
  }
  const browser = await launchChromium({ executablePath: arg('browser-executable') || undefined });
  const results = [];
  let globalMax = 0;

  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport, height: Number(arg('height', '1200')) }, deviceScaleFactor: 1 });
    // 'load' rather than 'networkidle': a looping hero video or a live dev
    // server never goes idle, and the previous wait would hang the gate.
    await page.goto(toTargetUrl(candidate), { waitUntil: 'load' });
    // Fonts must be settled before any typography or rect measurement.
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await page.evaluate(require('./font_probe').FONT_PROBE_SOURCE);

    const selectors = selectorsFor(selectorMap, viewport);
    // A live project page may still be hydrating or waiting on its first
    // request, so measuring right after 'load' can catch missing nodes or
    // transient geometry. Wait for the mapped nodes, then for layout to stop
    // moving, before believing any number this page reports.
    if (selectors) {
      const readySelector = arg('ready-selector');
      if (readySelector) await page.waitForSelector(readySelector, { timeout: readyTimeout }).catch(() => {});
      for (const selector of new Set(Object.values(selectors))) {
        await page.waitForSelector(selector, { timeout: readyTimeout }).catch(() => {});
      }
      await page.evaluate(async (limit) => {
        const measure = () => [...document.querySelectorAll('*')].length + Math.round(document.body.scrollHeight);
        let previous = -1;
        for (let i = 0; i < limit && previous !== measure(); i += 1) {
          previous = measure();
          await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 100)));
        }
      }, 10);
    }
    if (waitMs) await page.waitForTimeout(waitMs);
    const probe = await page.evaluate(({ viewport, selectors, styleProps }) => {
      const read = (el, h2dPath) => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        const style = {};
        for (const prop of styleProps) style[prop] = cs[prop];
        style.fontFamily = cs.fontFamily;
        // The declared stack says nothing about what actually painted: a brand
        // face that failed to load, or lacks the glyphs for this text, falls
        // back silently while getComputedStyle still reports it.
        const primary = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
        let primaryAvailable = null;
        try {
          primaryAvailable = window.__h2dFontUsed(primary, cs.fontWeight, cs.fontSize, cs.fontStyle, el.textContent);
        } catch { primaryAvailable = null; }
        return {
          data_h2d_path: h2dPath,
          rect: { x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height },
          tag: el.tagName,
          style,
          primary_family: primary,
          primary_family_available: primaryAvailable
        };
      };
      const nodes = [];
      const unresolved = [];
      if (selectors) {
        for (const [h2dPath, selector] of Object.entries(selectors)) {
          let el = null;
          try {
            el = document.querySelector(selector);
          } catch (err) {
            unresolved.push({ path: h2dPath, selector, reason: 'invalid selector' });
            continue;
          }
          if (!el) {
            unresolved.push({ path: h2dPath, selector, reason: 'not found' });
            continue;
          }
          nodes.push(read(el, h2dPath));
        }
        return { nodes, unresolved, mode: 'selector-map' };
      }
      const root = document.querySelector(`[data-h2d-viewport="${viewport}"][data-h2d-branch-root="true"]`) || document.querySelector(`[data-h2d-viewport="${viewport}"]`);
      if (!root) return { error: 'active branch root not found', nodes: [], unresolved, mode: 'markers' };
      const list = [];
      if (root.hasAttribute('data-h2d-path')) list.push(root);
      list.push(...root.querySelectorAll('[data-h2d-path]'));
      const seen = new Set();
      for (const el of list) {
        const h2dPath = el.getAttribute('data-h2d-path');
        if (!h2dPath || seen.has(h2dPath)) continue;
        seen.add(h2dPath);
        nodes.push(read(el, h2dPath));
      }
      return { nodes, unresolved, mode: 'markers' };
    }, { viewport, selectors, styleProps: TEXT_METRIC_PROPS.concat(BOX_PROPS) });

    const targetGroup = byViewport.get(viewport);
    const domMap = new Map((probe.nodes || []).map((n) => [n.data_h2d_path, n]));
    const targetMap = new Map(targetGroup.targets.map((t) => [t.data_h2d_path, t]));
    const missing = [], extra = [], issues = [], warnings = [], acceptedHits = [];
    let checked = 0, maxDelta = 0, styleChecked = 0;

    for (const [p, t] of targetMap) {
      const n = domMap.get(p);
      if (!n) { missing.push(p); continue; }
      checked += 1;

      for (const f of ['x', 'y', 'width', 'height']) {
        const d = delta(n.rect[f], t.rect[f]);
        maxDelta = Math.max(maxDelta, d); globalMax = Math.max(globalMax, d);
        if (d <= threshold) continue;
        const ok = acceptedFor(accepted, viewport, p, f);
        if (ok) acceptedHits.push({ type: 'rect', path: p, field: f, expected: t.rect[f], actual: n.rect[f], delta: d, reason: ok.reason });
        else issues.push({ type: 'delta', path: p, field: f, expected: t.rect[f], actual: n.rect[f], delta: d });
      }

      if (t.text_style) {
        styleChecked += 1;
        for (const prop of TEXT_METRIC_PROPS) {
          if (!(prop in t.text_style)) continue;
          const cmp = compareStyle(t.text_style[prop], n.style[prop], styleThreshold);
          if (cmp.equal) continue;
          const ok = acceptedFor(accepted, viewport, p, prop);
          const entry = { type: 'text-style', path: p, field: prop, expected: t.text_style[prop], actual: n.style[prop] };
          if (cmp.delta != null) entry.delta = cmp.delta;
          if (ok) acceptedHits.push({ ...entry, reason: ok.reason });
          else issues.push(entry);
        }
        if (t.text_style.fontFamily && primaryFamily(t.text_style.fontFamily) !== primaryFamily(n.style.fontFamily)) {
          const entry = { type: 'font-family', path: p, expected: t.text_style.fontFamily, actual: n.style.fontFamily, note: 'must be documented in font_manifest.json as font-substituted' };
          if (strictFontFamily) issues.push(entry); else warnings.push(entry);
        }
        // A matching declaration is not a matching render. Without this check a
        // candidate can keep a broken brand-font declaration, paint a fallback,
        // and still be called font-exact.
        if (n.primary_family_available === false) {
          warnings.push({
            type: 'rendered-face-unavailable',
            path: p,
            declared: n.primary_family,
            donor_rendered: t.rendered_font ? (t.rendered_font.post_script_name || t.rendered_font.family) : null,
            note: 'the declared family cannot render this text, so a fallback paints it: font_manifest must say font-substituted'
          });
        }
      }

      if (t.box_style) {
        for (const prop of BOX_PROPS) {
          if (!(prop in t.box_style)) continue;
          const cmp = compareStyle(t.box_style[prop], n.style[prop], styleThreshold);
          if (cmp.equal) continue;
          const entry = { type: 'box-style', path: p, field: prop, expected: t.box_style[prop], actual: n.style[prop] };
          if (cmp.delta != null) entry.delta = cmp.delta;
          const ok = acceptedFor(accepted, viewport, p, prop);
          // Failing by default is the teeth of the no-compensation rule: a
          // container constraint replaced by a parent offset reaches the same
          // rect, and a warning nobody must resolve would let it ship. The
          // honest escape is an owner-approved deviation, not a quiet note.
          if (ok) acceptedHits.push({ ...entry, reason: ok.reason });
          else if (lenientBoxStyle) warnings.push(entry);
          else issues.push(entry);
        }
      }
    }

    for (const p of domMap.keys()) if (!targetMap.has(p)) extra.push(p);
    if (!checked) issues.push({ type: 'nothing-measured', message: `no target was resolved on ${viewport}px: the candidate carries neither the expected markers nor a matching selector map` });
    if (probe.error) issues.push({ type: 'branch-root', message: probe.error });
    for (const u of probe.unresolved || []) issues.push({ type: 'selector-unresolved', path: u.path, selector: u.selector, message: u.reason });

    results.push({
      viewport,
      result: missing.length || issues.length ? 'fail' : 'pass',
      mode: probe.mode,
      checked,
      style_checked: styleChecked,
      missing,
      extra,
      max_delta: maxDelta,
      issues,
      warnings,
      accepted_deviations: acceptedHits
    });
    await page.close();
  }
  await browser.close();

  const overall = {
    result: results.every((r) => r.result === 'pass') ? 'pass' : 'fail',
    threshold_px: threshold,
    style_threshold_px: styleThreshold,
    strict_font_family: strictFontFamily,
    lenient_box_style: lenientBoxStyle,
    global_max_delta: globalMax,
    viewports: results,
    issues: results.flatMap((r) => r.issues.map((i) => ({ ...i, viewport: r.viewport }))),
    warnings: results.flatMap((r) => r.warnings.map((w) => ({ ...w, viewport: r.viewport }))),
    accepted_deviations: results.flatMap((r) => r.accepted_deviations.map((a) => ({ ...a, viewport: r.viewport })))
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(overall, null, 2));
  console.log(`result=${overall.result} global_max_delta=${globalMax} warnings=${overall.warnings.length} accepted=${overall.accepted_deviations.length} out=${outPath}`);
  process.exit(overall.result === 'pass' ? 0 : 2);
}
main().catch((err) => { console.error(err.stack || err); process.exit(1); });
