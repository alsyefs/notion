from fetch_pages import fetch_pages
from analyze_pages import analyze_tasks
import asyncio

FETCH_ITEM_LIMIT = 0  # Set to 0 to fetch all items (items are Notion pages)

if __name__ == "__main__":
    asyncio.run(fetch_pages(limit=FETCH_ITEM_LIMIT))
    analyze_tasks()
