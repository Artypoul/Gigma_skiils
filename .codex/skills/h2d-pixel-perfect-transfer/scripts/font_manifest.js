#!/usr/bin/env node
/**
 * Generate reports/font_manifest.json by measuring the candidate.
 *
 * Typography is the first step of a transfer, so this is the first gate to
 * produce evidence: which families the candidate actually declares, whether
 * those faces can really paint the text, and how that compares with what the
 * donor rendered. `font-exact` is only claimed when the primary families match
 * the donor's and every one of them is genuinely available — a brand face that
 * silently falls back is a substitution, not an exact match.
 *
 *   node scripts/font_manifest.js \
 *     --candidate dist/hero.html \
 *     --rect-targets h2d-transfer-output/reports/rect_targets.json \
 *     --viewports 1440 \
 *     --out h2d-transfer-output/reports/font_manifest.json
 *
 * Integration mode takes the same --selector-map as validate_active_viewport.js.
 */
const fs = require('fs');
const path = require('path');

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : def;
}
function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}
function toTargetUrl(p) {
  if (/^https?:\/\//.test(p) || /^file:/.test(p)) return p;
  return 'file://' + path.resolve(p);
}
function primaryFamily(value) {
  return String(value || '').split(',')[0].replace(/["']/g, '').trim();
}
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

async function main() {
  const candidate = arg('candidate') || arg('html');
  const rectTargetsPath = arg('rect-targets');
  const outPath = arg('out', 'reports/font_manifest.json');
  const selectorMapPath = arg('selector-map');
  const substitutionsPath = arg('substitutions');
  const readyTimeout = Number(arg('ready-timeout-ms', '10000'));
  const waitMs = Number(arg('wait-ms', '0'));
  const allowPartial = process.argv.includes('--allow-partial-viewports');
  if (!candidate || !rectTargetsPath) {
    throw new Error('Usage: --candidate <file|url> --rect-targets <file> --out <file> [--viewports 390,1440] [--selector-map <file>] [--substitutions <file>] [--ready-selector <css>] [--allow-partial-viewports]');
  }

  const { launchChromium } = require('./browser');
  const targets = readJson(rectTargetsPath);
  const selectorMap = selectorMapPath ? readJson(selectorMapPath) : null;
  const substitutions = substitutionsPath ? readJson(substitutionsPath) : {};
  const byViewport = new Map(targets.viewports.map((v) => [Number(v.viewport), v]));
  const recorded = [...byViewport.keys()];
  // Typography is responsive: measuring one width and declaring the manifest
  // done would leave the other breakpoints unproven, so the default is every
  // recorded viewport and a narrower run has to be declared.
  const requested = String(arg('viewports') || arg('viewport') || '').split(',').filter(Boolean).map(Number);
  const viewports = requested.length ? requested : recorded;
  const unrecorded = viewports.filter((v) => !byViewport.has(v));
  if (unrecorded.length) {
    throw new Error(`no rect targets recorded for viewport(s) ${unrecorded.join(', ')}; recorded: ${recorded.join(', ')}`);
  }
  const skipped = recorded.filter((v) => !viewports.includes(v));
  if (skipped.length && !allowPartial) {
    throw new Error(`viewport(s) ${skipped.join(', ')} are recorded but not measured; run them too or pass --allow-partial-viewports to scope the manifest deliberately`);
  }

  const browser = await launchChromium();
  const fonts = [];
  const licensingNotes = [];
  let unavailable = 0, substituted = 0, measured = 0, unapproved = 0;

  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport, height: Number(arg('height', '1200')) }, deviceScaleFactor: 1 });
    await page.goto(toTargetUrl(candidate), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await page.evaluate(require('./font_probe').FONT_PROBE_SOURCE);
    const selectors = selectorsFor(selectorMap, viewport);
    const group = byViewport.get(viewport);
    const wanted = group.targets.filter((t) => t.text_style && t.text_style.fontFamily);
    // A live project page may still be hydrating; probing too early would
    // report its nodes as not-found and turn a valid transfer into
    // manual-review.
    if (selectors) {
      const readySelector = arg('ready-selector');
      if (readySelector) await page.waitForSelector(readySelector, { timeout: readyTimeout }).catch(() => {});
      for (const target of wanted) {
        const selector = selectors[target.data_h2d_path];
        if (selector) await page.waitForSelector(selector, { timeout: readyTimeout }).catch(() => {});
      }
    }
    if (waitMs) await page.waitForTimeout(waitMs);

    const probe = await page.evaluate(({ selectors, paths }) => {
      const pick = (h2dPath) => {
        if (selectors && selectors[h2dPath]) {
          try { return document.querySelector(selectors[h2dPath]); } catch { return null; }
        }
        return document.querySelector(`[data-h2d-path="${h2dPath}"]`);
      };
      const out = {};
      for (const h2dPath of paths) {
        const el = pick(h2dPath);
        if (!el) { out[h2dPath] = null; continue; }
        const cs = getComputedStyle(el);
        const primary = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
        const text = (el.textContent || '').trim().slice(0, 200);
        let available = null;
        try {
          available = window.__h2dFontUsed(primary, cs.fontWeight, cs.fontSize, cs.fontStyle, text);
        } catch { available = null; }
        out[h2dPath] = {
          font_family: cs.fontFamily,
          primary_family: primary,
          font_weight: cs.fontWeight,
          font_size: cs.fontSize,
          available,
          sample: text.slice(0, 40)
        };
      }
      return out;
    }, { selectors, paths: wanted.map((t) => t.data_h2d_path) });

    for (const target of wanted) {
      const seen = probe[target.data_h2d_path];
      const donorPrimary = primaryFamily(target.text_style.fontFamily);
      if (!seen) {
        fonts.push({ viewport, data_h2d_path: target.data_h2d_path, donor_family: donorPrimary, result: 'not-found', source: 'computed-style' });
        continue;
      }
      measured += 1;
      const familyMatches = seen.primary_family.toLowerCase() === donorPrimary.toLowerCase();
      let entry_result = 'exact';
      let approval = null;
      if (seen.available === false) { entry_result = 'renders-fallback'; unavailable += 1; }
      else if (!familyMatches) {
        substituted += 1;
        // A substitution is a decision, not a measurement: without recorded
        // approval an accidental fallback would earn the same green verdict as
        // a deliberate one.
        approval = substitutions[donorPrimary] || substitutions[`${donorPrimary} -> ${seen.primary_family}`] || null;
        const approved = approval && approval.approved === true && typeof approval.reason === 'string' && approval.reason.trim().length >= 10;
        entry_result = approved ? 'substituted' : 'substituted-unapproved';
        if (!approved) unapproved += 1;
      }
      fonts.push({
        substitution_reason: approval && approval.reason ? approval.reason : null,
        substitution_approved_by: approval && approval.approved_by ? approval.approved_by : null,
        viewport,
        data_h2d_path: target.data_h2d_path,
        selector: selectors ? selectors[target.data_h2d_path] || null : null,
        donor_family: donorPrimary,
        donor_rendered: target.rendered_font ? (target.rendered_font.post_script_name || target.rendered_font.family) : null,
        font_family: seen.font_family,
        primary_family: seen.primary_family,
        font_weight: seen.font_weight,
        font_size: seen.font_size,
        primary_family_available: seen.available,
        sample: seen.sample,
        result: entry_result,
        source: 'computed-style'
      });
    }
    await page.close();
  }
  await browser.close();

  const notFound = fonts.filter((f) => f.result === 'not-found');
  let result;
  if (!measured) result = 'not-tested';
  else if (notFound.length) result = 'manual-review';
  else if (unavailable) result = 'font-mismatch-risk';
  else if (unapproved) result = 'manual-review';
  else if (substituted) result = 'font-substituted';
  else result = 'font-exact';

  if (unavailable) {
    licensingNotes.push(`${unavailable} node(s) declare a family that cannot paint their text; the browser substitutes silently. Load the real face or declare the fallback deliberately.`);
  }
  if (unapproved) {
    licensingNotes.push(`${unapproved} substitution(s) have no recorded approval. Add them to --substitutions as {"<donor family>": {"approved": true, "reason": "...", "approved_by": "..."}} so an accidental fallback is not mistaken for a decision.`);
  }
  if (substituted) {
    licensingNotes.push(`${substituted} node(s) use a different family than the donor. Record why — missing script coverage is a valid reason, an accidental fallback is not.`);
  }
  licensingNotes.push('Do not package proprietary font files without permission.');

  const report = {
    result,
    measured_nodes: measured,
    measured_viewports: viewports,
    recorded_viewports: recorded,
    scoped_viewports: Boolean(skipped.length),
    fonts,
    licensing_notes: licensingNotes
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(`result=${result} measured=${measured} viewports=${viewports.join('/')} substituted=${substituted} unapproved=${unapproved} renders_fallback=${unavailable} out=${outPath}`);
  process.exit(result === 'font-exact' || result === 'font-substituted' ? 0 : 2);
}
main().catch((err) => { console.error(err.stack || err); process.exit(1); });
