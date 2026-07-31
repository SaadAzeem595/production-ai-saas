import requests
import json

try:
    response = requests.get("https://openrouter.ai/api/v1/models")
    if response.status_code == 200:
        models = response.json().get("data", [])
        free_models = [m for m in models if m.get("id", "").endswith(":free")]
        print(f"Total free models found: {len(free_models)}")
        for m in free_models:
            print(f"- {m['id']} (Name: {m['name']})")
    else:
        print("Failed to fetch models:", response.text)
except Exception as e:
    print("Error:", e)
