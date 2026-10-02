"""Command line entry point: serve / open / install / uninstall."""
import argparse
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from . import __version__
from .server import PORT, serve

LABEL = "com.tdual.mdtab"


def _alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.5) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_server(port: int) -> None:
    """Start the server if it is not answering: via launchd when installed, otherwise detached."""
    if _alive(port):
        return
    if sys.platform == "darwin":
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{LABEL}"],
                       capture_output=True)
    if not _alive(port):
        subprocess.Popen([sys.executable, "-m", "mdtab", "serve", "--port", str(port)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(40):
        if _alive(port):
            return
        time.sleep(0.25)
    sys.exit("mdtab: server did not start")


def cmd_open(args) -> None:
    ensure_server(args.port)
    url = f"http://127.0.0.1:{args.port}/"
    if args.file:
        path = Path(args.file).expanduser().resolve()
        url += "view?path=" + urllib.parse.quote(str(path))
    webbrowser.open(url)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="mdtab", description=__doc__)
    ap.add_argument("--version", action="version", version=f"mdtab {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the viewer server in the foreground")
    s.add_argument("--port", type=int, default=PORT)
    s.set_defaults(fn=lambda a: serve(a.port))

    o = sub.add_parser("open", help="open a Markdown file in the browser (starts the server if needed)")
    o.add_argument("file", nargs="?")
    o.add_argument("--port", type=int, default=PORT)
    o.set_defaults(fn=cmd_open)

    i = sub.add_parser("install", help="macOS: launchd agent + MDTab.app; --default makes it the .md handler")
    i.add_argument("--default", action="store_true")
    i.set_defaults(fn=lambda a: _macos().install(set_default=a.default))

    u = sub.add_parser("uninstall", help="macOS: remove the launchd agent and MDTab.app")
    u.set_defaults(fn=lambda a: _macos().uninstall())

    args = ap.parse_args(argv)
    args.fn(args)


def _macos():
    if sys.platform != "darwin":
        sys.exit("mdtab install/uninstall is macOS only (serve/open work everywhere)")
    from . import macos
    return macos
