# План: H2D current-evidence pipeline

## Цель

Перенести в канонический репозиторий проверенные после неудачного переноса header/hero guardrails: полный адаптив из `.h2d`, неизменяемый контракт, свежие доказательства по текущим файлам, реальную Playwright-проверку и отрицательные тесты. При переносе сохранить более новые возможности H2D 0.3.0: typography-first, selector-map, asset provenance и owner-confirmed `changed-source`.

Scope: `h2d-transfer`, две общие инструкции recovery/Playwright, версии их плагинов и генерируемое `.codex`-зеркало.

Write-scope: `plugins/h2d-transfer/**`, `plugins/development-workflow/skills/feedback-recovery/SKILL.md`, `plugins/codex-toolkit/skills/playwright/SKILL.md`, соответствующие plugin manifests, `.github/workflows/validate.yml`, `docs/plan-h2d-current-evidence.md`, `.codex/**` только через `bash sync-codex.sh`.

Вне scope: файлы `app_itecho_svelte`, установленный plugin-cache, изменения дизайна header/hero, новые плагины, merge и deploy.

DoneWhen: полный синтетический `.h2d → contract → frozen reference → current gates → pass` проходит; негативные тесты отклоняют пропущенный viewport/profile, неверную геометрию/шрифт/пиксели, ручной или устаревший отчёт; старые возможности 0.3.0 не удалены; каталог и зеркало валидны; на актуальном PR нет блокирующих замечаний.

## Что делаем

| Что делаем | Было | Стало | Как делаем | БД | Endpoint / команда |
| --- | --- | --- | --- | --- | --- |
| Фиксируем источник, весь адаптив и недекодируемые входы | Viewport/root-map, integration selectors, readiness и sidecars вводились отдельными командами; можно было проверить не все ветки `.h2d` или повторить прогон с другими параметрами | Один контракт содержит SHA-256 источника, каждый decoded viewport/root/height/scroll/browser profile, candidate entry/URL, geometry/behavior/liveness mappings, readiness/timing, deviations/substitutions и полный asset scan (`assets`, `scan_roots`, threshold, allow-empty) с хешами sidecars | `transfer_contract` schema/template + generator из decoded H2D и обязательных CLI-входов | БД не меняется | `create_transfer_contract.py` |
| Перегенерируем доказательства по текущему кандидату без legacy bypass | `run_all_gates.py` проверял уже существующие отчёты, даже если они были созданы до последней правки | Финальная проверка всегда требует current-evidence provenance; direct legacy invocation после изменения candidate не проходит | `run_current_gates.py` строит доказательства; `run_all_gates.py` делегирует ему либо проверяет обязательные current hashes, отдельным остаётся только package self-check | БД не меняется | `run_current_gates.py --output … --project-root …` |
| Закрепляем визуальный оригинал и связываем его с H2D | Live donor мог измениться до или между итерациями; хеш нового скриншота доказывал бы только неизменность уже дрейфовавшей страницы | Freeze manifest содержит source SHA, H2D geometry/style preflight и явное происхождение visual baseline; live-capture без пикселей времени H2D не становится финальным эталоном без owner approval | `freeze_visual_reference.js` сначала сверяет runnable donor с decoded scope; contract требует trusted snapshot provenance либо отдельное owner-approved live-freeze decision | БД не меняется | `freeze_visual_reference.js` |
| Классифицируем behavior/liveness fail-closed | Отсутствующий inventory позволял `infer_*_required` выбрать static scope | До финализации контракта original проверяется во всей матрице; flags и inventory hash закрепляются, а `false` допустим только из измерения или owner-approved static fallback | Reference classification manifest; final runner не выводит requiredness из наличия отчётов | БД не меняется | `classify_reference.js` |
| Закрепляем полный dynamic baseline | Behavior/liveness могли каждый раз пересниматься с изменившегося live donor независимо от frozen pixels | Для каждого viewport/profile замораживаются original inventory/matrix/targets/traces, WebGL report и все транзитивно указанные frames/screenshots/videos; всё связано с source SHA/reference decision/environment и хешируется | Versioned `dynamic_reference_manifest`; при отсутствии или мутации любого обязательного артефакта interactive/dynamic transfer останавливается | БД не меняется | `freeze_dynamic_reference.py` |
| Проверяем всю матрицу в реальном браузере | Отдельный скриншот или один viewport ошибочно считался достаточным | Headless/headed профили × все viewport обязательны для geometry/fonts и responsive behavior/liveness; измеряются viewport/clientWidth/DPR/scroll/fonts | Расширение существующего `browser.js`, validators и dynamic replay без второго runtime helper | БД не меняется | Playwright gates с `--project-root` |
| Закрепляем rendering environment | Frozen baseline мог быть снят другим Chromium/OS/font stack и давать ложные пиксельные/метрические отличия | Manifest содержит browser/package version, platform, locale/timezone/reduced-motion, DPR и font faces; несовместимый current environment требует recapture или отдельного approval | Environment fingerprint в visual/dynamic manifests и final gate | БД не меняется | reference freeze + current runner |
| Связываем URL с актуальной сборкой | Уже запущенный server мог обслуживать старый build или другой checkout, хотя source files имеют новые hashes | Contract содержит build/start command, cwd, health check, bounded teardown и rendered build identity; либо candidate является content-addressed built entry | Current runner сам управляет process lifecycle и сверяет build marker/hash до browser gates | БД не меняется | candidate lifecycle contract |
| Проверяем поведение последовательностями и визуальными состояниями | Escape/outside-click запускались после reload из закрытого state; semantic ARIA мог пройти при неверном открытом UI | Matrix содержит prerequisites/action sequences; каждый post-interaction state имеет semantic и scoped visual comparison | open→Escape/open→outside-click replay, state screenshots + masked diff | БД не меняется | behavior matrix/capture/compare |
| Сравниваем реальное движение | Liveness pass означал только достаточное число samples и любое изменение | Candidate сравнивается с pinned original по timing, transforms, frame/canvas hashes и допустимым tolerances для каждой matrix state | Усиление `liveness_compare_traces.py` и state-aware capture | БД не меняется | liveness capture/compare |
| Сохраняем H2D 0.3.0 | Кеш 0.2.3 не знает selector-map, font paint proof, asset provenance и `changed-source` | Новые проверки добавляются поверх канона, не заменяют его | Совместимые схемы/runner и регрессионные тесты для существующих возможностей | БД не меняется | Существующие CLI остаются доступны |
| Закрепляем recovery-правило | После жалобы разрешался минимум «viewport + соседний breakpoint» | Specialist matrix всегда сильнее общего минимума; статусы берутся из активного skill/project | Узкие правки `feedback-recovery` и generic Playwright guidance | БД не меняется | без endpoint |
| Публикуем устанавливаемую версию | Правки в кеше исчезают при обновлении | Канон, версии plugin manifests и `.codex`-зеркало синхронизированы | Version bump трёх затронутых плагинов + `bash sync-codex.sh` | БД не меняется | `python validate_plugin.py` |
| Закрепляем регрессии в CI | H2D browser/negative suite запускался только локально | Catalogue workflow поднимает browser runtime и запускает integrity/current/browser H2D tests на каждом PR | Узкое расширение `.github/workflows/validate.yml` с кешируемой установкой Playwright | БД не меняется | GitHub Actions `validate` job |

## Что переиспользуем

- `scripts/browser.js`: расширяем разрешение Playwright по project root; дублирующий `runtime_modules.js` не переносим.
- `font_manifest.js`/`font_probe.js`: оставляем единственным runtime font gate; extracted font evidence становится входом, а не заменой измерения.
- `asset_provenance.py`: сохраняем обязательным gate и включаем в current runner.
- Selector-map, accepted deviations и `changed-source`: сохраняем существующие CLI/контракты и добавляем проверку свежести вокруг них.
- `sync-codex.sh` и `validate_plugin.py`: используем штатный путь зеркала и catalogue validation.

## БД и внешние контракты

БД не меняется. Внешние API не читаются и не пишутся. Единственные контракты — локальные JSON schemas, CLI и структура `.h2d`; они проверяются реальным donor-файлом и синтетическими fixtures без приватных данных.

## Edge cases и совместимость

- Data/API пункты 1–14: не применимо — нет БД, HTTP API, tenant/auth или внешних записей.
- Frontend «что уже есть»: применимо — сохраняем канонические H2D 0.3.0 validators и не копируем старый кеш целиком.
- Desktop/mobile: применимо — все decoded viewport обязательны, неполная матрица падает.
- Loading/empty/auth/payload/redirect: не применимо — skill проверяет локальные артефакты, а не продуктовый экран/API.
- CLI compatibility: отдельные discovery/debug команды остаются доступны, но ни `run_all_gates.py`, ни прямой legacy final command не могут дать final pass без current-evidence provenance.
- Browser dependencies: candidate root и project root разделены; отсутствие реального Playwright/browser — blocker, не фиктивный отчёт.
- Static/dynamic boundary: screenshot manifest допустим только для статических pixels; behavior/liveness требуют pinned dynamic baseline, созданный из закреплённого runnable donor или завершаются non-pass.
- Reference provenance: `.h2d` не содержит пиксельный снимок, поэтому геометрическая сверка сама по себе не доказывает отсутствие visual-only drift; live freeze требует owner decision, а без него final gate остаётся non-pass.
- Dynamic drift: original traces не регенерируются текущим runner; их source/reference hashes проверяются перед сравнением с candidate.
- Dynamic requiredness: contract generator обязан получить reference classification для всей viewport/profile matrix; удалённый или сфальсифицированный classification manifest не превращает scope в static.
- Integration inputs: geometry selector-map, candidate behavior/liveness mappings, readiness selector/timeouts, accepted deviations, font substitutions, asset map/decisions и их hashes являются частью immutable contract; отсутствующий или изменённый sidecar останавливает прогон.
- Asset scan: globs/paths, все scan roots, size threshold и allow-empty закреплены в контракте; сужение scan root после генерации не допускается.
- Accepted deviations: pixel diff получает только viewport/node-scoped masks из утверждённого sidecar; внутри маски расхождение допустимо, любое несвязанное отличие снаружи остаётся fail. `changed-source` не используется для content divergence.
- Responsive runtime: original baseline и candidate replay имеют запись для каждой пары viewport/profile; donor selectors преобразуются через закреплённые candidate mappings.
- WebGL/media: dynamic manifest хеширует отчёты и каждый transitively referenced binary artifact, а не только JSON/JSONL.
- Rendering environment: visual pixels сравниваются только при совместимом environment fingerprint; изменение браузера/OS/font stack требует recapture либо явного owner approval.
- Reachable states: reference classification сначала строит валидную behavior matrix, затем повторяет liveness discovery после каждой безопасной interaction sequence; непроверенный reachable state означает `liveness_required=true`, не false.
- Stable original selectors: inventory строит DOM-relative selectors по реальной sibling position/escaping, проверяет uniqueness/resolution перед freeze и останавливается на unresolved selector.
- Sequence semantics: close actions всегда имеют prerequisite open action; capture не перезагружает страницу между шагами одной sequence.
- Post-state visuals: behavior report сравнивает candidate/reference screenshots каждого state с теми же scoped deviation masks; ARIA/visibility без визуального совпадения недостаточны.
- Motion fidelity: liveness сравнивает относительный timing, transforms, frame/canvas hashes и state transitions, а не только sample count/наличие изменения.
- Candidate lifecycle: URL mode разрешён только через pinned build/start/health/teardown contract и build identity; внешний уже запущенный server без доказанной сборки non-pass.
- Dirty/stale evidence: изменение candidate/source/contract/reference после отчёта делает final gate красным.

## Проверки

1. Python integrity tests: freshness, provenance, full viewport/profile coverage, manual generator rejection.
2. Real-browser integration: headless/headed; правильный fixture проходит, неверные font-weight/width/pixels падают.
3. End-to-end current runner: сырой `.h2d` до финального `validation_run.result=pass`.
4. Donor-drift integration: changed live pixels не принимаются без trusted snapshot/owner decision; dynamic current run отклоняет изменённый или отсутствующий frozen trace manifest.
5. Requiredness negative fixture: удалённый/подменённый classification или ложный static flag на dynamic donor падает; owner-approved static fallback остаётся явным non-runtime решением.
6. Responsive dynamic fixture: behavior/liveness, включая разные desktop/mobile selectors, проверяются для всей viewport/profile matrix.
7. Reachable-state fixture: dynamic surface, появляющийся только после click, классифицируется и сравнивается; непроверенный state fail-closed.
8. Behavior-sequence fixture: candidate, который открывает menu, но не закрывает его по Escape/outside-click, падает.
9. Post-state visual fixture: semantic state совпадает, но неверная стилизация/содержимое открытого UI падает.
10. Motion-fidelity fixture: wrong frames/trajectory/timing при наличии движения падают.
11. Selector fixture: donor без id/markers получает уникальные resolvable selectors; unresolved original selector нельзя заморозить.
12. Nondefault integration fixture: selector-map, readiness и sidecar hashes воспроизводятся из контракта; изменение sidecar делает gate красным.
13. Candidate lifecycle fixture: stale server/другая build identity не может дать current pass; runner корректно завершает запущенный process.
14. Asset-scan negative fixture: удалённый/суженный scan root, изменённый threshold или allow-empty ломает provenance gate.
15. Deviation compatibility fixture: approved masked region проходит, дополнительная ошибка за пределами mask падает.
16. WebGL/media mutation fixture: изменение referenced frame/screenshot/video инвалидирует dynamic manifest.
17. Environment fixture: несовместимый browser/platform/font fingerprint без approval падает.
18. Legacy bypass fixture: direct `run_all_gates.py` после candidate mutation не проходит без regeneration/current hashes.
19. Existing H2D 0.3.0 compatibility tests/fixtures для typography, selector-map, asset provenance и changed-source.
20. `npm run check:js`, package self-check, `quick_validate.py` для изменённых skills.
21. `bash sync-codex.sh`, `python validate_plugin.py` и тот же H2D suite в GitHub Actions.

## Плановый консилиум

- Contract/integrity: запретил слепое копирование кеша и потребовал хеши источника, кандидата, контракта и frozen reference.
- Browser/runtime: выбрал расширение существующего `browser.js` вместо второго resolver; project root отделён от candidate evidence root.
- Package/installability: потребовал version bump затронутых плагинов, штатный mirror sync и catalogue validation.
- Codex plan review: добавил owner-gated visual provenance, pinned dynamic baseline, полный контракт non-H2D inputs и обязательный H2D regression suite в CI.
- Codex plan re-review: сделал behavior/liveness requiredness fail-closed, расширил dynamic coverage на всю matrix и все WebGL/media artifacts, закрепил asset scan/environment/candidate mappings и scoped pixel masks.
- Codex plan review round 3: добавил reachable-state classification, action prerequisites, post-state visual diff, motion fidelity, stable donor selectors, candidate build lifecycle и запрет legacy final-pass bypass.

Блокеров для реализации после plan review-gate нет. Главный риск — потерять более новые гарантии H2D 0.3.0; он закрывается совместимым merge и отдельными регрессионными тестами.
