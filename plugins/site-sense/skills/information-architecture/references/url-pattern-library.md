# URL pattern library

Use stable, readable URLs. Prefer lowercase Latin slugs with hyphens unless the project intentionally uses another convention.

## General rules

- One page = one canonical URL.
- Keep URLs short enough to understand but descriptive enough to classify.
- Avoid dates in evergreen content unless date is the organizing principle.
- Avoid stop words where they do not add meaning.
- Do not change existing ranking URLs without a redirect reason.
- Do not use internal IDs unless required by the platform.

## Common patterns

| Page type | Pattern | Example |
|---|---|---|
| Homepage | `/` | `/` |
| Product | `/product/` or `/products/[product]/` | `/products/analytics/` |
| Service | `/services/[service]/` | `/services/seo-audit/` |
| Industry/use case | `/solutions/[industry-or-use-case]/` | `/solutions/ecommerce/` |
| Feature | `/features/[feature]/` | `/features/reporting/` |
| Comparison | `/compare/[alternative]/` | `/compare/excel/` |
| Pricing | `/pricing/` | `/pricing/` |
| Blog post | `/blog/[slug]/` | `/blog/site-structure/` |
| Guide | `/guides/[topic]/` | `/guides/content-strategy/` |
| Template | `/templates/[template]/` | `/templates/seo-brief/` |
| Case study | `/customers/[customer-or-case]/` | `/customers/acme/` |
| Docs | `/docs/[section]/[page]/` | `/docs/getting-started/setup/` |
| Legal | `/legal/[page]/` | `/legal/privacy/` |
| Contact | `/contact/` | `/contact/` |

## Multilingual patterns

| Option | Pattern | When to use |
|---|---|---|
| Subfolder | `/en/page/`, `/ru/page/` | Most sites |
| Subdomain | `en.example.com` | Separate teams/markets |
| ccTLD | `example.de` | Strong country-specific strategy |

## Redesign URL rules

Keep old URLs when:

- they have backlinks;
- they rank or bring traffic;
- they are used in campaigns;
- they are printed or integrated elsewhere.

Change URLs only when:

- current URL is misleading;
- pages are merged/split;
- language/region structure changes;
- duplicate URLs are consolidated.

Every changed URL needs a 301 redirect target.
