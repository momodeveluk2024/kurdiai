"""
Voice visualizer styles for the Kurd AI centrepiece.

The big central animation stays big — it is the identity of the app. What changes
is that the user can now pick between several DISTINCT designs instead of being
stuck with one.

DESIGN RULE: SOLID, NOT TRANSPARENT.
Every style here uses opaque fills, crisp edges and defined shapes. No frosted
glass, no washed-out alpha bleeding, no translucent overlays — the owner asked
specifically not to have that look. Glow is used sparingly and only as a rim or
halo behind a solid form, never as the form itself.

Every style is pure QPainter — no new dependency, nothing extra in the build, and
it scales to any DPI.

ADDING A STYLE
──────────────
Subclass Visualizer, give it an id, a name_key for the translation catalogue, and
implement render(). Register it in STYLES. It appears in the picker automatically.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QLinearGradient, QPainter, QPainterPath,
    QPen, QPolygonF,
)


def _c(hex_str: str, alpha: int = 255) -> QColor:
    col = QColor(hex_str)
    col.setAlpha(alpha)
    return col


@dataclass
class RenderContext:
    """Everything a style needs to draw one frame."""
    t: float                      # animation clock, seconds
    amplitude: float              # smoothed live audio level, 0..1
    bars: list[float]             # per-band levels, 0..1 (spectrum-ish)
    state: str                    # LISTENING | SPEAKING | THINKING | SLEEPING
    speaking: bool
    muted: bool
    palette: dict[str, str]
    size: float                   # min(width, height) of the draw area
    emotion: str = "auto"         # auto | neutral | happy | sad | surprised | angry
    blink: float = 0.0            # 0 = eyes open, 1 = fully closed

    def mood(self) -> str:
        """Resolve 'auto' into a mood derived from the assistant's current state."""
        if self.emotion != "auto":
            return self.emotion
        if self.muted:
            return "sad"
        if self.state == "THINKING":
            return "thinking"
        if self.state == "SLEEPING":
            return "sleeping"
        if self.speaking:
            return "happy"
        return "neutral"

    def accent(self) -> str:
        if self.muted:
            return self.palette.get("MUTED_C", "#ff3366")
        if self.speaking:
            return self.palette.get("ACC", "#ff6b00")
        if self.state == "THINKING":
            return self.palette.get("ACC2", "#ffcc00")
        return self.palette.get("PRI", "#00d4ff")

    def dim(self) -> str:
        if self.muted:
            return "#8a1c36"
        if self.speaking:
            return "#8a3a00"
        if self.state == "THINKING":
            return "#8a6f00"
        return self.palette.get("PRI_DIM", "#007a99")


class Visualizer:
    id: str = "base"
    name_key: str = "viz.base"
    fallback_name: str = "Base"

    def render(self, p: QPainter, cx: float, cy: float, ctx: RenderContext) -> None:
        raise NotImplementedError


# ── 1. Arc Reactor — the original look, made solid and crisper ───────────────

class ArcReactor(Visualizer):
    id = "reactor"
    name_key = "viz.reactor"
    fallback_name = "Arc Reactor"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.34
        accent, dim = ctx.accent(), ctx.dim()

        # Solid core disc — opaque, not a translucent wash.
        core = r * (0.34 + ctx.amplitude * 0.06)
        p.setPen(QPen(_c(accent), 2.5))
        p.setBrush(QBrush(_c(ctx.palette.get("DARK", "#000d14"))))
        p.drawEllipse(QPointF(cx, cy), core, core)

        inner = core * 0.55
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c(accent)))
        p.drawEllipse(QPointF(cx, cy), inner, inner)

        # Concentric solid rings at fixed radii.
        for i, mult in enumerate((0.56, 0.72, 0.88, 1.04)):
            rr = r * mult
            width = 2.4 if i % 2 == 0 else 1.4
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(_c(dim), width))
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Rotating solid arc segments.
        for k, (mult, speed, span) in enumerate(
                ((0.64, 34, 70), (0.80, -22, 110), (0.96, 48, 46))):
            rr = r * mult
            rect = QRectF(cx - rr, cy - rr, rr * 2, rr * 2)
            start = int((ctx.t * speed + k * 90) * 16)
            p.setPen(QPen(_c(accent), 3.4, cap=Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, start, int((span + ctx.amplitude * 60) * 16))

        # Radial tick marks driven by audio.
        p.setPen(QPen(_c(accent), 2.2, cap=Qt.PenCapStyle.FlatCap))
        n = len(ctx.bars)
        for i, lvl in enumerate(ctx.bars):
            a = math.tau * i / n - math.pi / 2
            i0 = r * 1.12
            i1 = i0 + r * (0.06 + lvl * 0.26)
            p.drawLine(QPointF(cx + math.cos(a) * i0, cy + math.sin(a) * i0),
                       QPointF(cx + math.cos(a) * i1, cy + math.sin(a) * i1))


# ── 2. Radial Spectrum — solid wedges around a ring ─────────────────────────

class RadialSpectrum(Visualizer):
    id = "spectrum"
    name_key = "viz.spectrum"
    fallback_name = "Spectrum"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.34
        accent, dim = ctx.accent(), ctx.dim()
        n = len(ctx.bars)
        inner = r * 0.46

        p.setPen(Qt.PenStyle.NoPen)
        for i, lvl in enumerate(ctx.bars):
            a0 = math.tau * i / n
            a1 = a0 + math.tau / n * 0.62
            length = inner + r * (0.10 + lvl * 0.72)

            poly = QPolygonF([
                QPointF(cx + math.cos(a0) * inner, cy + math.sin(a0) * inner),
                QPointF(cx + math.cos(a0) * length, cy + math.sin(a0) * length),
                QPointF(cx + math.cos(a1) * length, cy + math.sin(a1) * length),
                QPointF(cx + math.cos(a1) * inner, cy + math.sin(a1) * inner),
            ])
            # Solid fill, brightness tracks level — no alpha fade.
            shade = QColor(accent)
            shade = shade.darker(int(190 - lvl * 80)) if lvl < 0.55 else shade
            p.setBrush(QBrush(shade))
            p.drawPolygon(poly)

        p.setBrush(QBrush(_c(ctx.palette.get("DARK", "#000d14"))))
        p.setPen(QPen(_c(accent), 3.0))
        p.drawEllipse(QPointF(cx, cy), inner * 0.86, inner * 0.86)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c(accent)))
        pulse = inner * (0.30 + ctx.amplitude * 0.18)
        p.drawEllipse(QPointF(cx, cy), pulse, pulse)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_c(dim), 1.6))
        p.drawEllipse(QPointF(cx, cy), r * 1.20, r * 1.20)


# ── 3. Oscilloscope — a solid waveform trace ────────────────────────────────

class Oscilloscope(Visualizer):
    id = "wave"
    name_key = "viz.wave"
    fallback_name = "Waveform"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.36
        accent, dim = ctx.accent(), ctx.dim()
        w = r * 2.2
        x0 = cx - w / 2

        # Grid — solid thin lines, reads as instrumentation.
        p.setPen(QPen(_c(dim), 1.0))
        for k in range(-2, 3):
            y = cy + k * r * 0.26
            p.drawLine(QPointF(x0, y), QPointF(x0 + w, y))
        for k in range(0, 9):
            x = x0 + w * k / 8
            p.drawLine(QPointF(x, cy - r * 0.55), QPointF(x, cy + r * 0.55))

        # The trace: solid stroked polyline, thick enough to read at a glance.
        pts = []
        n = 120
        for i in range(n + 1):
            frac = i / n
            x = x0 + w * frac
            env = math.sin(math.pi * frac)          # taper at both ends
            v = (math.sin(frac * 22 + ctx.t * 7.0) * 0.55
                 + math.sin(frac * 41 - ctx.t * 4.2) * 0.30
                 + math.sin(frac * 9 + ctx.t * 2.1) * 0.15)
            y = cy + v * env * r * (0.10 + ctx.amplitude * 0.80)
            pts.append(QPointF(x, y))

        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_c(accent), 3.0, cap=Qt.PenCapStyle.RoundCap,
                      join=Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)

        # Solid end caps.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c(accent)))
        for pt in (pts[0], pts[-1]):
            p.drawEllipse(pt, 4.0, 4.0)


# ── 4. Pulse Rings — solid rings expanding outward ──────────────────────────

class PulseRings(Visualizer):
    id = "pulse"
    name_key = "viz.pulse"
    fallback_name = "Pulse Rings"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.36
        accent, dim = ctx.accent(), ctx.dim()

        p.setBrush(Qt.BrushStyle.NoBrush)
        rings = 5
        for i in range(rings):
            phase = (ctx.t * 0.42 + i / rings) % 1.0
            rr = r * (0.28 + phase * 0.92)
            # Fade by WIDTH rather than alpha, so rings stay solid.
            width = max(0.8, 4.2 * (1.0 - phase))
            col = QColor(accent) if phase < 0.5 else QColor(dim)
            p.setPen(QPen(col, width))
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        core = r * (0.24 + ctx.amplitude * 0.14)
        p.setPen(QPen(_c(accent), 3.0))
        p.setBrush(QBrush(_c(ctx.palette.get("DARK", "#000d14"))))
        p.drawEllipse(QPointF(cx, cy), core, core)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c(accent)))
        p.drawEllipse(QPointF(cx, cy), core * 0.5, core * 0.5)


# ── 5. Equalizer — solid vertical bars ──────────────────────────────────────

class Equalizer(Visualizer):
    id = "bars"
    name_key = "viz.bars"
    fallback_name = "Equalizer"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.36
        accent, dim = ctx.accent(), ctx.dim()
        n = len(ctx.bars)
        total_w = r * 2.0
        bw = total_w / n * 0.66
        gap = total_w / n
        x0 = cx - total_w / 2 + gap / 2
        base = cy + r * 0.52
        maxh = r * 1.0

        p.setPen(Qt.PenStyle.NoPen)
        for i, lvl in enumerate(ctx.bars):
            h = max(3.0, maxh * (0.05 + lvl * 0.95))
            x = x0 + i * gap - bw / 2
            grad = QLinearGradient(0, base - h, 0, base)
            grad.setColorAt(0.0, _c(accent))
            grad.setColorAt(1.0, _c(dim))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(x, base - h, bw, h), bw * 0.28, bw * 0.28)

            # Solid peak cap.
            p.setBrush(QBrush(_c(accent)))
            p.drawRoundedRect(QRectF(x, base - h - 4.0, bw, 3.0), 1.5, 1.5)

        p.setPen(QPen(_c(dim), 2.0))
        p.drawLine(QPointF(cx - total_w / 2, base + 3), QPointF(cx + total_w / 2, base + 3))


# ── 6. Solid Orb — one filled sphere that breathes ──────────────────────────

class SolidOrb(Visualizer):
    id = "orb"
    name_key = "viz.orb"
    fallback_name = "Solid Orb"

    def render(self, p, cx, cy, ctx):
        r = ctx.size * 0.30
        accent, dim = ctx.accent(), ctx.dim()
        rr = r * (1.0 + ctx.amplitude * 0.16 + math.sin(ctx.t * 1.4) * 0.02)

        # Deformed solid blob — radius wobbles per angle with the audio.
        path = QPainterPath()
        n = 96
        for i in range(n + 1):
            a = math.tau * i / n
            wob = (math.sin(a * 3 + ctx.t * 2.1) * 0.035
                   + math.sin(a * 5 - ctx.t * 1.6) * 0.025) * (0.4 + ctx.amplitude)
            rad = rr * (1.0 + wob)
            pt = QPointF(cx + math.cos(a) * rad, cy + math.sin(a) * rad)
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()

        grad = QLinearGradient(cx, cy - rr, cx, cy + rr)
        grad.setColorAt(0.0, _c(accent))
        grad.setColorAt(1.0, _c(dim))
        p.setPen(QPen(_c(accent).lighter(130), 2.0))
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Solid concentric contour lines — gives it form without transparency.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_c(ctx.palette.get("DARK", "#000d14")), 1.6))
        for mult in (0.42, 0.62, 0.82):
            p.drawEllipse(QPointF(cx, cy - rr * 0.06), rr * mult, rr * mult * 0.92)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c(accent).lighter(160)))
        p.drawEllipse(QPointF(cx - rr * 0.30, cy - rr * 0.36), rr * 0.16, rr * 0.11)


# ── 7. Dot Matrix Face — an LED face that actually emotes ───────────────────

# Per-mood facial parameters. Everything is expressed in a normalised face space
# where x and y run -1..1, y increasing downward (screen convention).
#
#   eye_h      vertical scale of the eyes (small = squinting/happy)
#   eye_y      vertical eye position (higher = looking up)
#   brow       brow tilt: negative = inner ends down (angry), positive = inner
#              ends up (sad/worried), 0 = no brows drawn
#   smile      mouth curvature: positive = corners up (smile), negative = frown
#   mouth_open resting mouth thickness before speech is added
# Calibration note: mouth_open is a HALF-thickness in normalised face units, so
# small numbers go a long way — 0.16 already reads as a wide-open mouth. An
# earlier pass used values around 0.34 plus an unclamped speech term, which made
# the mouth swallow the entire lower face. Expression comes mostly from `smile`
# (the curve), not from thickness.
_MOODS: dict[str, dict[str, float]] = {
    "neutral":   dict(eye_h=1.00, eye_y=0.00, brow=0.00, smile=0.30, mouth_open=0.03),
    "happy":     dict(eye_h=0.55, eye_y=0.02, brow=0.00, smile=0.85, mouth_open=0.04),
    "sad":       dict(eye_h=0.88, eye_y=0.05, brow=0.40, smile=-0.62, mouth_open=0.03),
    "surprised": dict(eye_h=1.30, eye_y=-0.03, brow=0.26, smile=0.05, mouth_open=0.15),
    "angry":     dict(eye_h=0.72, eye_y=0.02, brow=-0.48, smile=-0.45, mouth_open=0.03),
    "thinking":  dict(eye_h=0.92, eye_y=-0.12, brow=0.20, smile=0.08, mouth_open=0.03),
    "sleeping":  dict(eye_h=0.05, eye_y=0.04, brow=0.00, smile=0.25, mouth_open=0.02),
}


class DotFace(Visualizer):
    """
    A face rendered as a grid of dots, like an LED matrix sign.

    Every dot is lit by sampling the facial features analytically rather than
    from a bitmap, so expressions interpolate smoothly and the face works at any
    resolution. Unlit dots stay faintly visible, which is what makes it read as a
    physical dot-matrix panel instead of scattered circles.

    The mouth opens with real microphone amplitude while speaking, and the mood
    follows the assistant's state unless a specific emotion is forced.
    """
    id = "face"
    name_key = "viz.face"
    fallback_name = "Dot Face"

    GRID = 26            # dots across; the face is square so this is both axes

    # Smoothed mood parameters, so switching expression eases rather than snaps.
    GOLDEN = 2.39996323            # golden angle, for even orb packing
    FORM_SECONDS = 1.9             # orb -> face assembly time

    def __init__(self):
        self._cur = dict(_MOODS["neutral"])
        self._dots = None          # built lazily on first render
        self._t0 = None            # animation clock at first render

    # ── dot geometry ────────────────────────────────────────────────────────

    def _ensure_dots(self) -> None:
        """
        Build the particle set once: each dot gets a HOME slot in the face grid
        and a START slot inside a packed orb.

        Slots are paired by distance from centre — the innermost orb positions map
        to the innermost grid positions — so the assembly reads as the orb
        expanding outward rather than dots crossing over each other.
        """
        if self._dots is not None:
            return

        homes = []
        for gy in range(self.GRID):
            for gx in range(self.GRID):
                nx = -1.0 + 2.0 * gx / (self.GRID - 1)
                ny = -1.0 + 2.0 * gy / (self.GRID - 1)
                if nx * nx + ny * ny > 1.04:
                    continue
                homes.append((nx, ny))

        homes.sort(key=lambda q: q[0] * q[0] + q[1] * q[1])
        n = len(homes)

        self._dots = []
        for i, (hx, hy) in enumerate(homes):
            # Sunflower packing gives an evenly dense disc with no seams.
            rad = 0.30 * math.sqrt((i + 0.5) / n)
            ang = i * self.GOLDEN
            self._dots.append({
                "hx": hx, "hy": hy,                              # face position
                "ox": math.cos(ang) * rad,                       # orb position
                "oy": math.sin(ang) * rad * 0.96,
                "v": 0.0,                                        # eased brightness
                "ph": (i * 0.618) % math.tau,                    # idle-wobble phase
            })

    def _target(self, ctx: RenderContext) -> dict[str, float]:
        return _MOODS.get(ctx.mood(), _MOODS["neutral"])

    def _face_value(self, nx, ny, m, blink, open_amt) -> float:
        """Brightness this position should have for the current expression."""
        eye_h = m["eye_h"] * (1.0 - blink * 0.94)
        eye_cy = -0.30 + m["eye_y"]
        eye_cx = 0.36
        eye_rx, eye_ry = 0.155, 0.205 * max(0.04, eye_h)

        v = 0.0
        for sign in (-1.0, 1.0):
            ex = (nx - sign * eye_cx) / eye_rx
            ey = (ny - eye_cy) / eye_ry
            d = ex * ex + ey * ey
            if d <= 1.0:
                v = max(v, 1.0 - d * 0.35)

        brow = m["brow"]
        if abs(brow) > 0.03 and blink < 0.7:
            for sign in (-1.0, 1.0):
                bx = (nx - sign * eye_cx) / 0.26
                if -1.0 <= bx <= 1.0:
                    inner = -sign * bx
                    by = eye_cy - 0.40 + brow * inner * 0.20
                    if abs(ny - by) <= 0.055:
                        v = max(v, 0.92)

        u = nx / 0.54
        if -1.0 <= u <= 1.0:
            centre = 0.34 + m["smile"] * (1.0 - u * u) * 0.26
            half_thick = 0.035 + open_amt * (1.0 - u * u)
            if abs(ny - centre) <= half_thick:
                v = max(v, 0.95)
        return v

    # ── render ──────────────────────────────────────────────────────────────

    def render(self, p, cx, cy, ctx):
        self._ensure_dots()
        if self._t0 is None:
            self._t0 = ctx.t

        # Assembly progress, eased so it starts fast and settles gently.
        raw = max(0.0, min(1.0, (ctx.t - self._t0) / self.FORM_SECONDS))
        form = 1.0 - (1.0 - raw) ** 3          # ease-out-cubic

        tgt = self._target(ctx)
        for k, v in tgt.items():
            self._cur[k] += (v - self._cur[k]) * 0.16
        m = self._cur

        accent = ctx.accent()
        half = ctx.size * 0.40
        step = (half * 2.0) / (self.GRID - 1)
        dot_max = step * 0.44

        lit_col = QColor(accent)
        off_col = QColor(accent)
        off_col.setAlpha(30)

        open_amt = min(m["mouth_open"] +
                       (ctx.amplitude * 0.16 if ctx.speaking else 0.0), 0.19)

        # A slow swirl during assembly makes the orb feel alive rather than
        # mechanically interpolated. It unwinds to zero as the face settles.
        swirl = (1.0 - form) * 0.9
        breathe = 1.0 + math.sin(ctx.t * 1.3) * 0.012 + ctx.amplitude * 0.05

        p.setPen(Qt.PenStyle.NoPen)

        for d in self._dots:
            # Position: orb slot -> face slot.
            ox, oy = d["ox"], d["oy"]
            if swirl > 0.001:
                ca, sa = math.cos(swirl), math.sin(swirl)
                ox, oy = ox * ca - oy * sa, ox * sa + oy * ca

            nx = ox + (d["hx"] - ox) * form
            ny = oy + (d["hy"] - oy) * form

            # Idle drift so the panel never looks frozen.
            wob = 0.004 + ctx.amplitude * 0.010
            nx += math.sin(ctx.t * 1.7 + d["ph"]) * wob
            ny += math.cos(ctx.t * 1.4 + d["ph"] * 1.3) * wob

            # Brightness: every dot glows while it is still an orb, then only the
            # facial features stay lit as the face resolves.
            face_v = self._face_value(d["hx"], d["hy"], m, ctx.blink, open_amt)
            target_v = face_v + (1.0 - form) * (0.85 - face_v)
            d["v"] += (target_v - d["v"]) * 0.22
            v = d["v"]

            x = cx + nx * half * breathe
            y = cy + ny * half * breathe

            if v <= 0.06:
                p.setBrush(QBrush(off_col))
                r = dot_max * 0.26
            else:
                p.setBrush(QBrush(lit_col))
                pulse = 1.0 + math.sin(ctx.t * 3.0 + d["ph"]) * 0.06 * v
                r = dot_max * (0.55 + 0.45 * v) * pulse
            p.drawEllipse(QPointF(x, y), r, r)

        # Panel ring fades in as the face assembles.
        if form > 0.15:
            rr = half * 1.22
            rect = QRectF(cx - rr, cy - rr, rr * 2, rr * 2)
            ring = QColor(ctx.dim())
            ring.setAlpha(int(255 * min(1.0, (form - 0.15) / 0.5)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ring, 1.6))
            p.drawEllipse(rect)

            if ctx.amplitude > 0.02:
                p.setPen(QPen(_c(accent), 3.0, cap=Qt.PenCapStyle.RoundCap))
                span = int(ctx.amplitude * 300 * 16)
                p.drawArc(rect, 90 * 16, -span // 2)
                p.drawArc(rect, 90 * 16, span // 2)

    def replay(self) -> None:
        """Re-run the orb->face assembly (used when the style is re-selected)."""
        self._t0 = None
        if self._dots:
            for d in self._dots:
                d["v"] = 0.0

# ── registry ────────────────────────────────────────────────────────────────

STYLES: tuple[Visualizer, ...] = (
    DotFace(),          # the expressive one — listed first
    ArcReactor(),
    RadialSpectrum(),
    Equalizer(),
    Oscilloscope(),
    PulseRings(),
    SolidOrb(),
)

DEFAULT_STYLE = "face"


def get_style(style_id: str) -> Visualizer:
    for s in STYLES:
        if s.id == style_id:
            return s
    return STYLES[0]


def style_ids() -> list[str]:
    return [s.id for s in STYLES]
