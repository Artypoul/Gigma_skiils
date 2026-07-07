# Sitemap Mermaid templates

Use Mermaid when the user wants a visual sitemap that can be pasted into docs, GitHub, Notion-compatible tools, or design handoff.

## Simple landing page

```mermaid
graph TD
HOME[Landing page /]
HOME --> HERO[Hero]
HOME --> PROBLEM[Problem]
HOME --> SOLUTION[Solution]
HOME --> PROOF[Proof]
HOME --> FAQ[FAQ]
HOME --> CTA[Final CTA]
```

## Multi-page marketing site

```mermaid
graph TD
HOME[Home /]
HOME --> PRODUCT[Product /product/]
HOME --> SOLUTIONS[Solutions /solutions/]
HOME --> PRICING[Pricing /pricing/]
HOME --> RESOURCES[Resources /resources/]
HOME --> COMPANY[Company /company/]
HOME --> CONTACT[Contact /contact/]

SOLUTIONS --> USECASE1[Use case 1]
SOLUTIONS --> USECASE2[Use case 2]
RESOURCES --> BLOG[Blog]
RESOURCES --> GUIDES[Guides]
RESOURCES --> CASES[Case studies]
```

## Service business

```mermaid
graph TD
HOME[Home /]
HOME --> SERVICES[Services /services/]
SERVICES --> SERVICE1[Service page]
SERVICES --> SERVICE2[Service page]
HOME --> CASES[Cases /cases/]
HOME --> ABOUT[About /about/]
HOME --> BLOG[Blog /blog/]
HOME --> CONTACT[Contact /contact/]
```

## Content hub and spokes

```mermaid
graph TD
HUB[Hub page]
HUB --> GUIDE1[Guide]
HUB --> GUIDE2[Guide]
HUB --> TEMPLATE[Template]
HUB --> COMPARISON[Comparison]
GUIDE1 --> PRODUCT[Product/service page]
GUIDE2 --> PRODUCT
COMPARISON --> PRICING[Pricing/demo]
```

## Notation rules

- Use readable node labels.
- Include URLs in labels for important pages.
- Keep the diagram high-level first; detailed page inventory belongs in a table.
- For large sites, create one diagram per section.
