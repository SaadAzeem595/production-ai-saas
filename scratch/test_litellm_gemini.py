import os
import litellm
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

model_name = "gemini/gemini-2.5-flash"
print(f"Testing litellm model: {model_name}")

try:
    response = litellm.completion(
        model=model_name,
        messages=[{"role": "user", "content": "Say Hello"}],
        api_key=api_key
    )
    print("Success!")
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print(f"Litellm error: {e}")
