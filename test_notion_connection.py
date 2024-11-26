import aiohttp
import asyncio
from globals import NOTION_API_TOKEN, PHD_MILESTONES_DATABASE_ID

headers = {"Authorization": f"Bearer {NOTION_API_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

async def test_fetch():
    url = f"https://api.notion.com/v1/databases/{PHD_MILESTONES_DATABASE_ID}/query"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json={}) as response:
            print(f"Status: {response.status}")
            print(f"Reason: {response.reason}")
            text = await response.text()
            print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(test_fetch())
