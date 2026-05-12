import urllib.request
import urllib.error
import urllib.parse
import json
import subprocess
import time

import sys

print("Starting custom debug server on 8003...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--port", "8003"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(4)

url = "http://127.0.0.1:8003/query"
payload = {"question": "91150187 - Find the journal entry number linked to this?"}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

print("Sending API request...")
try:
    response = urllib.request.urlopen(req)
    print(f"Success: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
    print("\n--- SERVER LOGS ---")
    outs, errs = server.communicate(timeout=5)
    print("STDOUT:", outs.decode('utf-8', errors='ignore'))
    print("STDERR:", errs.decode('utf-8', errors='ignore'))
except Exception as e:
    print(f"Exception: {e}")
    print("\n--- SERVER LOGS ---")
    outs, errs = server.communicate(timeout=5)
    print("STDOUT:", outs.decode('utf-8', errors='ignore'))
    print("STDERR:", errs.decode('utf-8', errors='ignore'))
finally:
    server.terminate()
