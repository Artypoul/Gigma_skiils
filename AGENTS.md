# AGENTS.md — бриф для Codex

Этот репозиторий — каталог скилов-консультантов. Две системы читают его по-разному:

- **Claude Code** — через маркетплейс `.claude-plugin/marketplace.json` → плагины в `plugins/`.
- **Codex** — двумя путями:
  1. **Codex-маркетплейс**: `.agents/plugins/marketplace.json` + `plugins/<X>/.codex-plugin/plugin.json`. Подключить командами: `codex plugin marketplace add <путь-к-репо>` → `codex plugin add <plugin>@gigma-skills` (плагины: `gigma-erp`, `gigma-consultant`, `vps-support`, `glaim`). Манифесты проходят `validate_plugin.py`.
  2. **Зеркало** `.codex/skills/` — копии скилов, видны когда Codex запущен в этом репо (фолбэк без установки).

Скилы (`SKILL.md`) общие для Claude и Codex. ⚠ Frontmatter `description`/`when_to_use` со значением, содержащим `: ` (двоеточие-пробел), **обязательно в кавычках** — иначе строгий YAML-парсер Codex отвергает скил.

**Канон — `plugins/`.** `.codex/skills/` и `.codex/reference/` — зеркало; синхронизировать одной командой: **`bash sync-codex.sh`** (пересобирает `.codex` из `plugins/`).

## Роли (скилы в `.codex/skills/`)

### Консультант по интернет-магазинам на Gigma (e-commerce)
Полный цикл: бриф → подбор решения → КП → план запуска → передача в операционные «руки».
- Вход: **`ecommerce-consultant`** (дирижёр-персона).
- Фазы: `ecommerce-discovery`, `ecommerce-solution-fit`, `ecommerce-commercial-proposal`, `ecommerce-launch-plan`.
- Факты сервиса: `.codex/reference/ecommerce-capabilities.md`.
- Канон API Gigma (источник правды): https://artypoul-docs-gigma-7b80.twc1.net/erp-rules.txt
- Операционные «руки»: скилы `create-tenant`, `load-nomenclature` (плагин `gigma-erp`) — тоже зеркалятся в `.codex/skills/`.
- MCP agents: скил `mcp-agent-access` подключает внешний MCP-сервер через ERP agent-user и обычный Sanctum Bearer token; старый `/api/mcp/*` слой не возвращать.
- Miniapps auth: скил `miniapp-auth` фиксирует канонический counterparty route, проверку signed contact и запрет на лишние публичные alias routes.
- Frontend API: скил `connect-frontend-api` подключает storefront/frontend/miniapp к Gigma API по канону `Docs-gigma`.

### Консультант по подписке сервиса «Твой ВПС»
Сервис — личный приватный сервер по подписке. Помогает управлять подпиской и установить/настроить приложение для подключения; при поломке — эскалирует в Telegram **@artypoul**. ⚠ Формулировки нейтральные: не позиционировать как «VPN/обход блокировок», не обсуждать доступ к запрещённому (см. reference раздел «Формулировки и правовая рамка»).
- Вход: **`vps-support`** (дирижёр-персона).
- Под-скилы: `vps-connect` (подключение в HAPP и аналогах), `vps-troubleshoot` (диагностика + эскалация).
- Факты сервиса: `.codex/reference/vps-service-facts.md`.

### GLAIM agent bridge
Скилы для GLAIM — операционной системы для AI-агентов и source-neutral bridge.
- Вход: **`connect-chat-frontend`** — подключение web/miniapp frontend к GLAIM source-chat API через безопасный backend/BFF.
- Контракт чата: `.codex/reference/chat-frontend-contract.md`.
- Главное правило: production frontend не получает `X-Source-Secret`, agent token или `X-Control-Secret`.

## Принцип для всех

Не выдумывать возможности — сверять с reference/каноном; говорить с пользователем простым языком; при реальной поломке/спорной развилке — эскалировать (Gigma — письмом владельцу; «Твой ВПС» — в Telegram @artypoul).
