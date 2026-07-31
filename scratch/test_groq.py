import os
from dotenv import load_dotenv
import litellm
load_dotenv()

token = os.getenv("GROQ_API_KEY")

try:
    print("Testing Groq llama-3.3-70b-versatile completion...")
    response = litellm.completion(
        model="groq/llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello, explain photosynthesis in 1 sentence."}],
        api_key=token
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error during completion:")
    print(e)
