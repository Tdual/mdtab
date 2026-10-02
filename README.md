# mdtab

Open a Markdown file from Finder and it appears in a browser tab: the folder tree on the left, the rendered document on the right. White background, no Electron, no accounts.

- Double-click a `.md` in Finder (after `./install.sh --set-default`) or run `bin/open-md.sh file.md`
- Left pane: the folder that contains the file. Expand subfolders, go up with `↑`, click any `.md`
- Live reload: the document re-renders when the file changes on disk
- Images and attachments resolve relative to the Markdown file; links to local `.md` files open inside mdtab
- Links open in a new tab (in-page anchors stay)
- "Reveal in Finder" button

## Requirements

- macOS (the Finder integration uses an AppleScript droplet and launchd)
- Python 3.9+ (stdlib only)
- [pandoc](https://pandoc.org/) for rendering (GitHub-flavored Markdown). Falls back to the `markdown` module if pandoc is missing.

```sh
brew install pandoc
```

## Install

```sh
git clone https://github.com/Tdual/mdtab.git
cd mdtab
./install.sh                 # launchd agent + ~/Applications/MDTab.app
./install.sh --set-default   # also make MDTab the default app for .md (macOS asks for confirmation)
```

Then open any Markdown file:

```sh
open README.md               # if MDTab is the default
bin/open-md.sh README.md     # otherwise
```

`./uninstall.sh` removes the agent and the app.

## How it works

| Piece | What it does |
|---|---|
| `server.py` | HTTP server on `127.0.0.1:7331`. Routes: `/view`, `/api/tree`, `/api/file`, `/api/raw`, `/api/mtime`, `/api/reveal` |
| `static/` | Single-page UI (`index.html`, `app.js`, `app.css`, `md-white.css`) |
| `bin/open-md.sh` | Starts the server if needed and opens the file's URL in the default browser |
| `install.sh` | Writes the launchd plist, compiles `MDTab.app` with `osacompile`, registers it for `net.daringfireball.markdown` |

Port can be changed with `MDTAB_PORT` (set it for both the server and `open-md.sh`).

## Security notes

- Binds to `127.0.0.1` only.
- Serves only paths under `$HOME`; anything else returns `bad file`.
- Raw HTML in Markdown is rendered (so `<img width=...>` works). This is a viewer for your own local files; do not expose it to a network.

## Test

`test/index.md` exercises image embedding, links and nested folders with spaces in their names:

```sh
bin/open-md.sh test/index.md
```

## License

MIT
