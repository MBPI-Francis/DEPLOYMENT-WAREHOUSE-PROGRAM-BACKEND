"""
Test script simulating an external program (e.g., Production App)
calling the Warehouse API using the X-API-Key header.
"""

import requests

# The URL of your local LAN FastAPI server
BASE_URL = "http://127.0.0.1:8000"




# The secret API key configured in core/config.py for production
HEADERS = {
    "X-API-Key": "mbpi-prod-secret-key-2026"
}


def test_warehouse_api():
    print("🚀 Sending request to Warehouse API using X-API-Key...")

    # Example: Fetching active raw materials catalog
    response = requests.get(f"http://127.0.0.1:8000/api/v1/rm/api/v1/rm/stock-on-hand/list/?limit=100&offset=0", headers=HEADERS)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCCESS! Program-to-program authentication is working.")
        data = response.json()
        print(f"📦 Retrieved {len(data)} raw materials from inventory.")
    else:
        print("❌ FAILED:")
        print(response.json())


if __name__ == "__main__":
    test_warehouse_api()