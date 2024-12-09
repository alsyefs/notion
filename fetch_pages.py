import aiohttp
import asyncio
import os
import pandas as pd
import json
from tqdm import tqdm
from globals import (NOTION_API_TOKEN, NOTION_DATABASE_ID, DATA_DIR, PAGES_CSV_FILE_PATH, PAGES_JSON_FILE_PATH, PAGES_ATTACHMENT_DIR)

headers = {"Authorization": f"Bearer {NOTION_API_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

nid_cache = {}

async def fetch_page_nid(page_id, session):  # 'NID' is the numeric ID of a page. Different than 'ID' which is called 'UID' here.
    """Fetch the NID of a page given its ID, using a cache to minimize API calls."""
    if not page_id:
        return None
    if page_id in nid_cache:
        return nid_cache[page_id]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            page_data = await response.json()
            properties = page_data.get("properties", {})
            nid = safe_get(properties, "NID", "unique_id", "number")
            nid_cache[page_id] = nid
            return nid
        else:
            print(f"Failed to fetch page {page_id}: {response.status}")
            return None

async def fetch_all_pages(session, limit=None):
    """Fetch tasks from the Notion database."""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    has_more = True
    next_cursor = None
    all_tasks = []
    total_fetched = 0
    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        if limit:
            payload["page_size"] = min(limit - total_fetched, 100)
        else:
            payload["page_size"] = 100

        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    response_text = await response.text()
                    print(f"Error fetching tasks: {response.status}, {response.reason}, {response_text}")
                    response.raise_for_status()
                data = await response.json()
                results = data.get("results", [])
                all_tasks.extend(results)
                total_fetched += len(results)
                if limit and total_fetched >= limit:
                    break
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor", None)
        except Exception as e:
            print(f"Exception occurred: {e}")
            raise
    return all_tasks

async def fetch_page_blocks(block_id, session):
    """Recursively fetch all blocks for a given block_id, including nested blocks."""
    blocks = []
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    has_more = True
    next_cursor = None
    while has_more:
        params = {"page_size": 100}
        if next_cursor:
            params["start_cursor"] = next_cursor
        retry_count = 0  # Retry mechanism for handling rate limits
        while retry_count < 5:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 429:  # Rate limit error
                        retry_count += 1
                        retry_after = int(response.headers.get("Retry-After", 1))
                        print(f"Rate limit reached. Retrying after {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue  # To retry the request
                    elif response.status != 200:
                        response_text = await response.text()
                        print(f"Error fetching page blocks: {response.status} {response.reason}: {response_text}")
                        response.raise_for_status()
                    data = await response.json()
                    results = data.get("results", [])
                    blocks.extend(results)
                    has_more = data.get("has_more", False)  # Check for pagination
                    next_cursor = data.get("next_cursor", None)
                    tasks = []  # Recursively fetch child blocks for each block that has children
                    for block in results:
                        if block.get("has_children", False):
                            tasks.append(fetch_page_blocks(block["id"], session))
                    if tasks:
                        child_blocks_list = await asyncio.gather(*tasks)
                        for block, children in zip(results, child_blocks_list):
                            block["children"] = children
                    break  # Exit retry loop on success
            except aiohttp.ClientResponseError as e:
                retry_count += 1
                print(f"ClientResponseError {e.status}: {e.message}. Retrying... ({retry_count}/5)")
                await asyncio.sleep(2 ** retry_count)  # Exponential back-off
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
    return blocks

async def fetch_comments(page_id, session):
    """Fetch comments for a given page."""
    comments = []
    url = f"https://api.notion.com/v1/comments"
    params = {"block_id": page_id}
    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                comments = data.get("results", [])
            else:
                print(f"Failed to fetch comments for page {page_id}: {response.status} - {await response.text()}")
    except Exception as e:
        print(f"Exception occurred while fetching comments: {e}")
    return comments

async def extract_page_blocks(blocks):
    """Extract text content from blocks, handling all supported block types, including nested blocks."""
    texts = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        block_text = ""
        if block_type in [  # Handle blocks with rich text (most text-based blocks)
            "paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "to_do",
            "toggle", "quote", "callout"
        ]:
            text_items = block[block_type].get("rich_text", [])
            for item in text_items:
                plain_text = item.get("plain_text", "")
                annotations = item.get("annotations", {})
                if annotations.get("bold"):  # Apply formatting for annotations
                    plain_text = f"**{plain_text}**"
                if annotations.get("italic"):
                    plain_text = f"*{plain_text}*"
                if annotations.get("underline"):
                    plain_text = f"__{plain_text}__"
                if annotations.get("strikethrough"):
                    plain_text = f"~~{plain_text}~~"
                if item.get("href"):
                    plain_text = f"[{plain_text}]({item['href']})"
                block_text += plain_text
            if block_text.strip():
                texts.append(block_text)
        elif block_type == "to_do":  # Handle to-do blocks (checkbox items)
            text_items = block[block_type].get("rich_text", [])
            checked = block[block_type].get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            block_text = checkbox + " " + "".join(item.get("plain_text", "") for item in text_items)
            texts.append(block_text)
        elif block_type == "equation":  # Handle equations
            equation_content = block[block_type].get("expression", "")
            block_text = f"[Equation: {equation_content}]"
            texts.append(block_text)
        elif block_type == "code":  # Handle code blocks
            code_content = block[block_type].get("text", [])
            language = block[block_type].get("language", "plain")
            code_text = "".join(item.get("plain_text", "") for item in code_content)
            block_text = f"[Code: {language}]\n{code_text}"
            texts.append(block_text)
        elif block_type == "table" and block.get("children"):  # Handle tables and rows
            texts.append("Table:")
            child_texts = await extract_page_blocks(block["children"])
            texts.extend(child_texts)
        elif block_type == "table_row":
            row_cells = block[block_type].get("cells", [])
            row_text = ["".join(item.get("plain_text", "") for item in cell) for cell in row_cells]
            block_text = "; ".join(row_text)
            texts.append(block_text)
        elif block_type in ["image", "video", "file", "pdf", "audio"]:  # Handle media (images, video, etc.)
            file_info = block[block_type].get("file") or block[block_type].get("external")
            if file_info:
                file_url = file_info.get("url")
                block_text = f"[{block_type.capitalize()}] {file_url}"
                texts.append(block_text)
        elif block_type in ["bookmark", "embed", "link_preview"]:  # Handle bookmarks, embeds, and link previews
            url = block[block_type].get("url")
            block_text = f"[{block_type.capitalize()}] {url}"
            texts.append(block_text)
        elif block_type == "child_page":  # Handle child pages
            page_title = block[block_type].get("title", "Untitled")
            block_text = f"[Child Page] {page_title}"
            texts.append(block_text)
        elif block_type == "divider":  # Handle dividers
            block_text = "---"
            texts.append(block_text)
        elif block_type == "synced_block" and block.get("children"):  # Handle synced blocks
            synced_content = await extract_page_blocks(block["children"])
            texts.extend(synced_content)
        elif block_type == "unsupported":  # Handle unsupported and unhandled blocks
            block_text = "[Unsupported block]"
            texts.append(block_text)
        else:
            block_text = f"[Unhandled block type: {block_type}]"
            texts.append(block_text)
        if "children" in block and block["children"]:  # Recursively process children blocks if present
            child_texts = await extract_page_blocks(block["children"])
            texts.extend(child_texts)
    return texts

# def safe_get(dct, *keys):
#     for key in keys:
#         if isinstance(dct, dict):
#             dct = dct.get(key)
#         elif isinstance(dct, list) and isinstance(key, int) and len(dct) > key:
#             dct = dct[key]
#         else:
#             return None
#     return dct

def safe_get(dct, *keys):
    """Enhanced safe dictionary access that better handles Notion title fields."""
    current = dct
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
            current = current[key]
        else:
            return None
        if current is None:
            return None
    return current

async def process_page(result, session):
    """Process an individual Notion task and return its data as a dictionary."""
    properties = result.get("properties", {})
    page_id = result.get("id", "")
    title_prop = properties.get("Name", {})
    title = ""
    if title_prop and "title" in title_prop:
        title_items = title_prop["title"]
        title = "".join(item.get("plain_text", "") for item in title_items)
    page_blocks = await fetch_page_blocks(page_id, session)
    page_content_texts = await extract_page_blocks(page_blocks)
    page_content_str = "\n".join(page_content_texts)
    NID = safe_get(properties, "NID", "unique_id", "number") or page_id
    files_media = safe_get(properties, "Files & media", "files") or []  # Handle "Files & Media"
    file_names = []
    attachment_dir = os.path.join(PAGES_ATTACHMENT_DIR, str(NID))
    download_tasks = []
    if files_media:
        attachment_dir = os.path.join(PAGES_ATTACHMENT_DIR, str(NID))
    for file in files_media:
        file_name = file.get("name")
        file_url = None
        if file.get("type") == "external":
            file_url = file["external"].get("url")
        elif file.get("type") == "file":
            file_url = file["file"].get("url")
        if file_url:
            file_name = sanitize_filename(file_name)
            file_path = os.path.join(attachment_dir, file_name)
            download_tasks.append(asyncio.create_task(download_file(file_url, file_path, session)))  # Add download task for async processing
            file_names.append(file_name)
    if download_tasks:
        download_results = await asyncio.gather(*download_tasks)
        if any(download_results):
            os.makedirs(attachment_dir, exist_ok=True)
    # Fetch Parent NID and Children NIDs
    parent_uid = safe_get(properties, "Parent item", "relation", 0, "id")
    parent_nid = await fetch_page_nid(parent_uid, session) if parent_uid else None
    children_uids = [item["id"] for item in safe_get(properties, "Sub-item", "relation") or []]
    children_nids = [await fetch_page_nid(uid, session) for uid in children_uids]
    comments = await fetch_comments(page_id, session)
    comment_texts = [comment["rich_text"][0].get("plain_text", "") for comment in comments if comment.get("rich_text")]
    comments_str = "\n".join(comment_texts)
    return {
        "UID": page_id,
        "NID": NID,
        # "Name": safe_get(properties, "Name", "title", 0, "plain_text") or "Untitled",
        "Name": title or "Untitled",
        "Body Content": page_content_str,
        "Status": safe_get(properties, "Status", "select", "name"),
        "Started": safe_get(properties, "Started", "date", "start"),
        "Completed": safe_get(properties, "Completed", "date", "start"),
        "Due": safe_get(properties, "Due", "date", "start"),
        "Updated Time": result.get("last_edited_time"),
        "Priority": safe_get(properties, "Priority", "select", "name"),
        "Files & Media": file_names,
        "Created": result.get("created_time"),
        "Parent UID": parent_uid,
        "Parent NID": parent_nid,
        "Children UIDs": children_uids,
        "Children NIDs": children_nids,
        "Comments": comments_str,
    }

async def download_file(url, path, session):
    """Download a file from a given URL."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(await response.read())
                return True
            else:
                print(f"Failed to download ({url}). response status: {response.status}")
    except Exception as e:
        print(f"Error downloading file ({url}): {e}")
    return False

def sanitize_filename(filename):
    """Sanitize the filename to remove or replace invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:255]

async def fetch_and_process_pages(limit=None):
    """Fetch tasks from the Notion database and process only new or updated tasks."""
    print(f"Fetching tasks from Notion (limit: {limit or 'no limit'})...")
    existing_tasks_df = None
    cache_file = PAGES_CSV_FILE_PATH
    if os.path.exists(cache_file):  # Load existing data if available
        existing_tasks_df = pd.read_csv(cache_file)
        existing_tasks_df.set_index("UID", inplace=True)
    async with aiohttp.ClientSession() as session:
        all_tasks = await fetch_all_pages(session, limit=limit)
        tasks = []
        total_tasks = len(all_tasks)
        with tqdm(total=total_tasks, unit="task", dynamic_ncols=True, leave=True) as pbar:
            for result in all_tasks:
                page_id = result.get("id")
                last_edited_time = result.get("last_edited_time")
                if (  # Skip unchanged tasks if cached
                    existing_tasks_df is not None
                    and page_id in existing_tasks_df.index
                    and existing_tasks_df.loc[page_id, "Updated Time"] == last_edited_time
                ):
                    pbar.update(1)
                    continue
                task = await process_page(result, session)  # Process page if new or updated
                tasks.append(task)
                pbar.update(1)

    print("Finished fetching tasks!")
    return tasks

def save_tasks_to_csv(new_tasks, cache_file=PAGES_CSV_FILE_PATH):
    """Save new or updated tasks to the CSV file."""
    if not new_tasks:  # If no new tasks, return early
        return
    new_tasks_df = pd.DataFrame(new_tasks)
    if os.path.exists(cache_file):
        existing_df = pd.read_csv(cache_file)
        if not new_tasks_df.empty:
            merged_df = pd.concat([existing_df, new_tasks_df]).drop_duplicates(subset="UID", keep="last")
            merged_df.to_csv(cache_file, index=False)
    else:
        new_tasks_df.to_csv(cache_file, index=False)

async def fetch_pages(limit=10):
    os.makedirs(os.path.dirname(DATA_DIR), exist_ok=True)
    tasks = await fetch_and_process_pages(limit)
    save_tasks_to_csv(tasks, cache_file=PAGES_CSV_FILE_PATH)
    # If the CSV file is updated, show a message. If not, show no changes were made.
    if len(tasks) > 0:
        print(f"New tasks fetched: {len(tasks)}")
    else:
        print("No new tasks fetched.")
    tasks_df = pd.read_csv(PAGES_CSV_FILE_PATH)
    tasks_df.to_json(PAGES_JSON_FILE_PATH, orient="records", indent=4)

if __name__ == "__main__":
    asyncio.run(fetch_pages(limit=10))
