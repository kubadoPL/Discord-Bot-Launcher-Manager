import os
import sys
import importlib.util
import threading

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(script_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

WEBAPPS_DIR = "webApps"
BASE_PORT = 5000  # starting port

def run_flask_app(module_name, filepath, port):
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Set environment variable PORT before running
    os.environ["PORT"] = str(port)
    print(f"[INFO] Running {module_name} on port {port}")
    
    # Run the app
    module.run_api()

def main():
    files = [f for f in os.listdir(WEBAPPS_DIR) if f.endswith(".py")]
    threads = []
    
    for i, filename in enumerate(files):
        port = BASE_PORT + i
        filepath = os.path.join(WEBAPPS_DIR, filename)
        module_name = filename[:-3]  # strip '.py'
        
        # Run each Flask app in its own thread (so they run concurrently)
        t = threading.Thread(target=run_flask_app, args=(module_name, filepath, port))
        t.start()
        threads.append(t)
    
    # Join threads (optional - to keep main alive)
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
