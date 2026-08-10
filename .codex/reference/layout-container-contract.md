# Layout, container and design-system contract

Use this contract for both H2D and dev-mode transfers. The source, not the candidate, defines the system.

## Fixed order

1. Freeze or inspect the independent source.
2. Measure fonts and typography roles.
3. Inventory recurring tokens, containers, layout mechanisms and components.
4. Map source responsibilities to candidate tokens, selectors and component definitions.
5. Implement outside-in: shared system → page/container chain → components → block content.
6. Validate every responsive state after the last change.

A minimal isolated typography probe may run before layout implementation. It cannot attest block geometry.

## Complete layout inventory

For every distinct source state, include all nodes that own:

- viewport/page/section/content containment;
- width, max/min constraints and gutters;
- flex/grid flow, alignment, wrapping and track behavior;
- positioning/containing blocks and stacking;
- overflow, clipping and aspect ratio;
- responsive visibility, order or alternate structure.

A map containing only the section root, headline and final media/card is incomplete. Preserve the full ancestor chain even when only one block is in scope; mark context-only ancestors explicitly instead of dropping them.

Required mapping fields:

```text
viewport/state | source path/selector | role | parent source path |
source constraints | candidate selector/component | candidate responsibility |
implementation-required or context-only
```

## Design-system inventory

Record recurring source values before block code:

- palette and semantic usage;
- typography roles and metrics;
- spacing, radii, borders and shadows;
- container widths, gutters and breakpoints;
- icon rules and asset roles;
- every UI pattern repeated at least twice and its states.

Implement recurring values in one token/theme layer. Implement each repeated pattern once and instantiate it with content. A block-local literal or copied component is acceptable only when the source value/pattern is genuinely unique and the inventory says so.

## Responsive evidence

- Derive breakpoints from source CSS/runtime evidence or decoded H2D classification, never filenames or common device widths.
- Capture every distinct state, actual boundaries and adjacent probes when the route supports them.
- Do not infer mobile rules by shrinking desktop.
- Re-check typography, container ownership, component variants and layout mechanisms in every state.

## Mapping integrity

- Create source-to-candidate maps before production block layout.
- One candidate element cannot silently stand in for several source layout nodes.
- A clean implementation may combine technical wrappers only when the map names the combined responsibilities and the proof shows the same responsive constraints.
- Keep maps current when candidate structure changes.

## No compensation

Do not repair the child when the parent contract is wrong. Reject spacer elements, unexplained fixed heights, fractional transforms, per-viewport magic offsets, typography fitting, duplicated token literals and pasted component variants used to hit a screenshot.

## Independent proof

Prepare the donor/reference before candidate implementation. Do not build it from candidate markup, CSS, selectors, screenshots or manually typed candidate measurements. Shared binary assets follow provenance rules; substantial authored-code overlap means the reference is not independent.

## Ready conditions

The transferred scope is ready only when:

- typography is measured and settled;
- the full container chain is mapped;
- recurring tokens and components are implemented once;
- every source layout responsibility has a candidate owner;
- all responsive states are measured after the latest change;
- H2D strict geometry/style, system, provenance and visual gates pass, or dev-mode reports the honest non-proof status.
