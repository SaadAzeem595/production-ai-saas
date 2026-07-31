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

print(f"Testing GEMINI_API_KEY as an IBM IAM API key: {api_key[:12]}...")

url = "https://iam.cloud.ibm.com/identity/token"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
}
payload = {
    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
    "apikey": api_key
}

data = urllib.parse.urlencode(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        print(f"Success! IBM Cloud IAM Token retrieved. Status Code: {status_code}")
        response_json = json.loads(body)
        print("Token Type:", response_json.get("token_type"))
        print("Expiration (relative):", response_json.get("expiration"))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode("utf-8")
        print("Error Body:", error_body)
    except Exception:
        pass
except Exception as e:
    print(f"An unexpected error occurred: {e}")
