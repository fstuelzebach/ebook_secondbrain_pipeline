import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  # optional if testing pages

if not NOTION_API_KEY:
    raise ValueError("No NOTION_API_KEY found in .env!")

# Base headers for Notion API
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Example: list pages from a database
database_id = NOTION_DATABASE_ID or "your-database-id-here"
url = f"https://api.notion.com/v1/databases/{database_id}/query"

try:
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    print("Successfully connected to Notion! Here's a sample response:")
    print(json.dumps(data, indent=2))
except requests.exceptions.HTTPError as e:
    print("HTTP error occurred:", e)
    print(response.text)
except Exception as e:
    print("Other error occurred:", e)
