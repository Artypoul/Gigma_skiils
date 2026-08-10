#!/usr/bin/env node
/* Candidate-side reuse gate: repeated donor patterns must be ONE component.
 *
 * The design-system extractor describes the donor. This gate looks at the
 * CANDIDATE: for every repeated donor pattern the component map names a
 * selector, and all instances that selector finds must be structurally
 * identical and share the same computed tokens. N pasted copies drift — an
 * edited copy changes its subtree signature or its computed styles, and that
 * is exactly what fails here.
 *
 *   node scripts/validate_component_reuse.js \
 *     --candidate http://127.0.0.1:5005/ \
 *     --design-system h2d-transfer-output/reports/design_system.json \
 *     --component-map h2d-transfer-output/reports/component_map.json \
 *     --out h2d-transfer-output/reports/component_reuse.json
 *
 * component map format:
 *   {"work-tag": {"selector": ".work-tags li", "donor_signature": "li.WorkTags_Tag[...]", "min_instances": 2}, ...}
 * Every donor component candidate above the repeat floor must either appear in
 * the map or be listed in "excluded" with a reason (e.g. capture artifact).
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

async function main() {
  const candidate = arg('candidate');
  const designSystemPath = arg('design-system');
  const mapPath = arg('component-map');
  const outPath = arg('out', 'reports/component_reuse.json');
  const viewport = Number(arg('viewport', '1440'));
  const minRepeats = Number(arg('min-repeats', '3'));
  if (!candidate || !designSystemPath || !mapPath) {
    throw new Error('Usage: --candidate <file|url> --design-system <file> --component-map <file> --out <file> [--viewport 1440] [--min-repeats 3]');
  }

  const designSystem = readJson(designSystemPath);
  const map = readJson(mapPath);
  const entries = map.components || map;
  const excluded = map.excluded || {};
  const issues = [];
  const checks = [];

  // Coverage: every repeated donor pattern is mapped or explicitly excluded.
  const donorComponents = (designSystem.components || []).filter((c) => (c.count || 0) >= minRepeats);
  const mappedSignatures = new Set(Object.values(entries).map((e) => e.donor_signature).filter(Boolean));
  for (const component of donorComponents) {
    const signature = component.signature;
    if (mappedSignatures.has(signature)) continue;
    const exclusion = Object.entries(excluded).find(([sig]) => sig === signature);
    if (exclusion && String(exclusion[1] || '').trim().length >= 10) continue;
    issues.push({
      component: signature.slice(0, 120),
      issue: `repeated donor pattern (x${component.count}) is neither mapped to a candidate component nor excluded with a reason`,
    });
  }

  const { launchChromium } = require('./browser');
  const browser = await launchChromium({ executablePath: arg('browser-executable') || undefined });
  const page = await browser.newPage({ viewport: { width: viewport, height: Number(arg('height', '1400')) }, deviceScaleFactor: 1 });
  await page.goto(toTargetUrl(candidate), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const waitMs = Number(arg('wait-ms', '0'));
  if (waitMs) await page.waitForTimeout(waitMs);

  for (const [name, entry] of Object.entries(entries)) {
    if (!entry || typeof entry.selector !== 'string') {
      issues.push({ component: name, issue: 'component map entry has no selector' });
      continue;
    }
    const minInstances = Number(entry.min_instances || 2);
    const probe = await page.evaluate(({ selector }) => {
      const signatureOf = (el, depth) => {
        const classes = [...el.classList].sort().join('.');
        let sig = el.tagName.toLowerCase() + (classes ? '.' + classes : '');
        if (depth > 0) {
          const kids = [...el.children].map((child) => signatureOf(child, depth - 1));
          if (kids.length) sig += '[' + kids.join(',') + ']';
        }
        return sig;
      };
      let nodes = [];
      try {
        nodes = [...document.querySelectorAll(selector)];
      } catch {
        return { error: 'invalid selector' };
      }
      return {
        instances: nodes.map((el) => {
          const cs = getComputedStyle(el);
          return {
            signature: signatureOf(el, 2),
            tokens: { fontFamily: cs.fontFamily, fontSize: cs.fontSize, fontWeight: cs.fontWeight, color: cs.color, backgroundColor: cs.backgroundColor, borderRadius: cs.borderTopLeftRadius, padding: cs.padding },
          };
        }),
      };
    }, { selector: entry.selector });

    if (probe.error) {
      issues.push({ component: name, issue: `selector "${entry.selector}": ${probe.error}` });
      continue;
    }
    const instances = probe.instances || [];
    const check = { component: name, selector: entry.selector, instances: instances.length };
    if (instances.length < minInstances) {
      issues.push({ component: name, issue: `selector "${entry.selector}" finds ${instances.length} instance(s); expected at least ${minInstances}` });
      checks.push({ ...check, result: 'fail' });
      continue;
    }
    const signatures = new Set(instances.map((i) => i.signature));
    if (signatures.size > 1) {
      issues.push({ component: name, issue: `instances diverge structurally (${signatures.size} distinct subtree shapes) — pasted copies drifted instead of one component`, shapes: [...signatures].slice(0, 3).map((s) => s.slice(0, 120)) });
      checks.push({ ...check, result: 'fail' });
      continue;
    }
    const tokenKeys = Object.keys(instances[0].tokens);
    const divergent = tokenKeys.filter((key) => new Set(instances.map((i) => i.tokens[key])).size > 1);
    // Content differs between instances by design; shared visual tokens must not.
    if (divergent.length) {
      issues.push({ component: name, issue: `instances diverge in computed tokens: ${divergent.join(', ')}`, sample: divergent.map((key) => ({ [key]: [...new Set(instances.map((i) => i.tokens[key]))].slice(0, 3) })) });
      checks.push({ ...check, result: 'fail' });
      continue;
    }
    checks.push({ ...check, result: 'pass' });
  }
  await browser.close();

  const hasComponents = donorComponents.length > 0 || Object.keys(entries).length > 0;
  const result = !hasComponents ? 'no-repeated-patterns' : (issues.length ? 'fail' : 'pass');
  const report = {
    result,
    viewport,
    min_repeats: minRepeats,
    donor_components_considered: donorComponents.length,
    mapped: Object.keys(entries).length,
    excluded: Object.keys(excluded).length,
    checks,
    issues,
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(`result=${result} mapped=${report.mapped} checks=${checks.length} issues=${issues.length} out=${outPath}`);
  process.exit(result === 'fail' ? 2 : 0);
}
main().catch((err) => { console.error(err.stack || err); process.exit(1); });
