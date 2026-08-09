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
const path = require('path');
const crypto = require('crypto');

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

function resolveChromium(projectRoot = null) {
  // An installed skill usually lives outside the project it is transferring
  // into, so resolving only relative to this file would miss the project's own
  // playwright — the very fallback the docs promise. Try the project first.
  const { createRequire } = require('module');
  const root = projectRoot ? path.resolve(projectRoot) : process.cwd();
  const projectRequire = createRequire(path.join(root, 'noop.js'));
  for (const name of ['playwright', 'playwright-core']) {
    for (const load of [(n) => projectRequire(n), (n) => require(n)]) {
      try {
        return { chromium: load(name).chromium, pkg: name };
      } catch (err) {
        if (err.code !== 'MODULE_NOT_FOUND') throw err;
      }
    }
  }
  throw new Error(
    'Neither "playwright" nor "playwright-core" can be resolved from this skill or from ' + root + '.\n' +
    'Install one of them, e.g.:  npm install playwright && npx playwright install chromium\n' +
    'Then re-run scripts/preflight_env.py before claiming any gate result.'
  );
}

/** `--browser-executable <path>` works in every bundled gate, not just one. */
function executableFromArgv(argv = process.argv) {
  const i = argv.indexOf('--browser-executable');
  return i >= 0 && argv[i + 1] ? argv[i + 1] : null;
}

/** Launch headless Chromium; `executablePath` only matters for playwright-core. */
async function launchChromium(options = {}) {
  const projectRoot = options.projectRoot || null;
  const { chromium, pkg } = resolveChromium(projectRoot);
  const deterministicGraphicsArgs = ['--use-angle=swiftshader', '--use-gl=angle'];
  const launchOptions = { headless: true, ...options };
  launchOptions.args = [...deterministicGraphicsArgs, ...(options.args || []).filter(value => !deterministicGraphicsArgs.includes(value))];
  delete launchOptions.projectRoot;
  // An explicit override wins whichever package resolved: the full playwright
  // can also be present without its downloaded Chromium, and ignoring
  // CHROME_PATH there would fail with a browser sitting right on disk.
  if (!launchOptions.executablePath) {
    launchOptions.executablePath = executableFromArgv() || process.env.CHROME_PATH || undefined;
  }
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

function contextOptions(profile = {}, viewport = {}) {
  const width = Number(viewport.width);
  const height = Number(viewport.height);
  if (!Number.isInteger(width) || width <= 0 || !Number.isInteger(height) || height <= 0) {
    throw new Error('contextOptions requires positive integer viewport width and height');
  }
  const result = {
    viewport: { width, height },
    deviceScaleFactor: Number(profile.device_scale_factor || profile.deviceScaleFactor || 1),
    isMobile: Boolean(profile.is_mobile ?? profile.isMobile),
    hasTouch: Boolean(profile.has_touch ?? profile.hasTouch),
    locale: profile.locale || 'en-US',
    timezoneId: profile.timezone || profile.timezoneId || 'UTC',
    reducedMotion: profile.reduced_motion || profile.reducedMotion || 'reduce',
  };
  if (profile.user_agent || profile.userAgent) result.userAgent = profile.user_agent || profile.userAgent;
  if (profile.color_scheme || profile.colorScheme) result.colorScheme = profile.color_scheme || profile.colorScheme;
  if (profile.screen && Number(profile.screen.width) > 0 && Number(profile.screen.height) > 0) {
    result.screen = { width: Number(profile.screen.width), height: Number(profile.screen.height) };
  }
  return result;
}

function canonicalUrlHash(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex');
}

function redactUrl(value) {
  try {
    const parsed = new URL(value);
    parsed.username = '';
    parsed.password = '';
    const sensitive = /token|key|secret|signature|sig|session|auth|jwt|code|password/i;
    for (const key of [...parsed.searchParams.keys()]) {
      if (sensitive.test(key)) parsed.searchParams.set(key, '[redacted]');
    }
    return { safe_url: parsed.toString(), canonical_url_sha256: canonicalUrlHash(value) };
  } catch {
    return { safe_url: '[non-url]', canonical_url_sha256: canonicalUrlHash(value) };
  }
}

function requestKey(method, url) {
  return `${String(method || 'GET').toUpperCase()} ${canonicalUrlHash(url)}`;
}

function isExpectedSandboxConsole(message) {
  const text = typeof message === 'string' ? message : (message && typeof message.text === 'function' ? message.text() : String(message || ''));
  return /Failed to load resource: net::ERR_(FAILED|BLOCKED_BY_CLIENT|ABORTED)/i.test(text);
}

async function installNetworkSandbox(context, rules = []) {
  const allowed = new Set((rules || []).map((rule) => requestKey(rule.method, rule.url)));
  const events = [];
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = request.url();
    const protocol = (() => { try { return new URL(url).protocol; } catch { return ''; } })();
    const local = ['file:', 'data:', 'blob:', 'about:'].includes(protocol);
    const key = requestKey(request.method(), url);
    const redacted = redactUrl(url);
    if (local || allowed.has(key)) {
      events.push({ kind: 'request', action: 'allowed', method: request.method(), ...redacted });
      return route.continue();
    }
    events.push({ kind: 'request', action: 'blocked', method: request.method(), resource_type: request.resourceType(), ...redacted });
    return route.abort('blockedbyclient');
  });
  if (typeof context.routeWebSocket === 'function') {
    await context.routeWebSocket(/.*/, (ws) => {
      events.push({ kind: 'websocket', action: 'blocked', ...redactUrl(ws.url()) });
      ws.close();
    });
  }
  await context.addInitScript(() => {
    const blocked = (kind, url) => {
      window.__h2dBlockedTransports = window.__h2dBlockedTransports || [];
      window.__h2dBlockedTransports.push({ kind, url: String(url || '') });
    };
    const NativeWebSocket = window.WebSocket;
    if (NativeWebSocket) window.WebSocket = function(url){ blocked('websocket', url); throw new DOMException('Blocked by H2D evidence sandbox', 'SecurityError'); };
    const NativeEventSource = window.EventSource;
    if (NativeEventSource) window.EventSource = function(url){ blocked('eventsource', url); throw new DOMException('Blocked by H2D evidence sandbox', 'SecurityError'); };
    if (navigator.sendBeacon) navigator.sendBeacon = function(url){ blocked('beacon', url); return false; };
  });
  return events;
}

async function installRuntimeInstrumentation(context) {
  await context.addInitScript(() => {
    window.__h2dRuntime = { listeners: [], global_listeners: [], canvas_contexts: [], property_handlers: [], timers: [], media_queries: [] };
    const delegatedTypes = new Set(['click','dblclick','pointerdown','pointerup','pointermove','mousedown','mouseup','mousemove','touchstart','touchend','keydown','keyup','input','change','submit','dragstart','dragend','drop']);
    const originalAdd = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
      try {
        if (this instanceof Element) {
          const current = new Set(String(this.getAttribute('data-h2d-listener-events') || '').split(',').filter(Boolean));
          current.add(String(type));
          this.setAttribute('data-h2d-listener-events', [...current].sort().join(','));
        } else if ((this === window || this === document) && delegatedTypes.has(String(type))) {
          const target = this === window ? 'window' : 'document';
          const key = `${target}:${String(type)}`;
          if (!window.__h2dRuntime.global_listeners.some(row => row.key === key)) window.__h2dRuntime.global_listeners.push({ key, target, type: String(type) });
        }
      } catch {}
      return originalAdd.call(this, type, listener, options);
    };
    const originalSetTimeout = window.setTimeout.bind(window);
    const originalSetInterval = window.setInterval.bind(window);
    window.setTimeout = function(handler, delay, ...args) {
      window.__h2dRuntime.timers.push({ kind: 'timeout', delay_ms: Number(delay || 0) });
      return originalSetTimeout(handler, delay, ...args);
    };
    window.setInterval = function(handler, delay, ...args) {
      window.__h2dRuntime.timers.push({ kind: 'interval', delay_ms: Number(delay || 0) });
      return originalSetInterval(handler, delay, ...args);
    };
    if (window.matchMedia) {
      const originalMatchMedia = window.matchMedia.bind(window);
      window.matchMedia = function(query) {
        const value = String(query);
        if (!window.__h2dRuntime.media_queries.includes(value)) window.__h2dRuntime.media_queries.push(value);
        return originalMatchMedia(value);
      };
    }
    if (window.HTMLCanvasElement) {
      const originalGetContext = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const result = originalGetContext.call(this, type, ...args);
        try {
          this.setAttribute('data-h2d-canvas-context', String(type));
          window.__h2dRuntime.canvas_contexts.push({ type: String(type) });
        } catch {}
        return result;
      };
    }
  });
}

function stableSelectorScript() {
  return `(el) => {
    if (!el || el.nodeType !== 1) return null;
    if (el.id) return '#' + CSS.escape(el.id);
    const marker = el.getAttribute('data-h2d-path') || el.getAttribute('data-behavior-id');
    if (marker) {
      const name = el.hasAttribute('data-h2d-path') ? 'data-h2d-path' : 'data-behavior-id';
      return '[' + name + '=' + JSON.stringify(marker) + ']';
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.documentElement) {
      let part = node.tagName.toLowerCase();
      const siblings = node.parentElement ? [...node.parentElement.children].filter(x => x.tagName === node.tagName) : [];
      if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
      parts.unshift(part);
      node = node.parentElement;
    }
    return 'html > ' + parts.join(' > ');
  }`;
}

async function environmentFingerprint(browser, context, page) {
  const browserVersion = browser.version();
  const values = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    const debug = gl && gl.getExtension('WEBGL_debug_renderer_info');
    const graphics = gl ? {
      vendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
      renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      version: gl.getParameter(gl.VERSION),
      shading_language_version: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
    } : { vendor: null, renderer: null, version: null, shading_language_version: null };
    return {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      dpr: devicePixelRatio,
      graphics,
    };
  });
  return { browser: 'chromium', browser_version: browserVersion, node: process.version, os: `${process.platform}-${process.arch}`, graphics_launch_flags: ['--use-angle=swiftshader', '--use-gl=angle'], ...values };
}

module.exports = {
  resolveChromium, launchChromium, findLocalChrome, executableFromArgv,
  contextOptions, installNetworkSandbox, installRuntimeInstrumentation,
  stableSelectorScript, environmentFingerprint, redactUrl, canonicalUrlHash,
  isExpectedSandboxConsole,
};
