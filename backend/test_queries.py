import urllib.request
import json
import time
import subprocess
import os

import sys

print("Starting backend server on port 8001...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(5)  # give it time to start

url = 'http://127.0.0.1:8001/query'

queries = [
    "Which products are associated with the highest number of billing documents?",
    "Trace the full flow of billing document 91150187",
    "Show sales orders that were delivered but not billed"
]

with open("test_results.txt", "w", encoding="utf-8") as f:
    f.write("TESTING REQUIRED QUERIES AGAINST LOCAL BACKEND...\n\n")
    for q in queries:
        f.write(f"==================================================\n")
        f.write(f"QUESTION: {q}\n")
        f.write(f"==================================================\n")
        
        data = json.dumps({"question": q}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode('utf-8'))
            
            f.write("[SQL GENERATED]\n")
            f.write(str(result.get("sql", "None")) + "\n\n")
            
            f.write("[FINAL ANSWER]\n")
            f.write(str(result.get("answer", "None")) + "\n\n")
            
            f.write(f"[DATA EXTRACTED]: {len(result.get('data', []))} records returned.\n\n")
            
        except Exception as e:
            f.write(f"Error testing query: {e}\n\n")

print("Done writing to test_results.txt. Shutting down server...")
server.terminate()
