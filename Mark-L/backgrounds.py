"""
Background styles for the Kurd AI main canvas.

The app shipped with a single near-black fill (#00060a). At full-screen that
leaves an enormous empty field around the centrepiece, which reads as unfinished
rather than sleek. These give the canvas depth so the visualizer sits IN a space
instead of floating in a void.

Each background is pure QPainter — no images, no assets, no licensing questions,
and it recolours itself from the user's accent palette.

Backgrounds are painted first, then the visualizer draws on top. Keep them low
contrast: they must never compete with the centrepiece or make text unreadable.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient


def _c(hex_str: str, alpha: int = 255) -> QColor:
    col = QColor(hex_str)
    col.setAlpha(alpha)
    return col


def _mix(a: str, b: str, t: float) -> QColor:
    ca, cb = QColor(a), QColor(b)
    return QColor(
        int(ca.red() + (cb.red() - ca.red()) * t),
        int(ca.green() + (cb.green() - ca.green()) * t),
        int(ca.blue() + (cb.blue() - ca.blue()) * t),
    )


class Background:
    id: str = "base"
    name_key: str = "bg.base"
    fallback_name: str = "Base"

    # A colour template can claim the whole look by overriding the accent, so the
    # visualizer drawn on top matches it. None means "keep the user's accent".
    accent_override: str | None = None

    def paint(self, p: QPainter, w: int, h: int, pal: dict[str, str], t: float) -> None:
        raise NotImplementedError

    def apply_palette(self, pal: dict[str, str]) -> dict[str, str]:
        """
        Return the palette the visualizer should use on top of this background.

        Without this a cyan face sits on a crimson backdrop and the two fight.
        Overriding PRI (and its dim variant) makes each colour template read as a
        complete theme rather than a recoloured backdrop.
        """
        if not self.accent_override:
            return pal
        out = dict(pal)
        out["PRI"] = self.accent_override
        out["PRI_DIM"] = _mix(self.accent_override, "#000000", 0.45).name()
        return out


class Void(Background):
    """The original flat near-black. Kept so nothing is taken away."""
    id = "void"
    name_key = "bg.void"
    fallback_name = "Void"

    def paint(self, p, w, h, pal, t):
        p.fillRect(0, 0, w, h, _c(pal.get("BG", "#00060a")))


class DeepOcean(Background):
    """Radial glow behind the centrepiece — the single biggest improvement."""
    id = "ocean"
    name_key = "bg.ocean"
    fallback_name = "Deep Ocean"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        accent = pal.get("PRI", "#00d4ff")
        p.fillRect(0, 0, w, h, _c(base))
        g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.62)
        g.setColorAt(0.00, _mix(base, accent, 0.20))
        g.setColorAt(0.45, _mix(base, accent, 0.07))
        g.setColorAt(1.00, _c(base))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRect(0, 0, w, h)


class Midnight(Background):
    """Top-to-bottom gradient — calm, and it grounds the layout."""
    id = "midnight"
    name_key = "bg.midnight"
    fallback_name = "Midnight"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        accent = pal.get("PRI_DIM", "#007a99")
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0.00, _mix(base, accent, 0.24))
        g.setColorAt(0.55, _mix(base, accent, 0.06))
        g.setColorAt(1.00, _c(base))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRect(0, 0, w, h)


class Nebula(Background):
    """Two offset colour clouds. The most 'designed' of the set."""
    id = "nebula"
    name_key = "bg.nebula"
    fallback_name = "Nebula"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        accent = pal.get("PRI", "#00d4ff")
        alt = pal.get("ACC", "#ff6b00")
        p.fillRect(0, 0, w, h, _c(base))
        p.setPen(Qt.PenStyle.NoPen)

        drift = math.sin(t * 0.10) * w * 0.03
        g1 = QRadialGradient(QPointF(w * 0.28 + drift, h * 0.32), max(w, h) * 0.55)
        g1.setColorAt(0.0, _mix(base, accent, 0.26))
        g1.setColorAt(1.0, _c(base, 0))
        p.setBrush(QBrush(g1)); p.drawRect(0, 0, w, h)

        g2 = QRadialGradient(QPointF(w * 0.74 - drift, h * 0.70), max(w, h) * 0.48)
        g2.setColorAt(0.0, _mix(base, alt, 0.15))
        g2.setColorAt(1.0, _c(base, 0))
        p.setBrush(QBrush(g2)); p.drawRect(0, 0, w, h)


class Carbon(Background):
    """Charcoal with a fine grid — technical, reads as a real instrument panel."""
    id = "carbon"
    name_key = "bg.carbon"
    fallback_name = "Carbon"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        p.fillRect(0, 0, w, h, _mix(base, "#20303a", 0.30))

        p.setPen(QPen(_c(pal.get("BORDER", "#0d3347"), 46), 1))
        step = 34
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)

        # Vignette so the grid fades at the edges instead of stopping dead.
        g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.72)
        g.setColorAt(0.0, _c(base, 0))
        g.setColorAt(1.0, _c(base, 205))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRect(0, 0, w, h)


class Horizon(Background):
    """A lit floor plane under the centrepiece — gives the scene a ground."""
    id = "horizon"
    name_key = "bg.horizon"
    fallback_name = "Horizon"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        accent = pal.get("PRI", "#00d4ff")
        p.fillRect(0, 0, w, h, _c(base))

        hy = h * 0.72
        g = QLinearGradient(0, hy, 0, h)
        g.setColorAt(0.0, _mix(base, accent, 0.20))
        g.setColorAt(1.0, _c(base))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRect(QRectF(0, hy, w, h - hy))

        # Perspective lines converging toward the centre.
        p.setPen(QPen(_c(accent, 34), 1))
        cx = w / 2
        for i in range(-9, 10):
            p.drawLine(QPointF(cx + i * w * 0.11, hy), QPointF(cx + i * w * 0.42, h))
        rows = 7
        for i in range(1, rows + 1):
            frac = (i / rows) ** 2.1
            y = hy + (h - hy) * frac
            p.setPen(QPen(_c(accent, int(40 * (1 - frac) + 12)), 1))
            p.drawLine(QPointF(0, y), QPointF(w, y))

        p.setPen(QPen(_c(accent, 80), 1.4))
        p.drawLine(QPointF(0, hy), QPointF(w, hy))


class Aurora(Background):
    """Slow drifting colour bands. The liveliest option."""
    id = "aurora"
    name_key = "bg.aurora"
    fallback_name = "Aurora"

    def paint(self, p, w, h, pal, t):
        base = pal.get("BG", "#00060a")
        accent = pal.get("PRI", "#00d4ff")
        alt = pal.get("ACC2", "#ffcc00")
        p.fillRect(0, 0, w, h, _c(base))
        p.setPen(Qt.PenStyle.NoPen)

        for i in range(3):
            phase = t * (0.16 + i * 0.05) + i * 2.1
            cxf = 0.5 + math.sin(phase) * 0.30
            cyf = 0.40 + math.cos(phase * 0.8) * 0.22
            col = accent if i != 1 else alt
            g = QRadialGradient(QPointF(w * cxf, h * cyf), max(w, h) * (0.40 + i * 0.09))
            g.setColorAt(0.0, _mix(base, col, 0.20 - i * 0.04))
            g.setColorAt(1.0, _c(base, 0))
            p.setBrush(QBrush(g))
            p.drawRect(0, 0, w, h)


class ColourTheme(Background):
    """
    A background with its OWN fixed colour scheme, independent of the accent.

    The styles above tint themselves from the user's accent colour, so they are
    all variations on one hue. These are proper templates — pick Crimson and the
    whole canvas becomes red regardless of what the accent is set to. That is
    what makes them feel like different themes rather than one theme reskinned.
    """

    def __init__(self, bg_id: str, name: str, deep: str, mid: str, glow: str,
                 vignette: float = 0.55, accent: str | None = None):
        self.id = bg_id
        self.name_key = f"bg.{bg_id}"
        self.fallback_name = name
        self._deep = deep        # darkest, at the edges
        self._mid = mid          # mid tone
        self._glow = glow        # brightest, behind the centrepiece
        self._vig = vignette
        # Default the visualizer accent to this theme's own highlight colour, so
        # picking "Crimson" turns the whole interface red, not just the backdrop.
        self.accent_override = accent or glow

    def paint(self, p, w, h, pal, t):
        p.fillRect(0, 0, w, h, _c(self._deep))
        p.setPen(Qt.PenStyle.NoPen)

        # Diagonal base wash so the canvas is never one flat colour.
        lg = QLinearGradient(0, 0, w, h)
        lg.setColorAt(0.0, _mix(self._deep, self._mid, 0.85))
        lg.setColorAt(0.5, _mix(self._deep, self._mid, 0.35))
        lg.setColorAt(1.0, _c(self._deep))
        p.setBrush(QBrush(lg))
        p.drawRect(0, 0, w, h)

        # Breathing glow centred behind the visualizer.
        pulse = 0.90 + 0.10 * math.sin(t * 0.55)
        rg = QRadialGradient(QPointF(w / 2, h * 0.47), max(w, h) * 0.55 * pulse)
        rg.setColorAt(0.0, _mix(self._mid, self._glow, 0.55))
        rg.setColorAt(0.5, _mix(self._deep, self._glow, 0.16))
        rg.setColorAt(1.0, _c(self._deep, 0))
        p.setBrush(QBrush(rg))
        p.drawRect(0, 0, w, h)

        # Vignette keeps the panels at the edges readable.
        vg = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.78)
        vg.setColorAt(0.0, _c(self._deep, 0))
        vg.setColorAt(1.0, _c(self._deep, int(255 * self._vig)))
        p.setBrush(QBrush(vg))
        p.drawRect(0, 0, w, h)


STYLES: tuple[Background, ...] = (
    # Accent-tinted
    DeepOcean(), Nebula(), Horizon(), Aurora(), Carbon(), Void(),
    # Fixed colour templates
    ColourTheme("crimson", "Crimson", "#0d0204", "#3a0812", "#ff2d55"),
    ColourTheme("violet",  "Violet",  "#08040f", "#26103f", "#a855f7"),
    ColourTheme("matrix",  "Matrix",  "#010a04", "#06301a", "#22ff88"),
    ColourTheme("amber",   "Amber",   "#0d0701", "#3a2205", "#ffa726"),
    ColourTheme("sunset",  "Sunset",  "#0f0409", "#45123a", "#ff6b6b"),
    ColourTheme("arctic",  "Arctic",  "#030a10", "#0e3550", "#7dd3fc", 0.40),
)

DEFAULT_BACKGROUND = "ocean"


def get_background(bg_id: str) -> Background:
    for s in STYLES:
        if s.id == bg_id:
            return s
    return STYLES[0]


def background_ids() -> list[str]:
    return [s.id for s in STYLES]
