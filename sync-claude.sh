#!/usr/bin/env bash
# Синхронизирует личную папку скилов Claude из канона plugins/.
# Canonical source = plugins/<plugin>/{skills,reference}; Claude читает
# ~/.claude/skills + ~/.claude/reference (скилы резолвят ../../reference/).
#
# Запуск: bash sync-claude.sh [--dest ПУТЬ] [--plugin ИМЯ]...
#   --dest    корень Claude (по умолчанию ~/.claude или $CLAUDE_HOME)
#   --plugin  синхронизировать только указанные плагины; можно повторять
#
# Скрипт трогает ТОЛЬКО скилы, пришедшие из этого репозитория: личные скилы,
# написанные вручную, не удаляются. Полная пересборка папки была бы опаснее —
# в ~/.claude/skills лежит и то, чего в репозитории нет.
set -euo pipefail
cd "$(dirname "$0")"

dest="${CLAUDE_HOME:-$HOME/.claude}"
plugins=()

while [ $# -gt 0 ]; do
  case "$1" in
    --dest)   dest="$2"; shift 2 ;;
    --plugin) plugins+=("$2"); shift 2 ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 2 ;;
  esac
done

# Без --plugin берём все плагины, у которых есть skills/.
if [ ${#plugins[@]} -eq 0 ]; then
  for plugin in plugins/*/; do
    [ -d "${plugin}skills" ] && plugins+=("$(basename "$plugin")")
  done
fi

mkdir -p "$dest/skills" "$dest/reference"

copied_skills=0
copied_refs=0

for name in "${plugins[@]}"; do
  plugin="plugins/$name"
  [ -d "$plugin" ] || { echo "Нет такого плагина: $name" >&2; exit 2; }

  if [ -d "$plugin/skills" ]; then
    for skill in "$plugin/skills"/*/; do
      [ -f "${skill}SKILL.md" ] || continue
      skill_name="$(basename "$skill")"
      # Пересоздаём конкретный скил целиком, чтобы не оставлять файлы,
      # удалённые в каноне.
      rm -rf "$dest/skills/$skill_name"
      cp -r "$skill" "$dest/skills/$skill_name"
      # Артефакты сборки Python не нужны на стороне Claude.
      find "$dest/skills/$skill_name" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
      copied_skills=$((copied_skills + 1))
    done
  fi

  if [ -d "$plugin/reference" ]; then
    for ref in "$plugin/reference"/*; do
      [ -f "$ref" ] || continue
      cp "$ref" "$dest/reference/"
      copied_refs=$((copied_refs + 1))
    done
  fi
done

echo "Claude sync OK: ${copied_skills} skills, ${copied_refs} reference files -> ${dest}"
