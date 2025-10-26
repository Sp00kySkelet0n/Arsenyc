import os
import re
import unicodedata
import asyncio
import aiofiles
from os.path import join
from typing import Iterable, Optional, Tuple, List

# Expose a single helper to ensure paths exist + write atomically-ish
async def write_text_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # simple atomic-ish write: write to temp then replace
    tmp = f"{path}.tmp"
    async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
        await f.write(text)
    os.replace(tmp, path)

def sanitize_filename(name: str, max_len: int = 120) -> str:
    # basic filesystem-safe sanitizer
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s.-]", "", name).strip().replace(" ", "_")
    if not name:
        name = "untitled"
    return name[:max_len]

def strip_comment_lines(text: str, comment_prefix: str = "#") -> str:
    # remove lines that *start* with the chosen comment prefix (default: python-style '#')
    lines = text.splitlines()
    kept = [ln for ln in lines if not ln.strip().startswith(comment_prefix)]
    return "\n".join(kept)

def build_markdown_from_blocks(
    title_name: str,
    blocks: Iterable[Tuple[str, Optional[str], str]],
    header_tag: str = "% notion"
) -> str:
    """
    blocks: iterable of (heading_title, language, code_text)
    Returns the consolidated cheatsheet Markdown.
    """
    parts: List[str] = []
    parts.append(f"# {title_name}\n")
    parts.append(f"{header_tag}\n")
    for heading, _lang, code in blocks:
        heading = heading or ""
        code_no_comments = strip_comment_lines(code, "#")
        parts.append(f"## {heading}\n")
        parts.append("```\n")
        parts.append(f"{code_no_comments}\n")
        parts.append("```\n\n")
    return "".join(parts)

# Generic fenced-code + heading extractor using mistletoe AST
def extract_heading_code_blocks_mistletoe(doc) -> List[Tuple[str, Optional[str], str]]:
    """
    Given a mistletoe.Document, return list of (heading_text, language, code_text).
    Heading is the *most recent* Heading before each CodeFence at the top level.
    """
    from mistletoe.block_token import CodeFence, Heading  # local import
    blocks: List[Tuple[str, Optional[str], str]] = []
    last_heading: Optional[str] = None

    for token in getattr(doc, "children", []):
        if isinstance(token, Heading):
            last_heading = "".join(child.content for child in token.children)
        elif isinstance(token, CodeFence):
            code = token.children[0].content if token.children else ""
            language = token.language
            blocks.append((last_heading, language, code))
    return blocks

# Quick tag detection (front matter + inline)
_YAML_FENCE = re.compile(r"^---\s*$", re.M)
_TAG_LINE = re.compile(r"(?:^|\s)#([A-Za-z0-9_/-]+)")

def detect_tags(markdown_text: str) -> List[str]:
    """
    Returns tags from YAML front matter 'tags:' (array or inline) and inline '#tag' style.
    This is intentionally lightweight (no PyYAML dependency).
    """
    tags = set()

    # Inline #tags
    for m in _TAG_LINE.finditer(markdown_text):
        tags.add(m.group(1))

    # Naive YAML front matter parse
    fm_tags = _extract_front_matter_tags(markdown_text)
    tags.update(fm_tags)

    return sorted(tags)

def _extract_front_matter_tags(text: str) -> List[str]:
    """
    Very light YAML front matter sniffing to extract tags (array or scalar).
    - ---
      tags: [a, b, c]
      # or
      tags:
        - a
        - b
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    # find the closing fence
    end = None
    for i in range(1, min(len(lines), 400)):  # cap scan
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return []

    body = "\n".join(lines[1:end])
    # Extremely small "parser"
    m_inline = re.search(r"^\s*tags\s*:\s*\[(.*?)\]", body, flags=re.M)
    if m_inline:
        raw = m_inline.group(1)
        items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
        return items

    # list form
    block = []
    in_tags = False
    for ln in body.splitlines():
        if not in_tags:
            if re.match(r"^\s*tags\s*:\s*$", ln):
                in_tags = True
        else:
            if re.match(r"^\s*-\s+(.+)$", ln):
                block.append(re.sub(r"^\s*-\s+", "", ln).strip().strip("'\""))
            elif re.match(r"^\S", ln):  # next top-level key
                break
    return block
