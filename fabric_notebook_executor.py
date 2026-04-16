"""
Fabric Notebook Upload and Execution Script
Uploads two notebooks to a Fabric workspace and executes them in order
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential

# Configuration
WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
LAKEHOUSE_NAME = "MedicareSkillsTerminalLH"
NOTEBOOK_1_PATH = r"C:\Users\anujpandey\Downloads\UnzipMedicareFiles.ipynb"
NOTEBOOK_2_PATH = r"C:\Users\anujpandey\Downloads\LoadMedicarePartDfiles.ipynb"

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
TIMEOUT_SECONDS = 300  # 5 minute timeout for notebook execution


class FabricNotebookExecutor:
    """Handles uploading and executing notebooks in Fabric"""

    def __init__(self):
        """Initialize with authentication"""
        self.credential = DefaultAzureCredential()
        self.token = self._get_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get_token(self) -> str:
        """Get Azure auth token for Fabric API"""
        token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        return token.token

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[Dict] = None, files: Optional[Dict] = None,
        binary_data: Optional[bytes] = None, content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Fabric API"""
        url = f"{FABRIC_API_BASE}{endpoint}"
        
        if binary_data:
            # Binary upload (for notebook content)
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type or "application/octet-stream",
            }
            response = requests.request(method, url, headers=headers, data=binary_data, timeout=30)
        elif files:
            # File upload (multipart)
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.request(method, url, headers=headers, files=files, timeout=30)
        else:
            response = requests.request(method, url, headers=self.headers, json=json_data, timeout=30)
        
        response.raise_for_status()
        return response.json() if response.text else {}

    def upload_notebook(self, notebook_path: str, notebook_name: Optional[str] = None) -> Dict[str, Any]:
        """Upload a notebook to the Fabric workspace"""
        if not os.path.exists(notebook_path):
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        if notebook_name is None:
            notebook_name = Path(notebook_path).stem
        
        print(f"\n📤 Uploading notebook: {notebook_name}")
        
        # Read notebook file
        with open(notebook_path, "r", encoding="utf-8") as f:
            notebook_json = f.read()
        
        # Create import request via POST with JSON body
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks"
        
        # Prepare the payload
        payload = {
            "displayName": notebook_name,
            "definition": {
                "format": "ipynb",
                "parts": [
                    {
                        "path": f"{notebook_name}.ipynb",
                        "payloadType": "InlineBase64",
                        "payload": notebook_json  # Fabric API will handle encoding
                    }
                ]
            }
        }
        
        try:
            result = self._make_request("POST", endpoint, json_data=payload)
            print(f"✅ Notebook uploaded: {result.get('id', notebook_name)}")
            return result
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            # Try alternative approach
            return self._upload_notebook_alt(notebook_path, notebook_name)

    def get_notebook_id(self, notebook_name: str) -> Optional[str]:
        """Get notebook ID by name"""
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks"
        try:
            result = self._make_request("GET", endpoint)
            notebooks = result.get("value", [])
            for nb in notebooks:
                if nb.get("displayName") == notebook_name:
                    return nb.get("id")
            return None
        except Exception as e:
            print(f"⚠️  Failed to retrieve notebook ID: {e}")
            return None

    def _upload_notebook_alt(self, notebook_path: str, notebook_name: str) -> Dict[str, Any]:
        """Alternative upload method - direct binary upload"""
        print(f"   Trying alternative upload method...")
        
        with open(notebook_path, "rb") as f:
            notebook_content = f.read()
        
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks/{notebook_name}"
        try:
            result = self._make_request(
                "PUT",
                endpoint,
                binary_data=notebook_content,
                content_type="application/octet-stream"
            )
            print(f"✅ Notebook uploaded via alternative method: {notebook_name}")
            return result
        except Exception as e:
            print(f"❌ Alternative upload also failed: {e}")
            raise

    def execute_notebook(self, notebook_name: str, wait_for_completion: bool = True) -> Dict[str, Any]:
        """Execute a notebook in the workspace"""
        print(f"\n▶️  Executing notebook: {notebook_name}")
        
        # Try to get notebook ID
        notebook_id = self.get_notebook_id(notebook_name)
        if not notebook_id:
            print(f"⚠️  Could not find notebook ID for {notebook_name}, using name as identifier")
            notebook_id = notebook_name
        
        # Execute notebook
        endpoint = f"/workspaces/{WORKSPACE_ID}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"
        execution_data = {
            "notebookId": notebook_id,
        }
        
        try:
            result = self._make_request("POST", endpoint, json_data=execution_data)
            execution_id = result.get("id")
            print(f"✅ Execution started - Job ID: {execution_id}")
            
            if wait_for_completion:
                return self._wait_for_execution(execution_id)
            return result
        except Exception as e:
            print(f"❌ Execution failed: {e}")
            raise

    def _wait_for_execution(self, execution_id: str) -> Dict[str, Any]:
        """Wait for notebook execution to complete"""
        print(f"⏳ Waiting for execution to complete (timeout: {TIMEOUT_SECONDS}s)...")
        
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            endpoint = f"/workspaces/{WORKSPACE_ID}/jobs/instances/{execution_id}"
            try:
                result = self._make_request("GET", endpoint)
                status = result.get("status", "Unknown")
                
                print(f"  Status: {status}", end="\r")
                
                if status in ["Completed", "Succeeded"]:
                    print(f"✅ Execution completed successfully")
                    return result
                elif status in ["Failed", "Error", "Cancelled"]:
                    print(f"❌ Execution failed with status: {status}")
                    if "failureInfo" in result:
                        print(f"   Error: {result['failureInfo']}")
                    return result
                
                time.sleep(check_interval)
            except Exception as e:
                print(f"⚠️  Error checking status: {e}")
                time.sleep(check_interval)
        
        print(f"❌ Execution timeout after {TIMEOUT_SECONDS} seconds")
        return {"status": "Timeout"}

    def run_pipeline(self):
        """Execute the full pipeline: upload both notebooks, then run them in order"""
        try:
            print("=" * 70)
            print("🚀 FABRIC NOTEBOOK EXECUTION PIPELINE")
            print("=" * 70)
            print(f"Workspace ID: {WORKSPACE_ID}")
            print(f"Lakehouse: {LAKEHOUSE_NAME}")
            
            # Extract notebook names
            notebook_1_name = Path(NOTEBOOK_1_PATH).stem
            notebook_2_name = Path(NOTEBOOK_2_PATH).stem
            
            # Upload both notebooks
            print("\n" + "=" * 70)
            print("📋 UPLOAD PHASE")
            print("=" * 70)
            
            upload_1 = self.upload_notebook(NOTEBOOK_1_PATH, notebook_1_name)
            upload_2 = self.upload_notebook(NOTEBOOK_2_PATH, notebook_2_name)
            
            # Execute notebooks in order
            print("\n" + "=" * 70)
            print("⚡ EXECUTION PHASE")
            print("=" * 70)
            
            print(f"\n[1/2] Running: {notebook_1_name}")
            exec_1 = self.execute_notebook(notebook_1_name, wait_for_completion=True)
            
            if exec_1.get("status") in ["Completed", "Succeeded"]:
                print(f"\n[2/2] Running: {notebook_2_name}")
                exec_2 = self.execute_notebook(notebook_2_name, wait_for_completion=True)
            else:
                print(f"\n⚠️  First notebook did not complete successfully. Skipping second notebook.")
                exec_2 = {"status": "Skipped", "reason": "Previous execution failed"}
            
            # Report results
            self._report_results(notebook_1_name, exec_1, notebook_2_name, exec_2)
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            raise

    def _report_results(self, nb1_name: str, result1: Dict, nb2_name: str, result2: Dict):
        """Generate execution report"""
        print("\n" + "=" * 70)
        print("📊 EXECUTION REPORT")
        print("=" * 70)
        
        print(f"\n📔 Notebook 1: {nb1_name}")
        print(f"   Status: {result1.get('status', 'Unknown')}")
        if "failureInfo" in result1:
            print(f"   Error: {result1['failureInfo']}")
        
        print(f"\n📔 Notebook 2: {nb2_name}")
        print(f"   Status: {result2.get('status', 'Unknown')}")
        if "failureInfo" in result2:
            print(f"   Error: {result2['failureInfo']}")
        
        print("\n" + "=" * 70)
        
        # Summary
        success_count = 0
        if result1.get("status") in ["Completed", "Succeeded"]:
            success_count += 1
        if result2.get("status") in ["Completed", "Succeeded"]:
            success_count += 1
        
        if success_count == 2:
            print("✅ ALL NOTEBOOKS EXECUTED SUCCESSFULLY")
        elif success_count == 1:
            print("⚠️  ONE NOTEBOOK FAILED")
        else:
            print("❌ BOTH NOTEBOOKS FAILED")
        
        print("=" * 70)


if __name__ == "__main__":
    executor = FabricNotebookExecutor()
    executor.run_pipeline()
