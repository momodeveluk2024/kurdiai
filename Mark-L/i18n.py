"""
Runtime translation for Kurd AI.

Supports English, Sorani Kurdish (کوردیی ناوەندی), Kurmanji Kurdish (Kurmancî)
and Arabic (العربية), switchable at runtime with no restart.

HOW IT WORKS
────────────
Catalogues live in lang/<code>.json as flat key -> string maps. en.json is the
reference and additionally carries per-string metadata (maxLength, note) used by
translators; the runtime only reads the text.

Widgets are BOUND rather than assigned:

    i18n.bind(label, "monitor.title")          # instead of label.setText("SYS MONITOR")

bind() sets the text immediately and remembers the widget, so when the language
changes every bound widget updates itself. Widgets are held weakly, so binding
never keeps a destroyed widget alive.

Custom-painted widgets (HudCanvas, MetricBar, _DropCanvas) draw text inside
paintEvent instead of owning a QLabel. They call t() directly at paint time and
connect to `changed` to trigger a repaint — no registry entry needed.

RIGHT-TO-LEFT
─────────────
Sorani and Arabic are RTL. set_language() flips QApplication layout direction,
which mirrors standard Qt layouts automatically. Custom paintEvent code does NOT
auto-mirror — those widgets must check is_rtl() themselves.
"""
from __future__ import annotations

import json
import weakref
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication

try:
    from paths import resource_path, app_root
except ImportError:  # standalone use
    def resource_path(*p): return Path(__file__).resolve().parent.joinpath(*p)
    def app_root(): return Path(__file__).resolve().parent


DEFAULT_LANG = "en"

# Display order in the picker. Sorani first — this is a Kurdish product.
LANGUAGES: tuple[tuple[str, str, str, str], ...] = (
    # (code, endonym,                    english name,      direction)
    ("ckb", "کوردیی ناوەندی",            "Kurdish (Sorani)",   "rtl"),
    ("kmr", "Kurmancî",                  "Kurdish (Kurmanji)", "ltr"),
    ("ar",  "العربية",                    "Arabic",             "rtl"),
    ("en",  "English",                   "English",            "ltr"),
)

LANG_CODES = tuple(c for c, *_ in LANGUAGES)
_DIRECTIONS = {c: d for c, _e, _n, d in LANGUAGES}


def _lang_dir() -> Path:
    """lang/ ships with the app, so it is a bundled resource, not user data."""
    return resource_path("lang")


class _I18N(QObject):
    changed = pyqtSignal(str)   # emits the new language code

    def __init__(self) -> None:
        super().__init__()
        self._lang: str = DEFAULT_LANG
        self._catalog: dict[str, str] = {}
        self._fallback: dict[str, str] = {}
        # (weakref to widget, setter name, key) — widgets to refresh on change
        self._bindings: list[tuple[weakref.ref, str, str]] = []
        self._load_fallback()

    # ── catalogue loading ───────────────────────────────────────────────────

    @staticmethod
    def _read(code: str) -> dict[str, str]:
        path = _lang_dir() / f"{code}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[i18n] Could not load {path.name}: {e}")
            return {}
        out: dict[str, str] = {}
        for key, val in raw.items():
            if key == "_meta":
                continue
            # en.json stores {"text": ..., "maxLength": ...}; others store plain strings.
            out[key] = val["text"] if isinstance(val, dict) else str(val)
        return out

    def _load_fallback(self) -> None:
        self._fallback = self._read(DEFAULT_LANG)

    # ── public API ──────────────────────────────────────────────────────────

    @property
    def language(self) -> str:
        return self._lang

    def direction(self) -> str:
        return _DIRECTIONS.get(self._lang, "ltr")

    def is_rtl(self) -> bool:
        return self.direction() == "rtl"

    def t(self, key: str, default: str | None = None) -> str:
        """
        Look up a translated string.

        Falls back to English, then to `default`, then to the key itself — so a
        missing translation degrades to readable English rather than a crash or
        an empty label.
        """
        val = self._catalog.get(key)
        if val:
            return val
        val = self._fallback.get(key)
        if val:
            return val
        return default if default is not None else key

    def set_language(self, code: str, *, apply_direction: bool = False) -> bool:
        """
        Switch language and refresh every bound widget. Returns False if unknown.

        apply_direction defaults to FALSE — deliberately. Calling
        QApplication.setLayoutDirection(RightToLeft) mirrors the entire window,
        and on this HUD that is actively harmful:

          * The activity-log panel slid off the left screen edge and was clipped.
          * MetricBar and HudCanvas paint at absolute x-coordinates inside
            paintEvent. Qt mirrors LAYOUTS, never custom painting — so the meter
            values ended up drawn on top of their own labels ("47KB/s" over "NET").
          * The footer byline and the window title were truncated.

        A sci-fi HUD is not a document. The arc reactor is radially symmetric and
        the meter column reads the same either way, so mirroring the chrome buys
        nothing while breaking the parts that cannot mirror themselves. What
        genuinely matters is that Arabic and Sorani TEXT flows right-to-left —
        and that is handled per-widget by apply_text_direction(), which Qt does
        correctly for QLabel, QTextEdit and QLineEdit.

        Pass apply_direction=True only if you have first made every custom
        paintEvent mirror-aware.
        """
        if code not in LANG_CODES:
            print(f"[i18n] Unknown language '{code}'")
            return False

        self._lang = code
        self._catalog = self._read(code) if code != DEFAULT_LANG else dict(self._fallback)

        if apply_direction:
            app = QApplication.instance()
            if app is not None:
                app.setLayoutDirection(
                    Qt.LayoutDirection.RightToLeft if self.is_rtl()
                    else Qt.LayoutDirection.LeftToRight
                )

        self._refresh_bindings()
        self.changed.emit(code)
        print(f"[i18n] Language -> {code} ({self.direction()})")
        return True

    # ── widget binding ──────────────────────────────────────────────────────

    def bind(self, widget, key: str, setter: str = "setText"):
        """
        Set a widget's text from the catalogue and keep it updated on change.

        Returns the widget so it can be used inline:
            lay.addWidget(i18n.bind(QLabel(), "monitor.title"))
        """
        try:
            getattr(widget, setter)(self.t(key))
        except Exception as e:
            print(f"[i18n] bind failed for {key}: {e}")
            return widget
        self._bindings.append((weakref.ref(widget), setter, key))
        return widget

    def bind_tooltip(self, widget, key: str):
        return self.bind(widget, key, setter="setToolTip")

    def bind_placeholder(self, widget, key: str):
        return self.bind(widget, key, setter="setPlaceholderText")

    def _refresh_bindings(self) -> None:
        """Re-apply every binding, dropping any whose widget has been destroyed."""
        alive: list[tuple[weakref.ref, str, str]] = []
        for ref, setter, key in self._bindings:
            widget = ref()
            if widget is None:
                continue
            try:
                getattr(widget, setter)(self.t(key))
                alive.append((ref, setter, key))
            except RuntimeError:
                # Underlying C++ object already deleted — drop the binding.
                continue
            except Exception as e:
                print(f"[i18n] refresh failed for {key}: {e}")
                alive.append((ref, setter, key))
        self._bindings = alive

    # ── per-widget text direction ───────────────────────────────────────────

    def apply_text_direction(self, *widgets) -> None:
        """
        Make TEXT read right-to-left in the given widgets, without mirroring the
        window frame.

        This is the correct granularity for a HUD: Arabic and Sorani paragraphs
        flow and align correctly, while the panel positions, the arc reactor and
        the meter bars stay exactly where they were designed to be.

        Safe to call on any widget — unsupported ones are skipped rather than
        raising, so adding a new widget type never breaks language switching.
        """
        rtl = self.is_rtl()
        direction = (Qt.LayoutDirection.RightToLeft if rtl
                     else Qt.LayoutDirection.LeftToRight)
        align = (Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)

        for w in widgets:
            if w is None:
                continue
            try:
                w.setLayoutDirection(direction)
            except Exception:
                pass
            # QTextEdit/QPlainTextEdit hold their direction in the document's
            # default text option, not on the widget.
            try:
                doc = w.document()
                opt = doc.defaultTextOption()
                opt.setTextDirection(direction)
                opt.setAlignment(align | Qt.AlignmentFlag.AlignAbsolute)
                doc.setDefaultTextOption(opt)
            except Exception:
                pass
            try:
                w.setAlignment(align)
            except Exception:
                pass

    def text_alignment(self):
        """AlignRight for RTL languages, AlignLeft otherwise — for custom painting."""
        return (Qt.AlignmentFlag.AlignRight if self.is_rtl()
                else Qt.AlignmentFlag.AlignLeft)

    # ── persistence ─────────────────────────────────────────────────────────

    def load_saved(self, config: dict | None = None) -> str:
        """Apply the language stored in config, defaulting to English."""
        code = DEFAULT_LANG
        if config:
            code = (config.get("ui_language") or DEFAULT_LANG).strip()
        if code not in LANG_CODES:
            code = DEFAULT_LANG
        self.set_language(code)
        return code


# Module-level singleton — import and use directly.
I18N = _I18N()

t = I18N.t
bind = I18N.bind
bind_tooltip = I18N.bind_tooltip
bind_placeholder = I18N.bind_placeholder
set_language = I18N.set_language
is_rtl = I18N.is_rtl
apply_text_direction = I18N.apply_text_direction
text_alignment = I18N.text_alignment


if __name__ == "__main__":
    import io
    import sys
    # The Windows console defaults to cp1252, which cannot encode Arabic or
    # Kurdish script and raises UnicodeEncodeError on print(). Force UTF-8.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    app = QApplication(sys.argv)
    for code, endonym, name, direction in LANGUAGES:
        I18N.set_language(code)
        print(f"\n{code}  {endonym}  ({name}, {direction})")
        for k in ("monitor.title", "state.listening", "drawer.remote", "upload.hint"):
            print(f"   {k:<20} {I18N.t(k)}")
