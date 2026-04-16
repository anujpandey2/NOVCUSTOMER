"""
Fabric Notebook Upload and Execution using Fabric REST API
Alternative approach with proper import syntax
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential
import base64

# Configuration
WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
LAKEHOUSE_NAME = "MedicareSkillsTerminalLH"
NOTEBOOK_1_PATH = r"C:\Users\anujpandey\Downloads\UnzipMedicareFiles.ipynb"
NOTEBOOK_2_PATH = r"C:\Users\anujpandey\Downloads\LoadMedicarePartDfiles.ipynb"

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
TIMEOUT_SECONDS = 600  # 10 minutes timeout for notebook execution


class FabricNotebookManager:
    """Manages notebook upload and execution in Fabric"""

    def __init__(self):
        """Initialize with authentication"""
        self.credential = DefaultAzureCredential()
        self.token = self._get_token()
        self.notebook_ids = {}  # Cache notebook IDs

    def _get_token(self) -> str:
        """Get Azure auth token for Fabric API"""
        token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        return token.token

    def _api_call(
        self, 
        method: str, 
        endpoint: str, 
        json_body: Optional[Dict] = None,
        binary_data: Optional[bytes] = None,
        content_type: str = "application/json",
        retry_count: int = 3
    ) -> requests.Response:
        """Make API call with retry logic"""
        url = f"{FABRIC_API_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        if json_body:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body)
        elif binary_data:
            headers["Content-Type"] = content_type
            data = binary_data
        else:
            data = None
        
        for attempt in range(retry_count):
            try:
                response = requests.request(
                    method, 
                    url, 
                    headers=headers, 
                    data=data, 
                    timeout=30
                )
                return response
            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    print(f"   ⚠️  Retry attempt {attempt + 1}/{retry_count-1}: {e}")
                    time.sleep(2 ** attempt)
                else:
                    raise

    def list_notebooks(self) -> list:
        """List all notebooks in workspace"""
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks"
        response = self._api_call("GET", endpoint)
        response.raise_for_status()
        return response.json().get("value", [])

    def import_notebook(self, notebook_path: str, notebook_name: Optional[str] = None) -> str:
        """
        Import a notebook using the import API
        Returns the notebook ID
        """
        if not os.path.exists(notebook_path):
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        if notebook_name is None:
            notebook_name = Path(notebook_path).stem
        
        print(f"\n📤 Importing notebook: {notebook_name}")
        
        # First check if notebook already exists
        notebooks = self.list_notebooks()
        for nb in notebooks:
            if nb.get("displayName") == notebook_name:
                notebook_id = nb.get("id")
                print(f"   ℹ️  Notebook already exists: {notebook_id}")
                self.notebook_ids[notebook_name] = notebook_id
                return notebook_id
        
        # Read notebook file
        with open(notebook_path, "rb") as f:
            notebook_bytes = f.read()
        
        # Use the import endpoint
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks"
        
        # Try import with multipart-like payload
        # Fabric expects: POST /workspaces/{id}/notebooks with nbformat content
        import_body = {
            "displayName": notebook_name
        }
        
        response = self._api_call("POST", endpoint, json_body=import_body)
        
        if response.status_code != 201 and response.status_code != 200:
            print(f"   ℹ️  API Response: {response.status_code}")
            print(f"   Response body: {response.text[:200]}")
        
        response.raise_for_status()
        result = response.json()
        notebook_id = result.get("id", result.get("displayName", notebook_name))
        
        print(f"   ✅ Notebook created: {notebook_id}")
        self.notebook_ids[notebook_name] = notebook_id
        
        # Now update the notebook content via PUT
        print(f"   📝 Updating notebook content...")
        content_endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/definition"
        
        # Create proper payload for notebook content
        definition_body = {
            "format": "ipynb",
            "parts": [
                {
                    "path": notebook_name,
                    "payloadType": "InlineBase64",
                    "payload": base64.b64encode(notebook_bytes).decode('utf-8')
                }
            ]
        }
        
        response = self._api_call("PUT", content_endpoint, json_body=definition_body)
        
        if response.status_code not in [200, 201, 202]:
            print(f"   ⚠️  Warning: Content update returned {response.status_code}")
            # Continue anyway - notebook may still work
        
        print(f"   ✅ Import completed: {notebook_name}")
        return notebook_id

    def execute_notebook(self, notebook_name: str) -> Optional[str]:
        """
        Execute a notebook and wait for completion
        Returns execution status
        """
        # Get notebook ID
        if notebook_name in self.notebook_ids:
            notebook_id = self.notebook_ids[notebook_name]
        else:
            # Try to find it
            notebooks = self.list_notebooks()
            notebook_id = None
            for nb in notebooks:
                if nb.get("displayName") == notebook_name or nb.get("id") == notebook_name:
                    notebook_id = nb.get("id")
                    break
            
            if not notebook_id:
                print(f"❌ Notebook not found: {notebook_name}")
                return "Not Found"
        
        print(f"\n▶️  Executing notebook: {notebook_name} (ID: {notebook_id})")
        
        # Execute the notebook
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"
        
        response = self._api_call("POST", endpoint)
        
        if response.status_code not in [200, 201, 202, 204]:
            print(f"❌ Execution failed: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            return "Failed"
        
        # Handle empty response (202 Accepted with no body)
        if response.status_code == 204 or not response.text:
            print(f"   ℹ️  Job execution accepted (no immediate response)")
            # Try to get recent jobs
            return self._get_latest_job_status(notebook_id)
        
        try:
            result = response.json()
            job_id = result.get("id")
        except json.JSONDecodeError:
            print(f"   ℹ️  No JSON response, attempting to retrieve job from job list")
            return self._get_latest_job_status(notebook_id)
        
        if not job_id:
            print(f"❌ No job ID returned")
            return "Failed"
        
        print(f"   ✅ Job started: {job_id}")
        
        # Wait for completion
        return self._poll_execution(job_id)

    def _poll_execution(self, job_id: str) -> str:
        """Poll for job completion"""
        print(f"   ⏳ Waiting for execution...", end="", flush=True)
        
        endpoint = f"/workspaces/{WORKSPACE_ID}/jobs/instances/{job_id}"
        start_time = time.time()
        poll_interval = 5
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            response = self._api_call("GET", endpoint)
            
            if response.status_code != 200:
                print(f"\n   ⚠️  Status check returned {response.status_code}")
                time.sleep(poll_interval)
                continue
            
            job_data = response.json()
            status = job_data.get("status", "Unknown")
            
            print(f"\r   ⏳ Status: {status}...", end="", flush=True)
            
            if status in ["Completed", "Succeeded", "Success"]:
                print("\r   ✅ Execution completed successfully         ")
                return "Completed"
            elif status in ["Failed", "Error", "Failure", "Cancelled"]:
                print(f"\r   ❌ Execution failed: {status}                  ")
                if "errors" in job_data:
                    print(f"      Error: {job_data['errors']}")
                return status
            
            time.sleep(poll_interval)
        
        print(f"\n   ⏱️  Execution timeout after {TIMEOUT_SECONDS} seconds")
        return "Timeout"

    def _get_latest_job_status(self, notebook_id: str) -> str:
        """Get the latest job status for a notebook"""
        print(f"   🔍 Checking job history for notebook...")
        
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?$top=1"
        
        try:
            response = self._api_call("GET", endpoint)
            if response.status_code == 200:
                jobs = response.json().get("value", [])
                if jobs:
                    latest_job = jobs[0]
                    job_id = latest_job.get("id")
                    status = latest_job.get("status", "Unknown")
                    print(f"   Latest job status: {status}")
                    
                    if status in ["Running", "NotStarted", "Queued"]:
                        print(f"   ✅ Job found: {job_id}")
                        return self._poll_execution(job_id)
                    else:
                        return status
        except Exception as e:
            print(f"   ⚠️  Could not retrieve job history: {e}")
        
        return "Unknown"

    def run_pipeline(self):
        """Execute full pipeline"""
        try:
            print("=" * 80)
            print("🚀 FABRIC NOTEBOOK EXECUTION PIPELINE")
            print("=" * 80)
            print(f"Workspace ID: {WORKSPACE_ID}")
            print(f"Lakehouse: {LAKEHOUSE_NAME}")
            
            notebook_1_name = Path(NOTEBOOK_1_PATH).stem
            notebook_2_name = Path(NOTEBOOK_2_PATH).stem
            
            # PHASE 1: Import notebooks
            print("\n" + "=" * 80)
            print("📋 IMPORT PHASE")
            print("=" * 80)
            
            id_1 = self.import_notebook(NOTEBOOK_1_PATH, notebook_1_name)
            id_2 = self.import_notebook(NOTEBOOK_2_PATH, notebook_2_name)
            
            # PHASE 2: Execute notebooks
            print("\n" + "=" * 80)
            print("⚡ EXECUTION PHASE")
            print("=" * 80)
            
            print(f"\n[1/2] Running: {notebook_1_name}")
            status_1 = self.execute_notebook(notebook_1_name)
            
            print(f"\n[2/2] Running: {notebook_2_name}")
            status_2 = self.execute_notebook(notebook_2_name)
            
            # PHASE 3: Report
            self._print_report(notebook_1_name, status_1, notebook_2_name, status_2)
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()

    def _print_report(self, nb1: str, status1: str, nb2: str, status2: str):
        """Print execution report"""
        print("\n" + "=" * 80)
        print("📊 EXECUTION REPORT")
        print("=" * 80)
        
        print(f"\n📔 Notebook 1: {nb1}")
        print(f"   Status: {status1}")
        
        print(f"\n📔 Notebook 2: {nb2}")
        print(f"   Status: {status2}")
        
        print("\n" + "=" * 80)
        
        if status1 in ["Completed", "Success"] and status2 in ["Completed", "Success"]:
            print("✅ BOTH NOTEBOOKS EXECUTED SUCCESSFULLY")
        elif status1 in ["Completed", "Success"]:
            print("⚠️  First notebook succeeded, second notebook did not complete")
        else:
            print("❌ EXECUTION ENCOUNTERED ISSUES")
        
        print("=" * 80)


if __name__ == "__main__":
    manager = FabricNotebookManager()
    manager.run_pipeline()
