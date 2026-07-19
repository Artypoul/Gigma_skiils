# First-pass quality: реализация и проверочная таблица

## Цель

Уменьшить ошибки агентов уже в первой проходке и не допускать ложного завершения в длинной работе. Контур должен фиксировать ожидаемый результат, разрешённую область, доступные действия, свежие доказательства и обязательный review до того, как агент назовёт задачу готовой.

Архитектурная основа: `docs/Fable_5_harness_architecture_plan_RU.docx`. Реализация не копирует чужой prompt или идентичность; устойчивые паттерны перенесены в project rules, skills, lifecycle hooks, controller, тесты и CI.

## Честный результат повторного аудита

До этого PR инструкции и личная установленная копия `first-pass-quality` существовали отдельно от каталога. Из-за этого репозиторий не поставлял сам enforcement, а его контрактные тесты зависели от user-specific `$HOME/Scripts/...` и не были воспроизводимы в CI.

Исправлено:

- `first-pass-quality` добавлен как самостоятельный marketplace plugin;
- Codex и Claude manifests/marketplace entries зарегистрированы вместе;
- `$feature` и generic first-pass получили явный приоритет без подмены project skills;
- дублирующие feature watch/turnstile hooks запрещены для одной сессии;
- восемь user-specific feature-hook тестов заменены прямыми тестами controller;
- test runner сам находит `pwsh` и использует системный temp path;
- Windows CI запускает полный 103-case contract suite;
- изолированный smoke-test запускает реальные Codex/Claude hook commands через доступный `pwsh`, проверяет их plugin data и восемью assertions доказывает, что пользовательские pointer-файлы не меняются;
- каталоговый validator проверяет hook discovery и запрещает user-specific пути в hooks/tests.

## Проверочная таблица реализации

| Требование | Инструмент реализации | Проверка | Статус |
| --- | --- | --- | --- |
| Один вопрос до новой задачи | `UserPromptSubmit`, clarification state, `Stop` | До ответа пользователя tool call блокируется; один короткий вопрос разрешён | Реализовано |
| Не повторять вопрос для продолжения | `ConfirmContext`, `StartTask -Continuation` | Continuation сохраняет границы или создаёт новый Task Lock | Реализовано |
| Зафиксировать первую проходку | `StartTask`: outcome, scope, write scope, mode, risk, actions, workflow/stage, criteria | Неполный Task Lock отклоняется | Реализовано |
| Не выйти за область | absolute scope/write scope, patch target parser, dirty guard | Чужой target и запись вне write scope блокируются | Реализовано для hooked local tools |
| Реально применять allowed actions | классификация tool kind до вызова | Неавторизованный write/commit/push/PR/delegate блокируется | Реализовано |
| Пережить новый prompt/compaction | context reset, `ConfirmContext`, `PreCompact`, `PostCompact` | Запись блокируется до reconciliation | Реализовано |
| Не принимать старое доказательство | last write timestamp + exact tool name/result | Evidence до последней записи или от другого tool отклоняется | Реализовано |
| Не заявлять ложный `ready` | acceptance, self-review, review gates + `SetStatus`/`Stop` | Terminal ready невозможен при pending/failed gate | Реализовано |
| Не продолжать после terminal status | `PreToolUse` terminal lock | Любой неменеджмент-инструмент после ready/partial/blocked/unknown отклоняется | Реализовано |
| Честно завершать partial/blocked/unknown | обязательные reason, limitations, next action | Неполный terminal report отклоняется | Реализовано |
| Не сломать PR flow | отдельные pre-publish criteria и `publish` gate; VCS/PR bookkeeping classes | tests → add → commit → push → PR проходит без сброса file evidence | Реализовано |
| Проверять текущий remote diff | успешный push всегда ставит review `pending` | `ready` блокируется до review текущего push | Реализовано |
| Не считать failed push новым diff | success-aware `PostToolUse` | Failed push не переоткрывает уже пройденный review, но включает recovery pause | Реализовано |
| Совместимость с `$feature` | `Workflow feature`, обязательный `WorkflowStage`, отдельные phase Task Locks | Missing stage и plan-write вне `WriteScope` отклоняются | Реализовано |
| Не дублировать feature hooks | first-pass controller — canonical; legacy watch/turnstile — только fallback | Static skill/catalog review + controller contract tests | Реализовано |
| Merge не равен deploy | PR mode не разрешает merge/force-push/deploy | typed merge и force-push отклоняются | Реализовано |
| Production только по точной сущности | Entity Lock, canonical input hash, stable/project fields | другой ID/input и replay отклоняются | Реализовано для hooked typed tools |
| Подтверждение production одноразовое | latest-prompt confirmation consumed в `PreToolUse` | повтор и auto-retry невозможны | Реализовано |
| Failed write не каскадирует | mutation pause + read/validator + `AcknowledgeWriteRecovery` | следующая mutation блокируется до проверки состояния | Реализовано |
| Делегация не расширяет полномочия | explicit delegate action, bounded handoff, parent verification | unbounded spawn и mutation до parent check отклоняются | Реализовано для normal spawn path |
| Артефакт проверяется структурно | `artifact-validator.ps1` | Markdown/JSON/image/PDF/DOCX container checks | Реализовано; visual QA отдельно |
| Hooks действительно поставляются | `hooks/hooks.json`, `$PLUGIN_ROOT`, manifests | catalog validator проверяет структуру и переносимые пути | Реализовано |
| Регрессии controller ловит CI | `tests/run-contract-tests.ps1` + Windows GitHub Actions job | 103 positive/negative contract assertions, включая Claude `Edit`/`Write` scope | Реализовано |
| Codex и Claude используют свои plugin roots/data | `PLUGIN_ROOT`/`PLUGIN_DATA` и `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` | 8 isolated real-command assertions через bash + `pwsh`, включая неизменность `.codex`/`.claude` pointer-файлов | Реализовано при наличии `pwsh 7` |

## Правила первой проходки

1. Для новой задачи задать Art один короткий вопрос об ожидаемом результате и дождаться ответа. Для уже уточнённого продолжения вопрос не повторять.
2. До первой мутации создать Task Lock: outcome, абсолютный scope, более узкий write scope при необходимости, out-of-scope, mode, risk, workflow/stage, allowed actions, pre-publish criteria и DoneWhen.
3. До действия загрузить ближайшие project rules и нужные skills. Generic first-pass не подменяет локальный workflow и не ослабляет более строгий gate.
4. После нового сообщения, resume или compaction выполнить context reconciliation. Расширение/замена задачи требует нового Task Lock с `-Continuation`.
5. Для каждого критерия заранее выбрать реальный validator. Passed evidence должно относиться к точному успешному tool result после последней содержательной записи.
6. Для PR отдельно пройти pre-publish gate до commit/push/PR и финальные acceptance/review gates после публикации.
7. Перед terminal status выполнить self-review: scope, diff/файлы, тесты, свежесть доказательств, ограничения и review текущего push.

## Общие правила агента

1. `ready` допустим только при пройденных context/workflow/acceptance/self-review/review gates и свежем evidence для всех DoneWhen.
2. После terminal status инструменты не продолжать; новая работа требует нового Task Lock.
3. Normal commit/push и PR create/edit/comment/review относятся к `pr` mode. Merge, force-push, deploy, деньги и внешние сущности остаются production.
4. Production write выполняется только typed wrapper с exact input и stable identity после свежего одноразового подтверждения Art.
5. Unknown outcome не повторять автоматически.
6. После failed/unknown write сначала проверить фактическое состояние и только затем снять recovery pause.
7. Ответ субагента не является доказательством: parent обязан независимо прочитать или протестировать результат.
8. Структурная проверка документа/изображения не заменяет render/screenshot и визуальный просмотр.

## Совместимость и приоритет

Порядок применения:

1. прямое указание пользователя и safety boundary;
2. ближайший project `AGENTS.md` и project-local skill;
3. выбранный workflow, например `$feature`;
4. generic `$first-pass-quality-gate`.

`first-pass-quality` оборачивает `$feature`, но не меняет doc-first последовательность `plan → review → code → review`. Planning и implementation получают разные Task Locks и write scopes. После каждого успешного push review текущего remote diff снова обязателен. Сообщение `merged` подтверждает только merge и не разрешает deploy.

## Как проверить локально

```powershell
pwsh -NoProfile -File ./plugins/first-pass-quality/tests/run-contract-tests.ps1
pwsh -NoProfile -File ./plugins/first-pass-quality/tests/run-hook-config-smoke.ps1
python ./validate_plugin.py
bash ./sync-codex.sh
git diff --check
```

## Остаточные ограничения

- Local hooks не являются sandbox: hosted tools и неизвестные wrapper paths могут не попасть в классификацию.
- Агент всё ещё принимает смысловое решение, считать ли новый prompt продолжением; `ContextDisposition` делает решение аудируемым, но не гарантирует его истинность.
- Вне Git dirty overlap нельзя доказать автоматически; запись требует явного `-AllowDirty`.
- Structural artifact validation не доказывает визуальное качество.
- Hooks из обновлённого plugin начинают реально действовать только после установки/reload, новой Codex-задачи и подтверждения trust.
- Claude hook-команды требуют PowerShell 7 (`pwsh`) в `PATH`; текущий smoke-test подтверждает Claude variables через bash + `pwsh` на Windows, но не является нативным macOS/Linux тестом.
- Этот PR публикует код и tests, но сам не устанавливает plugin и не меняет глобальные hooks пользователя.
