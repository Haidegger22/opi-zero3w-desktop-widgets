# Установка виджетов — по шагам (copy-paste)

Для Debian 13 + MATE (X11), экран 1024×600 (Orange Pi Zero 3W).
Каждый блок можно вставить в терминал целиком.

---

## Быстрый путь (рекомендуется) — установщик

```bash
git clone https://github.com/Haidegger22/opi-zero3w-desktop-widgets.git
cd opi-zero3w-desktop-widgets
./install.sh                 # проверит зависимости, скопирует скрипты, поставит автозапуск
# ./install.sh --yes         # + доустановить недостающие пакеты через apt
# ./install.sh --run         # + сразу запустить виджеты
# ./install.sh --no-autostart  # без автозапуска
```

Что делает `install.sh`:

1. проверяет `gi` / `cairo` / `PIL` / GTK3 и (с `--yes`) доустанавливает недостающее;
2. копирует скрипты в `~/.local/bin` с правом на запуск;
3. ставит автозапуск в `~/.config/autostart`, **подставляя твой `$HOME`** вместо `/home/orangepi`;
4. предупреждает, если не найден `pactl` (без него шторка громкости не меняет звук);
5. с `--run` запускает карусель, температуру и шторку.

---

## То же самое вручную

### Шаг 1. Зависимости

```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil librsvg2-common
# pactl (для шторки громкости) — один из вариантов:
sudo apt install -y pulseaudio-utils      # или pipewire-pulse
```

### Шаг 2. Скачать репозиторий

```bash
cd ~
git clone https://github.com/Haidegger22/opi-zero3w-desktop-widgets.git
cd ~/opi-zero3w-desktop-widgets
```

### Шаг 3. Скрипты

```bash
mkdir -p ~/.local/bin
install -m 755 app-carousel-v.py app-carousel.py cpu-temp-float.py volume-drawer.py ~/.local/bin/
ls -l ~/.local/bin/
```

### Шаг 4. Автозапуск (пути подставляются автоматически)

```bash
mkdir -p ~/.config/autostart
cd ~/opi-zero3w-desktop-widgets
for f in autostart/*.desktop; do
  sed "s|/home/orangepi|$HOME|g" "$f" > ~/.config/autostart/"$(basename "$f")"
done
cat ~/.config/autostart/app-carousel.desktop   # проверь, что путь твой
```

### Шаг 5. Запустить сейчас (без перезагрузки)

```bash
export DISPLAY=:0 XAUTHORITY=$HOME/.Xauthority
~/.local/bin/app-carousel-v.py &   # карусель (вертикальная, основная)
~/.local/bin/cpu-temp-float.py &   # температура CPU
~/.local/bin/volume-drawer.py &    # шторка громкости
```

### Шаг 6. Проверка

- Карусель появляется **справа по центру**, окна её перекрывают (тип окна `DOCK`);
- виджет температуры — **правый нижний угол**, обновление раз в 5 с;
- шторка громкости — **полоска внизу по центру**, тап/свайп вверх выдвигает панель.

```bash
pgrep -af "app-carousel-v|cpu-temp-float|volume-drawer"
DISPLAY=:0 xdotool search --name "app-carousel" | head -1 | xargs -I{} xprop -id {} _NET_WM_WINDOW_TYPE
```

---

## Важно

- Требуется **X11** (не Wayland) и рабочий стол MATE.
- Chromium открывается **через прокси** `127.0.0.1:7890` (FlClashX/mihomo) — порт задаётся
  константой `CHROMIUM_PROXY` в начале `app-carousel-v.py`. **Если прокси у тебя нет — поставь пустую
  строку** `CHROMIUM_PROXY = ""`, иначе Chromium не сможет открывать страницы.
- Иконки приложений берутся по путям из списка `APPS` — они должны существовать в системе.
- RetroArch запускается командой `RETRO_CMD` (по умолчанию `retroarch`) — если у тебя свой
  скрипт запуска, укажи его путь в этой константе.

## Откат

```bash
pkill -f app-carousel-v.py; pkill -f cpu-temp-float.py; pkill -f volume-drawer.py
rm -f ~/.config/autostart/app-carousel.desktop \
      ~/.config/autostart/cpu-temp-float.desktop \
      ~/.config/autostart/volume-drawer.desktop
rm -f ~/.local/bin/{app-carousel-v.py,app-carousel.py,cpu-temp-float.py,volume-drawer.py}
```

## Если нет git

Скачай архив и распакуй — содержимое идентично репозиторию:

```bash
cd ~
wget https://github.com/Haidegger22/opi-zero3w-desktop-widgets/archive/refs/heads/main.zip
unzip main.zip && cd opi-zero3w-desktop-widgets-main
./install.sh --yes --run
```

Источник истины — файлы в репозитории (в прежних версиях этой инструкции лежали копии кода;
они удалены, чтобы не расходиться с самими скриптами).
