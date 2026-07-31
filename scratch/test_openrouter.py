import os
from dotenv import load_dotenv
import litellm

load_dotenv()

token = os.getenv("OPENROUTER_API_KEY")
print("OPENROUTER_API_KEY present:", bool(token))

try:
    print("Testing OpenRouter google/gemma-4-26b-a4b-it:free completion...")
    response = litellm.completion(
        model="openrouter/google/gemma-4-26b-a4b-it:free",
        messages=[{"role": "user", "content": "Hello, explain photosynthesis in 1 sentence."}],
        api_key=token
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error during completion:")
    print(e)
