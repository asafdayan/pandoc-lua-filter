markdown# 🧠 AGENT.md — Markdown to Overleaf (Obsidian Plugin)

## 🎯 Goal

Create an **Obsidian plugin** called **Markdown to Overleaf** that:
1. Converts the currently active Markdown note into LaTeX using **Pandoc** and your **asafdayan/pandoc-lua-filter** setup.
2. Processes embedded images and drawings:
   - `![[file.png]]` → copy to assets folder.
   - `![[drawing.md]]` containing ```tldraw``` → extract JSON → convert to PNG via `tldraw-cli`.
3. Packages the resulting `.tex` file and its assets into a `.zip`.
4. Uploads the `.zip` file to a temporary host (default: [transfer.sh](https://transfer.sh)).
5. Opens the resulting Overleaf import link automatically:
```

[https://www.overleaf.com/docs?snip_uri=](https://www.overleaf.com/docs?snip_uri=)<uploaded_zip_url>

```
yaml
---

## 🧱 Plugin Structure
```

.obsidian/plugins/md2overleaf/
├─ manifest.json
├─ package.json
├─ main.ts
├─ styles.css (optional)
└─ README.md

```
yaml
---

## ⚙️ Plugin Features

### ✅ Command

- Register a command in the Obsidian Command Palette:
  **“Export to Overleaf”**
  
When triggered:
1. Saves the current note.
2. Runs Pandoc conversion using your Lua filters, template, and metadata.
3. Processes and converts embedded files.
4. Zips everything.
5. Uploads the ZIP.
6. Opens it automatically in Overleaf.

Use `Notice()` to show progress messages such as:
- “Running Pandoc conversion…”
- “Processing embedded files…”
- “Uploading project…”
- “Opening in Overleaf…”

---

## ⚙️ Settings Panel

Create a settings tab under “Markdown to Overleaf” with these persistent options:

| Setting | Type | Description | Default |
|----------|------|-------------|----------|
| **Pandoc Path** | text | Path to the Pandoc executable | `pandoc` |
| **Filter Directory** | text | Path to the `filters/` folder in your Lua filter repo | `${vault}/pandoc-lua-filter/filters` |
| **Template Path** | text | Path to your Pandoc LaTeX template | `${vault}/pandoc-lua-filter/template.tex` |
| **Metadata Path** | text | Path to your Pandoc metadata YAML | `${vault}/pandoc-lua-filter/metadata.yaml` |
| **Upload Host** | text | URL to upload ZIPs (transfer.sh by default) | `https://transfer.sh` |
| **Use tldraw-cli** | toggle | Convert embedded tldraw drawings to PNG | `true` |
| **Auto-open Overleaf** | toggle | Open Overleaf automatically after upload | `true` |

Settings must persist between Obsidian restarts via `this.plugin.settings`.

---

## 🧩 Correct Conversion Step (matches your repo)

### Step 1 — Pandoc Conversion

Run the following Pandoc command:

```bash
<pandoc_path> "<note_path>" \\
  --from markdown \\
  --to latex \\
  --template "<template_path>" \\
  --metadata-file "<metadata_path>" \\
  --lua-filter "<filter_dir>/main.lua" \\
  --output "<out_dir>/<basename>.tex"
```

All paths are taken from the plugin settings (with the defaults above).

The plugin must create <out_dir> automatically (e.g., in .md2overleaf/<basename>/).

Show a progress notice before and after conversion.

🖼️ Step 2 — Asset Handling
After the .tex file is generated:

Scan for all Markdown embeds in the format:

```
lua![[relative/path/to/file]]
```

For each:

If it’s an image (.png, .jpg, .jpeg), copy it into <out_dir>/assets/.

If it’s a .md file containing a tldraw block:

Extract the JSON inside the code block.

Save it as a .tldr file.

Run:

```bash
bashnpx tldraw export "<tldr_path>" --format png --output "<out_dir>/assets/<name>.png" --overwrite
```

Replace the embed in the LaTeX file with:

```latex
latex\\includegraphics[width=\\linewidth]{assets/<name>.png}
```

Save the modified .tex file.

📦 Step 3 — Packaging

Create a .zip archive of <out_dir>/ using AdmZip.

Include the .tex file and all files from the assets folder.

Save the ZIP to <out_dir>/<basename>.zip.

☁️ Step 4 — Upload
Upload the ZIP using the configured host (default: transfer.sh):

```bash
bashcurl -s -F "file=@<zip_path>" <upload_host>/<basename>.zip
```

Extract the returned URL and build the Overleaf import link:

```
arduinohttps://www.overleaf.com/docs?snip_uri=<uploaded_zip_url>
```

🌿 Step 5 — Open in Overleaf
If Auto-open is enabled:

Open the Overleaf link in the default browser.

Otherwise:

Show a notice with the clickable link.

🧩 Technical Details
manifest.json

```json
json{
  "id": "md2overleaf",
  "name": "Markdown to Overleaf",
  "version": "0.2.0",
  "minAppVersion": "1.4.0",
  "author": "Asaf Dayan",
  "description": "Convert Markdown to LaTeX using Pandoc + Lua filters and open in Overleaf",
  "authorUrl": "https://github.com/asafdayan",
  "isDesktopOnly": true
}
```

package.json

```json
json{
  "name": "md2overleaf",
  "version": "0.2.0",
  "description": "Obsidian plugin to export Markdown → Overleaf using Pandoc and Lua filters",
  "main": "main.js",
  "scripts": {
    "build": "esbuild main.ts --bundle --outfile=main.js --platform=node"
  },
  "dependencies": {
    "fs-extra": "^11.2.0",
    "adm-zip": "^0.5.10",
    "openurl": "^1.1.1"
  },
  "devDependencies": {
    "esbuild": "^0.19.0",
    "@types/node": "^20.0.0"
  }
}
```

🧩 main.ts Requirements
Implement the following classes and functions:
exportToOverleaf()

Save current note.

Run Pandoc command (with user-configured paths).

Handle embeds and tldraw exports.

Create ZIP (AdmZip).

Upload ZIP via curl.

Generate Overleaf URL.

If auto-open enabled → require("openurl").open(overleafUrl).

Use Notice() to report progress.

Md2OverleafSettingTab

Render the settings table.

Bind inputs for all configuration fields listed above.

Persist settings to disk with this.plugin.saveData() and this.plugin.loadData().

🚀 Build Instructions

Run:

```bash
bashnpm install
npm run build
```

Copy the plugin folder into:

```
perl<vault>/.obsidian/plugins/md2overleaf/
```

Reload Obsidian.

Enable Markdown to Overleaf in Community Plugins.

Run command: Export to Overleaf from the Command Palette.

✅ Acceptance Criteria

The “Export to Overleaf” command appears in Obsidian.

When executed:

Runs your Pandoc-Lua conversion pipeline.

Correctly processes embedded images and tldraw drawings.

Creates and uploads a ZIP.

Opens Overleaf automatically (if enabled).

The settings tab works, and all paths can be configured.

The plugin functions entirely offline except for the upload step.

End of AGENT.md
