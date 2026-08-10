#!/usr/bin/env bash
# Синхронизирует личную папку скилов Claude из канона plugins/.
# Canonical source = plugins/<plugin>/{skills,reference}; Claude читает
# ~/.claude/skills + ~/.claude/reference (скилы резолвят ../../reference/).
#
# Запуск: bash sync-claude.sh [--dest ПУТЬ] [--plugin ИМЯ]... [--adopt ИМЯ]... [--prune]
#   --dest    корень Claude (по умолчанию ~/.claude или $CLAUDE_HOME)
#   --plugin  синхронизировать только указанные плагины; можно повторять
#   --adopt   взять под управление изменённый чужой скил (перезаписать)
#   --prune   удалить управляемые скилы, которых больше нет в каноне
#
# ЛИЧНЫЕ СКИЛЫ НЕПРИКОСНОВЕННЫ. Имена в каноне и в личной папке пересекаются
# (например `feature`), поэтому скрипт ведёт реестр того, что создал сам, и
# отказывается перезаписывать директорию, которой в реестре нет. Исключение —
# директория, побайтно совпадающая с каноном: это результат прежней синхрони-
# зации, её можно принять молча.
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

# Полный канон нужен всегда: --prune сверяется с ним, а не с выборкой,
# иначе `--plugin X --prune` снёс бы управляемые скилы всех остальных плагинов.
canon_all=()
for plugin in plugins/*/; do
  [ -d "${plugin}skills" ] || continue
  for skill in "${plugin}skills"/*/; do
    [ -f "${skill}SKILL.md" ] && canon_all+=("$(basename "$skill")")
  done
done

# Все имена плагинов проверяем ДО первой записи: иначе опечатка во втором
# аргументе оставила бы половину скилов скопированной, но не внесённой в реестр.
if [ ${#plugins[@]} -eq 0 ]; then
  for plugin in plugins/*/; do
    [ -d "${plugin}skills" ] && plugins+=("$(basename "$plugin")")
  done
else
  for name in "${plugins[@]}"; do
    [ -d "plugins/$name" ] || { echo "Нет такого плагина: $name" >&2; exit 2; }
  done
fi

manifest="$dest/.gigma-managed-skills"
mkdir -p "$dest/skills" "$dest/reference"
touch "$manifest"

is_managed() { grep -Fxq "$1" "$manifest"; }
is_adopted() { for a in ${adopt+"${adopt[@]}"}; do [ "$a" = "$1" ] && return 0; done; return 1; }
in_canon()   { for c in ${canon_all+"${canon_all[@]}"}; do [ "$c" = "$1" ] && return 0; done; return 1; }
# Директория, совпадающая с каноном, — наша прежняя копия, а не чужой скил.
# __pycache__ исключён: копия его не получает, и без этого любая прежняя
# синхронизация выглядела бы «изменённой чужой».
same_as_canon() { diff -r -q -x '__pycache__' "$1" "$2" >/dev/null 2>&1; }

synced=()
copied_refs=0
conflicts=()

for name in "${plugins[@]}"; do
  plugin="plugins/$name"

  if [ -d "$plugin/skills" ]; then
    for skill in "$plugin/skills"/*/; do
      [ -f "${skill}SKILL.md" ] || continue
      skill_name="$(basename "$skill")"
      target="$dest/skills/$skill_name"

      if [ -e "$target" ] && ! is_managed "$skill_name" && ! is_adopted "$skill_name" \
         && ! same_as_canon "$skill" "$target"; then
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
  echo "ОТКАЗ: в $dest/skills уже есть изменённые скилы, которые этот скрипт не создавал:" >&2
  for c in "${conflicts[@]}"; do echo "  - $c" >&2; done
  echo "Перезаписать осознанно: --adopt ИМЯ (повторять для каждого). Остальные скилы синхронизированы." >&2
fi

# Удаляем только управляемое, чего больше нет в ПОЛНОМ каноне: скил другого
# плагина, не выбранного через --plugin, из канона никуда не делся.
removed=0
if [ "$prune" = "1" ]; then
  while IFS= read -r known; do
    [ -n "$known" ] || continue
    in_canon "$known" && continue
    if [ -d "$dest/skills/$known" ]; then
      rm -rf "$dest/skills/$known"
      removed=$((removed + 1))
    fi
  done < "$manifest"
fi

# Реестр = прежние управляемые (за вычетом удалённых) + синхронизированные сейчас.
{
  while IFS= read -r known; do
    [ -n "$known" ] || continue
    if [ "$prune" = "1" ] && ! in_canon "$known"; then continue; fi
    echo "$known"
  done < "$manifest"
  for s in ${synced+"${synced[@]}"}; do echo "$s"; done
} | sort -u > "$manifest.tmp"
mv "$manifest.tmp" "$manifest"

echo "Claude sync OK: ${#synced[@]} skills, ${copied_refs} reference files -> ${dest}"
[ "$removed" -gt 0 ] && echo "Удалено устаревших управляемых скилов: ${removed}"
[ ${#conflicts[@]} -gt 0 ] && exit 3
exit 0
