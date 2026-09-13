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
     "chromium --disk-cache-size=1073741824 --proxy-server=http://127.0.0.1:7890 "
     "--proxy-bypass-list='localhost;127.0.0.1;192.168.*;10.*;<local>'"),
    ("Telegram", "/usr/share/pixmaps/telegram.png", "flatpak run org.telegram.desktop"),
    ("Терминал", "/usr/share/icons/Papirus/48x48/apps/gnome-terminal.svg", "mate-terminal"),
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
