#!/usr/bin/env bash
# ============================================================================
#  Регенерирует раздел «копипаст-листинги» в INSTALL.md из реальных файлов.
#  Запуск:  ./tools/update-install-listings.sh
#
#  Зачем: листинги нужны для установки без git, но если держать их руками —
#  они расходятся с кодом. Этот скрипт вставляет актуальное содержимое файлов
#  между маркерами AUTO-LISTINGS в INSTALL.md.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TARGET="INSTALL.md"
START="<!-- AUTO-LISTINGS:START -->"
END="<!-- AUTO-LISTINGS:END -->"

FILES=(
  app-carousel-v.py
  app-carousel.py
  cpu-temp-float.py
  volume-drawer.py
  install.sh
  autostart/app-carousel.desktop
  autostart/cpu-temp-float.desktop
  autostart/volume-drawer.desktop
)

[ -f "$TARGET" ] || { echo "нет $TARGET"; exit 1; }
grep -q "$START" "$TARGET" || { echo "в $TARGET нет маркера $START"; exit 1; }
grep -q "$END"   "$TARGET" || { echo "в $TARGET нет маркера $END"; exit 1; }

lang_of() {
  case "$1" in
    *.py)       echo python ;;
    *.sh)       echo bash ;;
    *.desktop)  echo ini ;;
    *)          echo "" ;;
  esac
}

tmp="$(mktemp)"
# 1. всё до маркера START
awk -v s="$START" '$0 == s { exit } { print }' "$TARGET" > "$tmp"

# 2. сгенерированный блок
{
  echo "$START"
  echo
  echo "> Раздел сгенерирован из файлов репозитория. Не правь его руками — правь файлы"
  echo "> и запусти \`tools/update-install-listings.sh\`."
  echo
  for f in "${FILES[@]}"; do
    [ -f "$f" ] || continue
    echo "### \`$f\`"
    echo
    echo '```'"$(lang_of "$f")"
    cat "$f"
    echo '```'
    echo
  done
  echo "$END"
} >> "$tmp"

# 3. всё после маркера END
awk -v e="$END" 'found { print } $0 == e { found = 1 }' "$TARGET" >> "$tmp"

mv "$tmp" "$TARGET"
echo "✓ $TARGET обновлён: $(wc -l < "$TARGET") строк, файлов в листингах: ${#FILES[@]}"
