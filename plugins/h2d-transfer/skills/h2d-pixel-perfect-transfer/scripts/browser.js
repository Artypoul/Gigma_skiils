/**
 * Shared Chromium launcher for the bundled gates.
 *
 * The gates must be runnable from inside a real project, not only from a fully
 * provisioned skill checkout. So the driver is resolved in order:
 *   1. `playwright` (ships its own browsers);
 *   2. `playwright-core` (very common in projects, ships no browser) plus an
 *      installed Chrome/Edge — override with CHROME_PATH or --browser-executable.
 *
 * Failing to find either is an environment blocker, never a gate verdict:
 * the message says what to install instead of letting a script die on a bare
 * MODULE_NOT_FOUND stack.
 */
const fs = require('fs');

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser'
].filter(Boolean);

function findLocalChrome() {
  return CHROME_CANDIDATES.find((p) => {
    try { return fs.existsSync(p); } catch { return false; }
  }) || null;
}

function resolveChromium() {
  for (const name of ['playwright', 'playwright-core']) {
    try {
      return { chromium: require(name).chromium, pkg: name };
    } catch (err) {
      if (err.code !== 'MODULE_NOT_FOUND' || !String(err.message).includes(name)) throw err;
    }
  }
  throw new Error(
    'Neither "playwright" nor "playwright-core" can be resolved.\n' +
    'Install one of them, e.g.:  npm install playwright && npx playwright install chromium\n' +
    'Then re-run scripts/preflight_env.py before claiming any gate result.'
  );
}

/** Launch headless Chromium; `executablePath` only matters for playwright-core. */
async function launchChromium(options = {}) {
  const { chromium, pkg } = resolveChromium();
  const launchOptions = { headless: true, ...options };
  if (!launchOptions.executablePath && pkg === 'playwright-core') {
    const local = findLocalChrome();
    if (!local) {
      throw new Error(
        '"playwright-core" ships no browser and no local Chrome/Edge was found.\n' +
        'Install Chrome/Edge, set CHROME_PATH, or install the full "playwright" package.'
      );
    }
    launchOptions.executablePath = local;
  }
  return chromium.launch(launchOptions);
}

module.exports = { resolveChromium, launchChromium, findLocalChrome };
