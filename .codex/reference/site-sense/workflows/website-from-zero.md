# Workflow: сайт с нуля

Используй, когда нужно создать новый сайт, лендинг или многостраничную структуру.

## Последовательность

После каждого этапа добавляй блок `## Handoff` по правилам из `handoff-contracts.md`. Это обязательное условие: следующий skill не должен угадывать, какие данные считать финальными.

1. `product-marketing-context`
   - собрать продукт, аудиторию, проблемы, альтернативы, доказательства;
   - результат: `product-marketing.md`.

2. `meaning-positioning`
   - найти оффер, смысловую карту, позиционирование, message hierarchy;
   - результат: `meaning-map.md`.

3. `information-architecture`
   - построить sitemap, навигацию, URL, taxonomy, перелинковку;
   - результат: `information-architecture.md`.

4. `content-strategy`
   - определить страницы, статьи, кластеры, buyer journey;
   - результат: `content-plan.md`.

5. `seo-content-brief`
   - подготовить брифы ключевых страниц;
   - результат: `seo-briefs.md`.

6. `page-copywriting`
   - написать тексты страниц;
   - результат: `page-copy.md`.

7. `conversion-copy-review`
   - проверить, где слабо, непонятно, без доказательств или без CTA;
   - результат: `copy-review.md`.

8. `russian-copy-polish`
   - финально вычитать русский текст;
   - результат: чистовая версия.

9. Финальная сборка
   - собрать `final-site-spec.md` из стратегии, sitemap, URL, SEO, page copy и launch checklist.

## Stage gates

| После этапа | Минимум, который должен быть |
|---|---|
| Product context | сегмент, JTBD, alternatives, value proposition, proof gaps, CTA |
| Meaning | message hierarchy, recommended positioning, offer, objections, hero variants |
| IA | page inventory, sitemap ASCII, URL map, header/footer, internal links |
| Content | pillars, clusters, buyer journey map, prioritized roadmap |
| SEO | intent, metadata, H1/H2, FAQ, schema candidates, internal links |
| Copy | full copy по ключевым страницам или выбранному scope |
| Review | P1/P2/P3 fixes и переписанные примеры |
| Polish | чистовой русский текст и risk notes |

Если gate не пройден, агент не должен делать вид, что цепочка завершена. Нужно либо создать недостающий артефакт с допущениями, либо явно пометить его как `Needs validation`.

## Минимальные входные данные

- продукт или услуга;
- целевой сегмент;
- цель сайта;
- формат сайта: лендинг, многостраничник, каталог, блог, SaaS, услуги, e-commerce, docs;
- основной CTA;
- ограничения: сроки, бренд, CMS, SEO, существующие URL.

## Критерий готовности

Сайт готов к передаче в дизайн/разработку, когда есть:

- структура страниц;
- тексты ключевых блоков;
- URL и навигация;
- SEO-брифы приоритетных страниц;
- список доказательств и trust-блоков;
- CTA и путь пользователя;
- финальная редактура;
- launch checklist;
- список открытых рисков/допущений.
