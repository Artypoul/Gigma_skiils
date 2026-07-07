# Attribution

Этот пакет создан как синтез идей, структуры и подходов из трёх открытых репозиториев. Файлы внутри `site-sense-skills` написаны заново на русском языке и адаптированы под задачу создания сайтов: смыслы, структура, SEO и тексты.

## Источники

### 1. coreyhaines31/marketingskills

- GitHub: https://github.com/coreyhaines31/marketingskills
- Фокус: marketing Agent Skills для CRO, copywriting, SEO, analytics, growth, site architecture.
- Полезные идеи для этого пакета: cross-agent формат, папки `skills/skill-name/SKILL.md`, триггерные descriptions, site architecture, content strategy, SEO, CRO, copywriting.
- Лицензия исходного репозитория: MIT, согласно странице репозитория.

### 2. rampstackco/claude-skills

- GitHub: https://github.com/rampstackco/claude-skills
- Фокус: единая библиотека Claude Skills для lifecycle сайта: brand, design, content, SEO, dev, ops, growth, research.
- Полезные идеи для этого пакета: единый порядок секций в `SKILL.md`, обязательные reference files, разделение `When to use`, `When NOT to use`, `Required inputs`, `The framework`, `Workflow`, `Failure patterns`, `Output format`, `Reference files`.
- Лицензия исходного репозитория: MIT, согласно странице репозитория.

### 3. About-Intelligence/awesome-marketing-skills

- GitHub: https://github.com/About-Intelligence/awesome-marketing-skills
- Фокус: универсальные marketing skill prompts для SEO, CRO, copywriting, growth, ChatGPT, Claude, Cursor.
- Полезные идеи для этого пакета: простота использования через копирование prompt/skill, категории SEO & Strategy, CRO, Content & Copy, Growth & Retention, Sales GTM, value proposition и JTBD-логика.
- Лицензия исходного репозитория: MIT, согласно странице репозитория.

## Что именно заимствовано

Заимствованы не тексты, а принципы:

- Skill как папка с `SKILL.md`.
- YAML frontmatter с `name` и `description`.
- Триггерные descriptions для автоматического выбора skill.
- Разделение задач: контекст, смыслы, структура, SEO, copywriting, CRO.
- Подход «главный skill + reference files + templates + checklists».

## Что адаптировано

- Русский язык по умолчанию.
- Оркестратор для полного цикла сайта.
- Сильный акцент на «смыслы» и позиционирование, а не только на SEO и тексты.
- Шаблоны, которые можно сразу передавать дизайнеру, SEO-специалисту, редактору и разработчику.
- Финальная русскоязычная редактура: ясность, доказательность, отсутствие канцелярита.
