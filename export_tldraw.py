#!/usr/bin/env python3
"""Export embedded tldraw canvases to PNG and rewrite Obsidian embeds.

This script looks for Obsidian-style embeds of tldraw drawings inside a
Markdown note (patterns like ``![[canvas.tldr]]``). For every drawing it finds,
it extracts an embedded PNG preview from the ``.tldr`` file, writes it next to
the source drawing (``canvas.png`` by default) and rewrites the embed into a
regular Markdown image so Pandoc can emit ``\includegraphics`` in the LaTeX
output.

To make the transformation reversible, the original embed target is stored in a
``data-tldraw-embed`` attribute. ``restore_math_blocks.py`` knows how to read
this attribute and restore the ``![[...]]`` notation once the conversion
finishes.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

EMBED_PATTERN = re.compile(r"!\[\[([^\]]+)\]\]")
DATA_URL_PREFIX = "data:image/png;base64,"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export tldraw embeds inside an Obsidian Markdown note."
    )
    parser.add_argument(
        "markdown_file",
        help="Path to the Markdown note that may contain ![[...tldr]] embeds.",
    )
    parser.add_argument(
        "--search-dir",
        action="append",
        dest="search_dirs",
        default=None,
        help=(
            "Additional directory to search for .tldr files. Can be repeated. "
            "If omitted, only paths relative to the note and the current "
            "working directory are inspected."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-export PNG files even if they already exist.",
    )
    return parser.parse_args()


@dataclass
class Embed:
    original: str  # the inner part of ![[...]] including alias if present
    file_reference: str  # original file reference before alias / block fragment
    alias: Optional[str]
    match_span: Tuple[int, int]


def iter_tldraw_embeds(text: str) -> Iterator[Embed]:
    for match in EMBED_PATTERN.finditer(text):
        inner = match.group(1).strip()
        file_reference, alias = split_reference(inner)
        if not file_reference:
            continue
        # Keep the original extension (if present) so we can match .tldr files.
        if not file_reference.lower().endswith(".tldr"):
            candidate = f"{file_reference}.tldr"
        else:
            candidate = file_reference
        if candidate.lower().endswith(".tldr"):
            yield Embed(inner, candidate, alias, match.span())


def split_reference(reference: str) -> Tuple[str, Optional[str]]:
    """Split an Obsidian link target into the path and the alias.

    ``reference`` is the inner content of ``![[...]]``. It may contain an alias
    separated by ``|`` and block / heading references separated by ``#``. To
    locate the actual file we only care about the portion before ``#``.
    """

    alias: Optional[str] = None
    path_part = reference
    if "|" in reference:
        path_part, alias = reference.split("|", 1)
        path_part = path_part.strip()
        alias = alias.strip()
    # Remove block references such as #^block-id or #Heading.
    if "#" in path_part:
        path_part = path_part.split("#", 1)[0].strip()
    return path_part, alias


CONVERTER_SCRIPT = Path(__file__).with_name("tldraw_convert.mjs")


class TLDrawExporter:
    def __init__(self, note_path: Path, search_dirs: Optional[Iterable[Path]], force: bool = False):
        self.note_path = note_path
        self.note_dir = note_path.parent
        self.force = force
        dirs = [self.note_dir]
        if search_dirs:
            for directory in search_dirs:
                if directory not in dirs:
                    dirs.append(directory)
        # Always include the current working directory as the last resort.
        cwd = Path.cwd()
        if cwd not in dirs:
            dirs.append(cwd)
        self.search_dirs = dirs
        self.cache: Dict[str, Path] = {}
        self.node_executable = shutil.which("node")

    def resolve_tldr(self, file_reference: str) -> Path:
        cached = self.cache.get(file_reference)
        if cached:
            return cached
        relative_path = Path(file_reference)
        if relative_path.is_absolute():
            if not relative_path.exists():
                raise FileNotFoundError(f"Could not locate {file_reference}")
            self.cache[file_reference] = relative_path
            return relative_path
        for directory in self.search_dirs:
            candidate = directory / relative_path
            if candidate.exists():
                self.cache[file_reference] = candidate
                return candidate
        # If the user referenced the file without the .tldr extension, try to append it.
        if not file_reference.lower().endswith(".tldr"):
            return self.resolve_tldr(f"{file_reference}.tldr")
        raise FileNotFoundError(
            f"Unable to find '{file_reference}' relative to {self.note_dir} or the configured search directories"
        )

    def export_png(self, tldr_path: Path) -> Path:
        png_path = tldr_path.with_suffix(".png")
        needs_refresh = self.force or not png_path.exists() or tldr_path.stat().st_mtime > png_path.stat().st_mtime
        if not needs_refresh:
            return png_path
        if self.node_executable and CONVERTER_SCRIPT.exists():
            try:
                self._export_with_node(tldr_path, png_path)
                return png_path
            except Exception as exc:
                print(
                    f"Warning: Node-based export failed for '{tldr_path}': {exc}. Falling back to embedded preview.",
                    file=sys.stderr,
                )
        self._export_from_embedded_preview(tldr_path, png_path)
        return png_path

    def _export_with_node(self, tldr_path: Path, png_path: Path) -> None:
        command = [self.node_executable, str(CONVERTER_SCRIPT), str(tldr_path), str(png_path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            details = stderr or stdout or "Unknown error"
            raise RuntimeError(details)
        if not png_path.exists():
            raise RuntimeError("tldraw_convert.mjs finished but did not create an output file")

    def _export_from_embedded_preview(self, tldr_path: Path, png_path: Path) -> None:
        with tldr_path.open("r", encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{tldr_path} is not valid JSON") from exc
        png_data_url = next(iter(find_data_urls(data, prefixes=(DATA_URL_PREFIX,))), None)
        if not png_data_url:
            raise RuntimeError(
                f"No embedded PNG data found in {tldr_path}. Either install @tldraw/tldraw and rerun, "
                "or open the drawing in Obsidian once and export it manually to seed a preview."
            )
        header, b64_payload = png_data_url.split(",", 1)
        if not header.startswith("data:image/png"):
            raise RuntimeError(f"Unsupported data URL format in {tldr_path}: {header}")
        png_bytes = base64.b64decode(b64_payload)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        with png_path.open("wb") as output:
            output.write(png_bytes)

    def build_markdown_image(self, embed: Embed, png_path: Path) -> str:
        alt_text = embed.alias or Path(embed.file_reference).stem
        safe_alt = alt_text.replace("\"", "'")
        relative_png = os.path.relpath(png_path, start=self.note_dir)
        relative_png = Path(relative_png).as_posix()
        encoded_embed = base64.urlsafe_b64encode(embed.original.encode("utf-8")).decode("ascii")
        return f"![{safe_alt}]({relative_png}){{data-tldraw-embed=\"{encoded_embed}\"}}"


def find_data_urls(obj: object, prefixes: Tuple[str, ...]) -> Iterator[str]:
    if isinstance(obj, str):
        if any(obj.startswith(prefix) for prefix in prefixes):
            yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from find_data_urls(value, prefixes)
    elif isinstance(obj, list):
        for value in obj:
            yield from find_data_urls(value, prefixes)


def main() -> None:
    args = parse_args()
    note_path = Path(args.markdown_file).expanduser().resolve()
    if not note_path.exists():
        print(f"Error: {note_path} does not exist.", file=sys.stderr)
        sys.exit(1)
    search_dirs_list = []
    env_dirs = os.environ.get("TLDRAW_SEARCH_DIRS")
    if env_dirs:
        for raw in env_dirs.split(os.pathsep):
            raw = raw.strip()
            if not raw:
                continue
            search_dirs_list.append(Path(raw).expanduser().resolve())
    if args.search_dirs:
        for raw in args.search_dirs:
            search_dirs_list.append(Path(raw).expanduser().resolve())
    search_dirs: Optional[Iterable[Path]] = search_dirs_list or None
    exporter = TLDrawExporter(note_path, search_dirs, force=args.force)
    original_text = note_path.read_text(encoding="utf-8")
    embeds = list(iter_tldraw_embeds(original_text))
    if not embeds:
        return
    new_chunks = []
    cursor = 0
    for embed in embeds:
        start, end = embed.match_span
        new_chunks.append(original_text[cursor:start])
        cursor = end
        try:
            tldr_path = exporter.resolve_tldr(embed.file_reference)
        except FileNotFoundError as exc:
            print(f"Warning: {exc}. Leaving embed unchanged.", file=sys.stderr)
            new_chunks.append(original_text[start:end])
            continue
        try:
            png_path = exporter.export_png(tldr_path)
        except Exception as exc:
            print(f"Warning: Failed to export '{embed.file_reference}': {exc}", file=sys.stderr)
            new_chunks.append(original_text[start:end])
            continue
        replacement = exporter.build_markdown_image(embed, png_path)
        new_chunks.append(replacement)
    new_chunks.append(original_text[cursor:])
    updated_text = "".join(new_chunks)
    if updated_text != original_text:
        note_path.write_text(updated_text, encoding="utf-8")


if __name__ == "__main__":
    main()
