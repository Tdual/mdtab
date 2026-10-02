#!/bin/bash
# Open a Markdown file in mdtab. Starts the server (via launchd, or directly) if it is not running.
set -u
PORT="${MDTAB_PORT:-7331}"; F="${1:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if ! curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null; then
  launchctl kickstart -k "gui/$(id -u)/com.tdual.mdtab" 2>/dev/null || \
    (nohup /usr/bin/python3 "$ROOT/server.py" >/dev/null 2>&1 &)
  for _ in $(seq 1 20); do curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null && break; sleep 0.25; done
fi
if [ -n "$F" ]; then
  ABS="$(cd "$(dirname "$F")" && pwd)/$(basename "$F")"
  Q=$(/usr/bin/python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$ABS")
  open "http://127.0.0.1:$PORT/view?path=$Q"
else
  open "http://127.0.0.1:$PORT/"
fi
