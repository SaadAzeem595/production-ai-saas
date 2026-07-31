import os
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

print(f"Testing GEMINI_API_KEY direct request: {api_key[:12]}...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
headers = {
    "Content-Type": "application/json"
}
payload = {
    "contents": [{"parts": [{"text": "Ping"}]}]
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        print(f"Success! Status Code: {status_code}")
        response_json = json.loads(body)
        print("Response Content:", response_json)
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode("utf-8")
        print("Error Body:", error_body)
    except Exception:
        pass
except Exception as e:
    print(f"An unexpected error occurred: {e}")
