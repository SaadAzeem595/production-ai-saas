import os
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv()

groq_key = os.getenv("GROQ_API_KEY")

if not groq_key:
    print("Error: GROQ_API_KEY is not set.")
    exit(1)

print(f"Testing GROQ_API_KEY: {groq_key[:12]}...")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {groq_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Ping"}],
    "max_tokens": 5
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        print(f"Groq API Success! Status Code: {status_code}")
        response_json = json.loads(body)
        print("Response Content:", response_json["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print(f"Groq API Error {e.code}: {e.reason}")
    try:
        print("Error Body:", e.read().decode("utf-8"))
    except Exception:
        pass
except Exception as e:
    print(f"An unexpected error occurred: {e}")
