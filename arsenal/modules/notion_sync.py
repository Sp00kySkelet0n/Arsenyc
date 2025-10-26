import os
from typing import List, Tuple, Optional
from os.path import join
from notion_client import AsyncClient
from notion_to_md import NotionToMarkdownAsync
from mistletoe import Document
from .config import BASEPATH
from .common_sync import (
    write_text_file,
    build_markdown_from_blocks,
    extract_heading_code_blocks_mistletoe,
)

BASE_OUTPUT = join(BASEPATH, "my_cheats")

async def write_synced_file_notion(auth_token: str, page_id: str, title_name: str) -> None:
    """
    Fetch a Notion page, convert to Markdown, pull fenced code blocks grouped under the last heading,
    drop Python-style comment lines, then write to BASE_OUTPUT/{page_id}.md
    """
    notion = AsyncClient(auth=auth_token)
    n2m = NotionToMarkdownAsync(notion)

    md_blocks = await n2m.page_to_markdown(page_id)
    md_str = n2m.to_markdown_string(md_blocks).get("parent") or ""

    doc = Document(md_str)
    blocks: List[Tuple[str, Optional[str], str]] = extract_heading_code_blocks_mistletoe(doc)

    out_text = build_markdown_from_blocks(title_name, blocks, header_tag="% notion")
    out_path = join(BASE_OUTPUT, f"{page_id}.md")
    await write_text_file(out_path, out_text)

async def sync_notion_main(auth_token: str, include_tag_property: str = "Arsenyc") -> None:
    """
    Scans Notion for pages and writes one cheatsheet per page if the checkbox property is true.
    Matches your previous "Arsenyc" property behavior.
    """
    import aiohttp

    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "filter": {"value": "page", "property": "object"},
        "page_size": 100,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            resp.raise_for_status()
            payload = await resp.json()

    os.makedirs(BASE_OUTPUT, exist_ok=True)

    for result in payload.get("results", []):
        props = result.get("properties", {})
        # defensive checks
        if include_tag_property in props and props[include_tag_property].get("checkbox"):
            page_id = result["id"]
            name_prop = props.get("Name", {})
            title_list = name_prop.get("title", [])
            page_title = title_list[0]["plain_text"] if title_list else "Untitled"
            await write_synced_file_notion(auth_token, page_id, page_title)
            print(f"[*] Notion page '{page_title}' synced")
