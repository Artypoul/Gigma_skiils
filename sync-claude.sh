#!/usr/bin/env bash
# Синхронизирует личную папку скилов Claude из канона plugins/.
# Canonical source = plugins/<plugin>/{skills,reference}; Claude читает
# ~/.claude/skills + ~/.claude/reference (скилы резолвят ../../reference/).
#
# Запуск: bash sync-claude.sh [--dest ПУТЬ] [--plugin ИМЯ]... [--adopt ИМЯ]... [--prune]
#   --dest    корень Claude (по умолчанию ~/.claude или $CLAUDE_HOME)
#   --plugin  синхронизировать только указанные плагины; можно повторять
#   --adopt   взять под управление уже существующий чужой скил (перезаписать)
#   --prune   удалить управляемые скилы, которых больше нет в каноне
#
# ЛИЧНЫЕ СКИЛЫ НЕПРИКОСНОВЕННЫ. Имена в каноне и в личной папке пересекаются
# (например `feature`), поэтому скрипт ведёт реестр того, что он создал сам, и
# отказывается перезаписывать директорию, которой в реестре нет. Такое имя
# нужно либо явно передать через --adopt, либо переименовать личный скил.
set -euo pipefail
cd "$(dirname "$0")"

dest="${CLAUDE_HOME:-$HOME/.claude}"
plugins=()
adopt=()
prune=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dest)   dest="$2"; shift 2 ;;
    --plugin) plugins+=("$2"); shift 2 ;;
    --adopt)  adopt+=("$2"); shift 2 ;;
    --prune)  prune=1; shift ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 2 ;;
  esac
done

# Без --plugin берём все плагины, у которых есть skills/.
if [ ${#plugins[@]} -eq 0 ]; then
  for plugin in plugins/*/; do
    [ -d "${plugin}skills" ] && plugins+=("$(basename "$plugin")")
  done
fi

manifest="$dest/.gigma-managed-skills"
mkdir -p "$dest/skills" "$dest/reference"
touch "$manifest"

is_managed() { grep -Fxq "$1" "$manifest"; }
is_adopted() { for a in ${adopt+"${adopt[@]}"}; do [ "$a" = "$1" ] && return 0; done; return 1; }

synced=()
copied_refs=0
conflicts=()

for name in "${plugins[@]}"; do
  plugin="plugins/$name"
  [ -d "$plugin" ] || { echo "Нет такого плагина: $name" >&2; exit 2; }

  if [ -d "$plugin/skills" ]; then
    for skill in "$plugin/skills"/*/; do
      [ -f "${skill}SKILL.md" ] || continue
      skill_name="$(basename "$skill")"
      target="$dest/skills/$skill_name"

      if [ -e "$target" ] && ! is_managed "$skill_name" && ! is_adopted "$skill_name"; then
        conflicts+=("$skill_name")
        continue
      fi

      # Пересоздаём скил целиком, чтобы не оставлять файлы, удалённые в каноне.
      rm -rf "$target"
      cp -r "$skill" "$target"
      # Артефакты сборки Python на стороне Claude не нужны.
      find "$target" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
      synced+=("$skill_name")
    done
  fi

  if [ -d "$plugin/reference" ]; then
    # Рекурсивно: у части плагинов reference разложен по подпапкам.
    cp -r "$plugin/reference/." "$dest/reference/"
    copied_refs=$((copied_refs + $(find "$plugin/reference" -type f | wc -l | tr -d ' ')))
  fi
done

if [ ${#conflicts[@]} -gt 0 ]; then
  echo "ОТКАЗ: в $dest/skills уже есть скилы, которые этот скрипт не создавал:" >&2
  for c in "${conflicts[@]}"; do echo "  - $c" >&2; done
  echo "Перезаписать осознанно: --adopt ИМЯ (повторять для каждого). Остальные скилы синхронизированы." >&2
fi

# Удаляем только то, чем управляли сами и чего больше нет в каноне.
removed=0
if [ "$prune" = "1" ]; then
  while IFS= read -r known; do
    [ -n "$known" ] || continue
    for s in ${synced+"${synced[@]}"}; do [ "$s" = "$known" ] && continue 2; done
    if [ -d "$dest/skills/$known" ]; then
      rm -rf "$dest/skills/$known"
      removed=$((removed + 1))
    fi
  done < "$manifest"
fi

# Реестр = управляемые ранее + синхронизированные сейчас (при --prune только текущие).
{
  if [ "$prune" != "1" ]; then cat "$manifest"; fi
  for s in ${synced+"${synced[@]}"}; do echo "$s"; done
} | sort -u > "$manifest.tmp"
mv "$manifest.tmp" "$manifest"

echo "Claude sync OK: ${#synced[@]} skills, ${copied_refs} reference files -> ${dest}"
[ "$removed" -gt 0 ] && echo "Удалено устаревших управляемых скилов: ${removed}"
[ ${#conflicts[@]} -gt 0 ] && exit 3
exit 0
