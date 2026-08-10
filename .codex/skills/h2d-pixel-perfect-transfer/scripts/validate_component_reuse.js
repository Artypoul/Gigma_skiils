#!/usr/bin/env node
/* Candidate-side reuse gate: repeated donor patterns must be ONE component.
 *
 * Three layers of proof, because each one alone can be gamed:
 *   1. source: every mapped component names its single definition file, the
 *      file exists and actually defines what the selector matches — N pasted
 *      identical copies have no single definition to point at;
 *   2. instance count: the expected count comes from the DONOR's design-system
 *      report, not from the map author; a different count is legitimate only
 *      as a recorded content-divergence decision (`instances_expected` + reason);
 *   3. render: at the component's own donor viewport, every instance the
 *      selector finds must share one subtree shape and one set of computed
 *      tokens — pasted copies drift the moment anyone edits one.
 *
 *   node scripts/validate_component_reuse.js \
 *     --candidate http://127.0.0.1:5005/ \
 *     --candidate-root . \
 *     --design-system h2d-transfer-output/reports/design_system.json \
 *     --component-map h2d-transfer-output/reports/component_map.json \
 *     --out h2d-transfer-output/reports/component_reuse.json
 *
 * component map format:
 *   {"components": {"work-tag": {
 *       "selector": ".work-tags li",
 *       "donor_signature": "li.WorkTags_Tag[...]",   // exact signature from design_system.json
 *       "definition": "src/components/WorkTag.svelte", // single source of the pattern
 *       "viewport": 1440,                             // optional override of the donor viewport
 *       "instances_expected": 6,                      // optional owner-recorded content divergence
 *       "instances_reason": "Itecho lists 6 services, donor lists 38 tags"
 *     }},
 *    "excluded": {"<signature>": "reason (e.g. capture artifact)"}}
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

/** Words from the selector that the definition file must mention: class names and tags. */
function selectorIdentifiers(selector) {
  const classes = [...selector.matchAll(/\.([A-Za-z0-9_-]+)/g)].map((m) => m[1]);
  if (classes.length) return classes;
  const tags = [...selector.matchAll(/(?:^|[\s>+~])([a-z][a-z0-9-]*)/g)].map((m) => m[1]);
  return tags;
}

function checkDefinition(candidateRoot, entry, name, issues) {
  if (typeof entry.definition !== 'string' || !entry.definition.trim()) {
    issues.push({ component: name, issue: 'component map entry has no "definition" — the single source file that defines this pattern; pasted copies have none to name' });
    return false;
  }
  const definitionPath = path.resolve(candidateRoot, entry.definition);
  if (!definitionPath.startsWith(path.resolve(candidateRoot))) {
    issues.push({ component: name, issue: `definition escapes the candidate root: ${entry.definition}` });
    return false;
  }
  if (!fs.existsSync(definitionPath) || !fs.statSync(definitionPath).isFile()) {
    issues.push({ component: name, issue: `definition file not found: ${entry.definition}` });
    return false;
  }
  const source = fs.readFileSync(definitionPath, 'utf8');
  const identifiers = selectorIdentifiers(entry.selector || '');
  const mentioned = identifiers.some((id) => source.includes(id));
  if (identifiers.length && !mentioned) {
    issues.push({ component: name, issue: `definition ${entry.definition} never mentions ${identifiers.slice(0, 3).join('/')} from the selector — it does not define what the selector matches` });
    return false;
  }
  return true;
}

async function main() {
  const candidate = arg('candidate');
  const candidateRoot = arg('candidate-root', '.');
  const designSystemPath = arg('design-system');
  const mapPath = arg('component-map');
  const outPath = arg('out', 'reports/component_reuse.json');
  const defaultViewport = Number(arg('viewport', '1440'));
  const minRepeats = Number(arg('min-repeats', '3'));
  if (!candidate || !designSystemPath || !mapPath) {
    throw new Error('Usage: --candidate <file|url> --candidate-root <dir> --design-system <file> --component-map <file> --out <file> [--viewport 1440] [--min-repeats 3]');
  }

  const designSystem = readJson(designSystemPath);
  const map = readJson(mapPath);
  const entries = map.components || map;
  const excluded = map.excluded || {};
  const issues = [];
  const checks = [];

  const donorComponents = (designSystem.components || []).filter((c) => (c.count || 0) >= minRepeats);
  const donorBySignature = new Map(donorComponents.map((c) => [c.signature, c]));

  // Coverage: every repeated donor pattern is mapped or explicitly excluded.
  const mappedSignatures = new Set(Object.values(entries).map((e) => e && e.donor_signature).filter(Boolean));
  for (const component of donorComponents) {
    const signature = component.signature;
    if (mappedSignatures.has(signature)) continue;
    const reason = excluded[signature];
    if (typeof reason === 'string' && reason.trim().length >= 10) continue;
    issues.push({
      component: signature.slice(0, 120),
      issue: `repeated donor pattern (x${component.count}) is neither mapped to a candidate component nor excluded with a reason`,
    });
  }

  // Group mapped components by the viewport they exist at: a mobile-only
  // pattern cannot be judged in a desktop DOM state.
  const byViewport = new Map();
  for (const [name, entry] of Object.entries(entries)) {
    if (!entry || typeof entry.selector !== 'string') {
      issues.push({ component: name, issue: 'component map entry has no selector' });
      continue;
    }
    const donor = entry.donor_signature ? donorBySignature.get(entry.donor_signature) : null;
    if (entry.donor_signature && !donor) {
      issues.push({ component: name, issue: `donor_signature not found among the donor's repeated components: ${String(entry.donor_signature).slice(0, 100)}` });
      continue;
    }
    const viewport = Number(entry.viewport || (donor && donor.viewport) || defaultViewport);
    if (!byViewport.has(viewport)) byViewport.set(viewport, []);
    byViewport.get(viewport).push({ name, entry, donor });
  }

  const { launchChromium } = require('./browser');
  const browser = await launchChromium({ executablePath: arg('browser-executable') || undefined });
  const waitMs = Number(arg('wait-ms', '0'));

  for (const [viewport, group] of [...byViewport.entries()].sort((a, b) => b[0] - a[0])) {
    const page = await browser.newPage({ viewport: { width: viewport, height: Number(arg('height', '1400')) }, deviceScaleFactor: 1 });
    await page.goto(toTargetUrl(candidate), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    if (waitMs) await page.waitForTimeout(waitMs);

    for (const { name, entry, donor } of group) {
      const check = { component: name, selector: entry.selector, viewport };
      if (!checkDefinition(candidateRoot, entry, name, issues)) {
        checks.push({ ...check, result: 'fail' });
        continue;
      }

      // The expected count belongs to the donor report, not the map author.
      // Diverging is legitimate only as a recorded owner decision.
      let expected = donor ? donor.count : Number(entry.min_instances || 2);
      let expectation = donor ? `donor count ${donor.count}` : `min_instances ${expected}`;
      if (entry.instances_expected != null) {
        const reason = String(entry.instances_reason || '');
        if (reason.trim().length < 10) {
          issues.push({ component: name, issue: 'instances_expected without a substantive instances_reason is not a recorded decision' });
          checks.push({ ...check, result: 'fail' });
          continue;
        }
        expected = Number(entry.instances_expected);
        expectation = `owner-recorded ${expected} (${reason.trim().slice(0, 80)})`;
      }

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
        checks.push({ ...check, result: 'fail' });
        continue;
      }
      const instances = probe.instances || [];
      check.instances = instances.length;
      check.expected = expected;
      if (instances.length !== expected) {
        issues.push({ component: name, issue: `selector "${entry.selector}" finds ${instances.length} instance(s) at ${viewport}px; expected ${expectation}. A different count is a content divergence — record it via instances_expected + instances_reason after the owner's decision` });
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
    await page.close();
  }
  await browser.close();

  const hasComponents = donorComponents.length > 0 || Object.keys(entries).length > 0;
  const result = !hasComponents ? 'no-repeated-patterns' : (issues.length ? 'fail' : 'pass');
  const report = {
    result,
    min_repeats: minRepeats,
    donor_components_considered: donorComponents.length,
    mapped: Object.keys(entries).length,
    excluded: Object.keys(excluded).length,
    viewports_checked: [...byViewport.keys()].sort((a, b) => b - a),
    checks,
    issues,
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(`result=${result} mapped=${report.mapped} checks=${checks.length} issues=${issues.length} out=${outPath}`);
  process.exit(result === 'fail' ? 2 : 0);
}
main().catch((err) => { console.error(err.stack || err); process.exit(1); });
