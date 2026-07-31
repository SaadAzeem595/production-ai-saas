import os
import urllib.request
import urllib.parse
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

print(f"Listing models with GEMINI_API_KEY: {api_key[:12]}...")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

req = urllib.request.Request(url, method="GET")

try:
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        print(f"Success! Status Code: {status_code}")
        response_json = json.loads(body)
        models = [m.get("name") for m in response_json.get("models", [])]
        print(f"Found {len(models)} models:")
        for m in sorted(models):
            print(f" - {m}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode("utf-8")
        print("Error Body:", error_body)
    except Exception:
        pass
except Exception as e:
    print(f"An unexpected error occurred: {e}")
