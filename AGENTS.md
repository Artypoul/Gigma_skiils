# AGENTS.md — бриф для Codex

Этот репозиторий — каталог скилов-консультантов. Две системы читают его по-разному:

- **Claude Code** — через маркетплейс `.claude-plugin/marketplace.json` → плагины в `plugins/`.
- **Codex** — двумя путями:
  1. **Codex-маркетплейс**: `.agents/plugins/marketplace.json` + `plugins/<X>/.codex-plugin/plugin.json`. Подключить командами: `codex plugin marketplace add <путь-к-репо>` → `codex plugin add <plugin>@gigma-skills` (плагины: `gigma-erp`, `gigma-consultant`, `vps-support`, `glaim`, `development-workflow`). Манифесты проходят `validate_plugin.py`.
  2. **Зеркало** `.codex/skills/` — копии скилов, видны когда Codex запущен в этом репо (фолбэк без установки).

Скилы (`SKILL.md`) общие для Claude и Codex. ⚠ Frontmatter `description`/`when_to_use` со значением, содержащим `: ` (двоеточие-пробел), **обязательно в кавычках** — иначе строгий YAML-парсер Codex отвергает скил.

**Канон — `plugins/`.** `.codex/skills/` и `.codex/reference/` — зеркало; синхронизировать одной командой: **`bash sync-codex.sh`** (пересобирает `.codex` из `plugins/`).

## PR / monster review

После создания PR и после каждого `git push` в PR-ветку запускать polling ревью: ждать monster review / Codex review / Claude review, если они подключены, смотреть GitHub comments/reviews и inbox. Блокеры и реальные замечания чинить в той же ветке, пушить follow-up commit и снова ждать re-review. Не объявлять PR готовым, пока последний review-цикл не подтвердил, что блокеров нет; если автоматический monster недоступен, явно сказать об этом и провести локальный monster-review ролями.

## Роли (скилы в `.codex/skills/`)

### Консультант по интернет-магазинам на Gigma (e-commerce)
Полный цикл: бриф → подбор решения → КП → план запуска → передача в операционные «руки».
- Вход: **`ecommerce-consultant`** (дирижёр-персона).
- Фазы: `ecommerce-discovery`, `ecommerce-solution-fit`, `ecommerce-commercial-proposal`, `ecommerce-launch-plan`.
- Факты сервиса: `.codex/reference/ecommerce-capabilities.md`.
- Канон API Gigma (источник правды): https://artypoul-docs-gigma-7b80.twc1.net/erp-rules.txt
- Операционные «руки»: скилы `create-tenant`, `load-nomenclature` (плагин `gigma-erp`) — тоже зеркалятся в `.codex/skills/`.
- MCP agents: скил `request-agent-access` получает agent token через self-service заявку на почту owner/admin, а `mcp-agent-access` подключает внешний MCP-сервер через ERP agent-user и обычный Sanctum Bearer token; старый `/api/mcp/*` слой не возвращать.
- Miniapps auth: скил `miniapp-auth` фиксирует канонический counterparty route, проверку signed contact и запрет на лишние публичные alias routes.
- Callback auth: скил `counterparty-callback-auth` покрывает вход клиента по звонку через `POST /api/counterparty/callback_auth/init|status`, одноразовую выдачу `access_token`, App Token header и UCaller flow.
- Frontend API: скил `connect-frontend-api` подключает storefront/frontend/miniapp к Gigma API по канону `Docs-gigma`.
- Payment webhooks: скил `receive-order-paid-webhook` подключает внешний backend/сервис к Gigma ERP `order.paid` webhook с HMAC-подписью, timestamp freshness и идемпотентностью по `event_id`.

### Консультант по подписке сервиса «Твой ВПС»
Сервис — личный приватный сервер по подписке. Помогает управлять подпиской и установить/настроить приложение для подключения; при поломке — эскалирует в Telegram **@artypoul**. ⚠ Формулировки нейтральные: не позиционировать как «VPN/обход блокировок», не обсуждать доступ к запрещённому (см. reference раздел «Формулировки и правовая рамка»).
- Вход: **`vps-support`** (дирижёр-персона).
- Под-скилы: `vps-connect` (подключение в HAPP и аналогах), `vps-troubleshoot` (диагностика + эскалация).
- Факты сервиса: `.codex/reference/vps-service-facts.md`.

### GLAIM agent bridge
Скилы для GLAIM — операционной системы для AI-агентов и source-neutral bridge.
- Вход: **`connect-chat-frontend`** — подключение miniapp, сайта, витрины или другого frontend-источника напрямую к GLAIM source-chat API.
- Контракт чата: `.codex/reference/chat-frontend-contract.md`.
- Главное правило: source token — клиентский credential только для `/api/v2/sources/{source}/chat/*`; Gigma backend/BFF в канонической цепочке нет, agent token и `X-Control-Secret` во frontend не попадают.

### Development workflow
Общие скилы разработки, не привязанные к продуктовому домену.
- Вход: **`development-handoff`** — проверяемый handoff перед продолжением PR, фиксом review, передачей агенту или работой со скилами/плагинами.
- Главное правило: продолжать работу от фактов Git/GitHub/CI/локальных файлов, а не от устаревшей памяти чата; перед skill move/add/remove проверять ownership, версии плагинов, marketplace discovery, `.codex` sync и re-review.

## Принцип для всех

Не выдумывать возможности — сверять с reference/каноном; говорить с пользователем простым языком; при реальной поломке/спорной развилке — эскалировать (Gigma — письмом владельцу; «Твой ВПС» — в Telegram @artypoul).
