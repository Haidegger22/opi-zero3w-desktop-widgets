#!/usr/bin/env python3
# Шторка громкости снизу экрана: полоска с неоновым ореолом,
# свайп вверх — выдвигается ползунок, 2 с бездействия — прячется.
import subprocess, sys, time, math
from PIL import Image, ImageFilter, ImageEnhance
from Xlib import X as XLIBX
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
