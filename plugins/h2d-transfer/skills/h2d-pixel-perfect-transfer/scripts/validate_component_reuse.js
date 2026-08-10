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
const crypto = require('crypto');

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

/** Truncated display signatures can collide; the hash never does. */
function donorHashCollision(donorComponents, component) {
  return donorComponents.some((other) => other !== component && other.signature === component.signature);
}

/**
 * An exclusion is self-serve only for machine-recognizable capture artifacts:
 * elements injected by browser extensions and translators, which no donor
 * authored as page UI. "Any hyphenated tag" would be wrong — donors legitimately
 * ship Web Components like `<product-card>` — so only tags with a known
 * injector prefix qualify. Anything else the agent wants to exclude needs an
 * `approval_ref` into the contract's externally verified approvals — a
 * free-text reason is not a decision.
 */
const CAPTURE_ARTIFACT_TAG_PREFIXES = [
  'ya-tr-',              // Yandex translator spans
  'grammarly-',          // Grammarly injection
  'deepl-',              // DeepL extension
  'immersive-translate', // Immersive Translate extension
  'gt-',                 // Google Translate widgets
  'lingvanex-',
  'mate-translate-',
];
function isCaptureArtifactSignature(signature) {
  const tag = String(signature).split(/[.\[]/)[0].toLowerCase();
  return CAPTURE_ARTIFACT_TAG_PREFIXES.some((prefix) => tag.startsWith(prefix));
}

/** Identifiers from the selector that the definition file must mention: classes, tags, attribute values. */
function selectorIdentifiers(selector) {
  const classes = [...selector.matchAll(/\.([A-Za-z0-9_-]+)/g)].map((m) => m[1]);
  const attrValues = [...selector.matchAll(/\[[^\]=]+=\s*["']?([A-Za-z0-9_-]+)["']?\s*\]/g)].map((m) => m[1]);
  const ids = [...selector.matchAll(/#([A-Za-z0-9_-]+)/g)].map((m) => m[1]);
  const found = [...classes, ...attrValues, ...ids];
  if (found.length) return found;
  return [...selector.matchAll(/(?:^|[\s>+~])([a-z][a-z0-9-]*)/g)].map((m) => m[1]);
}

function checkDefinition(candidateRoot, entry, name, issues) {
  if (typeof entry.definition !== 'string' || !entry.definition.trim()) {
    issues.push({ component: name, issue: 'component map entry has no "definition" — the single source file that defines this pattern; pasted copies have none to name' });
    return false;
  }
  const definitionPath = path.resolve(candidateRoot, entry.definition);
  // Separator-aware containment: a raw prefix check would accept a sibling
  // like /tmp/site-backup next to /tmp/site.
  const relative = path.relative(path.resolve(candidateRoot), definitionPath);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    issues.push({ component: name, issue: `definition escapes the candidate root: ${entry.definition}` });
    return false;
  }
  if (!fs.existsSync(definitionPath) || !fs.statSync(definitionPath).isFile()) {
    issues.push({ component: name, issue: `definition file not found: ${entry.definition}` });
    return false;
  }
  const source = fs.readFileSync(definitionPath, 'utf8');
  const identifiers = selectorIdentifiers(entry.selector || '');
  if (!identifiers.length) {
    // With nothing to check the source layer would silently pass any file.
    issues.push({ component: name, issue: `selector "${entry.selector}" has no verifiable identifiers (class, id, tag or attribute value) — use a selector the definition file can be checked against` });
    return false;
  }
  const mentioned = identifiers.some((id) => source.includes(id));
  if (!mentioned) {
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
  if (!candidate || !designSystemPath || !mapPath) {
    throw new Error('Usage: --candidate <file|url> --candidate-root <dir> --design-system <file> --component-map <file> --out <file> [--viewport 1440]');
  }

  const designSystem = readJson(designSystemPath);
  const map = readJson(mapPath);
  // Flat form has no `components` wrapper; `excluded` there is metadata, not
  // a component entry, or a valid exclusion-only map could never pass.
  const { excluded: excludedMeta, components: wrappedComponents, ...flat } = map;
  const entries = wrappedComponents || flat;
  const excluded = excludedMeta || {};
  const issues = [];
  const checks = [];
  const minRepeats = Number(designSystem.min_component_repeats);
  if (minRepeats !== 2) {
    issues.push({ issue: `design-system component inventory must use the bundled repeat floor 2; got ${designSystem.min_component_repeats}` });
  }

  const donorComponents = (designSystem.components || []).filter((c) => (c.count || 0) >= minRepeats);
  const donorBySignature = new Map(donorComponents.map((c) => [c.signature, c]));
  const donorByHash = new Map(donorComponents.filter((c) => c.signature_sha256).map((c) => [c.signature_sha256, c]));

  // Coverage: every repeated donor pattern is mapped or explicitly excluded.
  // Hashes are authoritative when present — displayed signatures are truncated
  // and two large patterns may share a 240-char prefix.
  const mappedSignatures = new Set(Object.values(entries).map((e) => e && e.donor_signature).filter(Boolean));
  const mappedHashes = new Set(Object.values(entries).map((e) => e && e.donor_signature_sha256).filter(Boolean));
  let mappedCount = 0;
  let realExcludedCount = 0;
  for (const component of donorComponents) {
    const covered = component.signature_sha256
      ? mappedHashes.has(component.signature_sha256) || (mappedSignatures.has(component.signature) && !donorHashCollision(donorComponents, component))
      : mappedSignatures.has(component.signature);
    if (covered) { mappedCount += 1; continue; }
    const exclusion = excluded[component.signature_sha256] || excluded[component.signature];
    if (exclusion != null) {
      const reason = typeof exclusion === 'string' ? exclusion : String(exclusion.reason || '');
      const approvalRef = typeof exclusion === 'object' && exclusion ? exclusion.approval_ref : null;
      if (reason.trim().length < 10) {
        issues.push({ component: component.signature.slice(0, 120), issue: 'exclusion has no substantive reason' });
        continue;
      }
      if (isCaptureArtifactSignature(component.signature)) continue;
      if (approvalRef) { realExcludedCount += 1; continue; }
      // A donor-authored pattern cannot be waved off with free text.
      issues.push({
        component: component.signature.slice(0, 120),
        issue: 'excluding a donor-authored repeated pattern needs an approval_ref into the contract approvals — a free-text reason is a self-approval',
      });
      continue;
    }
    issues.push({
      component: component.signature.slice(0, 120),
      signature_sha256: component.signature_sha256,
      issue: `repeated donor pattern (x${component.count}) is neither mapped to a candidate component nor excluded with a reason`,
    });
  }
  // A map that excludes everything and maps nothing is not a reuse proof.
  const donorAuthored = donorComponents.filter((c) => !isCaptureArtifactSignature(c.signature));
  if (donorAuthored.length && mappedCount === 0) {
    issues.push({ issue: `all ${donorAuthored.length} donor-authored repeated pattern(s) are excluded or unmapped; a transfer with zero reused components cannot pass the reuse gate` });
  }

  // Group mapped components by the viewport they exist at: a mobile-only
  // pattern cannot be judged in a desktop DOM state.
  const byViewport = new Map();
  for (const [name, entry] of Object.entries(entries)) {
    if (!entry || typeof entry.selector !== 'string') {
      issues.push({ component: name, issue: 'component map entry has no selector' });
      continue;
    }
    const donor = entry.donor_signature_sha256
      ? donorByHash.get(entry.donor_signature_sha256)
      : (entry.donor_signature ? donorBySignature.get(entry.donor_signature) : null);
    if ((entry.donor_signature || entry.donor_signature_sha256) && !donor) {
      issues.push({ component: name, issue: `donor signature not found among the donor's repeated components: ${String(entry.donor_signature_sha256 || entry.donor_signature).slice(0, 100)}` });
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
        // A count override is a content decision: it needs the owner's
        // approval reference, not just prose the map author wrote alone.
        if (reason.trim().length < 10 || !entry.approval_ref) {
          issues.push({ component: name, issue: 'instances_expected needs both a substantive instances_reason and an approval_ref into the contract approvals; a self-authored override is not the owner\'s decision' });
          checks.push({ ...check, result: 'fail' });
          continue;
        }
        expected = Number(entry.instances_expected);
        expectation = `owner-approved ${expected} (${reason.trim().slice(0, 60)}; approval ${entry.approval_ref})`;
        check.approval_ref = entry.approval_ref;
      }

      const probe = await page.evaluate(({ selector, skipProps }) => {
        const signatureOf = (el, depth) => {
          const classes = [...el.classList].sort().join('.');
          let sig = el.tagName.toLowerCase() + (classes ? '.' + classes : '');
          if (depth > 0) {
            const kids = [...el.children].map((child) => signatureOf(child, depth - 1));
            if (kids.length) sig += '[' + kids.join(',') + ']';
          }
          return sig;
        };
        const structureOf = (el, depth) => {
          let sig = el.tagName.toLowerCase();
          if (depth > 0) {
            const kids = [...el.children].map((child) => structureOf(child, depth - 1));
            if (kids.length) sig += '[' + kids.join(',') + ']';
          }
          return sig;
        };
        // Tokens are profiled over the SUBTREE, not just the root: a pasted
        // copy that restyles a nested heading keeps the root's tokens intact,
        // and a root-only probe would never see the drift.
        const PROPS = ['fontFamily', 'fontSize', 'fontWeight', 'color', 'backgroundColor', 'borderTopLeftRadius', 'padding'];
        const tokensOf = (el, depth) => {
          const cs = getComputedStyle(el);
          const own = {};
          for (const prop of PROPS) {
            if (!skipProps.includes(prop)) own[prop] = cs[prop];
          }
          const node = { tokens: own };
          if (depth > 0) {
            const kids = [...el.children].map((child) => tokensOf(child, depth - 1));
            if (kids.length) node.children = kids;
          }
          return node;
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
              structure_signature: structureOf(el, 2),
              tokens: { fontFamily: cs.fontFamily, fontSize: cs.fontSize, fontWeight: cs.fontWeight, color: cs.color, backgroundColor: cs.backgroundColor, borderRadius: cs.borderTopLeftRadius, padding: cs.padding },
              subtree_profile: JSON.stringify(tokensOf(el, 2)),
            };
          }),
        };
      }, { selector: entry.selector, skipProps: Array.isArray(entry.token_variants) ? entry.token_variants : [] });

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
      // The mapped nodes must BE the donor pattern, not merely be identical to
      // each other. Classes may change, but the class-agnostic DOM shape at the
      // same depth must match the source-derived structure signature.
      if (donor) {
        const expectedStructure = String(donor.structure_signature || '');
        const candidateStructures = new Set(instances.map((instance) => instance.structure_signature));
        if (!expectedStructure || candidateStructures.size !== 1 || !candidateStructures.has(expectedStructure)) {
          issues.push({
            component: name,
            issue: 'mapped selector structure differs from the donor component — the map points at an unrelated repeated candidate pattern',
            expected_structure: expectedStructure || '(missing from design-system report)',
            candidate_structures: [...candidateStructures].slice(0, 3),
          });
          checks.push({ ...check, result: 'fail' });
          continue;
        }
      }
      // Content differs between instances by design; shared visual tokens must
      // not — unless the donor itself varies them intentionally (nth-child
      // theming, parent context), which the map records as token_variants.
      let allowedVariants = [];
      if (Array.isArray(entry.token_variants) && entry.token_variants.length) {
        if (String(entry.variant_reason || '').trim().length < 10) {
          issues.push({ component: name, issue: 'token_variants without a substantive variant_reason is not a recorded donor variant' });
          checks.push({ ...check, result: 'fail' });
          continue;
        }
        allowedVariants = entry.token_variants;
      }
      const tokenKeys = Object.keys(instances[0].tokens).filter((key) => !allowedVariants.includes(key));
      const divergent = tokenKeys.filter((key) => new Set(instances.map((i) => i.tokens[key])).size > 1);
      if (divergent.length) {
        issues.push({ component: name, issue: `instances diverge in computed tokens: ${divergent.join(', ')}`, sample: divergent.map((key) => ({ [key]: [...new Set(instances.map((i) => i.tokens[key]))].slice(0, 3) })) });
        checks.push({ ...check, result: 'fail' });
        continue;
      }
      // Same root is not enough: the subtree profile (variant props already
      // excluded inside the page probe) must agree instance to instance.
      const subtreeProfiles = new Set(instances.map((i) => i.subtree_profile));
      if (subtreeProfiles.size > 1) {
        issues.push({ component: name, issue: `instances diverge in nested computed tokens (${subtreeProfiles.size} distinct subtree style profiles) — a pasted copy restyled a descendant` });
        checks.push({ ...check, result: 'fail' });
        continue;
      }
      checks.push({ ...check, result: 'pass', token_variants: allowedVariants.length ? allowedVariants : undefined });
    }
    await page.close();
  }
  await browser.close();

  const hasComponents = donorComponents.length > 0 || Object.keys(entries).length > 0;
  const result = issues.length ? 'fail' : (!hasComponents ? 'no-repeated-patterns' : 'pass');
  const report = {
    result,
    generator_sha256: crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),
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
