#!/usr/bin/env node
/* Build applicable action sequences; do not invent state transitions for every control. */
const fs = require('fs'); const path = require('path');
function arg(name, fallback = null) { const i = process.argv.indexOf(`--${name}`); return i >= 0 ? process.argv[i + 1] : fallback; }
function action(kind, selector, value = null) { return { action: kind, selector, value }; }
function main() {
  const inventoryPath = arg('inventory'); const out = arg('out', 'reports/interaction_matrix.json');
  if (!inventoryPath) throw new Error('Usage: --inventory behavior_inventory.json --out interaction_matrix.json');
  const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));
  if (inventory.result === 'fail' || inventory.coverage_complete === false) throw new Error('Cannot generate a final matrix from incomplete behavior inventory');
  const interactions = [];
  for (const component of inventory.components || []) {
    const base = { component_id: component.component_id, selector: component.selector, frame_path: component.frame_path || 'main', criticality: component.criticality || 'critical' };
    const push = (suffix, sequence, expectedTransition = false, expected = null) => interactions.push({ ...base, interaction_id: `${component.component_id}:${suffix}`, sequence, expected_transition: expectedTransition, expected });
    const events = new Set(component.listeners || []);
    if (component.kind === 'disclosure') {
      push('open-click', [action('click', component.selector)], true, 'opened');
      push('close-escape', [action('click', component.selector), action('escape', component.selector)], true, 'closed');
      push('close-outside', [action('click', component.selector), action('outside-click', component.selector)], true, 'closed');
      push('keyboard-enter', [action('focus', component.selector), action('keyboard-enter', component.selector)], true, 'toggled');
      push('keyboard-space', [action('focus', component.selector), action('keyboard-space', component.selector)], true, 'toggled');
    } else if (component.kind === 'input') {
      push('input', [action('focus', component.selector), action('input', component.selector, 'h2d-probe')], true, 'value-changed');
      push('validation', [action('focus', component.selector), action('input', component.selector, ''), action('blur', component.selector)], false, 'validation-observed');
    } else if (component.kind === 'select') {
      push('select', [action('select-next', component.selector)], true, 'value-changed');
    } else if (component.kind === 'form') {
      push('submit-intent', [action('submit-intent', component.selector)], true, 'submission-intent');
    } else if (component.kind === 'link') {
      push('navigation-intent', [action('click', component.selector)], true, 'navigation-intent');
    } else if (component.kind === 'button' || events.has('click')) {
      push('click', [action('click', component.selector)], events.has('click'), events.has('click') ? 'listener-outcome' : null);
    }
    if (events.has('pointerdown') || events.has('mousedown') || events.has('dragstart')) {
      push('pointer-drag', [action('pointer-drag', component.selector, { dx: 80, dy: 0, button: 'left', pointerType: 'mouse' })], true, 'pointer-outcome');
    }
    if (events.has('keydown') || component.kind === 'shadow-control') {
      push('tab-sequence', [action('focus', component.selector), action('tab', component.selector), action('shift-tab', component.selector)], false, 'focus-order');
    }
  }
  const report = { result: interactions.length ? 'pass' : 'not-tested', coverage_complete: true, interactions };
  fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(report, null, 2));
  console.log(`interactions=${interactions.length} out=${out}`);
}
try { main(); } catch (error) { console.error(error.stack || error); process.exit(1); }
