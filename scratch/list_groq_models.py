import os
import requests
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    models = response.json().get("data", [])
    print("Available Groq Models:")
    for model in models:
        # Check if the model has a vision-like name or print all
        print(f"- {model['id']}")
except Exception as e:
    print("Error listing models:", e)
