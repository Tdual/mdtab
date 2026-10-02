#!/usr/bin/env python3
"""mdtab: local Markdown viewer. Listens on 127.0.0.1:7331 and serves only files under $HOME.
Dependencies: Python stdlib, pandoc (preferred) or the `markdown` module (fallback)."""
from __future__ import annotations
import html, json, mimetypes, os, re, subprocess, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"
HOME = Path.home().resolve()
PORT = int(os.environ.get("MD_VIEWER_PORT", "7331"))
MD_EXT = {".md", ".markdown", ".mdown"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".DS_Store", ".obsidian", "cdk.out"}

def safe(p: str) -> Path | None:
    """Return the path only if it resolves to somewhere under $HOME."""
    try:
        q = Path(p).expanduser().resolve()
    except Exception:
        return None
    return q if q == HOME or HOME in q.parents else None

PANDOC = next((c for c in ("/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc") if os.path.exists(c)), None)

def rewrite_links(body: str, base_dir: Path) -> str:
    """Resolve relative image/link targets against the Markdown file's directory.
    Attachments -> /api/raw, local .md -> /view. http(s)/data/#anchor are left untouched."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|data:|mailto:|#|/api/|/view)", url):
            return m.group(0)
        raw_path = urllib.parse.unquote(url.split("#")[0])
        target = (base_dir / raw_path).resolve() if not raw_path.startswith("/") else Path(raw_path).resolve()
        if not safe(str(target)):
            return m.group(0)
        if attr == "href" and target.suffix.lower() in MD_EXT:
            return f'href="/view?path={urllib.parse.quote(str(target))}"'
        return f'{attr}="/api/raw?path={urllib.parse.quote(str(target))}"'
    body = re.sub(r'\b(src|href)="([^"]+)"', fix, body)
    # External URLs and attachments open in a new tab; local .md links (/view) and
    # in-page anchors navigate within the current tab.
    return re.sub(r'<a\s+(?![^>]*\btarget=)(?=[^>]*href="(?:https?:|mailto:|/api/raw))',
                  '<a target="_blank" rel="noopener" ', body)

def render(md_text: str) -> str:
    """Render with pandoc (GFM) when available. python-markdown requires 4-space indents for nested
    lists, which breaks the common 2-3 space style, so it is only a fallback."""
    if PANDOC:
        r = subprocess.run([PANDOC, "-f", "gfm+hard_line_breaks", "-t", "html5", "--no-highlight"],
                           input=md_text, capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            return r.stdout
    try:
        import markdown  # optional: pip install mdtab[markdown]
    except ImportError:
        return ("<p><b>No renderer available.</b> Install pandoc (<code>brew install pandoc</code>) "
                "or <code>pip install mdtab[markdown]</code>.</p><pre>" + html.escape(md_text) + "</pre>")
    return markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
                             extension_configs={"toc": {"permalink": False}})

class H(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):  # keep stdout quiet
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _file(self, path: Path, ctype: str):
        b = path.read_bytes()
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path); q = urllib.parse.parse_qs(u.query)
        p = q.get("path", [""])[0]
        if u.path in ("/", "/view"):
            return self._file(STATIC / "index.html", "text/html; charset=utf-8")
        if u.path == "/healthz":
            return self._json({"ok": True})
        if u.path.startswith("/static/"):
            f = (STATIC / u.path[len("/static/"):]).resolve()
            if STATIC in f.parents and f.is_file():
                ct = {"css": "text/css", "js": "application/javascript", "html": "text/html"}.get(f.suffix[1:], "application/octet-stream")
                return self._file(f, ct + "; charset=utf-8")
            return self._json({"error": "not found"}, 404)
        if u.path == "/api/tree":
            d = safe(p)
            if not d or not d.is_dir(): return self._json({"error": "bad dir"}, 400)
            items = []
            for c in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if c.name in SKIP_DIRS or c.name.startswith("."): continue
                items.append({"name": c.name, "path": str(c), "dir": c.is_dir(), "md": c.suffix.lower() in MD_EXT})
            parent = str(d.parent) if d != HOME and HOME in d.parents else None
            display = "~" + str(d)[len(str(HOME)):] if d == HOME or HOME in d.parents else str(d)
            return self._json({"dir": str(d), "display": display, "parent": parent, "items": items})
        if u.path == "/api/file":
            f = safe(p)
            if not f or not f.is_file(): return self._json({"error": "bad file"}, 400)
            text = f.read_text(encoding="utf-8", errors="replace")
            body = rewrite_links(render(text), f.parent) if f.suffix.lower() in MD_EXT else f"<pre>{html.escape(text)}</pre>"
            return self._json({"path": str(f), "name": f.name, "dir": str(f.parent), "mtime": f.stat().st_mtime, "html": body})
        if u.path == "/api/raw":
            f = safe(p)
            if not f or not f.is_file(): return self._json({"error": "bad file"}, 400)
            ct = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
            return self._file(f, ct)
        if u.path == "/api/mtime":
            f = safe(p)
            return self._json({"mtime": f.stat().st_mtime if f and f.is_file() else None})
        if u.path == "/api/reveal":
            f = safe(p)
            if f and f.exists(): subprocess.Popen(["open", "-R", str(f)])
            return self._json({"ok": bool(f)})
        return self._json({"error": "not found"}, 404)

def serve(port: int = PORT) -> None:
    """Run the viewer in the foreground (launchd calls this via `python -m mdtab serve`)."""
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    serve()
