#!/usr/bin/env bash
# ============================================================================
#  Установщик виджетов рабочего стола Orange Pi Zero 3W (X11 / MATE / GTK3)
#  Копирует скрипты в ~/.local/bin, ставит автозапуск, проверяет зависимости.
#
#  Использование:
#     ./install.sh                 # установить (зависимости только проверить)
#     ./install.sh --yes           # доустановить недостающие пакеты через apt
#     ./install.sh --no-autostart  # не добавлять автозапуск
#     ./install.sh --run           # сразу запустить виджеты на DISPLAY=:0
# ============================================================================
set -euo pipefail

BIN="$HOME/.local/bin"
AUTOSTART="$HOME/.config/autostart"
SRC="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS=(app-carousel-v.py app-carousel.py cpu-temp-float.py volume-drawer.py)
APT_PKGS=(python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil python3-cairo)

YES=0; DO_AUTOSTART=1; DO_RUN=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y)        YES=1 ;;
    --no-autostart)  DO_AUTOSTART=0 ;;
    --run)           DO_RUN=1 ;;
    -h|--help)       sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Неизвестный флаг: $arg (см. --help)"; exit 2 ;;
  esac
done

say() { printf '  %s\n' "$*"; }

echo "== 1/4. Проверка зависимостей =="
missing_pkgs=()
check_py() { python3 -c "import $1" >/dev/null 2>&1 || { say "✗ нет модуля: $1"; missing_pkgs+=("$2"); }; }
check_py gi python3-gi
check_py cairo python3-cairo
check_py PIL python3-pil
python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" >/dev/null 2>&1 \
  || { say "✗ нет GTK3-биндингов"; missing_pkgs+=("gir1.2-gtk-3.0"); }
command -v pactl >/dev/null 2>&1 || say "⚠ pactl не найден — шторка громкости не сможет менять громкость (пакет pulseaudio-utils или pipewire-pulse)"
command -v python3 >/dev/null 2>&1 || { echo "Нужен python3"; exit 1; }

if [ ${#missing_pkgs[@]} -gt 0 ]; then
  say "Не хватает пакетов: ${missing_pkgs[*]}"
  if [ "$YES" = "1" ]; then
    say "Устанавливаю через apt…"
    sudo apt update && sudo apt install -y "${missing_pkgs[@]}"
  else
    say "Установи вручную:  sudo apt install -y ${missing_pkgs[*]}"
    say "или повтори запуск с флагом --yes"
    exit 1
  fi
else
  say "✓ все нужные модули на месте (gi, cairo, PIL, GTK3)"
fi

echo "== 2/4. Скрипты → $BIN =="
mkdir -p "$BIN"
for f in "${SCRIPTS[@]}"; do
  if [ -f "$SRC/$f" ]; then
    install -m 755 "$SRC/$f" "$BIN/$f"
    say "✓ $f"
  else
    say "⚠ нет файла $f — пропускаю"
  fi
done

echo "== 3/4. Автозапуск =="
if [ "$DO_AUTOSTART" = "1" ]; then
  mkdir -p "$AUTOSTART"
  for f in "$SRC"/autostart/*.desktop; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    sed "s|/home/orangepi|$HOME|g" "$f" > "$AUTOSTART/$name"
    say "✓ $name (путь → $HOME)"
  done
else
  say "пропущено (--no-autostart)"
fi

echo "== 4/4. Запуск =="
if [ "$DO_RUN" = "1" ]; then
  export DISPLAY="${DISPLAY:-:0}"
  export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
  for f in app-carousel-v.py cpu-temp-float.py volume-drawer.py; do
    [ -x "$BIN/$f" ] || continue
    nohup "$BIN/$f" >/dev/null 2>&1 &
    say "✓ запущен $f (pid $!)"
  done
  say "Остановить:  pkill -f app-carousel-v.py  (и так же для остальных)"
else
  say "не запускаю. Вручную:"
  say "  DISPLAY=:0 XAUTHORITY=\$HOME/.Xauthority $BIN/app-carousel-v.py &"
  say "  DISPLAY=:0 XAUTHORITY=\$HOME/.Xauthority $BIN/cpu-temp-float.py &"
  say "  DISPLAY=:0 XAUTHORITY=\$HOME/.Xauthority $BIN/volume-drawer.py &"
fi

echo
echo "Готово. Настроить под себя: параметры в начале каждого скрипта"
echo "(APPS — список ярлыков; CHROMIUM_PROXY — прокси; RETRO_CMD — запуск RetroArch)."
