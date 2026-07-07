# Workflow map

`website-strategy-orchestrator` — только точка входа и диспетчер. Не запускай его как внутренний шаг рабочей цепочки.


## Новый сайт

`product-marketing-context` → `meaning-positioning` → `information-architecture` → `content-strategy` → `seo-content-brief` → `page-copywriting` → `conversion-copy-review` → `russian-copy-polish`

## Редизайн

`product-marketing-context` → `meaning-positioning` → `information-architecture` → `conversion-copy-review` текущих страниц → `content-strategy` → `seo-content-brief` → `page-copywriting` → `conversion-copy-review` новой версии → `russian-copy-polish`

## SEO-страница без готового контекста

`product-marketing-context` → `meaning-positioning` → `seo-content-brief` → `page-copywriting` → `conversion-copy-review` → `russian-copy-polish`

## SEO-страница с готовым контекстом

`seo-content-brief` → `page-copywriting` → `conversion-copy-review` → `russian-copy-polish`

## Одна страница без готового контекста

`product-marketing-context` → `meaning-positioning` → `page-copywriting` → `conversion-copy-review` → `russian-copy-polish`

## Одна страница с готовым контекстом

`page-copywriting` → `conversion-copy-review` → `russian-copy-polish`

## Только редактура

`russian-copy-polish`

## Только аудит конверсии

`conversion-copy-review`

Если страница должна ранжироваться в поиске, добавь `seo-content-brief` перед `page-copywriting`.
