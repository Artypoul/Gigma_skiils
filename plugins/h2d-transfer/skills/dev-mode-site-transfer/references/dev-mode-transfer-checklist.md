# Dev mode transfer checklist

Use this file when transferring a live site from browser dev mode into clean code.

## 1. Route decision

Use dev mode transfer when:

- source is a live URL;
- you can actually open the page and inspect the rendered result in browser dev mode;
- page is mostly normal DOM/CSS;
- the site is WordPress/Elementor, Tilda, Webflow-like, or old static markup;
- you want a clean reconstruction faster than a proof-gated forensic clone.

Escalate to H2D or stricter validation when:

- source already exists as `.h2d`;
- user explicitly says `pixel-perfect`;
- page behavior depends on canvas, WebGL, complex motion, or runtime traces;
- there are many stateful interactions that inspector-only copying cannot explain safely.

Stop with `blocked` when the page does not open, auth/runtime gating prevents meaningful inspection, or browser/devtools access is unavailable.

## 2. What to collect from dev mode

Before block-by-block notes, create one design-system inventory:

- recurring palette values and every semantic use;
- typography roles, families, weights, sizes, line-heights and letter spacing;
- spacing, radii, borders, shadows and icon rules;
- container widths, gutters and actual breakpoint boundaries;
- repeated UI patterns, occurrence counts and visible states;
- candidate token/component name and its single definition file.

For each block collect:

- screenshot of the block;
- DOM role and content order;
- final visible text;
- asset URLs;
- font family, size, weight, line-height;
- text and background colors;
- spacing: padding, gap, margin;
- container width or max-width;
- desktop and mobile arrangement;
- any interaction states.

## 3. Good transfer targets

Usually easy:

- hero blocks;
- text + image sections;
- CTA strips;
- cards/grids;
- testimonials;
- contact/footer sections;
- simple galleries;
- embedded video sections.

Usually medium:

- sliders and carousels;
- tabs;
- accordions;
- anchor nav;
- sticky headers;
- popups and overlays.

Usually risky:

- canvas-driven visuals;
- WebGL;
- parallax choreography;
- custom JS calculators;
- forms with opaque third-party logic;
- lazy-loaded state that appears only after user flow.

## 4. Rebuild rules

- rebuild in semantic, maintainable markup;
- keep the visual result, not the builder wrappers;
- keep naming by component role;
- convert repeated visual values into tokens/classes;
- require blocks to consume the shared tokens instead of repeating donor literals;
- build every source pattern repeated at least twice as one component and instantiate it with data/content;
- preserve important embeds only when needed by the product.

Do not import:

- analytics scripts;
- unrelated third-party widgets;
- tracking attributes;
- giant copied inline style blobs;
- builder helper markup that exists only to satisfy the original CMS.

## 5. Stack-specific warnings

### WordPress / Elementor

- expect wrapper-heavy DOM;
- use the page as a visual/layout guide, not as the desired component tree;
- inspect computed styles, not only class names;
- watch for mobile overrides hidden in Elementor CSS.

### Legacy static HTML

- expect brittle inline widths and spacer hacks;
- verify image aspect ratios manually;
- check whether repeated service pages are near-duplicates and can share components.

### Modern React/SPA

- inspect hydration boundaries and runtime data dependencies before claiming the block is portable;
- if the visible state depends on data fetches or app context, document what is fake vs real in the rebuild.

## 6. Final handoff checklist

- route choice is explicit: dev mode transfer, not H2D proof transfer;
- blocks are inventoried and named by role;
- rebuilt code is cleaner than the source;
- lightweight evidence was kept: desktop/mobile captures or equivalent per-block notes;
- desktop and mobile were checked;
- the design-system inventory is complete for the transferred scope;
- recurring values resolve through one shared token layer;
- every repeated pattern resolves to one candidate component definition;
- shipped sources were searched for scattered donor literals and duplicated component markup;
- asset and text parity were checked;
- remaining behavior gaps are named explicitly;
- status is honest: `clean-transfer`, `close-match`, `needs-polish`, `changed-source`, or `blocked`.
