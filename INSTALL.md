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

1. печатает текущие `RETRO_CMD` и `CHROMIUM_PROXY` — проверь их перед установкой;
2. проверяет `gi` / `cairo` / `PIL` / GTK3 и (с `--yes`) доустанавливает недостающее;
3. копирует скрипты в `~/.local/bin` с правом на запуск, **делая бэкап (`.bak-дата`)** того, что заменяет;
4. ставит автозапуск в `~/.config/autostart`, **подставляя твой `$HOME`** вместо `/home/orangepi` (тоже с бэкапом);
5. предупреждает, если не найден `pactl` (без него шторка громкости не меняет звук);
6. с `--run` запускает карусель, температуру и шторку.

---

## То же самое вручную

### Шаг 1. Зависимости

```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil librsvg2-common
# pactl (для шторки громкости) — один из вариантов:
sudo apt install -y pulseaudio-utils      # или pipewire-pulse
```

Опционально (включает «сон» карусели, см. Шаг 7):

```bash
sudo apt install -y python3-xlib
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

### Шаг 7 (опционально). Сон карусели — анимация только когда виджет реально виден

Если установлен `python3-xlib`, карусель каждые 220 мс проверяет по стеку окон X11, не
перекрыта ли она чужим окном. Перекрыта — полностью перестаёт перерисовываться (карусель
закрыта окном, а Xorg при этом не жжёт CPU на полупрозрачных слоях). Фаза кометы считается
по «времени без сна», поэтому после пробуждения анимация продолжается ровно с того места,
где замерла — без прыжка.

Замер на Orange Pi Zero 3W (15 с на состояние, по `/proc`):

| Состояние | Карусель, 1 ядро | Xorg, 1 ядро | Вся система, 8 ядер |
|---|---|---|---|
| рабочий стол открыт (анимация) | 31,0% | 83,9% | 19,6% |
| перекрыта окном (сон) | **1,7%** | 21,1% | 7,9% |

Переключение видно по выводу процесса (или в `journalctl`, если виджет запущен юнитом):

```
[carousel] рабочий стол закрыт — сон
[carousel] рабочий стол открыт — анимация
```

Выключатель сна — переменная окружения: `CAROUSEL_NO_SLEEP=1 ~/.local/bin/app-carousel-v.py`.

Без `python3-xlib` виджет просто работает как раньше (импорт обёрнут в `try`), ошибок не будет.
Второй экземпляр не запустится — защита через `flock` на `$XDG_RUNTIME_DIR/app-carousel-v.lock`.

---

## Важно

- Требуется **X11** (не Wayland) и рабочий стол MATE.
- **Сон карусели** (см. Шаг 7) требует `python3-xlib`; это единственная необязательная
  зависимость — без неё виджет рисуется постоянно, как в прежних версиях.
- Chromium открывается **через прокси** `127.0.0.1:7890` (FlClashX/mihomo) — порт задаётся
  константой `CHROMIUM_PROXY` в начале `app-carousel-v.py`. **Если прокси у тебя нет — поставь пустую
  строку** `CHROMIUM_PROXY = ""`, иначе Chromium не сможет открывать страницы.
- Chromium запускается **с отладочным портом** (`CHROMIUM_DEBUG_PORT = 9222`) — так браузером
  могут пользоваться инструменты автоматизации (поиск через реальный браузер, чтение страниц
  с логинами) даже после перезагрузки. Не нужен порт — поставь `CHROMIUM_DEBUG_PORT = 0`.
  Проверка: `curl -s --noproxy '*' http://127.0.0.1:9222/json/version`.
- Иконки приложений берутся по путям из списка `APPS` — они должны существовать в системе.
- RetroArch запускается командой `RETRO_CMD` (по умолчанию `retroarch`) — если у тебя свой
  скрипт запуска, укажи его путь в этой константе **до** запуска установщика, иначе ярлык
  будет запускать голый `retroarch`.

## Откат

```bash
pkill -f app-carousel-v.py; pkill -f cpu-temp-float.py; pkill -f volume-drawer.py
rm -f ~/.config/autostart/app-carousel.desktop \
      ~/.config/autostart/cpu-temp-float.desktop \
      ~/.config/autostart/volume-drawer.desktop
rm -f ~/.local/bin/{app-carousel-v.py,app-carousel.py,cpu-temp-float.py,volume-drawer.py}
```

## Если нет git

**Вариант А — архив:**

```bash
cd ~
wget https://github.com/Haidegger22/opi-zero3w-desktop-widgets/archive/refs/heads/main.zip
unzip main.zip && cd opi-zero3w-desktop-widgets-main
./install.sh --yes --run
```

**Вариант Б — копипаст:** полный код всех файлов — ниже. Раздел **сгенерирован** из файлов
репозитория скриптом `tools/update-install-listings.sh` (после правки скриптов запусти его,
чтобы инструкция не расходилась с кодом).

<!-- AUTO-LISTINGS:START -->

> Раздел сгенерирован из файлов репозитория. Не правь его руками — правь файлы
> и запусти `tools/update-install-listings.sh`.

### `app-carousel-v.py`

```python
#!/usr/bin/env python3
"""
Виджет-карусель приложений — ВЕРТИКАЛЬНАЯ версия (приклеена справа)
====================================================================
Окно типа DOCK + «ниже всех окон»: не исчезает при «показать рабочий стол»
(Fn+Enter), окна приложений перекрывают виджет.

ЭКОНОМИЯ CPU: если виджет перекрыт другим окном (рабочий стол не виден),
анимация замирает — таймер отрисовки не дёргает queue_draw, Xorg не
перерисовывает полупрозрачные слои. Как только рабочий стол снова открыт,
анимация продолжается с той же фазы (без прыжка).

Управление:
  • колесо мыши / стрелки ⌃⌄   — прокрутка
  • свайп пальцем (вертикально) — прокрутка (следует за пальцем)
  • тап по центральной иконке   — запуск приложения
  • тап по боковой иконке       — доводит её в центр
  • средний клик                — закрыть
"""
import os
import subprocess
import sys
import time
import math
import fcntl

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import cairo

try:
    gi.require_version("GdkX11", "3.0")
    from gi.repository import GdkX11
except Exception:
    GdkX11 = None

try:
    from Xlib import display as xdisplay, X as XX
except Exception:
    xdisplay = None

# ---- параметры ----
W, H = 240, 430      # вертикальное окно (расширено влево — под горизонтальное название)
STEP = 86.0          # шаг между иконками по вертикали
ICON = 52            # базовый размер иконки
CX = W - 66          # центр иконок — у правого края (название и точки слева)
BG_A = 0.0           # прозрачность подложки (0.0 = фон прозрачный)
NEON = (0.55, 1.00, 0.60)   # светлый неоновый зелёный
MARGIN_RIGHT = 6     # отступ от правого края экрана

# --- персональные настройки (правь под себя) ---
CHROMIUM_PROXY = "http://127.0.0.1:7890"  # прокси для Chromium; "" — без прокси (нет FlClash/mihomo)
CHROMIUM_CACHE = "1073741824"             # размер дискового кэша Chromium, байт (1 ГБ)
CHROMIUM_DEBUG_PORT = 9222                # отладочный порт (CDP) для инструментов; 0 — выключить
XCURSOR_THEME  = "comet-hidden"           # тема курсора (скрытый курсор-комета); "" — системная
RETRO_CMD      = "retroarch"              # команда запуска RetroArch (свой путь/скрипт — укажи здесь)
HOME_DIR       = os.path.expanduser("~")  # домашний каталог пользователя

XA = os.environ.get("XAUTHORITY", os.path.join(HOME_DIR, ".Xauthority"))
ENV = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0"), "XAUTHORITY": XA}

# команда Chromium собирается из настроек выше
_chromium = "chromium"
if XCURSOR_THEME:
    _chromium = f"env XCURSOR_THEME={XCURSOR_THEME} " + _chromium
_chromium += f" --disk-cache-size={CHROMIUM_CACHE}"
if CHROMIUM_PROXY:
    _chromium += (f" --proxy-server={CHROMIUM_PROXY}"
                  " --proxy-bypass-list='localhost;127.0.0.1;192.168.*;10.*;<local>'")
if CHROMIUM_DEBUG_PORT:
    # Без этих флагов Chromium недоступен по CDP (порт 9222) — ломается поиск через браузер
    # и чтение страниц с логинами. С флагами порт живёт и после перезагрузки, т.к. браузер
    # запускается именно из карусели.
    _chromium += (f" --remote-debugging-port={CHROMIUM_DEBUG_PORT}"
                  " --remote-allow-origins=*")

NO_SLEEP = os.environ.get("CAROUSEL_NO_SLEEP") == "1"   # 1 = не засыпать никогда
FPS_MS = 33            # ~30 fps — плавная комета, мягче по CPU
WATCH_MS = 220         # как часто проверяем, закрыт ли рабочий стол

# защита от второго экземпляра (автозапуск + ручной / сервисом)
LOCK_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "app-carousel-v.lock")
_lock_fh = None


def single_instance():
    """True — мы единственный экземпляр; False — уже запущен, надо выйти."""
    global _lock_fh
    try:
        _lock_fh = open(LOCK_PATH, "w")
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fh.write(str(os.getpid()))
        _lock_fh.flush()
        return True
    except Exception:
        return False

# подпись, файл иконки, команда запуска
APPS = [
    ("Chromium", "/usr/share/icons/hicolor/256x256/apps/chromium.png", _chromium),
    ("Telegram", "/usr/share/pixmaps/telegram.png", "flatpak run org.telegram.desktop"),
    ("Терминал", "/usr/share/icons/Papirus/48x48/apps/gnome-terminal.svg", "mate-terminal"),
    ("Домашняя папка", "/usr/share/icons/mate/256x256/places/user-home.png",
     "caja ~"),
    ("RetroArch", "/usr/share/pixmaps/retroarch.png", RETRO_CMD),]


def rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class CarouselV(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        # «приклеено» к рабочему столу: DOCK + ниже всех окон
        self.set_keep_below(True)
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        scr = self.get_screen()
        vis = scr.get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.set_size_request(W, H)
        self.resize(W, H)
        sw, sh = 1024, 600
        try:
            disp = Gdk.Display.get_default()
            mon = disp.get_primary_monitor() or disp.get_monitor(0)
            g = mon.get_geometry()
            sw, sh = g.width, g.height
        except Exception:
            pass
        # приклеена справа, по центру по вертикали
        self.move(sw - W - MARGIN_RIGHT, int((sh - H) / 2))

        # иконки
        self.pix = []
        for _, path, _ in APPS:
            try:
                self.pix.append(GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 128, 128, True))
            except Exception:
                self.pix.append(None)

        self._pos = 0.0
        self._target = 0.0
        self._press = None
        self._swiped = False
        self._bump_i = None    # иконка, которую тапнули (анимация нажатия)
        self._bump_t = 0.0     # время старта анимации нажатия
        self._start_pos = 0.0
        self._zones = []

        # --- сон, когда рабочий стол закрыт другим окном ---
        self._xdisp = None          # отдельное X-соединение для проверки перекрытия
        self._xroot = None
        self._xid = None
        self._sleeping = False
        self._pause_start = None
        self._paused_total = 0.0    # сколько времени проспали (сдвиг фазы кометы)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        GLib.timeout_add(FPS_MS, self._animate)   # ~30 fps — плавная комета, мягче по CPU
        GLib.timeout_add(WATCH_MS, self._watch)   # следим, виден ли рабочий стол

    # ---- проверка: перекрыт ли виджет другим окном ----
    def _now(self):
        """Время анимации: не считает время сна → комета продолжает с той же фазы."""
        if self._pause_start is not None:
            return self._pause_start - self._paused_total
        return time.time() - self._paused_total

    def _init_x(self):
        if xdisplay is None or NO_SLEEP:
            return False
        try:
            gw = self.get_window()
            if gw is None:
                return False
            self._xid = gw.get_xid()
            self._xdisp = xdisplay.Display()
            self._xroot = self._xdisp.screen().root
            return True
        except Exception:
            self._xdisp = None
            self._xroot = None
            self._xid = None
            return False

    def _occluded(self):
        """True — над нами (в нашем прямоугольнике) лежит видимое чужое окно."""
        if NO_SLEEP:
            return False
        if self._xid is None and not self._init_x():
            return False
        try:
            root = self._xroot
            kids = root.query_tree().children
            ids = [c.id for c in kids]

            # наше окно может быть вложено в рамку WM — поднимаемся до ребёнка root
            w = self._xdisp.create_resource_object("window", self._xid)
            for _ in range(5):
                if w.query_tree().parent.id == root.id:
                    break
                w = w.query_tree().parent
            if w.id not in ids:
                return False        # себя не нашли — считаем, что видно
            idx = ids.index(w.id)

            g = w.get_geometry()
            # ВАЖНО: в python-xlib метод вызывается у ОКНА-ПРИЁМНИКА
            # (root.translate_coords(w, 0, 0) = где лежит (0,0) окна w в root)
            c = root.translate_coords(w, 0, 0)
            x0, y0 = c.x, c.y
            x1, y1 = x0 + g.width, y0 + g.height

            for other in kids[idx + 1:]:          # только то, что ВЫШЕ нас
                try:
                    a = other.get_attributes()
                    if a.map_state != XX.IsViewable:
                        continue
                    g2 = other.get_geometry()
                    # всплывающие мелочи (подсказки/меню) не считаем за окно
                    if a.override_redirect and g2.width * g2.height < (x1 - x0) * (y1 - y0):
                        continue
                    c2 = root.translate_coords(other, 0, 0)
                except Exception:
                    continue
                if (c2.x < x1 and c2.x + g2.width > x0 and
                        c2.y < y1 and c2.y + g2.height > y0):
                    return True
            return False
        except Exception:
            # X-соединение могло отвалиться — пересоздадим при следующей проверке
            self._xid = None
            self._xdisp = None
            return False

    def _watch(self):
        occ = self._occluded()
        if occ != self._sleeping:
            self._sleeping = occ
            if occ:
                self._pause_start = time.time()
                print("[carousel] рабочий стол закрыт — сон", flush=True)
            else:
                if self._pause_start is not None:
                    self._paused_total += time.time() - self._pause_start
                    self._pause_start = None
                self.queue_draw()
                print("[carousel] рабочий стол открыт — анимация", flush=True)
        return True
    def _animate(self):
        if self._sleeping:
            return True            # спим: не рисуем вообще, CPU только на проверку
        if abs(self._target - self._pos) > 0.002:
            self._pos += (self._target - self._pos) * 0.22
        elif self._pos != self._target:
            self._pos = self._target
        self.queue_draw()
        return True

    # ---- отрисовка ----
    def on_draw(self, w, cr):
        if BG_A > 0:
            cr.set_source_rgba(0.03, 0.035, 0.05, BG_A)
            rounded_rect(cr, 0, 0, W, H, 20)
            cr.fill()

        cx = CX                 # иконки — у правого края виджета
        cy = H / 2.0
        self._zones = []
        now = self._now()       # время без сна — после пробуждения фаза продолжается
        pulse = 0.85 + 0.15 * math.sin(now * 2.4)
        gc = NEON

        # ---- НЕОНОВОЕ КОЛЬЦО вокруг центральной иконки (стиль «F.R.I.D.A.Y.») ----
        R = ICON * 0.95          # компактнее — не задевает точки слева
        # дорожка, по которой бежит дуга
        cr.set_line_width(1.1)
        cr.set_source_rgba(gc[0], gc[1], gc[2], 0.28)
        cr.arc(cx, cy, R, 0, 2 * math.pi)
        cr.stroke()
        # положение «головы» кометы — источник света
        a0 = (now * 1.15) % (2 * math.pi)
        light_x = cx + R * math.cos(a0)
        light_y = cy + R * math.sin(a0)

        # ---- ХВОСТ КОМЕТЫ: тянется ПОЗАДИ головы и затухает ----
        tail = math.radians(150)
        segs = 44
        for k in range(segs):
            f = k / segs                              # 0 — у головы, 1 — конец хвоста
            a_s = a0 - tail * (k + 1) / segs
            a_e = a0 - tail * k / segs
            wid = 2.8 * (1 - f) + 0.6 * f             # хвост тоньше к концу
            al = (1 - f) ** 2.2                       # яркость затухает
            # мягкое свечение вокруг хвоста
            cr.set_line_width(wid + 5.0 * (1 - f) + 1.5)
            cr.set_source_rgba(0.15, 1.00, 0.48, al * 0.16 * pulse)
            cr.arc(cx, cy, R, a_s, a_e)
            cr.stroke()
            # ядро хвоста
            cr.set_line_width(wid)
            cr.set_source_rgba(0.40, 1.00, 0.62, al * 0.95 * pulse)
            cr.arc(cx, cy, R, a_s, a_e)
            cr.stroke()

        # ---- ГОЛОВА КОМЕТЫ: самая яркая точка + мощное свечение ----
        for rad, al, col in ((13.0, 0.06, (0.25, 1.0, 0.55)),
                             (9.0, 0.12, (0.35, 1.0, 0.60)),
                             (5.5, 0.26, (0.55, 1.0, 0.70)),
                             (3.0, 1.00, (0.90, 1.00, 0.95))):
            cr.arc(light_x, light_y, rad, 0, 2 * math.pi)
            cr.set_source_rgba(col[0], col[1], col[2], al * pulse)
            cr.fill()

        order = sorted(range(len(APPS)), key=lambda i: -abs(i - self._pos))
        for i in order:
            d = i - self._pos
            if abs(d) > 2.4:
                continue
            scale = max(0.35, 1.0 - abs(d) * 0.30)
            size = ICON * scale * self._bump_scale(i)
            alpha = max(0.15, 1.0 - abs(d) * 0.42)
            y = cy + d * STEP
            x = cx + abs(d) * 6          # лёгкий сдвиг вправо для «глубины»

            pb = self.pix[i]
            if pb:
                cr.save()
                cr.translate(x - size / 2, y - size / 2)
                cr.scale(size / pb.get_width(), size / pb.get_height())
                Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
                cr.paint_with_alpha(alpha)
                cr.restore()

                # === ПАДАЮЩИЙ СВЕТ И ТЕНЬ (только у центральной иконки) ===
                # Дуга — источник света: её сторона иконки ярче, противоположная — в тени.
                if abs(d) < 0.5:
                    cr.save()
                    cr.rectangle(x - size / 2, y - size / 2, size, size)
                    cr.clip()
                    # ATOP — свет/тень ложатся ТОЛЬКО на непрозрачные пиксели
                    # иконки (не создают чёрный квадрат на прозрачном фоне PNG)
                    cr.set_operator(cairo.OPERATOR_ATOP)
                    # 1) свет: радиальное пятно от центра дуги
                    lit = cairo.RadialGradient(light_x, light_y, 1.0,
                                               light_x, light_y, size * 1.30)
                    lit.add_color_stop_rgba(0.0, 0.80, 1.00, 0.88, 0.50 * pulse)
                    lit.add_color_stop_rgba(0.55, 0.55, 1.00, 0.68, 0.16 * pulse)
                    lit.add_color_stop_rgba(1.0, 0.35, 1.00, 0.55, 0.0)
                    cr.set_source(lit)
                    cr.paint()
                    # 2) тень: линейно от источника к противоположной стороне
                    sh = cairo.LinearGradient(light_x, light_y,
                                              2 * cx - light_x, 2 * cy - light_y)
                    sh.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.0)
                    sh.add_color_stop_rgba(0.55, 0.0, 0.0, 0.0, 0.20)
                    sh.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.66)
                    cr.set_source(sh)
                    cr.paint()
                    cr.restore()
            else:
                cr.arc(x, y, size / 2, 0, 2 * math.pi)
                cr.set_source_rgba(0.25, 0.3, 0.4, alpha)
                cr.fill()

            if abs(d) < 0.5:
                # название — ГОРИЗОНТАЛЬНО, слева от точек, на уровне центра
                # со свечением: сначала зелёный ореол (смещённые копии), затем белый текст
                cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(13)
                ext = cr.text_extents(APPS[i][0])
                tx = 10
                ty = cy + ext.height / 2
                for ox, oy, al in ((-1.2, 0, .18), (1.2, 0, .18), (0, -1.2, .18),
                                   (0, 1.2, .18), (0, 0, .25)):
                    cr.set_source_rgba(0.15, 1.00, 0.50, al * pulse)
                    cr.move_to(tx + ox, ty + oy)
                    cr.show_text(APPS[i][0])
                cr.set_source_rgba(0.96, 1.00, 0.97, 0.98)   # светящееся ядро
                cr.move_to(tx, ty)
                cr.show_text(APPS[i][0])

            self._zones.append((y - size / 2 - 4, y + size / 2 + 4, i))

        # точки-индикаторы (вертикально, между названием и кольцом)
        n = len(APPS)
        total = n * 12
        y0 = cy - total / 2 + 6
        for i in range(n):
            px = CX - 68
            if i == round(self._pos):
                cr.arc(px, y0 + i * 12, 3.2, 0, 2 * math.pi)
                cr.set_source_rgba(gc[0], gc[1], gc[2], 0.95)
            else:
                cr.arc(px, y0 + i * 12, 2.2, 0, 2 * math.pi)
                cr.set_source_rgba(0.45, 0.5, 0.58, 0.6)
            cr.fill()
        return False

    # ---- события ----
    def on_scroll(self, w, ev):
        if ev.direction == Gdk.ScrollDirection.UP:
            self._target = max(0, self._target - 1)
        elif ev.direction == Gdk.ScrollDirection.DOWN:
            self._target = min(len(APPS) - 1, self._target + 1)
        else:
            return False
        self.queue_draw()
        return True

    def on_press(self, w, ev):
        if ev.button == 2:
            self.destroy()
            return True
        if ev.button == 1:
            self._press = (ev.x, ev.y, time.time(), list(self._zones))
            self._swiped = False
            self._start_pos = self._pos
            return True
        return False

    def on_motion(self, w, ev):
        if not self._press:
            return False
        x0, y0, t0, zones = self._press
        dy = ev.y - y0          # ВЕРТИКАЛЬНЫЙ свайп
        if not self._swiped and abs(dy) > 14:
            self._swiped = True
        if self._swiped:
            self._pos = max(0.0, min(len(APPS) - 1.0, self._start_pos - dy / STEP))
            self._target = self._pos
            self.queue_draw()
            return True
        return False

    def on_release(self, w, ev):
        if not self._press:
            return False
        x0, y0, t0, zones = self._press
        dt = time.time() - t0
        self._press = None
        if self._swiped:
            self._target = round(self._pos)
            self._swiped = False
            self.queue_draw()
            return True
        self._swiped = False
        if dt < 0.7:
            self._handle_tap(x0, y0, zones)
        return True

    def _bump_scale(self, i):
        if self._bump_i != i:
            return 1.0
        dt = time.time() - self._bump_t
        T = 0.34
        if dt >= T:
            self._bump_i = None
            return 1.0
        return 1.0 + 0.40 * math.sin(math.pi * dt / T)

    def _handle_tap(self, x, y, zones):
        for y1, y2, i in zones:
            # тап засчитываем только в колонке иконок (не по названию слева)
            if y1 <= y <= y2 and abs(x - CX) < 46:
                self._bump_i = i
                self._bump_t = time.time()
                print(f"[bump] нажатие на иконку {i} ({APPS[i][0]})", flush=True)
                if abs(i - self._pos) < 0.5:
                    subprocess.Popen(APPS[i][2], shell=True, env=ENV)
                else:
                    self._target = float(i)
                    self.queue_draw()
                return


if __name__ == "__main__":
    if not single_instance():
        print("[carousel] уже запущен — выходим", flush=True)
        sys.exit(0)
    win = CarouselV()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
```

### `app-carousel.py`

```python
#!/usr/bin/env python3
"""
Виджет-карусель приложений для рабочего стола (GTK3 + Cairo)
=============================================================
Закреплён на рабочем столе, полупрозрачный, AMOLED-стиль.

Управление:
  • колесо мыши / тап по стрелкам ‹ › — прокрутка карусели
  • тап по центральной иконке — запуск приложения
  • тап по боковой иконке — доводит её в центр
  • перетаскивание по фону — перемещение виджета
  • средний клик — закрыть
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import cairo
import math
import os
import subprocess
import time

W, H = 380, 150
STEP = 96.0          # шаг между иконками
ICON = 54            # базовый размер иконки
BG_A = 0.0           # прозрачность подложки виджета: 0.0 = полностью прозрачный фон
NEON = (0.55, 1.00, 0.60)   # светлый неоновый зелёный (подсветка активной иконки)
# --- персональные настройки (правь под себя) ---
RETRO_CMD = "retroarch"                  # команда запуска RetroArch (свой путь/скрипт — укажи здесь)
HOME_DIR  = os.path.expanduser("~")      # домашний каталог пользователя

XA = os.environ.get("XAUTHORITY", os.path.join(HOME_DIR, ".Xauthority"))
ENV = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0"), "XAUTHORITY": XA}

APPS = [
    ("Chromium", "/usr/share/icons/hicolor/256x256/apps/chromium.png",
     "chromium"),
    ("Telegram", "/usr/share/pixmaps/telegram.png",
     "flatpak run org.telegram.desktop"),
    ("Терминал", "/usr/share/icons/Papirus/48x48/apps/gnome-terminal.svg",
     "mate-terminal"),
    ("RetroArch", "/usr/share/pixmaps/retroarch.png", RETRO_CMD),
]


def rounded_rect(cr, x, y, w, h, r):
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.line_to(x, y + r)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class Carousel(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("app-carousel")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        # «Приклеено» к рабочему столу: тип DOCK — WM не скрывает такие окна
        # при «показать рабочий стол»; флаг BELOW опускает под обычные окна.
        self.set_keep_below(True)
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        scr = self.get_screen()
        vis = scr.get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.set_size_request(W, H)
        self.resize(W, H)
        # строго по центру экрана
        sw = scr.get_width()
        sh = scr.get_height()
        self.move(int((sw - W) / 2), int((sh - H) / 2))

        # иконки
        self.pix = []
        for _, path, _ in APPS:
            pb = None
            if os.path.exists(path):
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, ICON, ICON, True)
                except Exception:
                    pb = None
            self.pix.append(pb)

        self._pos = 0.0        # текущая позиция (индекс, дробная)
        self._target = 0.0     # цель
        self._press = None     # (x, y, время, зоны) при касании
        self._swiped = False   # был ли свайп (а не клик)
        self._start_pos = 0.0
        self._zones = []       # (x1,x2,индекс) иконок

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        GLib.timeout_add(16, self._animate)
        GLib.timeout_add(1500, self._keep_on_top_of_desktop)

    def _keep_on_top_of_desktop(self):
        """Тип DESKTOP держит окно ниже приложений и не даёт WM его скрыть.
        Но Caja (иконки рабочего стола) может подняться выше при кликах —
        периодически поднимаемся наверх ВНУТРИ своего (DESKTOP) слоя."""
        try:
            win = self.get_window()
            if win:
                win.restack(None, True)
        except Exception:
            pass
        return True

    # ---- анимация ----
    def _animate(self):
        if abs(self._target - self._pos) > 0.002:
            self._pos += (self._target - self._pos) * 0.22
        elif self._pos != self._target:
            self._pos = self._target
        # постоянная перерисовка — для мягкой пульсации неоновой подсветки
        self.queue_draw()
        return True

    # ---- отрисовка ----
    def on_draw(self, w, cr):
        # Фон — полностью прозрачный (виджет «парит»: видны только иконки)
        # Лёгкую подложку можно вернуть, задав BG_A > 0
        if BG_A > 0:
            cr.set_source_rgba(0.03, 0.035, 0.05, BG_A)
            rounded_rect(cr, 0, 0, W, H, 20)
            cr.fill()

        cx = W / 2.0
        cy = H / 2.0 - 6
        self._zones = []

        # ---- неоновая зелёная подсветка центральной иконки (с мягкой пульсацией) ----
        pulse = 0.85 + 0.15 * math.sin(time.time() * 2.4)
        gc = NEON
        glow = cairo.RadialGradient(cx, cy + 4, ICON * 0.18, cx, cy + 4, ICON * 1.35)
        glow.add_color_stop_rgba(0.0, gc[0], gc[1], gc[2], 0.55 * pulse)
        glow.add_color_stop_rgba(0.45, gc[0], gc[1], gc[2], 0.28 * pulse)
        glow.add_color_stop_rgba(1.0, gc[0], gc[1], gc[2], 0.0)
        cr.set_source(glow)
        cr.arc(cx, cy + 4, ICON * 1.35, 0, 2 * math.pi)
        cr.fill()

        # иконки: рисуем дальние первыми
        order = sorted(range(len(APPS)), key=lambda i: -abs(i - self._pos))
        for i in order:
            d = i - self._pos                     # смещение от центра
            x = cx + d * STEP
            if abs(d) > 2.6:
                continue
            scale = max(0.35, 1.0 - abs(d) * 0.30)
            size = ICON * scale
            alpha = max(0.15, 1.0 - abs(d) * 0.42)
            y = cy - size / 2 + abs(d) * 5

            # у центральной иконки — неоновая окантовка
            if abs(d) < 0.5:
                cr.set_source_rgba(gc[0], gc[1], gc[2], 0.85 * pulse)
                cr.set_line_width(2.0)
                cr.arc(x, cy + abs(d) * 5, size * 0.60, 0, 2 * math.pi)
                cr.stroke()

            pb = self.pix[i]
            if pb:
                cr.save()
                cr.translate(x - size / 2, y)
                cr.scale(size / pb.get_width(), size / pb.get_height())
                Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
                cr.paint_with_alpha(alpha)
                cr.restore()
            else:
                cr.arc(x, cy, size / 2, 0, 2 * math.pi)
                cr.set_source_rgba(0.25, 0.3, 0.4, alpha)
                cr.fill()

            # подпись центральной — неоновым зелёным
            if abs(d) < 0.5:
                cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(12)
                ext = cr.text_extents(APPS[i][0])
                cr.set_source_rgba(gc[0], gc[1], gc[2], 0.95)
                cr.move_to(cx - ext.width / 2, H - 10)
                cr.show_text(APPS[i][0])

            self._zones.append((x - size / 2 - 4, x + size / 2 + 4, i))

        # стрелки-подсказки
        cr.set_source_rgba(0.55, 0.62, 0.72, 0.6)
        cr.set_font_size(17)
        cr.move_to(11, cy + 6)
        cr.show_text("‹")
        cr.move_to(W - 19, cy + 6)
        cr.show_text("›")

        # точки-индикаторы
        n = len(APPS)
        total = n * 12
        x0 = cx - total / 2 + 6
        for i in range(n):
            if i == round(self._pos):
                cr.arc(x0 + i * 12, H - 22, 3.2, 0, 2 * math.pi)
                cr.set_source_rgba(gc[0], gc[1], gc[2], 0.95)
            else:
                cr.arc(x0 + i * 12, H - 22, 2.2, 0, 2 * math.pi)
                cr.set_source_rgba(0.45, 0.5, 0.58, 0.6)
            cr.fill()
        return False


    # ---- события ----
    def on_scroll(self, w, ev):
        if ev.direction == Gdk.ScrollDirection.UP:
            self._target = max(0, self._target - 1)
        elif ev.direction == Gdk.ScrollDirection.DOWN:
            self._target = min(len(APPS) - 1, self._target + 1)
        else:
            return False
        self.queue_draw()
        return True

    def on_press(self, w, ev):
        if ev.button == 2:
            self.destroy()
            return True
        if ev.button == 1:
            # запоминаем начало касания: различаем КЛИК и СВАЙП
            self._press = (ev.x, ev.y, time.time(), list(self._zones))
            self._swiped = False
            self._start_pos = self._pos
            return True
        return False

    def on_motion(self, w, ev):
        if not self._press:
            return False
        x0, y0, t0, zones = self._press
        dx = ev.x - x0
        # порог 14 px: меньше — случайное дрожание пальца, больше — свайп
        if not self._swiped and abs(dx) > 14:
            self._swiped = True
        if self._swiped:
            self._pos = max(0.0, min(len(APPS) - 1.0, self._start_pos - dx / STEP))
            self._target = self._pos
            self.queue_draw()
            return True
        return False

    def on_release(self, w, ev):
        if not self._press:
            return False
        x0, y0, t0, zones = self._press
        dt = time.time() - t0
        self._press = None
        if self._swiped:
            # свайп завершён — притягиваем к ближайшей иконке
            self._target = round(self._pos)
            self._swiped = False
            self.queue_draw()
            return True
        self._swiped = False
        # короткое касание без смещения — это КЛИК
        if dt < 0.7:
            self._handle_tap(x0, y0, zones)
        return True

    def _handle_tap(self, x, y, zones):
        """Обработка одиночного касания (запуск / центрирование)."""
        for x1, x2, i in zones:
            if x1 <= x <= x2:
                if abs(i - self._pos) < 0.5:
                    subprocess.Popen(APPS[i][2], shell=True, env=ENV)   # запуск приложения
                else:
                    self._target = float(i)                            # довести в центр
                    self.queue_draw()
                return
        cy = H / 2
        if x < 34 and abs(y - cy) < 60:
            self._target = max(0, round(self._pos) - 1)
            self.queue_draw()
        elif x > W - 34 and abs(y - cy) < 60:
            self._target = min(len(APPS) - 1, round(self._pos) + 1)
            self.queue_draw()


if __name__ == "__main__":
    Carousel().show_all()
    Gtk.main()
```

### `cpu-temp-float.py`

```python
#!/usr/bin/env python3
"""
cpu-temp-float.py — плавающий виджет температуры CPU на рабочем столе.
Полупрозрачный, поверх всех окон, перетаскивается мышью (средняя/левая
кнопка за окно), обновление каждые 5 сек. Рисуется градусник через Cairo.
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo
import math

TEMP_SENSOR = "/sys/class/thermal/thermal_zone0/temp"
UPDATE_SEC = 5
W, H = 84, 44

def read_temp():
    try:
        with open(TEMP_SENSOR) as f:
            return int(f.read().strip()) // 1000
    except Exception:
        return -1

class TempFloat(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_title("cpu-temp")
        self.set_default_size(W, H)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_accept_focus(False)

        # прозрачный фон
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_position(Gtk.WindowPosition.NONE)
        # стартовая позиция — правый нижний угол
        mw = screen.get_width()
        mh = screen.get_height()
        self.move(mw - W - 16, mh - H - 20)  # 16px от края, 20px над нижней кромкой

        self._temp = 0
        self._drag = None  # (start_x, start_y, win_x, win_y)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        # средний клик — закрыть
        self.connect("destroy", Gtk.main_quit)

        self.update_temp()
        GLib.timeout_add_seconds(UPDATE_SEC, self.update_temp)

    def update_temp(self):
        t = read_temp()
        if t >= 0:
            self._temp = t
            self.queue_draw()
        return True

    def on_draw(self, wid, cr):
        # прозрачный фон
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        # полупрозрачный тёмный скруглённый фон
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0.08, 0.09, 0.12, 0.72)
        r = 10
        cr.move_to(r, 0)
        cr.line_to(W - r, 0)
        cr.arc(W - r, r, r, -math.pi/2, 0)
        cr.line_to(W, H - r)
        cr.arc(W - r, H - r, r, 0, math.pi/2)
        cr.line_to(r, H)
        cr.arc(r, H - r, r, math.pi/2, math.pi)
        cr.line_to(0, r)
        cr.arc(r, r, r, math.pi, 3*math.pi/2)
        cr.fill()

        t = self._temp
        # цвет по температуре
        if t < 50:
            rc, gc, bc = 0.35, 0.85, 0.35   # зелёный
        elif t < 70:
            rc, gc, bc = 1.0, 0.72, 0.15    # жёлтый
        else:
            rc, gc, bc = 1.0, 0.25, 0.25    # красный

        # --- градусник слева ---
        # колба
        cx, by, br = 22, H - 8, 7
        cr.set_source_rgb(rc, gc, bc)
        cr.arc(cx, by, br, 0, 2*math.pi)
        cr.fill()
        # палочка
        cr.set_source_rgb(0.85, 0.85, 0.88)
        cr.set_line_width(4)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx, by - br)
        cr.line_to(cx, 7)
        cr.stroke()
        # ртуть внутри палочки
        fill_h = max(0, min(t, 95)) / 95.0 * (by - br - 9)
        cr.set_source_rgb(rc, gc, bc)
        cr.set_line_width(2)
        cr.move_to(cx, by - br)
        cr.line_to(cx, by - br - fill_h)
        cr.stroke()

        # --- текст температуры справа ---
        cr.set_font_size(19)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_BOLD)
        txt = f"{t}°"
        xb = cr.text_extents(txt)
        tx = W - xb.width - 6
        ty = (H + xb.height/2) / 2 + 2
        # обводка
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(3)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.move_to(tx, ty)
        cr.text_path(txt)
        cr.stroke()
        # текст белый
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(tx, ty)
        cr.show_text(txt)
        return False

    def on_press(self, w, ev):
        if ev.button == 2:  # средняя — закрыть
            self.destroy()
            return True
        if ev.button == 1 or ev.button == 3:
            wx, wy = self.get_position()
            self._drag = (ev.x_root, ev.y_root, wx, wy)
            return True
        return False

    def on_release(self, w, ev):
        self._drag = None
        return False

    def on_motion(self, w, ev):
        if self._drag:
            sx, sy, wx, wy = self._drag
            self.move(wx + (ev.x_root - sx), wy + (ev.y_root - sy))
            return True
        return False

    def on_scroll(self, w, ev):
        # перемещение колесом — тоже двигаем
        if self._drag is None:
            self._drag = (ev.x_root, ev.y_root,
                          self.get_position()[0], self.get_position()[1])
        return False


if __name__ == "__main__":
    win = TempFloat()
    win.show_all()
    Gtk.main()
```

### `volume-drawer.py`

```python
#!/usr/bin/env python3
# Шторка громкости снизу экрана: полоска с неоновым ореолом,
# свайп вверх — выдвигается ползунок, 2 с бездействия — прячется.
import subprocess, sys, time, math
from PIL import Image, ImageFilter, ImageEnhance
import gi
gi.require_version("Gtk", "3.0")
import cairo
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

W, H = 300, 104          # окно шторки
BAR_W, BAR_H = 240, 3    # полоска внизу — тонкая, не бросается в глаза
PANEL_H = 74             # высота выдвижной панели
NEON = (0.55, 1.00, 0.60)
HIDE_AFTER = 2.0         # с бездействия до автоскрытия

# --- параметры «жидкого стекла» (iOS liquid glass) ---
BLUR = 16                # радиус размытия подложки (больше = мягче, «дороже»)
SAT = 1.65               # усиление насыщенности фона — подпись iOS-стекла
BRIGHT = 1.06            # лёгкий подъём яркости подложки
GLASS_A = 0.90           # непрозрачность самого стекла (размытый фон)
TINT_A = 0.60            # тёмная тонировка поверх стекла (dark mode material)


def get_volume():
    try:
        out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                             capture_output=True, text=True, timeout=5).stdout
        for part in out.split():
            if part.endswith("%"):
                return int(part.rstrip("%"))
    except Exception:
        pass
    return 0


def set_volume(pct):
    pct = max(0, min(150, int(pct)))
    try:
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return pct


def toggle_mute():
    subprocess.Popen(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Drawer(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()   # прозрачность окна (без чёрного фона)
        if vis:
            self.set_visual(vis)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        scr = self.get_screen()
        self.sw, self.sh = scr.get_width(), scr.get_height()
        self.vol = get_volume()
        self.open = 0.0        # 0 = скрыто, 1 = открыто
        self.target = 0.0
        self.last_act = 0.0
        self._vol_t = 0.0
        self.bg = None          # размытый фон (liquid glass), снимается 1 раз при открытии
        self._bg_t = 0.0
        self.drag_vol = False
        self.connect("draw", self.on_draw)
        self.connect("realize", self.on_realize)
        self.connect("map-event", self.on_map)
        self.move((self.sw - W) // 2, self.sh - H)
        self.set_default_size(W, H)
        self.show_all()
        GLib.timeout_add(16, self.tick)

    def _apply_input(self):
        try:
            reg = cairo.Region()
            if self.open > 0.05:
                reg.union(cairo.RectangleInt(0, 0, W, H))
            else:
                reg.union(cairo.RectangleInt((W - BAR_W) // 2 - 30, H - 26, BAR_W + 60, 26))
            self.get_window().input_shape_combine_region(reg, 0, 0)
        except Exception:
            pass

    def on_realize(self, *_):
        self._apply_input()
        try:
            self.get_window().set_override_redirect(True)
        except Exception:
            pass

    def on_map(self, *_):
        self._apply_input()
        return False

    def tick(self):
        if abs(self.target - self.open) > 0.01:
            self.open += (self.target - self.open) * 0.28
            self.queue_draw()
        elif self.open != self.target:
            self.open = self.target
            self.queue_draw()
            self._apply_input()
        # захват фона один раз при открытии (пока панель не нарисована),
        # чтобы в снимок не попало само стекло
        if self.target > 0.5 and self.open < 0.05 and self._bg_t == 0.0:
            self._bg_t = time.time()
            GLib.idle_add(self._grab_bg)
        elif self.target < 0.5:
            self._bg_t = 0.0
        if self.open > 0.05:
            self.queue_draw()
        if self.target > 0.5 and self.last_act and time.time() - self.last_act > HIDE_AFTER:
            self.target = 0.0
            self.last_act = 0.0
        if not self.drag_vol and not self._vol_t:
            self._vol_t = time.time()
        elif not self.drag_vol and time.time() - self._vol_t > 2.0:
            self._vol_t = time.time()
            self.vol = get_volume()
        return True

    def on_draw(self, w, cr):
        cr.save()
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.restore()
        e = self.open
        dy = PANEL_H * e        # насколько всё поднялось (свайп вверх)
        # ---- полоска с неоновым ореолом (едет вверх вместе со свайпом) ----
        # тонкая и приглушённая: ореол мягкий, ядро не «светит в глаза»
        bx, by = (W - BAR_W) / 2, H - BAR_H - 8 - dy
        for grow, al in ((4.5, 0.05), (2.6, 0.09), (1.3, 0.16)):
            rr(cr, bx - grow, by - grow, BAR_W + 2 * grow, BAR_H + 2 * grow, (BAR_H + 2 * grow) / 2)
            cr.set_source_rgba(NEON[0], NEON[1], NEON[2], al)
            cr.fill()
        rr(cr, bx, by, BAR_W, BAR_H, BAR_H / 2)
        cr.set_source_rgba(0.80, 0.96, 0.83, 0.82)
        cr.fill()
        if e > 0.02:
            self._draw_panel(cr, e)

    def _grab_bg(self):
        """Снимок фона под окном: размытие + насыщенность + яркость.
        Размытие и подъём насыщенности — то, что делает стекло «жидким» (как в iOS):
        фон не просто мутнеет, а превращается в мягкое, но живое цветное пятно."""
        try:
            rw = Gdk.get_default_root_window()
            x, y = self.get_window().get_root_coords(0, 0)
            pb = Gdk.pixbuf_get_from_window(rw, x, y, W, H)
            if not pb:
                return False
            img = Image.frombytes("RGB", (W, H), pb.get_pixels(), "raw", "RGB",
                                  pb.get_rowstride())
            img = img.filter(ImageFilter.GaussianBlur(BLUR))       # размытие подложки
            img = ImageEnhance.Color(img).enhance(SAT)             # насыщенность (signature iOS)
            img = ImageEnhance.Brightness(img).enhance(BRIGHT)     # лёгкий подъём яркости
            data = img.tobytes()
            self.bg = GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, False, 8, W, H, W * 3)
        except Exception:
            pass
        return False

    def _draw_panel(self, cr, e):
        # iOS LIQUID GLASS: тень → стекло → тонировка → спекуляр/линза → кромки
        ph = PANEL_H * e
        by = H - BAR_H - 8 - PANEL_H * e
        py = by + BAR_H + 6
        R = 14
        # 0) ВНЕШНЯЯ ТЕНЬ — стекло «висит» над фоном, а не приклеено к нему
        for off, al, lw in ((0, 0.10, 10.0), (2.0, 0.13, 6.0), (4.0, 0.15, 3.0)):
            rr(cr, 16 - lw / 2, py - lw / 2 + off, W - 32 + lw, ph + lw, R + lw / 2)
            cr.set_source_rgba(0, 0, 0, al * e)
            cr.fill()
        # 1) СТЕКЛО: размытая и насыщенная подложка — сквозь стекло ВИДНО фон, но мягко
        if self.bg:
            cr.save()
            rr(cr, 16, py, W - 32, ph, R)
            cr.clip()
            Gdk.cairo_set_source_pixbuf(cr, self.bg, 0, 0)
            cr.paint_with_alpha(GLASS_A * e)
            cr.restore()
        # 2) ТОНИРОВКА: тёмный «дымчатый» слой (тёмная тема iOS) — держит стекло тёмным
        cr.set_source_rgba(0.05, 0.06, 0.10, TINT_A * e)
        rr(cr, 16, py, W - 32, ph, R)
        cr.fill()
        # 3) ОБЪЁМ одним градиентом (10 точек — без швов и полос):
        #    спекуляр сверху (свет ловится кромкой) → линза снизу (глубина)
        g = cairo.LinearGradient(0, py, 0, py + ph)
        g.add_color_stop_rgba(0.00, 1, 1, 1, 0.34 * e)      # яркий спекуляр у кромки
        g.add_color_stop_rgba(0.08, 1, 1, 1, 0.22 * e)
        g.add_color_stop_rgba(0.18, 1, 1, 1, 0.12 * e)
        g.add_color_stop_rgba(0.30, 1, 1, 1, 0.05 * e)
        g.add_color_stop_rgba(0.44, 1, 1, 1, 0.01 * e)
        g.add_color_stop_rgba(0.56, 0, 0, 0, 0.02 * e)      # мягкий переход в линзу
        g.add_color_stop_rgba(0.68, 0, 0, 0, 0.08 * e)
        g.add_color_stop_rgba(0.80, 0, 0, 0, 0.16 * e)
        g.add_color_stop_rgba(0.90, 0, 0, 0, 0.23 * e)
        g.add_color_stop_rgba(1.00, 0, 0, 0, 0.30 * e)      # тёмная кромка снизу
        cr.set_source(g)
        rr(cr, 16, py, W - 32, ph, R)
        cr.fill()
        # 4) Неоновый контур (наш стиль) — мягче, чтобы не спорить с бликом кромки
        for lw, al in ((6.0, 0.07), (3.5, 0.14), (2.0, 0.38)):
            rr(cr, 16, py, W - 32, ph, R)
            cr.set_line_width(lw)
            cr.set_source_rgba(NEON[0], NEON[1], NEON[2], al * e)
            cr.stroke()
        # 5) ЯРКАЯ КРОМКА сверху — «край стекла» (подпись iOS: тонкий белый блик)
        cr.set_line_width(1.2)
        cr.set_source_rgba(1, 1, 1, 0.40 * e)
        rr(cr, 16.6, py + 0.6, W - 33.2, ph - 1.2, R - 0.6)
        cr.stroke()
        # 6) БОКОВЫЕ КРОМКИ — свет по левому и правому краю (линза по горизонтали)
        glr = cairo.LinearGradient(16, 0, W - 16, 0)
        glr.add_color_stop_rgba(0.00, 1, 1, 1, 0.20 * e)    # левая кромка светится
        glr.add_color_stop_rgba(0.18, 1, 1, 1, 0.04 * e)
        glr.add_color_stop_rgba(0.50, 1, 1, 1, 0.00)
        glr.add_color_stop_rgba(0.82, 1, 1, 1, 0.04 * e)
        glr.add_color_stop_rgba(1.00, 1, 1, 1, 0.20 * e)    # правая кромка светится
        cr.set_line_width(1.4)
        cr.set_source(glr)
        rr(cr, 16.8, py + 0.8, W - 33.6, ph - 1.6, R - 0.8)
        cr.stroke()
        # надпись — со свечением (как название в карусели)
        cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(13)
        label = ("Звук выключен" if self.vol == 0 else f"Громкость {self.vol}%")
        ext = cr.text_extents(label)
        tx0 = W / 2 - ext.width / 2
        for off in (1.4, 0.9):
            cr.set_source_rgba(0.0, 0.06, 0.02, 0.55 * e)     # тёмная обводка — читаемость на любом фоне
            for dx2, dy2 in ((-off, 0), (off, 0), (0, -off), (0, off)):
                cr.move_to(tx0 + dx2, py + 26 + dy2)
                cr.show_text(label)
        for off in (1.2, 0.8):
            cr.set_source_rgba(NEON[0], NEON[1], NEON[2], 0.30 * e)
            for dx2, dy2 in ((-off, 0), (off, 0), (0, -off), (0, off)):
                cr.move_to(tx0 + dx2, py + 26 + dy2)
                cr.show_text(label)
        cr.set_source_rgba(0.94, 1.0, 0.95, 0.97 * e)
        cr.move_to(tx0, py + 26)
        cr.show_text(label)
        tx, ty, tw = 44, py + ph - 26, W - 88
        rr(cr, tx, ty, tw, 6, 3)
        cr.set_source_rgba(0.06, 0.12, 0.09, 0.62 * e)   # тёмный трек — виден на любом фоне
        cr.fill()
        fill = tw * max(0, min(100, self.vol)) / 100.0
        if fill > 1:
            for g, a in ((6.0, 0.12), (3.0, 0.26)):
                rr(cr, tx - g, ty - g, fill + 2 * g, 6 + 2 * g, 6 + g)
                cr.set_source_rgba(NEON[0], NEON[1], NEON[2], a * e)
                cr.fill()
            rr(cr, tx, ty, fill, 6, 3)
            cr.set_source_rgba(0.82, 1.0, 0.86, 0.95 * e)
            cr.fill()
        cr.arc(tx + fill, ty + 3, 8, 0, 2 * math.pi)
        for g, a in ((7.0, 0.15), (3.5, 0.30)):
            cr.arc(tx + fill, ty + 3, 8 + g, 0, 2 * math.pi)
            cr.set_source_rgba(NEON[0], NEON[1], NEON[2], a * e)
            cr.fill()
        cr.arc(tx + fill, ty + 3, 7, 0, 2 * math.pi)
        cr.set_source_rgba(0.92, 1.0, 0.94, 0.96 * e)
        cr.fill()

    def _vol_from_x(self, x):
        tx, tw = 44, W - 88
        pct = (x - tx) / tw * 100.0
        return set_volume(round(max(0, min(100, pct)) / 5) * 5)

    def on_press(self, w, ev):
        self.target = 1.0
        self.last_act = time.time()
        self._apply_input()
        if self.open > 0.5 or ev.y < H - 40:
            self.drag_vol = True
            self.vol = self._vol_from_x(ev.x)
            self.queue_draw()
        return True

    def on_motion(self, w, ev):
        if self.drag_vol:
            self.last_act = time.time()
            self.vol = self._vol_from_x(ev.x)
            self.queue_draw()
        return True

    def on_release(self, w, ev):
        self.drag_vol = False
        self.last_act = time.time()
        return True


def rr(cr, x, y, w, h, r):
    if w <= 0 or h <= 0:
        return
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def main():
    d = Drawer()
    d.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                 | Gdk.EventMask.BUTTON_RELEASE_MASK
                 | Gdk.EventMask.POINTER_MOTION_MASK)
    d.connect("button-press-event", d.on_press)
    d.connect("motion-notify-event", d.on_motion)
    d.connect("button-release-event", d.on_release)
    d.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
```

### `install.sh`

```bash
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

# Резервная копия файла, который сейчас перезапишем (установщик НЕ должен терять настройки)
backup() {
  local f="$1" stamp
  [ -e "$f" ] || return 0
  stamp="$(date +%Y%m%d-%H%M%S)"
  cp -a "$f" "$f.bak-$stamp"
  say "↳ бэкап: $(basename "$f").bak-$stamp"
}

echo "== 0/4. Проверка констант под свою систему =="
say "RETRO_CMD      = $(sed -n 's/^RETRO_CMD *= *"\([^"]*\)".*/\1/p' app-carousel-v.py | head -1)  (команда запуска RetroArch)"
say "CHROMIUM_PROXY = $(sed -n 's/^CHROMIUM_PROXY *= *"\([^"]*\)".*/\1/p' app-carousel-v.py | head -1)"
say "⚠ Если RetroArch у тебя запускается своим скриптом — впиши его в RETRO_CMD"
say "  ПЕРЕД запуском установщика, иначе ярлык будет запускать голый retroarch."
say "  Уже установленные файлы будут заменены, но с бэкапом рядом (.bak-дата)."

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
    if [ -e "$BIN/$f" ] && ! cmp -s "$SRC/$f" "$BIN/$f"; then
      say "⚠ $f отличается от версии в репозитории — сохраняю бэкап"
    fi
    backup "$BIN/$f"
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
    backup "$AUTOSTART/$name"
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
```

### `autostart/app-carousel.desktop`

```ini
# Шаблон автозапуска. Путь /home/orangepi подставляется установщиком:
#   ./install.sh   (вручную: sed "s|/home/orangepi|$HOME|g" файл)
[Desktop Entry]
Type=Application
Name=App Carousel (вертикальная)
Comment=Виджет-карусель приложений на рабочем столе справа (неоновая комета)
Exec=/home/orangepi/.local/bin/app-carousel-v.py
X-GNOME-Autostart-enabled=true
Terminal=false
```

### `autostart/cpu-temp-float.desktop`

```ini
# Шаблон автозапуска. Путь /home/orangepi подставляется установщиком:
#   ./install.sh   (вручную: sed "s|/home/orangepi|$HOME|g" файл)
[Desktop Entry]
Type=Application
Name=CPU Temp Widget
Comment=Плавающий виджет температуры CPU
Exec=/home/orangepi/.local/bin/cpu-temp-float.py
X-GNOME-Autostart-enabled=true
Terminal=false
```

### `autostart/volume-drawer.desktop`

```ini
# Шаблон автозапуска. Путь /home/orangepi подставляется установщиком:
#   ./install.sh   (вручную: sed "s|/home/orangepi|$HOME|g" файл)
[Desktop Entry]
Type=Application
Name=Volume Drawer Widget
Comment=Шторка громкости снизу экрана (свайп вверх)
Exec=/home/orangepi/.local/bin/volume-drawer.py
X-GNOME-Autostart-enabled=true
Terminal=false
```

<!-- AUTO-LISTINGS:END -->
