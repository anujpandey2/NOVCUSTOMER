"""
Delete and re-create notebooks with proper import
"""

import os
import json
import time
import requests
from pathlib import Path
from azure.identity import DefaultAzureCredential

WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
NOTEBOOK_1_ID = "849c1a36-a4a3-413c-acb7-6e14e31471b9"
NOTEBOOK_2_ID = "745edc54-8f1a-4e38-b7d6-ee7068f7d26a"
NOTEBOOK_1_PATH = r"C:\Users\anujpandey\Downloads\UnzipMedicareFiles.ipynb"
NOTEBOOK_2_PATH = r"C:\Users\anujpandey\Downloads\LoadMedicarePartDfiles.ipynb"

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


def get_token():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://api.fabric.microsoft.com/.default")
    return token.token


def delete_notebook(notebook_id: str, name: str):
    """Delete an existing notebook"""
    print(f"\n🗑️  Deleting notebook: {name} ({notebook_id})")
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}"
    response = requests.delete(endpoint, headers=headers)
    
    if response.status_code in [200, 202, 204]:
        print(f"   ✅ Deleted successfully")
        return True
    else:
        print(f"   ⚠️  Delete returned {response.status_code}: {response.text[:100]}")
        return False


def import_notebook_correct(notebook_path: str, notebook_name: str):
    """
    Import a notebook using proper multipart/form-data approach
    """
    print(f"\n📤 Importing notebook: {notebook_name}")
    
    if not os.path.exists(notebook_path):
        raise FileNotFoundError(f"File not found: {notebook_path}")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Read notebook file
    with open(notebook_path, "rb") as f:
        file_content = f.read()
    
    # Use multipart/form-data for import
    files = {
        "file": (f"{notebook_name}.ipynb", file_content, "application/octet-stream"),
        "displayName": (None, notebook_name),
    }
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/import"
    
    response = requests.post(
        endpoint,
        headers=headers,
        files=files,
        timeout=30
    )
    
    print(f"   Response Status: {response.status_code}")
    
    if response.status_code in [200, 201, 202]:
        result = response.json()
        notebook_id = result.get("id")
        print(f"   ✅ Imported successfully: {notebook_id}")
        return notebook_id
    else:
        print(f"   ❌ Import failed: {response.text[:200]}")
        return None


def execute_notebook(notebook_id: str, notebook_name: str):
    """Execute a notebook"""
    print(f"\n▶️  Executing: {notebook_name}")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"
    
    response = requests.post(
        endpoint,
        headers=headers,
        timeout=30
    )
    
    print(f"   Response Status: {response.status_code}")
    
    if response.status_code in [200, 201, 202, 204]:
        print(f"   ✅ Execution started")
        
        if response.text:
            result = response.json()
            job_id = result.get("id")
            if job_id:
                print(f"   Job ID: {job_id}")
                return poll_execution(job_id)
        
        return get_latest_job_status(notebook_id)
    else:
        print(f"   ❌ Execution failed: {response.text[:200]}")
        return "Failed"


def poll_execution(job_id: str):
    """Poll job execution"""
    print(f"   ⏳ Polling job status...")
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/jobs/instances/{job_id}"
    start_time = time.time()
    timeout = 600
    check_interval = 5
    
    while time.time() - start_time < timeout:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"   ⚠️  Status check: {response.status_code}")
            time.sleep(check_interval)
            continue
        
        job_data = response.json()
        status = job_data.get("status", "Unknown")
        print(f"\r   Status: {status}...", end="", flush=True)
        
        if status in ["Completed", "Succeeded"]:
            print("\r   ✅ Execution completed           ")
            return "Completed"
        elif status in ["Failed", "Failure"]:
            print(f"\r   ❌ Execution failed              ")
            if "failureReason" in job_data:
                print(f"      Error: {job_data['failureReason'].get('message', 'Unknown')}")
            return "Failed"
        elif status == "Cancelled":
            print(f"\r   ⚠️  Execution was cancelled       ")
            return "Cancelled"
        
        time.sleep(check_interval)
    
    print(f"\n   ⏱️  Execution timeout")
    return "Timeout"


def get_latest_job_status(notebook_id: str):
    """Get latest job for a notebook"""
    print(f"   🔍 Checking latest job...")
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?$top=1"
    
    response = requests.get(endpoint, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"   Could not retrieve jobs: {response.status_code}")
        return "Unknown"
    
    jobs = response.json().get("value", [])
    if not jobs:
        return "Unknown"
    
    latest_job = jobs[0]
    job_id = latest_job.get("id")
    status = latest_job.get("status", "Unknown")
    
    print(f"   Job: {job_id}, Status: {status}")
    
    if status in ["Running", "NotStarted", "Queued"]:
        return poll_execution(job_id)
    else:
        return status


def main():
    print("=" * 80)
    print("🚀 FABRIC NOTEBOOK IMPORT & EXECUTION")
    print("=" * 80)
    
    try:
        # Step 1: Delete empty notebooks
        print("\n" + "=" * 80)
        print("🗑️  CLEANUP PHASE")
        print("=" * 80)
        
        delete_notebook(NOTEBOOK_1_ID, "UnzipMedicareFiles")
        delete_notebook(NOTEBOOK_2_ID, "LoadMedicarePartDfiles")
        
        time.sleep(2)  # Wait for deletion to complete
        
        # Step 2: Import notebooks properly
        print("\n" + "=" * 80)
        print("📤 IMPORT PHASE (with content)")
        print("=" * 80)
        
        nb1_id = import_notebook_correct(NOTEBOOK_1_PATH, "UnzipMedicareFiles")
        if not nb1_id:
            print("❌ Failed to import first notebook")
            return
        
        nb2_id = import_notebook_correct(NOTEBOOK_2_PATH, "LoadMedicarePartDfiles")
        if not nb2_id:
            print("❌ Failed to import second notebook")
            return
        
        time.sleep(2)  # Wait for import to complete
        
        # Step 3: Execute notebooks
        print("\n" + "=" * 80)
        print("⚡ EXECUTION PHASE")
        print("=" * 80)
        
        print("\n[1/2] First Notebook: UnzipMedicareFiles")
        status_1 = execute_notebook(nb1_id, "UnzipMedicareFiles")
        
        print("\n[2/2] Second Notebook: LoadMedicarePartDfiles")
        status_2 = execute_notebook(nb2_id, "LoadMedicarePartDfiles")
        
        # Report
        print("\n" + "=" * 80)
        print("📊 EXECUTION REPORT")
        print("=" * 80)
        print(f"\nNotebook 1: UnzipMedicareFiles")
        print(f"  Status: {status_1}")
        print(f"\nNotebook 2: LoadMedicarePartDfiles")
        print(f"  Status: {status_2}")
        print("\n" + "=" * 80)
        
        if status_1 in ["Completed"] and status_2 in ["Completed"]:
            print("✅ BOTH NOTEBOOKS EXECUTED SUCCESSFULLY")
        elif status_1 in ["Completed"]:
            print("⚠️  First notebook completed, second notebook has issues")
        elif status_2 in ["Completed"]:
            print("⚠️  Second notebook completed, first notebook has issues")
        else:
            print("❌ EXECUTION ENCOUNTERED ISSUES")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
