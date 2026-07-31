import os
import litellm
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment or .env file.")
    exit(1)

print(f"Testing GEMINI_API_KEY: {api_key[:12]}...")

try:
    print("Testing Gemini model completion...")
    response = litellm.completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": "Ping"}],
        api_key=api_key
    )
    print("Success! Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error calling Gemini API:")
    print(e)
