import os
import json
import redis
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_DIR = os.path.join(BASE_DIR)

def run_cmd(cmd):
    """Run shell commands and capture output."""
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def deploy():
    print("Starting deployment...")

    # Connect to Redis
    client = redis.Redis(host="localhost", port=6379, db=0)

    # Flush Redis
    print("Step 1: Clearing Redis...")
    client.flushdb()

    # Git pull
    print("Step 2: Pulling latest Git changes...")
    current_branch = run_cmd("git branch --show-current")
    run_cmd(f"git pull origin {current_branch}")

    # Process each component
    print("Step 3: Processing components...")
    if not os.path.exists(COMPONENTS_DIR):
        raise FileNotFoundError("component/ directory not found!")

    for comp_name in os.listdir(COMPONENTS_DIR):
        comp_path = os.path.join(COMPONENTS_DIR, comp_name)
        if not os.path.isdir(comp_path):
            continue

        print(f"Processing component: {comp_name}")

        # --- Load routes.json ---
        routes_file = os.path.join(comp_path, "routes", "routes.json")
        if os.path.exists(routes_file):
            with open(routes_file, "r") as f:
                data = json.load(f)

            comp_key = f"{comp_name}:routes"
            client.delete(comp_key)

            for route in data.get("routes", []):
                client.sadd(comp_key, route)

            for ev, oc in data.get("outcomes", {}).items():
                client.hset(f"event:{ev}", "outcomes", oc)

            print(f"Routes loaded for {comp_name}")

        else:
            print(f"No route.json found for {comp_name}")

        # Load middleware files
        middleware_dir = os.path.join(comp_path, "middleware")
        if os.path.exists(middleware_dir):
            for mw_type in os.listdir(middleware_dir):
                mw_path = os.path.join(middleware_dir, mw_type)
                if os.path.isdir(mw_path):
                    for file in os.listdir(mw_path):
                        file_path = os.path.join(mw_path, file)
                        if os.path.isfile(file_path):
                            with open(file_path, "r") as f:
                                content = f.read()

                            # Store in Redis
                            redis_key = f"{comp_name}:middleware:{mw_type}:{file}"
                            client.set(redis_key, content)
                            print(f"Loaded middleware: {redis_key}")

    print("Deployment completed successfully!")

if __name__ == "__main__":
    try:
        deploy()
    except Exception as e:
        print(f"Deployment failed: {e}")
        exit(1)
