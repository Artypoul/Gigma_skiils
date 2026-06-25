# AGENTS.md — бриф для Codex

Этот репозиторий — каталог скилов-консультантов. Две системы читают его по-разному:

- **Claude Code** — через маркетплейс `.claude-plugin/marketplace.json` → плагины в `plugins/`.
- **Codex** — через папку **`.codex/skills/`** (маркетплейс Codex не читает). Эти скилы — **копии** плагинов из `plugins/`.

**Канон — `plugins/`.** `.codex/skills/` и `.codex/reference/` держать в синхроне с ним при правках (формат `SKILL.md` одинаковый, поэтому копия 1:1).

## Роли (скилы в `.codex/skills/`)

### Консультант по интернет-магазинам на Gigma (e-commerce)
Полный цикл: бриф → подбор решения → КП → план запуска → передача в операционные «руки».
- Вход: **`ecommerce-consultant`** (дирижёр-персона).
- Фазы: `ecommerce-discovery`, `ecommerce-solution-fit`, `ecommerce-commercial-proposal`, `ecommerce-launch-plan`.
- Факты сервиса: `.codex/reference/ecommerce-capabilities.md`.
- Канон API Gigma (источник правды): https://artypoul-docs-gigma-7b80.twc1.net/erp-rules.txt
- Операционные «руки» (создание тенанта, загрузка каталога) — плагин `gigma-erp` (его скилы тоже в `plugins/`).

### Консультант для пользователей VPN-сервиса «Твой ВПС»
Помогает подключить VPN и решить проблемы, при поломке — эскалирует в Telegram **@artypoul**.
- Вход: **`vps-support`** (дирижёр-персона).
- Под-скилы: `vps-connect` (подключение в HAPP и аналогах), `vps-troubleshoot` (диагностика + эскалация).
- Факты сервиса: `.codex/reference/vps-service-facts.md`.

## Принцип для обоих

Не выдумывать возможности — сверять с reference/каноном; говорить с пользователем простым языком; при реальной поломке/спорной развилке — эскалировать (Gigma — письмом владельцу; VPN — в Telegram @artypoul).
