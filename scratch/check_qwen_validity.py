import os
import requests
import litellm
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

print("--- 1. Querying OpenRouter API /api/v1/models for Qwen VL models ---")
try:
    resp = requests.get("https://openrouter.ai/api/v1/models")
    if resp.status_code == 200:
        models_data = resp.json().get("data", [])
        qwen_models = [m["id"] for m in models_data if "qwen" in m["id"].lower() and "vl" in m["id"].lower()]
        print(f"Found Qwen Vision models on OpenRouter ({len(qwen_models)}):")
        for qm in qwen_models:
            print(" -", qm)
    else:
        print(f"OpenRouter models API returned status {resp.status_code}")
except Exception as e:
    print("Failed to query OpenRouter models list:", e)

print("\n--- 2. Testing direct LiteLLM call with 'qwen/qwen-2-vl-72b-instruct' ---")
try:
    res = litellm.completion(
        model="openrouter/qwen/qwen-2-vl-72b-instruct",
        messages=[{"role": "user", "content": "Hi! Say Hello in 3 words."}],
        api_key=api_key,
        extra_headers={"HTTP-Referer": "https://saadflask.me", "X-Title": "AI Nutrition Coach"}
    )
    print("Success with 'openrouter/qwen/qwen-2-vl-72b-instruct':")
    print(res.choices[0].message.content)
except Exception as e:
    print("Failed call with 'openrouter/qwen/qwen-2-vl-72b-instruct':", type(e).__name__, "-", e)
