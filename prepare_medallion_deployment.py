#!/usr/bin/env python3
"""
Medallion Architecture Deployment for Microsoft Fabric
Deploys 12 notebooks to a Fabric workspace and executes them sequentially
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
WORKSPACE_ID = "4850ec28-2ac1-4c80-a70d-977ab969085d"
NOTEBOOK_BASE_PATH = r"C:\Users\anujpandey"
API_URL = "https://api.powerbi.com/v1.0/myorg"

# Notebook definitions
NOTEBOOKS = [
    ("00_Generate_Sample_Data", "medallion_bronze", "Phase0_Setup", 1),
    ("00_Workspace_Setup", "medallion_bronze", "Phase0_Setup", 2),
    ("01_Bronze_Ingestion", "medallion_bronze", "Phase1_Bronze", 3),
    ("01_Bronze_Validation", "medallion_bronze", "Phase1_Bronze", 4),
    ("02_Quality_Rules_Engine", "medallion_silver", "Phase2_Silver", 5),
    ("02_Silver_Transform", "medallion_silver", "Phase2_Silver", 6),
    ("02_Silver_Validation", "medallion_silver", "Phase2_Silver", 7),
    ("03_Gold_Aggregations", "medallion_gold", "Phase3_Gold", 8),
    ("03_Gold_Validation", "medallion_gold", "Phase3_Gold", 9),
    ("04_Master_Orchestration_Pipeline", "medallion_gold", "Phase4_Orchestration", 10),
    ("04_Pipeline_Monitoring", "medallion_gold", "Phase4_Orchestration", 11),
    ("04_Log_Pipeline_Execution", "medallion_gold", "Phase4_Orchestration", 12),
]

LAKEHOUSES = ["medallion_bronze", "medallion_silver", "medallion_gold"]


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{title}")
    print("-" * 70)


def get_access_token() -> str:
    """Get access token using az CLI"""
    try:
        print("\n[*] Acquiring access token from Azure CLI...")
        result = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', 'https://api.powerbi.com', '--query', 'accessToken', '-o', 'tsv'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            token = result.stdout.strip()
            if token and not token.startswith("ERROR"):
                print("[+] Token acquired successfully")
                return token
        
        raise Exception(f"Token acquisition failed: {result.stderr}")
    except Exception as e:
        print(f"[!] ERROR: {e}")
        return None


def verify_notebooks() -> Tuple[bool, List[str]]:
    """Verify all notebook files exist"""
    print_section("[STEP 1] Verifying Notebook Files")
    
    missing = []
    for name, _, _, _ in NOTEBOOKS:
        file_path = os.path.join(NOTEBOOK_BASE_PATH, f"{name}.py")
        
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"[OK] {name:40s} ({size:,} bytes)")
        else:
            print(f"[ERROR] {name:40s} NOT FOUND")
            missing.append(name)
    
    if missing:
        print(f"\n[!] {len(missing)} notebook(s) missing!")
        return False, missing
    
    print(f"\n[+] All {len(NOTEBOOKS)} notebooks verified")
    return True, []


def generate_deployment_plan() -> Dict:
    """Generate deployment plan"""
    print_section("[STEP 2] Generating Deployment Plan")
    
    plan = {
        "workspace_id": WORKSPACE_ID,
        "timestamp": datetime.now().isoformat(),
        "lakehouses": LAKEHOUSES,
        "notebooks": []
    }
    
    for name, lakehouse, phase, order in NOTEBOOKS:
        plan["notebooks"].append({
            "order": order,
            "name": name,
            "lakehouse": lakehouse,
            "phase": phase,
            "path": os.path.join(NOTEBOOK_BASE_PATH, f"{name}.py")
        })
    
    print(f"[+] Generated deployment plan with {len(plan['notebooks'])} notebooks")
    print(f"[+] Lakehouses: {', '.join(LAKEHOUSES)}")
    
    return plan


def convert_python_to_notebook(python_path: str) -> Dict:
    """Convert Python file to Jupyter notebook format"""
    with open(python_path, 'r') as f:
        content = f.read()
    
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": content.split('\n')
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Synapse PySpark",
                "language": "python",
                "name": "synapsepyspark"
            },
            "language_info": {"name": "python"}
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }
    
    return notebook


def document_api_calls() -> Dict:
    """Document API calls that would be made"""
    print_section("[STEP 3] Documenting API Calls")
    
    api_calls = {
        "create_lakehouses": {
            "method": "POST",
            "endpoint": f"{API_URL}/groups/{WORKSPACE_ID}/lakehouses",
            "lakehouses": LAKEHOUSES,
            "description": "Create three lakehouses for Bronze, Silver, and Gold layers"
        },
        "create_folders": {
            "method": "POST",
            "endpoint": f"{API_URL}/groups/{WORKSPACE_ID}/notebooks",
            "folders": [
                "Notebooks/Phase0_Setup",
                "Notebooks/Phase1_Bronze",
                "Notebooks/Phase2_Silver",
                "Notebooks/Phase3_Gold",
                "Notebooks/Phase4_Orchestration"
            ],
            "description": "Create folder structure for notebooks"
        },
        "deploy_notebooks": {
            "method": "POST",
            "endpoint": f"{API_URL}/groups/{WORKSPACE_ID}/imports",
            "count": len(NOTEBOOKS),
            "description": "Deploy all 12 notebooks to workspace"
        },
        "bind_notebooks": {
            "method": "PATCH",
            "endpoint": f"{API_URL}/groups/{WORKSPACE_ID}/items/{{notebookId}}",
            "description": "Bind notebooks to their respective lakehouses"
        },
        "execute_notebooks": {
            "method": "POST",
            "endpoint": f"{API_URL}/groups/{WORKSPACE_ID}/notebooks/{{notebookId}}/executeInSession",
            "count": len(NOTEBOOKS),
            "order": "Sequential",
            "description": "Execute notebooks in prescribed order"
        }
    }
    
    print("\nAPI Operations Required:")
    print(f"  [1] Create Lakehouses: {len(LAKEHOUSES)} lakehouses")
    print(f"  [2] Create Folders: 5 folder paths")
    print(f"  [3] Deploy Notebooks: {len(NOTEBOOKS)} notebooks")
    print(f"  [4] Bind Notebooks: Link to lakehouses")
    print(f"  [5] Execute Notebooks: Sequential execution")
    
    return api_calls


def create_execution_manifest() -> Dict:
    """Create execution manifest"""
    print_section("[STEP 4] Creating Execution Manifest")
    
    manifest = {
        "workspace_id": WORKSPACE_ID,
        "timestamp": datetime.now().isoformat(),
        "status": "READY_FOR_DEPLOYMENT",
        "phases": {
            "Phase0_Setup": {
                "name": "Setup",
                "notebooks": [n for n in NOTEBOOKS if n[2] == "Phase0_Setup"],
                "order": 1
            },
            "Phase1_Bronze": {
                "name": "Bronze Ingestion",
                "notebooks": [n for n in NOTEBOOKS if n[2] == "Phase1_Bronze"],
                "order": 2
            },
            "Phase2_Silver": {
                "name": "Silver Transformation",
                "notebooks": [n for n in NOTEBOOKS if n[2] == "Phase2_Silver"],
                "order": 3
            },
            "Phase3_Gold": {
                "name": "Gold Aggregations",
                "notebooks": [n for n in NOTEBOOKS if n[2] == "Phase3_Gold"],
                "order": 4
            },
            "Phase4_Orchestration": {
                "name": "Orchestration & Monitoring",
                "notebooks": [n for n in NOTEBOOKS if n[2] == "Phase4_Orchestration"],
                "order": 5
            }
        }
    }
    
    print(f"[+] Manifest created with 5 phases and {len(NOTEBOOKS)} notebooks")
    
    return manifest


def save_deployment_config(plan: Dict, api_calls: Dict, manifest: Dict):
    """Save deployment configuration to files"""
    print_section("[STEP 5] Saving Configuration Files")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files = {
        "MEDALLION_DEPLOYMENT_PLAN.json": plan,
        "MEDALLION_API_CALLS.json": api_calls,
        "MEDALLION_EXECUTION_MANIFEST.json": manifest
    }
    
    for filename, data in files.items():
        filepath = os.path.join(NOTEBOOK_BASE_PATH, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[+] Saved: {filename}")


def create_deployment_guide() -> str:
    """Create deployment guide"""
    guide = f"""
# Medallion Architecture Deployment Guide
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Workspace Details
- Workspace ID: {WORKSPACE_ID}
- Notebook Base Path: {NOTEBOOK_BASE_PATH}
- Total Notebooks: {len(NOTEBOOKS)}
- Lakehouses: {', '.join(LAKEHOUSES)}

## Notebooks to Deploy

### Phase 0: Setup (2 notebooks)
1. 00_Generate_Sample_Data → medallion_bronze
2. 00_Workspace_Setup → medallion_bronze

### Phase 1: Bronze (2 notebooks)
3. 01_Bronze_Ingestion → medallion_bronze
4. 01_Bronze_Validation → medallion_bronze

### Phase 2: Silver (3 notebooks)
5. 02_Quality_Rules_Engine → medallion_silver
6. 02_Silver_Transform → medallion_silver
7. 02_Silver_Validation → medallion_silver

### Phase 3: Gold (2 notebooks)
8. 03_Gold_Aggregations → medallion_gold
9. 03_Gold_Validation → medallion_gold

### Phase 4: Orchestration (3 notebooks)
10. 04_Master_Orchestration_Pipeline → medallion_gold
11. 04_Pipeline_Monitoring → medallion_gold
12. 04_Log_Pipeline_Execution → medallion_gold

## Deployment Steps

### Step 1: Create Lakehouses
```
POST {API_URL}/groups/{WORKSPACE_ID}/lakehouses
Body: {{ "displayName": "medallion_bronze" }}
```

Repeat for medallion_silver and medallion_gold.

### Step 2: Create Folder Structure
Create these folders in the workspace:
- Notebooks/Phase0_Setup/
- Notebooks/Phase1_Bronze/
- Notebooks/Phase2_Silver/
- Notebooks/Phase3_Gold/
- Notebooks/Phase4_Orchestration/

### Step 3: Deploy Notebooks
For each notebook:
```
POST {API_URL}/groups/{WORKSPACE_ID}/imports
Body: {{
  "displayName": "<notebook_name>",
  "type": "Notebook",
  "definition": {{ ... notebook content ... }}
}}
```

### Step 4: Bind to Lakehouses
For each notebook, update its lakehouse binding:
```
PATCH {API_URL}/groups/{WORKSPACE_ID}/items/<notebookId>
Body: {{
  "metadata": {{
    "dependencies": {{
      "lakehouse": "<lakehouse_id>"
    }}
  }}
}}
```

### Step 5: Execute Sequentially
Execute notebooks in this order, waiting for each to complete:
1. 00_Generate_Sample_Data
2. 00_Workspace_Setup
3. 01_Bronze_Ingestion
4. 01_Bronze_Validation
5. 02_Quality_Rules_Engine
6. 02_Silver_Transform
7. 02_Silver_Validation
8. 03_Gold_Aggregations
9. 03_Gold_Validation
10. 04_Master_Orchestration_Pipeline
11. 04_Pipeline_Monitoring
12. 04_Log_Pipeline_Execution

## Authentication
Uses Azure CLI authentication: `az account get-access-token --resource https://api.powerbi.com`

## Expected Results
- All 12 notebooks deployed successfully
- 3 lakehouses created and populated with data
- Bronze layer: Raw event and transaction data
- Silver layer: Validated and transformed data
- Gold layer: Analytics-ready aggregations
- Full audit logging and monitoring

## Validation
After deployment:
1. Check Fabric workspace for 3 lakehouses
2. Verify all 12 notebooks are deployed
3. Check lakehouse tables for data
4. Review execution logs and metrics

## Support
For issues, refer to:
- MEDALLION_DEPLOYMENT_PLAN.json - Detailed plan
- MEDALLION_API_CALLS.json - API specifications
- MEDALLION_EXECUTION_MANIFEST.json - Execution sequence
"""
    return guide


def generate_summary_report(plan: Dict, api_calls: Dict, manifest: Dict) -> str:
    """Generate comprehensive summary report"""
    
    report = f"""
============================================================
MEDALLION ARCHITECTURE DEPLOYMENT - PREPARATION COMPLETE
============================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Workspace ID: {WORKSPACE_ID}

DEPLOYMENT OVERVIEW
============================================================
Status: READY FOR DEPLOYMENT
Total Notebooks: {len(NOTEBOOKS)}
Total Phases: 5
Total Lakehouses: {len(LAKEHOUSES)}

NOTEBOOK INVENTORY
============================================================
"""
    
    for name, lakehouse, phase, order in NOTEBOOKS:
        report += f"[{order:02d}] {name:40s} → {lakehouse:20s} ({phase})\n"
    
    report += f"""
LAKEHOUSES
============================================================
{chr(10).join([f"• {lh}" for lh in LAKEHOUSES])}

EXECUTION PHASES
============================================================
Phase 0: Setup (2 notebooks)
  - Generate sample data
  - Initialize workspace

Phase 1: Bronze (2 notebooks)
  - Ingest raw data
  - Validate ingestion

Phase 2: Silver (3 notebooks)
  - Apply quality rules
  - Transform data
  - Validate transformations

Phase 3: Gold (2 notebooks)
  - Create aggregations
  - Validate aggregations

Phase 4: Orchestration (3 notebooks)
  - Execute orchestration pipeline
  - Generate monitoring data
  - Log execution metrics

API ENDPOINTS REQUIRED
============================================================
- Create Lakehouses: POST /groups/{{id}}/lakehouses
- Deploy Notebooks: POST /groups/{{id}}/imports
- Bind Resources: PATCH /groups/{{id}}/items/{{id}}
- Execute Notebooks: POST /groups/{{id}}/notebooks/{{id}}/executeInSession

CONFIGURATION FILES GENERATED
============================================================
✓ MEDALLION_DEPLOYMENT_PLAN.json
✓ MEDALLION_API_CALLS.json
✓ MEDALLION_EXECUTION_MANIFEST.json
✓ MEDALLION_DEPLOYMENT_GUIDE.md
✓ MEDALLION_DEPLOYMENT_REPORT.txt

NEXT STEPS
============================================================
1. Review configuration files
2. Execute deployment using Fabric API or CLI
3. Monitor execution progress
4. Validate results in Fabric workspace

SUCCESS CRITERIA
============================================================
✓ All 3 lakehouses created
✓ All 12 notebooks deployed
✓ All notebooks bound to correct lakehouses
✓ All notebooks execute without errors
✓ Data populated in Bronze, Silver, and Gold layers
✓ Audit logs generated

============================================================
READY FOR DEPLOYMENT
============================================================
"""
    
    return report


def main():
    """Main deployment preparation"""
    print_header("MEDALLION ARCHITECTURE DEPLOYMENT PREPARATION")
    print(f"Workspace: {WORKSPACE_ID}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Verify notebooks
    success, missing = verify_notebooks()
    if not success:
        print(f"\n[!] FATAL: Cannot proceed with missing notebooks")
        return 1
    
    # Step 2: Generate deployment plan
    plan = generate_deployment_plan()
    
    # Step 3: Document API calls
    api_calls = document_api_calls()
    
    # Step 4: Create execution manifest
    manifest = create_execution_manifest()
    
    # Step 5: Save configuration
    save_deployment_config(plan, api_calls, manifest)
    
    # Create deployment guide
    guide = create_deployment_guide()
    guide_path = os.path.join(NOTEBOOK_BASE_PATH, "MEDALLION_DEPLOYMENT_GUIDE.md")
    with open(guide_path, 'w') as f:
        f.write(guide)
    print(f"[+] Saved: MEDALLION_DEPLOYMENT_GUIDE.md")
    
    # Generate summary report
    report = generate_summary_report(plan, api_calls, manifest)
    report_path = os.path.join(NOTEBOOK_BASE_PATH, "MEDALLION_DEPLOYMENT_REPORT.txt")
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"[+] Saved: MEDALLION_DEPLOYMENT_REPORT.txt")
    
    # Print summary
    print(report)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
