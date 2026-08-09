/**
 * In-page probe: is the declared primary family the one that actually paints?
 *
 * `document.fonts.check()` cannot answer this — it returns true for families
 * that do not exist, because the fallback can still render the text. So the
 * probe measures instead: render the sample with `"Family", <generic>` and with
 * `<generic>` alone. Identical widths against every generic mean the family was
 * never applied and something else is painting.
 *
 * Exported as source because it runs in the page, not in Node.
 */
const FONT_PROBE_SOURCE = `
window.__h2dFontUsed = function (primary, weight, size, style, text) {
  if (!primary) return null;
  var generic = ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui', 'ui-sans-serif', 'ui-serif', 'ui-monospace'];
  if (generic.indexOf(primary.toLowerCase()) >= 0) return true;
  var sample = String(text || '').trim().slice(0, 60) || 'Ag';
  function measure(family) {
    var span = document.createElement('span');
    span.style.cssText = 'position:absolute;left:-9999px;top:-9999px;white-space:nowrap;visibility:hidden';
    span.style.fontFamily = family;
    span.style.fontWeight = weight || 'normal';
    span.style.fontSize = size || '16px';
    span.style.fontStyle = style || 'normal';
    span.textContent = sample;
    document.body.appendChild(span);
    var w = span.getBoundingClientRect().width;
    span.parentNode.removeChild(span);
    return w;
  }
  var quoted = '"' + primary.replace(/"/g, '') + '"';
  for (var i = 0; i < 3; i++) {
    var ref = generic[i];
    if (Math.abs(measure(quoted + ', ' + ref) - measure(ref)) > 0.5) return true;
  }
  return false;
};
`;

module.exports = { FONT_PROBE_SOURCE };
