"""
Floating desktop companion — the "mini mode" Kurd AI minimises into.

A small, frameless, always-on-top character that sits on the desktop, reacts to
the assistant's state and to your voice, and can be dragged anywhere. Double-click
it to bring the full HUD back.

WHY THE CHARACTER IS DRAWN IN CODE
──────────────────────────────────
Every ready-made desktop mascot worth having (Shimeji and friends) ships
copyrighted character art — usually anime characters the project has no right to
sublicense. Kurd AI is distributed under a proprietary licence with the author's
name on it, so shipping downloaded art would put a copyright claim on someone
else's work inside a product claiming to be original.

So the character is drawn procedurally with QPainter. That means:
  * zero licensing risk — it is original work, generated from maths
  * it scales to any DPI with no blurring, and needs no image assets
  * it recolours itself from the user's accent colour automatically
  * it adds nothing to the PyInstaller bundle size

ANIMATION STATES
────────────────
  LISTENING  calm slow bob, eyes open and blinking, ring pulses with mic level
  SPEAKING   energetic bounce, mouth animates from the audio amplitude
  THINKING   eyes glance upward, three dots orbit the head
  SLEEPING   eyes closed, very slow breathing, dimmed
  MUTED      eyes open, a slash across the ring, desaturated
"""
from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import QMenu, QWidget

# Window is larger than the character so the glow has room to bloom.
_SIZE = 190
_BODY = 96.0


def _c(hex_str: str, alpha: int = 255) -> QColor:
    col = QColor(hex_str)
    col.setAlpha(alpha)
    return col


class CompanionWindow(QWidget):
    """Small always-on-top animated companion."""

    restore_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    mute_toggled = pyqtSignal()

    def __init__(self, palette: dict[str, str], parent=None):
        # Tool (not Window) keeps it out of the taskbar and out of Alt-Tab, which
        # is what makes it feel like a desktop pet rather than a second app.
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(_SIZE, _SIZE)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Double-click to restore  ·  drag to move")

        self._pal = palette
        self._state = "LISTENING"
        self._muted = False
        self._amp = 0.0          # smoothed 0..1 audio level
        self._amp_target = 0.0

        self._t = 0.0            # animation clock, seconds
        self._blink = 0.0        # 0 = open, 1 = fully closed
        self._next_blink = 2.5
        self._drag_offset: QPoint | None = None
        self._eye_dx = 0.0
        self._eye_dy = 0.0
        self._dots = [random.uniform(0, math.tau) for _ in range(3)]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)    # ~30 fps — smooth, and gentle on the CPU

    # ── external API ────────────────────────────────────────────────────────

    def set_palette(self, palette: dict[str, str]) -> None:
        self._pal = palette
        self.update()

    def set_state(self, state: str) -> None:
        self._state = (state or "LISTENING").upper()
        self.update()

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self.update()

    def set_amplitude(self, level: float) -> None:
        """Feed a 0..1 audio level. Smoothed in _tick so the motion is not jittery."""
        self._amp_target = max(0.0, min(1.0, float(level)))

    # ── animation ───────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._t += 0.033

        # Asymmetric smoothing: rise fast so it feels responsive to speech,
        # fall slowly so it does not flicker between syllables.
        if self._amp_target > self._amp:
            self._amp += (self._amp_target - self._amp) * 0.45
        else:
            self._amp += (self._amp_target - self._amp) * 0.12
        self._amp_target *= 0.90

        # Blink: a quick close-and-open on a randomised interval.
        if self._state == "SLEEPING":
            self._blink = 1.0
        else:
            self._next_blink -= 0.033
            if self._next_blink <= 0:
                self._blink += 0.34
                if self._blink >= 1.0:
                    self._blink = 1.0
                    self._next_blink = -0.001
                if self._next_blink < 0 and self._blink >= 1.0:
                    self._next_blink = random.uniform(2.0, 5.5)
                    self._blink = 0.999
            if 0 < self._blink < 1.0 and self._next_blink > 0:
                self._blink = max(0.0, self._blink - 0.28)

        # Eyes drift slowly, and glance up while thinking.
        if self._state == "THINKING":
            self._eye_dy += (-3.2 - self._eye_dy) * 0.08
            self._eye_dx += (math.sin(self._t * 1.4) * 2.2 - self._eye_dx) * 0.08
        else:
            self._eye_dx += (math.sin(self._t * 0.6) * 1.8 - self._eye_dx) * 0.05
            self._eye_dy += (math.sin(self._t * 0.43) * 1.1 - self._eye_dy) * 0.05

        for i in range(len(self._dots)):
            self._dots[i] += 0.055

        self.update()

    # ── painting ────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx, cy = self.width() / 2.0, self.height() / 2.0

        # Vertical bob — slower and shallower when idle, bouncier while speaking.
        if self._state == "SPEAKING":
            bob = math.sin(self._t * 5.0) * (3.0 + self._amp * 6.0)
        elif self._state == "SLEEPING":
            bob = math.sin(self._t * 0.9) * 1.6
        else:
            bob = math.sin(self._t * 1.7) * 2.6
        cy += bob

        accent = self._pal.get("PRI", "#00d4ff")
        dim = self._pal.get("PRI_DIM", "#007a99")
        if self._muted:
            accent = self._pal.get("MUTED_C", "#ff3366")
            dim = "#7a2038"
        elif self._state == "SPEAKING":
            accent = self._pal.get("ACC", "#ff6b00")
            dim = "#8a3a00"
        elif self._state == "THINKING":
            accent = self._pal.get("ACC2", "#ffcc00")
            dim = "#8a6f00"

        breathe = 1.0 + math.sin(self._t * 1.25) * 0.022
        radius = (_BODY / 2.0) * breathe * (1.0 + self._amp * 0.10)

        self._paint_glow(p, cx, cy, radius, accent)
        self._paint_ring(p, cx, cy, radius, accent, dim)
        self._paint_body(p, cx, cy, radius, accent, dim)
        self._paint_face(p, cx, cy, radius, accent)

        if self._state == "THINKING":
            self._paint_think_dots(p, cx, cy, radius, accent)
        if self._muted:
            self._paint_mute_slash(p, cx, cy, radius)

    def _paint_glow(self, p, cx, cy, r, accent) -> None:
        """Soft outer bloom, brighter with audio."""
        reach = r * (1.75 + self._amp * 0.55)
        grad = QRadialGradient(QPointF(cx, cy), reach)
        strength = 62 if self._state != "SLEEPING" else 26
        grad.setColorAt(0.00, _c(accent, int(strength + self._amp * 60)))
        grad.setColorAt(0.45, _c(accent, int(strength * 0.42)))
        grad.setColorAt(1.00, _c(accent, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), reach, reach)

    def _paint_ring(self, p, cx, cy, r, accent, dim) -> None:
        """Rotating arc ring — the 'this is an AI' cue, and the audio meter."""
        rr = r * 1.32
        rect = QRectF(cx - rr, cy - rr, rr * 2, rr * 2)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_c(dim, 90), 1.4))
        p.drawEllipse(rect)

        spin = -self._t * (28 if self._state != "SPEAKING" else 74)
        span = 52 + self._amp * 120
        p.setPen(QPen(_c(accent, 210), 2.6, cap=Qt.PenCapStyle.RoundCap))
        for k in range(3):
            start = int((spin + k * 120) * 16)
            p.drawArc(rect, start, int(span * 16))

        # Amplitude ticks around the ring while listening or speaking.
        if self._state in ("LISTENING", "SPEAKING") and self._amp > 0.02:
            p.setPen(QPen(_c(accent, 150), 1.8, cap=Qt.PenCapStyle.RoundCap))
            for i in range(20):
                a = math.tau * i / 20.0
                lvl = self._amp * (0.45 + 0.55 * abs(math.sin(self._t * 3 + i)))
                inner = rr * 1.10
                outer = inner + 4 + lvl * 13
                p.drawLine(
                    QPointF(cx + math.cos(a) * inner, cy + math.sin(a) * inner),
                    QPointF(cx + math.cos(a) * outer, cy + math.sin(a) * outer),
                )

    def _paint_body(self, p, cx, cy, r, accent, dim) -> None:
        """Rounded translucent body with a glassy highlight."""
        grad = QRadialGradient(QPointF(cx - r * 0.28, cy - r * 0.34), r * 1.85)
        grad.setColorAt(0.00, _c(accent, 205))
        grad.setColorAt(0.42, _c(dim, 185))
        grad.setColorAt(1.00, _c(self._pal.get("DARK", "#000d14"), 235))
        p.setPen(QPen(_c(accent, 165), 1.8))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Specular highlight — this is most of what makes it read as "cute".
        hp = QPainterPath()
        hp.addEllipse(QPointF(cx - r * 0.33, cy - r * 0.42), r * 0.30, r * 0.20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c("#ffffff", 62)))
        p.drawPath(hp)

    def _paint_face(self, p, cx, cy, r, accent) -> None:
        eye_dx = r * 0.34
        eye_y = cy - r * 0.08 + self._eye_dy
        ew, eh = r * 0.17, r * 0.25
        open_amt = 1.0 - self._blink

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_c("#eafcff", 240)))

        for sign in (-1, 1):
            ex = cx + sign * eye_dx + self._eye_dx * 0.5
            if open_amt <= 0.08:
                p.setPen(QPen(_c("#eafcff", 220), 2.4, cap=Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(ex - ew, eye_y), QPointF(ex + ew, eye_y))
                p.setPen(Qt.PenStyle.NoPen)
            else:
                path = QPainterPath()
                path.addEllipse(QPointF(ex, eye_y), ew, eh * open_amt)
                p.drawPath(path)

        # Mouth: a small arc that opens with the voice while speaking.
        if self._state == "SPEAKING":
            mh = r * (0.06 + self._amp * 0.26)
            mw = r * 0.24
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(_c("#0a1a22", 210)))
            path = QPainterPath()
            path.addEllipse(QPointF(cx, cy + r * 0.34), mw, mh)
            p.drawPath(path)
        elif self._state != "SLEEPING":
            p.setPen(QPen(_c("#eafcff", 165), 2.0, cap=Qt.PenCapStyle.RoundCap))
            rect = QRectF(cx - r * 0.20, cy + r * 0.16, r * 0.40, r * 0.28)
            p.drawArc(rect, 200 * 16, 140 * 16)   # gentle smile

    def _paint_think_dots(self, p, cx, cy, r, accent) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        for i, a in enumerate(self._dots):
            rad = r * 1.62
            x = cx + math.cos(a) * rad
            y = cy + math.sin(a) * rad * 0.55 - r * 0.55
            size = 3.0 + math.sin(self._t * 3 + i) * 1.1
            p.setBrush(QBrush(_c(accent, 200)))
            p.drawEllipse(QPointF(x, y), size, size)

    def _paint_mute_slash(self, p, cx, cy, r) -> None:
        p.setPen(QPen(_c(self._pal.get("MUTED_C", "#ff3366"), 225), 3.4,
                      cap=Qt.PenCapStyle.RoundCap))
        d = r * 0.98
        p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))

    # ── interaction ─────────────────────────────────────────────────────────

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            # globalPosition() is float-based in Qt6; toPoint() for arithmetic.
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_offset is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        self._drag_offset = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._snap_to_screen()
        e.accept()

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.restore_requested.emit()
            e.accept()

    def contextMenuEvent(self, e) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {self._pal.get('PANEL', '#010d14')};
                color: {self._pal.get('TEXT', '#8ffcff')};
                border: 1px solid {self._pal.get('BORDER_B', '#1a5c7a')};
                padding: 4px;
            }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{
                background: {self._pal.get('PRI_GHO', '#001f2e')};
                color: {self._pal.get('PRI', '#00d4ff')};
            }}
        """)
        menu.setFont(QFont("Courier New", 8))
        menu.addAction("Restore", lambda: self.restore_requested.emit())
        menu.addAction("Unmute" if self._muted else "Mute",
                       lambda: self.mute_toggled.emit())
        menu.addSeparator()
        menu.addAction("Quit", lambda: self.quit_requested.emit())
        menu.exec(e.globalPos())

    def _snap_to_screen(self) -> None:
        """Keep the companion fully on-screen after a drag, and snap near edges."""
        scr = self.screen()
        if scr is None:
            return
        area = scr.availableGeometry()
        g = self.frameGeometry()
        x, y = g.x(), g.y()
        margin = 18

        if x - area.left() < margin:
            x = area.left()
        elif area.right() - (x + g.width()) < margin:
            x = area.right() - g.width()
        if y - area.top() < margin:
            y = area.top()
        elif area.bottom() - (y + g.height()) < margin:
            y = area.bottom() - g.height()

        x = max(area.left(), min(x, area.right() - g.width()))
        y = max(area.top(), min(y, area.bottom() - g.height()))
        self.move(x, y)

    def place_default(self) -> None:
        """Bottom-right of the primary screen, above the taskbar."""
        scr = self.screen()
        if scr is None:
            return
        area = scr.availableGeometry()
        self.move(area.right() - self.width() - 28,
                  area.bottom() - self.height() - 28)
