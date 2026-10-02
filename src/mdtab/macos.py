"""macOS integration: launchd agent, MDTab.app droplet, default-app registration."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LABEL = "com.tdual.mdtab"
BUNDLE_ID = "com.tdual.mdtab"
UTI = "net.daringfireball.markdown"
HOME = Path.home()
PLIST = HOME / "Library/LaunchAgents" / f"{LABEL}.plist"
APP = HOME / "Applications/MDTab.app"
LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")


def _domain() -> str:
    return f"gui/{os.getuid()}"


def install_agent() -> None:
    """launchd keeps `python -m mdtab serve` running; uses the interpreter mdtab was installed with."""
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    (HOME / "Library/Logs").mkdir(parents=True, exist_ok=True)
    log = HOME / "Library/Logs/mdtab.log"
    PLIST.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string><string>-m</string><string>mdtab</string><string>serve</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
""")
    subprocess.run(["launchctl", "bootout", f"{_domain()}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", _domain(), str(PLIST)], check=True)
    print(f"launchd: {LABEL} loaded ({sys.executable} -m mdtab serve)")


def install_app() -> None:
    """Compile a tiny AppleScript droplet that forwards dropped files to `mdtab open`."""
    APP.parent.mkdir(parents=True, exist_ok=True)
    py = sys.executable.replace('"', '\\"')
    script = f'''on open theFiles
	repeat with f in theFiles
		do shell script quoted form of "{py}" & " -m mdtab open " & quoted form of POSIX path of f
	end repeat
end open
on run
	do shell script quoted form of "{py}" & " -m mdtab open"
end run
'''
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "MDTab.applescript"
        src.write_text(script)
        shutil.rmtree(APP, ignore_errors=True)
        subprocess.run(["osacompile", "-o", str(APP), str(src)], check=True)
    pl = APP / "Contents/Info.plist"
    pb = "/usr/libexec/PlistBuddy"
    def set_or_add(key, typ, val):
        if subprocess.run([pb, "-c", f"Set :{key} {val}", str(pl)], capture_output=True).returncode:
            subprocess.run([pb, "-c", f"Add :{key} {typ} {val}", str(pl)], check=True)
    set_or_add("CFBundleIdentifier", "string", BUNDLE_ID)
    set_or_add("CFBundleName", "string", "MDTab")
    subprocess.run([pb, "-c", "Delete :CFBundleDocumentTypes", str(pl)], capture_output=True)
    for cmd in ["Add :CFBundleDocumentTypes array",
                "Add :CFBundleDocumentTypes:0 dict",
                "Add :CFBundleDocumentTypes:0:CFBundleTypeName string Markdown",
                "Add :CFBundleDocumentTypes:0:CFBundleTypeRole string Viewer",
                "Add :CFBundleDocumentTypes:0:LSHandlerRank string Owner",
                "Add :CFBundleDocumentTypes:0:LSItemContentTypes array",
                f"Add :CFBundleDocumentTypes:0:LSItemContentTypes:0 string {UTI}",
                "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions array",
                "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:0 string md",
                "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:1 string markdown"]:
        subprocess.run([pb, "-c", cmd, str(pl)], check=True)
    subprocess.run([LSREGISTER, "-f", str(APP)], check=True, capture_output=True)
    print(f"app: {APP} registered for {UTI}")


def set_default() -> None:
    """Make MDTab the default .md handler. macOS shows a confirmation dialog."""
    if shutil.which("utiluti"):
        subprocess.run(["utiluti", "type", "set", UTI, BUNDLE_ID], check=True)
    elif shutil.which("duti"):
        subprocess.run(["duti", "-s", BUNDLE_ID, UTI, "all"], check=True)
    else:
        print("no utiluti/duti found. In Finder: select a .md > Get Info > Open with > MDTab > Change All")
        return
    print("default .md app: MDTab (confirm the macOS dialog if it appeared)")


def install(set_default_app: bool = False, **kw) -> None:
    set_default_app = set_default_app or kw.get("set_default", False)
    install_agent()
    install_app()
    if set_default_app:
        set_default()
    else:
        print("tip: `mdtab install --default` makes MDTab the default app for .md files")


def uninstall() -> None:
    subprocess.run(["launchctl", "bootout", f"{_domain()}/{LABEL}"], capture_output=True)
    PLIST.unlink(missing_ok=True)
    shutil.rmtree(APP, ignore_errors=True)
    print("removed launchd agent and MDTab.app. If MDTab was your default .md app, pick another in Finder > Get Info.")
