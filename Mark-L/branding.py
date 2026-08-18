"""
Single source of truth for the app's identity, version, authorship and links.

Everything else reads from here — the About panel, the Windows .exe version resource,
the update checker, the phone dashboard footer and the console banner. Bump VERSION
in this file and nowhere else.

Keep this module dependency-free (stdlib only). It is imported very early, by the
PyInstaller spec at build time, and by tooling that runs outside the app.
"""
from __future__ import annotations

# ── Version ─────────────────────────────────────────────────────────────────
# Semantic versioning: MAJOR.MINOR.PATCH
#   MAJOR — breaking change to config or user data
#   MINOR — new capability
#   PATCH — fixes only
# The update checker compares this against the newest version published on GitHub.
VERSION = "1.0.0"
VERSION_TUPLE = tuple(int(p) for p in VERSION.split("."))

# ── Identity ────────────────────────────────────────────────────────────────
APP_NAME = "KurdAI"
APP_TITLE = "KURD AI"
APP_TAGLINE = "Kurdish Artificial Intelligence Assistant"

# Default name the assistant answers to. The user can override it in
# Customise Assistant; this is only the out-of-the-box value.
DEFAULT_ASSISTANT_NAME = "Kurd AI"

AUTHOR = "Ahmed Mohammad Noori"
COPYRIGHT_YEAR = "2026"
COPYRIGHT = f"Copyright © {COPYRIGHT_YEAR} {AUTHOR}. All rights reserved."

# ── Links ───────────────────────────────────────────────────────────────────
LINKEDIN = "https://www.linkedin.com/in/ahmed-mohammad-nuri-544b09408/"
TIKTOK = "https://www.tiktok.com/@iraqlance"
YOUTUBE = "https://www.youtube.com/@dsgames8409"

# Ordered for display in the About panel. The label is a catalogue key, not a
# literal, because full Arabic / Sorani / Kurmanji translation is coming and the
# About panel must localize with everything else.
SOCIAL_LINKS: tuple[tuple[str, str, str], ...] = (
    # (i18n key,          display label,  url)
    ("about.linkedin", "LinkedIn", LINKEDIN),
    ("about.tiktok", "TikTok", TIKTOK),
    ("about.youtube", "YouTube", YOUTUBE),
)

# ── Update source ───────────────────────────────────────────────────────────
# Where the update checker looks for new releases.
GITHUB_OWNER = "FatihMakes"
GITHUB_REPO = "Mark-L"
GITHUB_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"


def version_banner() -> str:
    """One-line banner for console output and logs."""
    return f"{APP_TITLE} v{VERSION} — {COPYRIGHT}"


def about_text() -> str:
    """Plain-text credits block, used by the About panel and the dashboard footer."""
    lines = [
        f"{APP_TITLE}  v{VERSION}",
        APP_TAGLINE,
        "",
        f"Created by {AUTHOR}",
        COPYRIGHT,
        "",
    ]
    lines.extend(f"{label}:  {url}" for _key, label, url in SOCIAL_LINKS)
    return "\n".join(lines)


if __name__ == "__main__":
    print(about_text())
