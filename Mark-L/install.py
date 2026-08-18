"""
Dependency installer for MARK L.  Run it explicitly:

    python install.py

Formerly named setup.py, which was dangerous: setuptools treats that name as a build
script, so `pip install .` — or any accidental import — executed a live `pip install`
at module import time and raised on failure. Everything now sits behind __main__.
"""
import subprocess
import sys
import platform
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    print("Installing requirements...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(HERE / "requirements.txt")]
    )
    if r.returncode != 0:
        print("\n❌ Dependency install failed. Fix the errors above and re-run.")
        return r.returncode

    print("Installing Playwright browsers...")
    r = subprocess.run([sys.executable, "-m", "playwright", "install"])
    if r.returncode != 0:
        print(
            "\n⚠️  Playwright browsers did not install. Browser automation "
            "(browser_control) will not work until you run:\n"
            f'    "{sys.executable}" -m playwright install\n'
        )

    if platform.system() == "Windows":
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            postinstall = Path(sys.executable).parent / "Scripts" / "pywin32_postinstall.py"
            print(
                "\n⚠️  pywin32 did not install correctly — desktop shortcut creation "
                "will fall back to a slower method that may not work on this machine.\n"
                "    Try fixing it manually with:\n"
                f'    "{sys.executable}" -m pip install --force-reinstall pywin32\n'
                f'    "{sys.executable}" "{postinstall}" -install\n'
            )

    print("\n✅ Setup complete! Run 'python main.py' to start MARK L.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

