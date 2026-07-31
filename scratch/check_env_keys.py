import os
from dotenv import load_dotenv
load_dotenv()

keys = ["LLM_PROVIDER", "GITHUB_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "IBM_WATSONX_APIKEY", "WATSONX_APIKEY", "OPENAI_API_KEY"]
for k in keys:
    val = os.getenv(k)
    status = "SET (value starts with " + val[:8] + "...)" if val else "NOT SET"
    print(f"{k}: {status}")
