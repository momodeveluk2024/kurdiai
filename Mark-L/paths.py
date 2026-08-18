"""
Path resolution that works both from source and from a PyInstaller build.

WHY THIS EXISTS
───────────────
Every module in this project currently resolves paths with one rule:

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

That single rule is wrong for a frozen build, because there are TWO different
roots and they are not the same directory:

  1. BUNDLED RESOURCES (read-only) — core/prompt.txt, dashboard/static/*.html,
     config/jarvis.ico. PyInstaller unpacks these into sys._MEIPASS, which is
     `<app>/_internal` for a onedir build and a temp folder for onefile. They are
     NOT next to the executable.

  2. USER DATA (read-write) — config/api_keys.json, config/certs/,
     memory/long_term.json. These must live next to the executable so they
     persist across launches and survive updates. Writing them into _MEIPASS
     would silently discard them on every run of a onefile build.

Using one root for both means either the app cannot find its own prompt file, or
it forgets the user every launch. Use resource_path() for things you read that
ship with the app, and data_path() for anything you write.
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running from a PyInstaller build rather than source."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def app_root() -> Path:
    """
    Root for WRITABLE user data — config/, memory/, logs.

    Frozen: the folder containing the .exe.
    Source: the project folder containing main.py.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    """
    Root for READ-ONLY bundled assets — prompt.txt, dashboard/static, icons.

    Frozen: PyInstaller's extraction directory (sys._MEIPASS).
    Source: identical to app_root().
    """
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return app_root()


def resource_path(*parts: str) -> Path:
    """Path to a bundled read-only asset, e.g. resource_path('core', 'prompt.txt')."""
    return resource_root().joinpath(*parts)


def data_path(*parts: str) -> Path:
    """
    Path to writable user data, e.g. data_path('config', 'api_keys.json').
    Creates the parent directory so callers can write immediately.
    """
    p = app_root().joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def resolve_readable(*parts: str) -> Path:
    """
    For assets that ship with the app but that a user may also override locally.

    Prefers a user copy next to the executable, falls back to the bundled one.
    Use this for core/prompt.txt so someone can customise the persona without
    rebuilding, while a fresh install still finds the shipped default.
    """
    user_copy = app_root().joinpath(*parts)
    if user_copy.exists():
        return user_copy
    return resource_path(*parts)


if __name__ == "__main__":
    print(f"frozen        : {is_frozen()}")
    print(f"app_root      : {app_root()}")
    print(f"resource_root : {resource_root()}")
    print(f"config        : {app_root() / 'config' / 'api_keys.json'}")
    print(f"prompt        : {resolve_readable('core', 'prompt.txt')}")
