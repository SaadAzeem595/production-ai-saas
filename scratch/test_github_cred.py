import os
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GITHUB_API_KEY")
base_url = os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")

if not api_key:
    print("Error: GITHUB_API_KEY is not set in the environment or .env file.")
    exit(1)

print(f"Testing GITHUB_API_KEY: {api_key[:12]}...{api_key[-12:]}")
print(f"Base URL: {base_url}")

url = f"{base_url}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "litellm-test"
}
# We use a very small payload to minimize costs and speed up validation.
payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Ping"}],
    "max_tokens": 5
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    print("\n--- Testing against standard GitHub API ---")
    gh_req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "litellm-test"
        }
    )
    with urllib.request.urlopen(gh_req) as response:
        print(f"GitHub API Success! Status Code: {response.getcode()}")
        gh_user = json.loads(response.read().decode("utf-8"))
        print(f"Logged in user: {gh_user.get('login')}")
except urllib.error.HTTPError as e:
    print(f"GitHub API Error {e.code}: {e.reason}")
    try:
        print("GitHub API Error Body:", e.read().decode("utf-8"))
    except Exception:
        pass
except Exception as e:
    print("GitHub API unexpected error:", e)

try:
    print("\n--- Testing against GitHub Models API ---")
    with urllib.request.urlopen(req) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        print(f"Success! Status Code: {status_code}")
        response_json = json.loads(body)
        print("Response Content:", response_json["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode("utf-8")
        print("Error Body:", error_body)
    except Exception:
        pass
except Exception as e:
    print(f"An unexpected error occurred: {e}")

