"""Cairo bar chart used by the Dashboard."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .. import theme as theme_mod


def _hex_to_floats(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    return int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255, int(hx[4:6], 16) / 255


class BarChart(Gtk.DrawingArea):
    def __init__(self, data: dict, palette: dict, height: int = 200):
        super().__init__()
        self._data = data
        self._palette = theme_mod.derive(palette)
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw, None)

    def update(self, data: dict, palette: dict | None = None) -> None:
        self._data = data
        if palette is not None:
            self._palette = theme_mod.derive(palette)
        self.queue_draw()

    def _draw(self, area, ctx, w, h, _user):
        days = sorted(self._data.keys())
        if not days:
            return
        values = [self._data[d] for d in days]
        max_val = max(values) if max(values) > 0 else 1

        c = self._palette
        accent = _hex_to_floats(c["accent"])
        fg = _hex_to_floats(c["fg_dim"])
        sub = _hex_to_floats(c["fg_muted"])

        pad_left, pad_right = 24, 16
        pad_top, pad_bottom = 18, 28
        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bottom

        n = len(values)
        slot = chart_w / n
        bar_w = slot * 0.55

        # Y guides (3 horizontal lines)
        ctx.set_source_rgba(*fg, 0.18)
        ctx.set_line_width(1.0)
        for i in range(4):
            y = pad_top + chart_h * (i / 3)
            ctx.move_to(pad_left, y)
            ctx.line_to(pad_left + chart_w, y)
            ctx.stroke()

        # Bars
        for i, val in enumerate(values):
            x = pad_left + i * slot + (slot - bar_w) / 2
            bh = (val / max_val) * chart_h
            y = pad_top + chart_h - bh

            # bar w/ rounded top
            ctx.set_source_rgba(*accent, 0.9)
            r = min(4, bar_w / 2)
            ctx.move_to(x, pad_top + chart_h)
            ctx.line_to(x, y + r)
            ctx.arc(x + r, y + r, r, 3.14, 3 * 3.14 / 2)
            ctx.line_to(x + bar_w - r, y)
            ctx.arc(x + bar_w - r, y + r, r, 3 * 3.14 / 2, 0)
            ctx.line_to(x + bar_w, pad_top + chart_h)
            ctx.close_path()
            ctx.fill()

            # day label
            ctx.set_source_rgba(*sub, 1.0)
            ctx.set_font_size(10)
            day_lbl = days[i][5:]   # MM-DD
            ext = ctx.text_extents(day_lbl)
            ctx.move_to(x + bar_w / 2 - ext.width / 2, h - 8)
            ctx.show_text(day_lbl)

            # value label
            if val > 0:
                vstr = f"{val:.1f}"
                ext = ctx.text_extents(vstr)
                ctx.set_source_rgba(*accent, 1.0)
                ctx.move_to(x + bar_w / 2 - ext.width / 2, y - 4)
                ctx.show_text(vstr)
