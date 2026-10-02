#!/bin/bash
# Install mdtab on macOS:
#   1. launchd agent that keeps the local server running (127.0.0.1:7331)
#   2. MDTab.app, a tiny AppleScript droplet, registered as a Markdown viewer
#   3. (optional) make MDTab the default app for .md files
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.tdual.mdtab"; BUNDLE_ID="com.tdual.mdtab"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="$HOME/Applications/MDTab.app"
PY="$(command -v python3)"

# 1. launchd agent
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$ROOT/server.py</string></array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/mdtab.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/mdtab.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "server: launchd agent $LABEL loaded"

# 2. MDTab.app (AppleScript droplet -> bin/open-md.sh)
mkdir -p "$HOME/Applications"; TMP="$(mktemp -d)"
cat > "$TMP/MDTab.applescript" <<AS
on open theFiles
	repeat with f in theFiles
		do shell script quoted form of "$ROOT/bin/open-md.sh" & " " & quoted form of POSIX path of f
	end repeat
end open
on run
	do shell script quoted form of "$ROOT/bin/open-md.sh"
end run
AS
rm -rf "$APP"; osacompile -o "$APP" "$TMP/MDTab.applescript"
PL="$APP/Contents/Info.plist"; PB=/usr/libexec/PlistBuddy
$PB -c "Set :CFBundleIdentifier $BUNDLE_ID" "$PL" 2>/dev/null || $PB -c "Add :CFBundleIdentifier string $BUNDLE_ID" "$PL"
$PB -c "Set :CFBundleName MDTab" "$PL" 2>/dev/null || $PB -c "Add :CFBundleName string MDTab" "$PL"
$PB -c "Delete :CFBundleDocumentTypes" "$PL" 2>/dev/null || true
$PB -c "Add :CFBundleDocumentTypes array" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0 dict" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:CFBundleTypeName string Markdown" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:CFBundleTypeRole string Viewer" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:LSHandlerRank string Owner" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:LSItemContentTypes array" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:LSItemContentTypes:0 string net.daringfireball.markdown" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions array" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:0 string md" "$PL"
$PB -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:1 string markdown" "$PL"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"
echo "app: $APP registered"

# 3. default app for .md (optional; macOS shows a confirmation dialog)
if [ "${1:-}" = "--set-default" ]; then
  if command -v utiluti >/dev/null; then utiluti type set net.daringfireball.markdown "$BUNDLE_ID"
  elif command -v duti >/dev/null; then duti -s "$BUNDLE_ID" net.daringfireball.markdown all
  else echo "install utiluti (brew install utiluti) or set the default app from Finder: Get Info > Open with > Change All"; fi
else
  echo "to make MDTab the default .md app: ./install.sh --set-default  (or Finder > Get Info > Open with > Change All)"
fi
