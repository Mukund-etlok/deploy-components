import os
import json
import redis
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIDDLEWARE_DIR = os.path.join(BASE_DIR, "middleware")
ROUTES_FILE = os.path.join(BASE_DIR, "routes.json")

def run_cmd(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def deploy():
    print("Starting deployment")

    # Redis Connection
    client = redis.Redis(host="localhost", port=6379, db=0)

    # 1. Clear all route data from Redis
    print("Step 1: Clearing all route data from Redis...")
    client.flushdb()

    # 2. Clear all middleware files
    print("Step 2: Clearing middleware files...")
    if os.path.exists(MIDDLEWARE_DIR):
        for file in os.listdir(MIDDLEWARE_DIR):
            if file.endswith((".py", ".json")):
                os.remove(os.path.join(MIDDLEWARE_DIR, file))

    # 3. Git pull current branch
    print("Step 3: Pulling latest Git changes...")
    current_branch = run_cmd("git branch --show-current")
    print(f"Current branch: {current_branch}")
    run_cmd(f"git pull origin {current_branch}")

    # 4. Copy middleware files
    print("Step 4: Copying middleware files...")
    if os.path.exists(MIDDLEWARE_DIR):
        print("Middleware directory found - files updated via git pull.")
    else:
        print("Warning: Middleware directory not found after git pull.")

    # 5. Load route data from routes.json into Redis
    print("Step 5: Loading all route data into Redis...")
    if not os.path.exists(ROUTES_FILE):
        raise FileNotFoundError("routes.json not found!")

    with open(ROUTES_FILE, "r") as f:
        data = json.load(f)

    for comp in data.get("components", []):
        comp_key = f"{comp['component']}:routes"
        print(f"Loading component: {comp['component']}")

        client.delete(comp_key)
        for route in comp.get("routes", []):
            client.sadd(comp_key, route)

        for ev, oc in comp.get("outcomes", {}).items():
            client.hset(f"event:{ev}", "outcomes", oc)

    print("All components loaded into Redis successfully!")

if __name__ == "__main__":
    try:
        deploy()
    except Exception as e:
        print(f"Deployment failed: {e}")
        exit(1)
