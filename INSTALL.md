# Установка виджетов — по шагам (copy-paste)

Для Debian 13 + MATE (X11), экран 1024×600 (Orange Pi Zero 3W).
Каждый блок можно вставить в терминал целиком.

## Шаг 1. Зависимости

```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil
```

## Шаг 2. Скачать репозиторий

```bash
cd ~
git clone https://github.com/Haidegger22/opi-zero3w-desktop-widgets.git
cd ~/opi-zero3w-desktop-widgets
```

## Шаг 3. Карусель приложений

```bash
mkdir -p ~/.local/bin
cp app-carousel-v.py ~/.local/bin/
chmod +x ~/.local/bin/app-carousel-v.py
```

## Шаг 4. Индикатор температуры CPU

```bash
cp cpu-temp-float.py ~/.local/bin/
chmod +x ~/.local/bin/cpu-temp-float.py
```

## Шаг 5. Автозапуск (пути подставятся автоматически)

```bash
mkdir -p ~/.config/autostart
cd ~/opi-zero3w-desktop-widgets
for f in autostart/*.desktop; do
  sed "s|/home/orangepi|$HOME|g" "$f" > ~/.config/autostart/"$(basename "$f")"
done
ls ~/.config/autostart/
```

## Шаг 6. Запустить сейчас (без перезагрузки)

```bash
DISPLAY=:0 ~/.local/bin/app-carousel-v.py &   # карусель
DISPLAY=:0 ~/.local/bin/cpu-temp-float.py &   # температура
```

## Шаг 7. Проверка

- Карусель должна появиться **справа по центру** рабочего стола
- Проверить, что запущены:
```bash
pgrep -af "app-carousel-v|cpu-temp-float"
```
- Проверить окно карусели (тип должен быть DOCK):
```bash
DISPLAY=:0 xdotool search --name "app-carousel" | head -1 | xargs -I{} xprop -id {} _NET_WM_WINDOW_TYPE
```

## Важно

- Требуется **X11** (не Wayland) и рабочий стол MATE.
- Chromium в карусели запускается **через прокси** `127.0.0.1:7890` — если у тебя другой порт,
  поправь команду в `app-carousel-v.py` (константа `APPS`).
- Иконки приложений берутся по путям из `APPS` — они должны существовать в системе.

## Откат

```bash
pkill -f app-carousel-v.py
pkill -f cpu-temp-float.py
rm -f ~/.config/autostart/app-carousel.desktop ~/.config/autostart/cpu-temp-float.desktop
```
## Полный код файлов (установка без git)

Вставляй блоки по порядку — каждый создаёт файл сам.

### 1. Карусель (вертикальная)

```bash
mkdir -p $(dirname $HOME/.local/bin/app-carousel-v.py)
cat > $HOME/.local/bin/app-carousel-v.py << 'SCRIPT_EOF'
#!/usr/bin/env python3
"""
Виджет-карусель приложений — ВЕРТИКАЛЬНАЯ версия (приклеена справа)
====================================================================
Окно типа DOCK + «ниже всех окон»: не исчезает при «показать рабочий стол»
(Fn+Enter), окна приложений перекрывают виджет.

Управление:
  • колесо мыши / стрелки ⌃⌄   — прокрутка
  • свайп пальцем (вертикально) — прокрутка (следует за пальцем)
  • тап по центральной иконке   — запуск приложения
  • тап по боковой иконке       — доводит её в центр
  • средний клик                — закрыть
"""
import os
import subprocess
import time
import math

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import cairo

# ---- параметры ----
W, H = 240, 430      # вертикальное окно (расширено влево — под горизонтальное название)
STEP = 86.0          # шаг между иконками по вертикали
ICON = 52            # базовый размер иконки
CX = W - 66          # центр иконок — у правого края (название и точки слева)
BG_A = 0.0           # прозрачность подложки (0.0 = фон прозрачный)
NEON = (0.55, 1.00, 0.60)   # светлый неоновый зелёный
MARGIN_RIGHT = 6     # отступ от правого края экрана

XA = os.environ.get("XAUTHORITY", "/home/orangepi/.Xauthority")
ENV = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0"), "XAUTHORITY": XA}

# подпись, файл иконки, команда запуска
APPS = [
    ("Chromium", "/usr/share/icons/hicolor/256x256/apps/chromium.png",
     "env XCURSOR_THEME=comet-hidden chromium --disk-cache-size=1073741824 "
     "--proxy-server=http://127.0.0.1:7890 "
     "--proxy-bypass-list='localhost;127.0.0.1;192.168.*;10.*;<local>'"),
    ("Telegram", "/usr/share/pixmaps/telegram.png", "flatpak run org.telegram.desktop"),
    ("Терминал", "/usr/share/icons/Papirus/48x48/apps/gnome-terminal.svg", "mate-terminal"),
    ("Домашняя папка", "/usr/share/icons/mate/256x256/places/user-home.png",
     "caja /home/orangepi"),
    ("RetroArch", "/usr/share/pixmaps/retroarch.png",
     "bash /home/orangepi/.openclaw/workspace/retrogame.sh"),
]


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

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        GLib.timeout_add(16, self._animate)   # ~60 fps — плавная комета

    def _animate(self):
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
        pulse = 0.85 + 0.15 * math.sin(time.time() * 2.4)
        gc = NEON

        # ---- НЕОНОВОЕ КОЛЬЦО вокруг центральной иконки (стиль «F.R.I.D.A.Y.») ----
        R = ICON * 0.95          # компактнее — не задевает точки слева
        # дорожка, по которой бежит дуга
        cr.set_line_width(1.1)
        cr.set_source_rgba(gc[0], gc[1], gc[2], 0.28)
        cr.arc(cx, cy, R, 0, 2 * math.pi)
        cr.stroke()
        # положение «головы» кометы — источник света
        a0 = (time.time() * 1.15) % (2 * math.pi)
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
    win = CarouselV()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

SCRIPT_EOF
chmod +x $HOME/.local/bin/app-carousel-v.py 2>/dev/null || true
```

### 2. Карусель (горизонтальная, опционально)

```bash
mkdir -p $(dirname $HOME/.local/bin/app-carousel.py)
cat > $HOME/.local/bin/app-carousel.py << 'SCRIPT_EOF'
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
XA = os.environ.get("XAUTHORITY", "/home/orangepi/.Xauthority")
ENV = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0"), "XAUTHORITY": XA}

APPS = [
    ("Chromium", "/usr/share/icons/hicolor/256x256/apps/chromium.png",
     "chromium"),
    ("Telegram", "/usr/share/pixmaps/telegram.png",
     "flatpak run org.telegram.desktop"),
    ("Терминал", "/usr/share/icons/Papirus/48x48/apps/gnome-terminal.svg",
     "mate-terminal"),
    ("RetroArch", "/usr/share/pixmaps/retroarch.png",
     "bash /home/orangepi/.openclaw/workspace/retrogame.sh"),
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
SCRIPT_EOF
chmod +x $HOME/.local/bin/app-carousel.py 2>/dev/null || true
```

### 3. Индикатор температуры

```bash
mkdir -p $(dirname $HOME/.local/bin/cpu-temp-float.py)
cat > $HOME/.local/bin/cpu-temp-float.py << 'SCRIPT_EOF'
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
SCRIPT_EOF
chmod +x $HOME/.local/bin/cpu-temp-float.py 2>/dev/null || true
```

### 4. Автозапуск карусели

```bash
mkdir -p $(dirname $HOME/.config/autostart/app-carousel.desktop)
cat > $HOME/.config/autostart/app-carousel.desktop << 'SCRIPT_EOF'
[Desktop Entry]
Type=Application
Name=App Carousel (вертикальная)
Comment=Виджет-карусель приложений на рабочем столе справа (неоновая комета)
Exec=/home/orangepi/.local/bin/app-carousel-v.py
X-GNOME-Autostart-enabled=true
Terminal=false
SCRIPT_EOF
chmod +x $HOME/.config/autostart/app-carousel.desktop 2>/dev/null || true
```

### 5. Автозапуск температуры

```bash
mkdir -p $(dirname $HOME/.config/autostart/cpu-temp-float.desktop)
cat > $HOME/.config/autostart/cpu-temp-float.desktop << 'SCRIPT_EOF'
[Desktop Entry]
Type=Application
Name=CPU Temp Widget
Comment=Плавающий виджет температуры CPU
Exec=/home/orangepi/.local/bin/cpu-temp-float.py
X-GNOME-Autostart-enabled=true
Terminal=false
SCRIPT_EOF
chmod +x $HOME/.config/autostart/cpu-temp-float.desktop 2>/dev/null || true
```

