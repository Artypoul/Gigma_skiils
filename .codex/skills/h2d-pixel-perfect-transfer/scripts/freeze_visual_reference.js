#!/usr/bin/env node
/* Capture an immutable, network-sandboxed visual reference across an explicit matrix. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { fileURLToPath } = require('url');
const {
  launchChromium, contextOptions, installNetworkSandbox,
  installRuntimeInstrumentation, environmentFingerprint, isExpectedSandboxConsole,
} = require('./browser');

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}
function sha(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }
function toUrl(value) {
  if (/^file:/.test(value)) return value;
  if (/^https?:\/\//.test(value)) throw new Error('Live URL freeze is intentionally unsupported here; create a pinned offline runnable snapshot first.');
  return 'file://' + path.resolve(value).replace(/\\/g, '/');
}
function loadJson(value, label) {
  if (!value) throw new Error(`${label} is required`);
  return JSON.parse(fs.readFileSync(path.resolve(value), 'utf8'));
}

async function main() {
  const donor = arg('donor');
  const matrix = loadJson(arg('matrix'), '--matrix');
  const profiles = loadJson(arg('profiles'), '--profiles');
  const outDir = path.resolve(arg('out-dir', 'h2d-reference'));
  const donorPath = path.resolve(donor || '');
  const donorRoot = path.resolve(arg('donor-root') || path.dirname(donorPath));
  if (!donor || !fs.statSync(donorPath).isFile()) throw new Error('--donor must be a content-addressable local runnable entry file');
  if (path.relative(donorRoot, donorPath).startsWith('..') || path.isAbsolute(path.relative(donorRoot, donorPath))) throw new Error('--donor must be inside --donor-root');
  if (!Array.isArray(matrix) || !matrix.length || !Array.isArray(profiles) || !profiles.length) throw new Error('matrix and profiles must be non-empty arrays');
  const shotsDir = path.join(outDir, 'screenshots');
  fs.mkdirSync(shotsDir, { recursive: true });
  const artifacts = [];
  const rows = [];
  const environmentByProfile = {};
  const donorSnapshots = new Map();
  const recordDonorFile = file => {
    const bytes = fs.readFileSync(file);
    const snapshot = { sha256: sha(bytes), size: bytes.length };
    const previous = donorSnapshots.get(file);
    if (previous && (previous.sha256 !== snapshot.sha256 || previous.size !== snapshot.size)) throw new Error(`donor resource changed during visual freeze: ${file}`);
    donorSnapshots.set(file, snapshot);
  };
  recordDonorFile(donorPath);
  for (const profile of profiles) {
    const browser = await launchChromium({ headless: profile.headless !== false, projectRoot: arg('project-root') || process.cwd() });
    try {
      for (const viewport of matrix) {
        const context = await browser.newContext(contextOptions(profile, viewport));
        const network = await installNetworkSandbox(context, []);
        await installRuntimeInstrumentation(context);
        const page = await context.newPage();
        const runtimeErrors = [];
        page.on('pageerror', error => runtimeErrors.push({ type: 'pageerror', message: String(error.message || error).slice(0, 500) }));
        page.on('console', message => { if (message.type() === 'error' && !isExpectedSandboxConsole(message)) runtimeErrors.push({ type: 'console-error', message: message.text().slice(0, 500) }); });
        await page.goto(toUrl(donorPath), { waitUntil: 'networkidle' });
        await page.waitForTimeout(Number(arg('settle-ms', '250')));
        const key = `${viewport.width}x${viewport.height}@${profile.id}`;
        const filename = `reference_${key.replace(/[^a-z0-9_.-]/gi, '_')}.png`;
        const absolute = path.join(shotsDir, filename);
        const buffer = await page.screenshot({ path: absolute, fullPage: true });
        const env = await environmentFingerprint(browser, context, page);
        const runtimeTransports = await page.evaluate(() => window.__h2dBlockedTransports || []);
        const fingerprint = sha(Buffer.from(JSON.stringify(env)));
        if (environmentByProfile[profile.id] && environmentByProfile[profile.id] !== fingerprint) throw new Error(`render environment changed within profile ${profile.id} at ${key}`);
        environmentByProfile[profile.id] = fingerprint;
        for (const event of network.filter(row => row.action === 'allowed')) {
          let parsed;
          try { parsed = new URL(event.safe_url); } catch { continue; }
          if (parsed.protocol !== 'file:') continue;
          const resource = path.resolve(fileURLToPath(parsed));
          const relative = path.relative(donorRoot, resource);
          if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error(`donor resource escapes --donor-root: ${resource}`);
          if (!fs.statSync(resource).isFile()) throw new Error(`donor resource is not a file: ${resource}`);
          recordDonorFile(resource);
        }
        const rel = path.relative(outDir, absolute).replace(/\\/g, '/');
        artifacts.push({ path: rel, sha256: sha(buffer), size: buffer.length, kind: 'visual-reference', matrix_key: key });
        rows.push({ matrix_key: key, screenshot: rel, sha256: sha(buffer), environment: env, environment_sha256: fingerprint, blocked_requests: network.filter(x => x.action === 'blocked').length, blocked_transports: runtimeTransports.length, runtime_errors: runtimeErrors });
        await context.close();
      }
    } finally {
      await browser.close();
    }
  }
  for (const file of donorSnapshots.keys()) recordDonorFile(file);
  const donorClosure = [...donorSnapshots].map(([file, snapshot]) => ({
    path: path.relative(donorRoot, file).replace(/\\/g, '/'),
    sha256: snapshot.sha256,
    size: snapshot.size,
  })).sort((a, b) => a.path.localeCompare(b.path));
  const donorIdentity = `sha256:${sha(Buffer.from(JSON.stringify(donorClosure)))}`;
  const result = rows.some(row => row.runtime_errors.length) ? 'fail' : 'pass';
  const manifest = { schema_version: '2.0', result, donor_identity: donorIdentity, donor_closure: donorClosure, environment_by_profile: environmentByProfile, environment_sha256: sha(Buffer.from(JSON.stringify(environmentByProfile))), matrix_keys: rows.map(row => row.matrix_key).sort(), rows, artifacts };
  fs.writeFileSync(path.join(outDir, 'visual_reference_manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(`result=${result} donor_identity=${donorIdentity} matrix=${rows.length}`);
  if (result !== 'pass') process.exitCode = 2;
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
