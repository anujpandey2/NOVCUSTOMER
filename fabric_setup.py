"""
Fabric Pipeline Setup Script
Creates workspace, lakehouse, and spark environment, then runs notebooks for data transformation
"""

import subprocess
import json
import time

# Configuration
WORKSPACE_NAME = "Fabric_Product_Analytics26"
CAPACITY_ID = "F64anuj"  # Fabric capacity
LAKEHOUSE_NAME = "Fabric_Product_LKH"
SPARK_ENV_NAME = "Fabric_HighPerf_Env"

def run_command(cmd, description):
    """Execute a shell command and return output"""
    print(f"\n{'='*60}")
    print(f"Executing: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    return result.returncode == 0, result.stdout, result.stderr

# Step 1: Create Fabric Workspace
def create_workspace():
    """Create Fabric workspace using Fabric CLI"""
    cmd = f"""
fabric workspace create --workspace "{WORKSPACE_NAME}" --capacity "{CAPACITY_ID}"
"""
    success, stdout, stderr = run_command(cmd, f"Creating Fabric Workspace: {WORKSPACE_NAME}")
    return success

# Step 2: Create Lakehouse
def create_lakehouse():
    """Create Lakehouse in the workspace"""
    cmd = f"""
fabric lakehouse create --workspace "{WORKSPACE_NAME}" --name "{LAKEHOUSE_NAME}"
"""
    success, stdout, stderr = run_command(cmd, f"Creating Lakehouse: {LAKEHOUSE_NAME}")
    return success

# Step 3: Create Spark Environment
def create_spark_environment():
    """Create optimized Spark Environment"""
    cmd = f"""
fabric spark-environment create --workspace "{WORKSPACE_NAME}" --name "{SPARK_ENV_NAME}" --memory-optimized
"""
    success, stdout, stderr = run_command(cmd, f"Creating Spark Environment: {SPARK_ENV_NAME}")
    return success

if __name__ == "__main__":
    print("Starting Fabric Product Analytics Infrastructure Setup...")
    print(f"Workspace: {WORKSPACE_NAME}")
    print(f"Capacity: {CAPACITY_ID}")
    print(f"Lakehouse: {LAKEHOUSE_NAME}")
    print(f"Spark Env: {SPARK_ENV_NAME}")
    
    # Execute setup steps
    steps = [
        ("Workspace Creation", create_workspace),
        ("Lakehouse Creation", create_lakehouse),
        ("Spark Environment Creation", create_spark_environment),
    ]
    
    results = {}
    for step_name, step_func in steps:
        try:
            results[step_name] = step_func()
            print(f"✓ {step_name}: {'Success' if results[step_name] else 'Failed'}")
        except Exception as e:
            print(f"✗ {step_name}: Error - {str(e)}")
            results[step_name] = False
    
    print("\n" + "="*60)
    print("SETUP SUMMARY")
    print("="*60)
    for step, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {step}")
