# backend/fetch_pages.py
import aiohttp
import asyncio
import os
import pandas as pd
import json
from tqdm import tqdm
from backend.text_style import PrintStyle
from backend.globals import (
    NOTION_API_TOKEN,
    NOTION_DATABASE_ID,
    DATA_DIR,
    PAGES_CSV_FILE_PATH,
    PAGES_JSON_FILE_PATH,
    PAGES_ATTACHMENT_DIR,
    NOTION_PROPERTY_NID,
    NOTION_PROPERTY_STATUS,
    NOTION_PROPERTY_STARTED,
    NOTION_PROPERTY_COMPLETED,
    NOTION_PROPERTY_DUE,
    NOTION_PROPERTY_PRIORITY,
    NOTION_PROPERTY_FILES_MEDIA,
    NOTION_PROPERTY_PARENT_ITEM,
    NOTION_PROPERTY_SUB_ITEM,
    NOTION_PROPERTY_TAGS,
    NOTION_PROPERTY_PARENT_TAGS,
)

headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
# Standard Notion property for the title is usually "Name" or "title"
NOTION_PROPERTY_NAME = "Name"
nid_cache = {}


async def fetch_page_nid(
    page_id, session
):  # 'NID' is the numeric ID of a page. Different than 'ID' which is called 'UID' here.
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
            # Use the global variable for NID
            nid = safe_get(properties, NOTION_PROPERTY_NID, "unique_id", "number")
            nid_cache[page_id] = nid
            return nid
        else:
            print(
                f"{PrintStyle.RED}Failed to fetch page {page_id}: {response.status}{PrintStyle.RESET}"
            )
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
                if response.status == 404:
                    print(
                        f"{PrintStyle.RED}CRITICAL ERROR: Database not found (404).{PrintStyle.RESET}"
                    )
                    print(
                        f"{PrintStyle.YELLOW}1. Check if NOTION_DATABASE_ID in .env is correct.{PrintStyle.RESET}"
                    )
                    print(
                        f"{PrintStyle.YELLOW}2. Ensure the integration is added to the database connections.{PrintStyle.RESET}"
                    )
                    # Return empty list to stop execution safely without crashing
                    return []
                if response.status != 200:
                    response_text = await response.text()
                    print(
                        f"{PrintStyle.RED}Error fetching tasks: {response.status} {response.reason}: {response_text}{PrintStyle.RESET}"
                    )
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
            print(f"{PrintStyle.RED}Exception occurred: {e}{PrintStyle.RESET}")
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
                        print(
                            f"{PrintStyle.YELLOW}Rate limit reached. Retrying after {retry_after} seconds...{PrintStyle.RESET}"
                        )
                        await asyncio.sleep(retry_after)
                        continue  # To retry the request
                    elif response.status != 200:
                        response_text = await response.text()
                        print(
                            f"{PrintStyle.RED}Error fetching page blocks: {response.status} {response.reason}: {response_text}{PrintStyle.RESET}"
                        )
                        response.raise_for_status()
                    data = await response.json()
                    results = data.get("results", [])
                    blocks.extend(results)
                    has_more = data.get("has_more", False)  # Check for pagination
                    next_cursor = data.get("next_cursor", None)
                    tasks = (
                        []
                    )  # Recursively fetch child blocks for each block that has children
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
                print(
                    f"{PrintStyle.RED}ClientResponseError {e.status}: {e.message}. Retrying... ({retry_count}/5){PrintStyle.RESET}"
                )
                await asyncio.sleep(2**retry_count)  # Exponential back-off
            except Exception as e:
                print(f"{PrintStyle.RED}Unexpected error: {e}{PrintStyle.RESET}")
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
                print(
                    f"{PrintStyle.RED}Failed to fetch comments for page {page_id}: {response.status} - {await response.text()}{PrintStyle.RESET}"
                )
    except Exception as e:
        print(
            f"{PrintStyle.RED}Exception occurred while fetching comments: {e}{PrintStyle.RESET}"
        )
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
            "paragraph",
            "heading_1",
            "heading_2",
            "heading_3",
            "bulleted_list_item",
            "numbered_list_item",
            "to_do",
            "toggle",
            "quote",
            "callout",
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
            block_text = (
                checkbox
                + " "
                + "".join(item.get("plain_text", "") for item in text_items)
            )
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
            row_text = [
                "".join(item.get("plain_text", "") for item in cell)
                for cell in row_cells
            ]
            block_text = "; ".join(row_text)
            texts.append(block_text)
        elif block_type in [
            "image",
            "video",
            "file",
            "pdf",
            "audio",
        ]:  # Handle media (images, video, etc.)
            file_info = block[block_type].get("file") or block[block_type].get(
                "external"
            )
            if file_info:
                file_url = file_info.get("url")
                block_text = f"[{block_type.capitalize()}] {file_url}"
                texts.append(block_text)
        elif block_type in [
            "bookmark",
            "embed",
            "link_preview",
        ]:  # Handle bookmarks, embeds, and link previews
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
        elif block_type == "synced_block" and block.get(
            "children"
        ):  # Handle synced blocks
            synced_content = await extract_page_blocks(block["children"])
            texts.extend(synced_content)
        elif block_type == "unsupported":  # Handle unsupported and unhandled blocks
            block_text = "[Unsupported block]"
            texts.append(block_text)
        else:
            block_text = f"[Unhandled block type: {block_type}]"
            texts.append(block_text)
        if (
            "children" in block and block["children"]
        ):  # Recursively process children blocks if present
            child_texts = await extract_page_blocks(block["children"])
            texts.extend(child_texts)
    return texts


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
    # Use global variable for Name
    title_prop = properties.get("Name", {})
    title = ""
    if title_prop and "title" in title_prop:
        title_items = title_prop["title"]
        title = "".join(item.get("plain_text", "") for item in title_items)

    page_blocks = await fetch_page_blocks(page_id, session)
    page_content_texts = await extract_page_blocks(page_blocks)
    page_content_str = "\n".join(page_content_texts)

    NID = safe_get(properties, NOTION_PROPERTY_NID, "unique_id", "number")

    # Use global variable for Files & Media
    files_media = (
        safe_get(properties, NOTION_PROPERTY_FILES_MEDIA, "files") or []
    )  # Handle "Files & Media"

    file_names = []
    attachment_dir = os.path.join(PAGES_ATTACHMENT_DIR, str(NID))
    download_tasks = []
    if files_media:
        attachment_dir = os.path.join(PAGES_ATTACHMENT_DIR, str(NID))
    for file in files_media:
        # ... existing file download logic ...
        file_name = file.get("name")
        file_url = None
        if file.get("type") == "external":
            file_url = file["external"].get("url")
        elif file.get("type") == "file":
            file_url = file["file"].get("url")
        if file_url:
            file_name = sanitize_filename(file_name)
            file_path = os.path.join(attachment_dir, file_name)
            download_tasks.append(
                asyncio.create_task(download_file(file_url, file_path, session))
            )  # Add download task for async processing
            file_names.append(file_name)
    if download_tasks:
        download_results = await asyncio.gather(*download_tasks)
        if any(download_results):
            os.makedirs(attachment_dir, exist_ok=True)

    # Fetch Parent NID and Children NIDs using global variables
    parent_uid = safe_get(properties, NOTION_PROPERTY_PARENT_ITEM, "relation", 0, "id")
    parent_nid = await fetch_page_nid(parent_uid, session) if parent_uid else None

    children_uids = [
        item["id"]
        for item in safe_get(properties, NOTION_PROPERTY_SUB_ITEM, "relation") or []
    ]
    children_nids = [await fetch_page_nid(uid, session) for uid in children_uids]

    tags_list = safe_get(properties, NOTION_PROPERTY_TAGS, "multi_select") or []
    tags = [tag["name"] for tag in tags_list] if tags_list else []

    # Fetch Parent Tags (Rollup or Multi-select)
    # Handle Rollup (array) or direct property
    p_tags_prop = properties.get(NOTION_PROPERTY_PARENT_TAGS, {})
    parent_tags = []
    if p_tags_prop.get("type") == "rollup":
        # Rollups can be arrays of multi_select arrays
        rollup_array = p_tags_prop.get("rollup", {}).get("array", [])
        for item in rollup_array:
            if item.get("type") == "multi_select":
                parent_tags.extend([t["name"] for t in item.get("multi_select", [])])
    elif p_tags_prop.get("type") == "multi_select":
        parent_tags = [t["name"] for t in p_tags_prop.get("multi_select", [])]

    # Remove duplicates from parent tags
    parent_tags = list(set(parent_tags))

    comments = await fetch_comments(page_id, session)
    comment_texts = [
        comment["rich_text"][0].get("plain_text", "")
        for comment in comments
        if comment.get("rich_text")
    ]
    comments_str = "\n".join(comment_texts)

    # Note: We use the global keys to FETCH, but we save them as standard keys (e.g. "Status", "Due")
    # This ensures analyze_pages.py doesn't break if a user renames "Status" to "My Status".
    return {
        "UID": page_id,
        "NID": NID,
        "Name": title or "Untitled",
        "Body Content": page_content_str,
        "Status": safe_get(properties, NOTION_PROPERTY_STATUS, "select", "name"),
        "Started": safe_get(properties, NOTION_PROPERTY_STARTED, "date", "start"),
        "Completed": safe_get(properties, NOTION_PROPERTY_COMPLETED, "date", "start"),
        "Due": safe_get(properties, NOTION_PROPERTY_DUE, "date", "start"),
        "Updated Time": result.get("last_edited_time"),  # Standard system property
        "Priority": safe_get(properties, NOTION_PROPERTY_PRIORITY, "select", "name"),
        "Files & Media": file_names,
        "Created": result.get("created_time"),  # Standard system property
        "Parent UID": parent_uid,
        "Parent NID": parent_nid,
        "Children UIDs": children_uids,
        "Children NIDs": children_nids,
        "Tags": tags,
        "Parent Tags": parent_tags,
        "Comments": comments_str,
    }


async def download_file(url, path, session):
    """Download a file from a given URL."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(await response.read())
                return True
            else:
                print(
                    f"{PrintStyle.RED}Failed to download ({url}). response status: {response.status}{PrintStyle.RESET}"
                )
    except Exception as e:
        print(f"{PrintStyle.RED}Error downloading file ({url}): {e}{PrintStyle.RESET}")
    return False


def sanitize_filename(filename):
    """Sanitize the filename to remove or replace invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename[:255]


# Add ANSI colors for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_schema_health(first_task_properties):
    """
    Checks if the properties defined in .env actually exist in the Notion database.
    """
    PrintStyle.print_header("DATABASE SCHEMA INTEGRITY CHECK")

    # Map global variable names to the property name expected in Notion
    checks = [
        ("Status", NOTION_PROPERTY_STATUS),
        ("Priority", NOTION_PROPERTY_PRIORITY),
        ("Due Date", NOTION_PROPERTY_DUE),
        ("Started", NOTION_PROPERTY_STARTED),
        ("Completed", NOTION_PROPERTY_COMPLETED),
        ("Files", NOTION_PROPERTY_FILES_MEDIA),
        ("Tags", NOTION_PROPERTY_TAGS),
        ("Parent Tags", NOTION_PROPERTY_PARENT_TAGS),
    ]

    missing_count = 0

    for label, prop_name in checks:
        if prop_name in first_task_properties:
            PrintStyle.print_success(f"Found property '{prop_name}'", label=label)
        else:
            # Cleaned up warning output to be one line
            print(
                f"  {PrintStyle.YELLOW}⚠️  MISSING: '{prop_name}' ({label}){PrintStyle.RESET}"
            )
            missing_count += 1

    PrintStyle.print_divider()

    if missing_count > 0:
        print(
            f"{PrintStyle.YELLOW}{PrintStyle.BOLD}⚠️  WARNING: {missing_count} configured properties were not found in Notion.{PrintStyle.RESET}"
        )
        # We now print the list of missing properties from the above message:
        PrintStyle.print_info("Missing properties:")
        for label, prop_name in checks:
            if prop_name not in first_task_properties:
                PrintStyle.print_info(f"- {prop_name} ({label})")
        # For debugging, we print all available properties from Notion too:
        PrintStyle.print_info("Available properties in Notion:")
        for prop in first_task_properties.keys():
            PrintStyle.print_info(f"- {prop}")

        PrintStyle.print_info(
            "Check your .env file if you renamed these columns in Notion."
        )
    else:
        PrintStyle.print_success(
            "PERFECT MATCH: All configured properties found!", label="SCHEMA"
        )

    PrintStyle.print_divider()
    PrintStyle.print_saved("Raw CSV", PAGES_CSV_FILE_PATH)
    PrintStyle.print_saved("Raw JSON", PAGES_JSON_FILE_PATH)
    PrintStyle.print_divider()
    print("")


async def fetch_and_process_pages(limit=None):
    """Fetch tasks from the Notion database and process only new or updated tasks."""
    print(
        f"{PrintStyle.CYAN}Fetching tasks from Notion (limit: {limit or 'no limit'})...{PrintStyle.RESET}"
    )
    existing_tasks_df = None
    cache_file = PAGES_CSV_FILE_PATH
    if os.path.exists(cache_file):  # Load existing data if available
        existing_tasks_df = pd.read_csv(cache_file)
        existing_tasks_df.set_index("UID", inplace=True)
    async with aiohttp.ClientSession() as session:
        all_tasks = await fetch_all_pages(session, limit=limit)
        if all_tasks:
            first_page_props = all_tasks[0].get("properties", {})
            check_schema_health(first_page_props)
        else:
            PrintStyle.print_warning(
                "No tasks found in database. Cannot verify schema."
            )
        tasks = []
        total_tasks = len(all_tasks)
        with tqdm(
            total=total_tasks, unit="task", dynamic_ncols=True, leave=True
        ) as pbar:
            for result in all_tasks:
                page_id = result.get("id")
                last_edited_time = result.get("last_edited_time")
                if (  # Skip unchanged tasks if cached
                    existing_tasks_df is not None
                    and page_id in existing_tasks_df.index
                    and existing_tasks_df.loc[page_id, "Updated Time"]
                    == last_edited_time
                ):
                    pbar.update(1)
                    continue
                task = await process_page(
                    result, session
                )  # Process page if new or updated
                tasks.append(task)
                pbar.update(1)

    print(
        f"{PrintStyle.GREEN}✔️  Finished fetching {len(tasks)} tasks!{PrintStyle.RESET}"
    )
    return tasks


def save_tasks_to_csv(new_tasks, cache_file=PAGES_CSV_FILE_PATH):
    """Save new or updated tasks to the CSV file."""
    if not new_tasks:  # If no new tasks, return early
        return
    new_tasks_df = pd.DataFrame(new_tasks)
    if os.path.exists(cache_file):
        existing_df = pd.read_csv(cache_file)
        if not new_tasks_df.empty:
            merged_df = pd.concat([existing_df, new_tasks_df]).drop_duplicates(
                subset="UID", keep="last"
            )
            merged_df.to_csv(cache_file, index=False)
    else:
        new_tasks_df.to_csv(cache_file, index=False)


async def fetch_pages(limit=10):
    os.makedirs(os.path.dirname(DATA_DIR), exist_ok=True)
    tasks = await fetch_and_process_pages(limit)
    save_tasks_to_csv(tasks, cache_file=PAGES_CSV_FILE_PATH)
    # If the CSV file is updated, show a message. If not, show no changes were made.
    if len(tasks) > 0:
        print(
            f"{PrintStyle.GREEN}✔️  Saved {len(tasks)} new/updated tasks to CSV.{PrintStyle.RESET}"
        )
    else:
        print(
            f"{PrintStyle.YELLOW}ℹ️  No new or updated tasks to save.{PrintStyle.RESET}"
        )
    tasks_df = pd.read_csv(PAGES_CSV_FILE_PATH)
    tasks_df.to_json(PAGES_JSON_FILE_PATH, orient="records", indent=4)


if __name__ == "__main__":
    asyncio.run(fetch_pages(limit=10))
