import os
import requests
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("GITHUB_API_KEY")
url = "https://models.inference.ai.azure.com/chat/completions"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
payload = {
    "messages": [
        {"role": "user", "content": "Explain photosynthesis in 1 sentence."}
    ],
    "model": "gpt-4o-mini"
}

try:
    print("Testing direct HTTP request to GitHub Models...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        if "auth" in k.lower() or "ratelimit" in k.lower():
            print(f"- {k}: {v}")
    print("Body:")
    print(response.text)
except Exception as e:
    print("Error during direct HTTP call:", e)
