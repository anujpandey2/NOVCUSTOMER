"""
Test different import API endpoints
"""

import os
import requests
from azure.identity import DefaultAzureCredential

WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
NOTEBOOK_PATH = r"C:\Users\anujpandey\Downloads\UnzipMedicareFiles.ipynb"

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


def get_token():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://api.fabric.microsoft.com/.default")
    return token.token


def try_endpoint(method: str, endpoint_path: str, description: str, files=None):
    """Try an API endpoint"""
    print(f"\n🔍 Testing: {description}")
    print(f"   Endpoint: {endpoint_path}")
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"{FABRIC_API_BASE}{endpoint_path}"
    
    try:
        if method == "POST" and files:
            response = requests.post(url, headers=headers, files=files, timeout=10)
        else:
            response = requests.request(method, url, headers=headers, timeout=10)
        
        print(f"   Status: {response.status_code}")
        if response.text:
            print(f"   Response: {response.text[:150]}")
        return response.status_code
    except Exception as e:
        print(f"   Error: {e}")
        return None


def main():
    print("=" * 80)
    print("🔍 FABRIC API ENDPOINT DISCOVERY")
    print("=" * 80)
    
    # Read notebook
    with open(NOTEBOOK_PATH, "rb") as f:
        file_content = f.read()
    
    files = {
        "file": ("UnzipMedicareFiles.ipynb", file_content, "application/octet-stream"),
    }
    
    # Try different endpoint variations
    endpoints = [
        ("/workspaces/" + WORKSPACE_ID + "/notebooks", "POST", "POST /workspaces/{id}/notebooks"),
        ("/workspaces/" + WORKSPACE_ID + "/notebooks/import", "POST", "POST /workspaces/{id}/notebooks/import"),
        ("/workspaces/" + WORKSPACE_ID + "/items/notebooks/import", "POST", "POST /workspaces/{id}/items/notebooks/import"),
        ("/workspaces/" + WORKSPACE_ID + "/items", "POST", "POST /workspaces/{id}/items (generic items endpoint)"),
    ]
    
    for endpoint, method, desc in endpoints:
        try_endpoint(method, endpoint, desc, files if method == "POST" else None)
    
    # Also list current notebooks to confirm access
    print("\n" + "=" * 80)
    print("📋 CURRENT NOTEBOOKS")
    print("=" * 80)
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks"
    response = requests.get(endpoint, headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        notebooks = response.json().get("value", [])
        if notebooks:
            for nb in notebooks:
                print(f"  - {nb.get('displayName')} (ID: {nb.get('id')})")
        else:
            print("  (No notebooks found)")
    else:
        print(f"  Error: {response.text[:100]}")


if __name__ == "__main__":
    main()
