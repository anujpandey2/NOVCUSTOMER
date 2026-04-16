"""
Script to upload notebook content and then execute notebooks
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
    """Get Azure auth token"""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://api.fabric.microsoft.com/.default")
    return token.token


def upload_notebook_content(notebook_id: str, notebook_path: str):
    """Upload actual notebook content to an existing notebook"""
    print(f"\n📝 Uploading content for notebook: {notebook_id}")
    
    if not os.path.exists(notebook_path):
        raise FileNotFoundError(f"File not found: {notebook_path}")
    
    # Read notebook content
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook_content = f.read()
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain",
    }
    
    # Try to upload via definition endpoint
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/definition"
    
    # For notebook content, we need to send it as the body directly
    response = requests.put(
        endpoint,
        headers=headers,
        data=notebook_content,
        timeout=30
    )
    
    print(f"   Response Status: {response.status_code}")
    if response.text:
        print(f"   Response: {response.text[:200]}")
    
    if response.status_code in [200, 201, 202]:
        print(f"   ✅ Content uploaded successfully")
        return True
    else:
        print(f"   ⚠️  Upload returned {response.status_code}, but will continue...")
        return False


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
        else:
            # No job ID, try to get recent jobs
            return get_latest_job_status(notebook_id)
    else:
        print(f"   ❌ Execution failed: {response.text[:200]}")
        return "Failed"


def get_latest_job_status(notebook_id: str):
    """Get latest job status for a notebook"""
    print(f"   🔍 Checking latest job...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?$top=1"
    
    response = requests.get(
        endpoint,
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"   Could not retrieve jobs: {response.status_code}")
        return "Unknown"
    
    jobs = response.json().get("value", [])
    if not jobs:
        print(f"   No jobs found")
        return "Unknown"
    
    latest_job = jobs[0]
    job_id = latest_job.get("id")
    status = latest_job.get("status", "Unknown")
    
    print(f"   Latest job: {job_id}")
    print(f"   Current status: {status}")
    
    if status in ["Running", "NotStarted", "Queued"]:
        return poll_execution(job_id)
    else:
        return status


def poll_execution(job_id: str):
    """Poll job execution"""
    print(f"   ⏳ Polling job status...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/jobs/instances/{job_id}"
    start_time = time.time()
    timeout = 600  # 10 minutes
    check_interval = 5
    
    while time.time() - start_time < timeout:
        response = requests.get(
            endpoint,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ⚠️  Status check returned {response.status_code}")
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
            if "failureInfo" in job_data:
                print(f"      Error: {job_data['failureInfo']}")
            return "Failed"
        elif status == "Cancelled":
            print(f"\r   ⚠️  Execution was cancelled       ")
            return "Cancelled"
        
        time.sleep(check_interval)
    
    print(f"\n   ⏱️  Execution timeout")
    return "Timeout"


def main():
    print("=" * 80)
    print("🚀 FABRIC NOTEBOOK EXECUTION PIPELINE (Content Upload + Run)")
    print("=" * 80)
    
    try:
        # Step 1: Upload content for both notebooks
        print("\n" + "=" * 80)
        print("📋 CONTENT UPLOAD PHASE")
        print("=" * 80)
        
        upload_notebook_content(NOTEBOOK_1_ID, NOTEBOOK_1_PATH)
        upload_notebook_content(NOTEBOOK_2_ID, NOTEBOOK_2_PATH)
        
        # Step 2: Execute notebooks
        print("\n" + "=" * 80)
        print("⚡ EXECUTION PHASE")
        print("=" * 80)
        
        print("\n[1/2] First Notebook: UnzipMedicareFiles")
        status_1 = execute_notebook(NOTEBOOK_1_ID, "UnzipMedicareFiles")
        
        print("\n[2/2] Second Notebook: LoadMedicarePartDfiles")
        status_2 = execute_notebook(NOTEBOOK_2_ID, "LoadMedicarePartDfiles")
        
        # Report
        print("\n" + "=" * 80)
        print("📊 EXECUTION REPORT")
        print("=" * 80)
        print(f"\n📔 UnzipMedicareFiles")
        print(f"   Status: {status_1}")
        print(f"\n📔 LoadMedicarePartDfiles")
        print(f"   Status: {status_2}")
        print("\n" + "=" * 80)
        
        if status_1 in ["Completed", "Success"] and status_2 in ["Completed", "Success"]:
            print("✅ BOTH NOTEBOOKS EXECUTED SUCCESSFULLY")
        elif status_1 in ["Completed", "Success"]:
            print("⚠️  First notebook completed, second did not complete successfully")
        elif status_2 in ["Completed", "Success"]:
            print("⚠️  Second notebook completed, first did not complete successfully")
        else:
            print("❌ BOTH NOTEBOOKS ENCOUNTERED ISSUES")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
