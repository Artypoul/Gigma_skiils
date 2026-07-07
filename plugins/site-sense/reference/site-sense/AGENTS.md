# AGENTS.md: Site Sense Skills

Эти инструкции предназначены для AI-агентов, которые работают с проектом сайта, маркетинговыми смыслами, структурой и текстами.

## Главный принцип

Не начинай писать страницы, пока не понятны:

1. кто аудитория;
2. какая у неё задача или боль;
3. какие есть альтернативы;
4. чем продукт отличается;
5. какое целевое действие должен совершить пользователь;
6. какая структура сайта нужна для поиска, навигации и конверсии.

Если контекста нет, используй `product-marketing-context` или `website-strategy-orchestrator`.

## Автовыбор skills

| Ситуация пользователя | Skill |
|---|---|
| «сделай сайт с нуля», «продумай сайт», «нужен лендинг/многостраничник» | `website-strategy-orchestrator` |
| «собери вводные», «кто ЦА», «какое позиционирование» | `product-marketing-context` |
| «найди смыслы», «сформулируй оффер», «почему покупать у нас» | `meaning-positioning` |
| «структура сайта», «карта сайта», «навигация», «URL» | `information-architecture` |
| «контент-план», «SEO-кластеры», «какие статьи/страницы нужны» | `content-strategy` |
| «SEO-бриф», «ТЗ для копирайтера», «семантика», «интент» | `seo-content-brief` |
| «напиши текст страницы», «hero», «лендинг», «главная» | `page-copywriting` |
| «проверь конверсию», «улучши страницу», «слабый CTA» | `conversion-copy-review` |
| «сделай нормальный русский текст», «убери нейрослоп», «отредактируй» | `russian-copy-polish` |

## Рабочая цепочка

```text
product-marketing-context
  → meaning-positioning
  → information-architecture
  → content-strategy
  → seo-content-brief
  → page-copywriting
  → conversion-copy-review
  → russian-copy-polish
```

`website-strategy-orchestrator` используется как входная точка для полного проекта и собирает цепочку в итоговый пакет.

## Контекст проекта

Перед работой проверь именно проектные входные файлы:

- `.agents/product-marketing.md`
- `.claude/product-marketing.md`
- `product-marketing-context.md`
- `brief.md`
- `site-brief.md`
- `content-brief.md`

Если есть, используй их и не задавай повторные вопросы.

## Служебные файлы skill-pack

Следующие пути содержат инструкции и шаблоны самого `site-sense`, а не факты о конкретном проекте:

- `.agents/site-sense/`
- `.claude/site-sense/`
- `.codex/reference/site-sense/`
- `plugins/site-sense/reference/site-sense/`

Используй их как workflow guidance, checklist и templates. Не считай их пользовательским контекстом и не подменяй ими реальные вводные по сайту.

## Reference files

У каждого skill есть локальная папка `references/`. Если `SKILL.md` ссылается на файл `references/name.md`, сначала используй этот файл как supporting material для шаблона, чек-листа или правил.

Не игнорируй reference-файлы, когда задача требует структурированного результата: sitemap, SEO-бриф, page copy, review scorecard, финальная редактура.

## Правило вопросов

Не устраивай интервью на 20 вопросов. Сначала:

1. прочитай доступный контекст;
2. сделай разумные допущения;
3. задай максимум 5 вопросов, только если без них результат будет неверным;
4. если пользователь просит продолжать без уточнений, продолжай с разделом `Допущения`.

## Стандартные выходные артефакты

Для полного проекта сайта создай:

- `product-marketing.md` — продукт, ЦА, задачи, альтернативы, доказательства;
- `meaning-map.md` — смыслы, оффер, сообщения, objections, voice of customer;
- `information-architecture.md` — sitemap, навигация, URL, taxonomy, перелинковка;
- `content-plan.md` — контентные кластеры, страницы, статьи, buyer journey;
- `seo-briefs.md` — SEO-брифы ключевых страниц;
- `page-copy.md` — готовые тексты страниц;
- `copy-review.md` — ревью конверсии и качества;
- `final-site-spec.md` — финальная спецификация для дизайна/разработки.

## Качество результата

Каждый результат должен быть:

- конкретным, а не абстрактным;
- привязанным к аудитории;
- проверяемым;
- пригодным для передачи дизайнеру, разработчику, SEO-специалисту или редактору;
- написанным на русском без канцелярита и лишней «AI-гладкости».

## Запрещённые паттерны

Не делай так:

- писать «мы предлагаем комплексные решения» без конкретики;
- начинать с красивого hero без стратегии;
- смешивать ЦА в одну массу;
- делать структуру сайта по оргструктуре компании;
- создавать URL без правил;
- подменять доказательства обещаниями;
- писать CTA вроде «Узнать больше» везде;
- делать SEO-страницы без интента поиска;
- терять assumptions между этапами цепочки.

## Handoff между этапами

Каждый skill обязан завершать результат блоком `## Handoff`, чтобы следующий этап не угадывал контекст заново. Используй общий контракт из `.agents/site-sense/workflows/handoff-contracts.md`, `.claude/site-sense/workflows/handoff-contracts.md`, `.codex/reference/site-sense/workflows/handoff-contracts.md`, `plugins/site-sense/reference/site-sense/workflows/handoff-contracts.md` или `workflows/handoff-contracts.md`.

Минимум в handoff:

- какой артефакт создан;
- готов ли он для следующего skill;
- какой следующий skill рекомендован;
- какие входные данные передаются дальше;
- какие допущения нужно сохранить;
- какие вопросы реально блокируют точность;
- что нельзя менять без подтверждения: URL, CTA, оффер, claims, legal/compliance.

## Защита от рекурсии

`website-strategy-orchestrator` — только входная точка и финальный сборщик. Не запускай его как этап внутри полной цепочки. Рабочая цепочка начинается с `product-marketing-context` и заканчивается `russian-copy-polish`.

## Gate-проверки

Перед переходом дальше проверь минимум:

| Переход | Минимум для перехода |
|---|---|
| Context → Meaning | сегмент, JTBD/задача, alternatives, value proposition, CTA, proof/proof gaps |
| Meaning → IA | core message, differentiation, objections, proof map, hero direction |
| IA → Content/SEO | page inventory, sitemap, URL map, navigation, internal links |
| SEO → Copy | intent, H1/H2, metadata, must-answer questions, CTA, proof requirements |
| Copy → Review | полный текст, CTA, proof blocks, FAQ или причина, почему FAQ не нужен |
| Review → Polish | P1/P2/P3 fixes или принятый черновик |

Если gate не пройден, создай краткий недостающий артефакт с `Assumptions` и продолжай, не делая вид, что данные подтверждены.

## SEO и факты

Не выдумывай keyword volume, KD, CPC, позиции конкурентов, отзывы, кейсы, цифры и результаты. Если данных нет, делай intent-first бриф и помечай `Needs validation`.
