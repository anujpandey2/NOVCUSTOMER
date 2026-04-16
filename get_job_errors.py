"""
Get detailed job error information
"""

import requests
from azure.identity import DefaultAzureCredential

WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
NOTEBOOK_1_ID = "849c1a36-a4a3-413c-acb7-6e14e31471b9"
NOTEBOOK_2_ID = "745edc54-8f1a-4e38-b7d6-ee7068f7d26a"

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


def get_token():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://api.fabric.microsoft.com/.default")
    return token.token


def get_job_details(notebook_id: str):
    """Get details about the most recent job for a notebook"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get job list
    endpoint = f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?$top=1"
    response = requests.get(endpoint, headers=headers)
    
    if response.status_code != 200:
        print(f"Could not get job list: {response.status_code}")
        return
    
    jobs = response.json().get("value", [])
    if not jobs:
        print(f"No jobs found for notebook")
        return
    
    job = jobs[0]
    print(f"\nJob Details:")
    print(f"  Job ID: {job.get('id')}")
    print(f"  Status: {job.get('status')}")
    print(f"  Started: {job.get('startTimeUtc')}")
    print(f"  Ended: {job.get('endTimeUtc')}")
    
    if "failureInfo" in job:
        print(f"  Failure Info: {job['failureInfo']}")
    
    if "errors" in job:
        print(f"  Errors: {job['errors']}")
    
    print(f"\nFull job data:")
    print(json.dumps(job, indent=2, default=str))


if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("📊 JOB ERROR ANALYSIS")
    print("=" * 80)
    
    print("\n🔍 Notebook 1 (UnzipMedicareFiles):")
    get_job_details(NOTEBOOK_1_ID)
    
    print("\n" + "=" * 80)
    print("\n🔍 Notebook 2 (LoadMedicarePartDfiles):")
    get_job_details(NOTEBOOK_2_ID)
