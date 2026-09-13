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
            self.queue_draw()
        elif self._pos != self._target:
            self._pos = self._target
            self.queue_draw()
        return True

    # ---- отрисовка ----
    def on_draw(self, w, cr):
        # фон
        cr.set_source_rgba(0.03, 0.035, 0.05, 0.82)
        rounded_rect(cr, 0, 0, W, H, 20)
        cr.fill()
        # рамка
        cr.set_source_rgba(0.20, 0.68, 1.0, 0.35)
        cr.set_line_width(1.2)
        rounded_rect(cr, 0.6, 0.6, W - 1.2, H - 1.2, 20)
        cr.stroke()

        cx = W / 2.0
        cy = H / 2.0 - 6
        self._zones = []

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

            # подпись центральной
            if abs(d) < 0.5:
                cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(12)
                ext = cr.text_extents(APPS[i][0])
                cr.set_source_rgb(0.95, 0.96, 0.98)
                cr.move_to(cx - ext.width / 2, H - 10)
                cr.show_text(APPS[i][0])

            self._zones.append((x - size / 2 - 4, x + size / 2 + 4, i))

        # стрелки-подсказки
        cr.set_source_rgba(0.55, 0.62, 0.72, 0.75)
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
            cr.arc(x0 + i * 12, H - 22, 3 if i == round(self._pos) else 2.2, 0, 2 * math.pi)
            if i == round(self._pos):
                cr.set_source_rgba(0.20, 0.68, 1.0, 0.95)
            else:
                cr.set_source_rgba(0.45, 0.5, 0.58, 0.7)
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
