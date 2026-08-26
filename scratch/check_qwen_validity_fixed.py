import os
import requests
import litellm
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

headers = {"HTTP-Referer": "https://saadflask.me", "X-Title": "AI Nutrition Coach"}

models_to_check = [
    "qwen/qwen-2-vl-72b-instruct",
    "qwen/qwen2.5-vl-72b-instruct",
    "qwen/qwen3-vl-8b-instruct",
    "qwen/qwen3-vl-32b-instruct"
]

print("--- Testing Qwen Vision models with max_tokens=1024 ---")
for m in models_to_check:
    print(f"\nTesting '{m}'...")
    try:
        res = litellm.completion(
            model=f"openrouter/{m}",
            messages=[{"role": "user", "content": "Hi! Answer in 3 words."}],
            api_key=api_key,
            max_tokens=1024,
            extra_headers=headers
        )
        print(f"SUCCESS ({m}):", res.choices[0].message.content.strip())
    except Exception as e:
        print(f"FAILED ({m}):", type(e).__name__, "-", e)
