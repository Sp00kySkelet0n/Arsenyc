import asyncio
import aiohttp
import requests
import aiofiles
from mistletoe import Document
from mistletoe.block_token import CodeFence, Heading
from notion_client import AsyncClient
from notion_to_md import NotionToMarkdownAsync
from os.path import dirname, abspath, expanduser, join
from . import cheat
from . import config
from .config import BASEPATH
base_path = join(BASEPATH, "my_cheats")


async def write_synced_file(auth_token,page_id,title_name):

    notion = AsyncClient(auth=auth_token)

    n2m = NotionToMarkdownAsync(notion)

    # Export a page as a markdown blocks
    md_blocks = await n2m.page_to_markdown(page_id)

    # Convert markdown blocks to string
    md_str = n2m.to_markdown_string(md_blocks).get('parent')
    # Regex to find all blocks of code with a title right above it
    doc = Document(md_str)

    code_blocks = []
    last_heading = None

    for token in doc.children:
        if isinstance(token, Heading):
            # Extract plain text from heading
            last_heading = ''.join(child.content for child in token.children)
        elif isinstance(token, CodeFence):
            code_blocks.append({
            'title': last_heading,
            'language': token.language,
            'code': token.children[0].content
            })
    all_blocks=[]
    all_blocks.append(f"# {title_name}")
    all_blocks.append(f"% notion")
    for block in code_blocks:
        code_block = block['code']
        code_without_comments = [line for line in code_block.splitlines() if not line.strip().startswith('#')]
        code_without_comments_str = '\n'.join(code_without_comments)
        all_blocks.append(f"""
## {block['title']}
```
{code_without_comments_str}
```
""")
    all_blocks_str=''.join(all_blocks)
    # Write to a file
    async with aiofiles.open(f"{base_path}/{page_id}.md", "w") as f:
        await f.write(all_blocks_str)


async def sync_notion_main(token):
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "filter": {
            "value": "page",
            "property": "object"
        },
        "page_size": 100
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            pages = await response.json()
            for result in pages["results"]:
                is_synced = result['properties']['Arsenyc']['checkbox']
                if is_synced:
                    project_id = result['id']
                    project_title = result['properties']['Name']['title'][0]['plain_text']
                    await write_synced_file(token,project_id,project_title)
                    print(f"[*] Page { project_title } synced")
