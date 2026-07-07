# Workflow: handoff contracts

Этот файл нужен агенту, чтобы вся цепочка работала как система, а не как набор отдельных prompts.

## Главное правило

Каждый skill в конце результата должен добавить блок `## Handoff`, даже если пользователь не попросил его явно.

Формат блока:

```markdown
## Handoff

- Artifact produced: `[filename.md]`
- Ready for next skill: yes/no
- Recommended next skill: `[skill-name]`
- Inputs passed forward:
  - [ключевой вход]
- Assumptions to keep:
  - [допущение]
- Open questions:
  - [только вопросы, которые реально блокируют точность]
- Do not change without confirmation:
  - [URL, CTA, оффер, claims, compliance-ограничения]
``` 

Поле `Recommended next skill` должно содержать одно конкретное имя skill. Не подставляй туда имя файла, free-form комментарий или несколько вариантов через "or".

## Цепочка и контракты

| Этап | Skill | Артефакт | Что обязан отдать дальше | Следующий skill |
|---|---|---|---|---|
| 1 | `product-marketing-context` | `product-marketing.md` | продукт, сегменты, JTBD, альтернативы, value proposition, proof, objections, CTA, tone, assumptions | `meaning-positioning` |
| 2 | `meaning-positioning` | `meaning-map.md` | recommended positioning, offer, hero claim, message hierarchy, proof map, objections, words to use/avoid | `information-architecture` |
| 3 | `information-architecture` | `information-architecture.md` | page inventory, sitemap, URL map, navigation, taxonomy, internal links, page goals, page CTA | `content-strategy` |
| 4 | `content-strategy` | `content-plan.md` | content pillars, topic clusters, buyer stage, page/article backlog, priorities, internal linking strategy | `seo-content-brief` |
| 5 | `seo-content-brief` | `seo-briefs.md` | per-page intent, query groups, URL, title/meta/H1/H2, must-answer questions, FAQ, schema, internal links, conversion next step | `page-copywriting` |
| 6 | `page-copywriting` | `page-copy.md` | final draft by page, hero variants, chosen structure, CTA, proof blocks, FAQ, design notes, missing proof | `conversion-copy-review` |
| 7 | `conversion-copy-review` | `copy-review.md` | scorecard, P1/P2/P3 fixes, proof gaps, CTA/friction notes, rewritten examples | `page-copywriting` |
| 8 | `russian-copy-polish` | `final-copy.md` | final edited copy, what changed, risk notes, locked claims/SEO terms preserved | `website-strategy-orchestrator` |

## Правило отсутствующих данных

Если данных не хватает:

1. сначала проверь существующие файлы проекта;
2. используй допущения, если задача может двигаться дальше;
3. задай максимум 5 вопросов, только если без них результат станет неверным;
4. не блокируй цепочку из-за нехватки второстепенных данных;
5. не выдумывай факты, цифры, keyword volume, рейтинги, кейсы, отзывы или результаты.

## Правило SEO-данных

Если нет инструментальных данных по ключам, SERP, частотности или конкурентам:

- не придумывай volume, KD, CPC и позиции конкурентов;
- делай intent-first бриф;
- помечай разделы как `Needs validation`;
- предлагай, какие данные проверить в GSC, Ahrefs, Semrush, Яндекс.Вордстат, Search Console или SERP.

## Правило циклов

Не запускай всю цепочку заново после каждого изменения. Возвращайся только к ближайшему предыдущему skill, который влияет на проблему.

Примеры:

- проблема в CTA → `conversion-copy-review` → `page-copywriting`;
- проблема в URL → `information-architecture`;
- проблема в интенте страницы → `seo-content-brief`;
- проблема в оффере → `meaning-positioning`;
- проблема в сегменте → `product-marketing-context`.

Если после `conversion-copy-review` нужны только микро-правки языка без смысловых изменений, сначала зафиксируй исправления в copy, а затем переходи в `russian-copy-polish`.

## Definition of done

Цепочка считается рабочей, если в конце есть:

- продуктовый контекст;
- смысловая карта;
- sitemap и URL map;
- page inventory;
- SEO-брифы для приоритетных страниц или пометка, почему SEO не нужно;
- тексты ключевых страниц;
- список proof gaps;
- CTA и путь пользователя;
- чистовая русская версия;
- финальный checklist передачи дизайнеру/разработчику/SEO/редактору.
