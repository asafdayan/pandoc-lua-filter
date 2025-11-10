# Obsidian Markdown to LaTeX with pandoc

Use the Shell Commands plugin for Obsidian for ease of use. The `mdtex.sh`
script orchestrates the full pipeline:

1. **Sanitize Markdown** – `sanitize_markdown.py` normalises headings and math
   environments so Pandoc parses them reliably.
2. **Export tldraw canvases** – `export_tldraw.py` looks for `![[...tldr]]`
   embeds, calls the official `@tldraw/tldraw` JavaScript `convert()` helper via
   `tldraw_convert.mjs` to render PNGs, and rewrites the embed into a regular
   Markdown image so Pandoc emits `\includegraphics`. If the conversion helper
   is unavailable it falls back to the preview that Obsidian stores inside the
   `.tldr` file.
3. **Pandoc conversion** – `final_filter.lua` customises callouts while Pandoc
   renders the document to LaTeX.
4. **Restore the note** – `restore_math_blocks.py` restores both math fences and
   the original `![[...]]` embeds so the Markdown remains Obsidian-friendly.

## Working with tldraw drawings

- Keep your drawings as `.tldr` files and embed them in notes using
  `![[drawing.tldr]]`. The exporter saves the rendered PNG next to the drawing
  (for example `drawing.png`) so repeated conversions only regenerate the image
  when the `.tldr` file changes.
- Install the JavaScript dependency once with `npm install @tldraw/tldraw` so
  the Node helper can call `convert()`. If `node` or the package is missing the
  exporter falls back to the embedded preview that Obsidian writes into the
  `.tldr` file.
- If your drawings live outside the note’s folder, pass additional lookup
  directories to `export_tldraw.py` via `--search-dir <path>` in `mdtex.sh`, or
  populate the `TLDRAW_SEARCH_DIRS` environment variable with a
  colon-separated list of folders.