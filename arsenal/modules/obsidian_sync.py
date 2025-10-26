import os
from pathlib import Path
from typing import Iterable, List, Optional
from os.path import join
from mistletoe import Document
from .config import BASEPATH

from .common_sync import (
    sanitize_filename,
    write_text_file,
    extract_heading_code_blocks_mistletoe,
    detect_tags,
)

BASE_OUTPUT = join(BASEPATH, "my_cheats")

def find_markdown_files(vault_dir: Path) -> Iterable[Path]:
    return vault_dir.rglob("*.md")

def file_matches_tag(md_text: str, wanted_tag: str) -> bool:
    tags = detect_tags(md_text)
    # accept both 'arsenyc' and '#arsenyc' styles; detect_tags strips '#'
    return wanted_tag in tags

async def build_obsidian_file_for_tag(
    vault_dir: Path,
    wanted_tag: str = "arsenyc",
    output_name: Optional[str] = None,
) -> str:
    """
    Walk the Obsidian vault and aggregate *all* code blocks from notes that contain the wanted tag.
    Grouping under each note's title as a level-2 heading, and within that, sub-headings as found.
    Writes a single cheatsheet file. Returns its path.
    """
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    output_name = output_name or f"obsidian_{wanted_tag}.md"
    out_path = join(BASE_OUTPUT, sanitize_filename(output_name))

    parts: List[str] = []
    parts.append(f"# Obsidian — #{wanted_tag}\n")
    parts.append("% obsidian\n")

    for md_path in find_markdown_files(vault_dir):
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        if not file_matches_tag(text, wanted_tag):
            continue

        # section for this note
        note_title = md_path.stem
        parts.append(f"## {note_title}\n")

        # parse and extract blocks from this file
        doc = Document(text)
        blocks = extract_heading_code_blocks_mistletoe(doc)

        if not blocks:
            continue

        # re-render code blocks (strip '#' comment lines as in your Notion flow)
        for heading, _lang, code in blocks:
            heading = heading or ""
            parts.append(f"### {heading}\n" if heading else "")
            parts.append("```\n")
            # strip python-style comment lines (same behavior as your original)
            code_no_comments = "\n".join(
                ln for ln in code.splitlines() if not ln.strip().startswith("#")
            )
            parts.append(f"{code_no_comments}\n")
            parts.append("```\n\n")

    await write_text_file(out_path, "".join(parts))
    return out_path
