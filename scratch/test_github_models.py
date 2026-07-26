from dotenv import load_dotenv
import os
import litellm
load_dotenv()

token = os.getenv("GITHUB_API_KEY")

try:
    print("Testing GPT-4o mini text completion via GitHub Models...")
    response = litellm.completion(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, explain photosynthesis in 1 sentence."}],
        api_key=token,
        base_url="https://models.inference.ai.azure.com"
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error during completion:")
    print(e)
