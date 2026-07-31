import os
import base64
from dotenv import load_dotenv
import litellm

load_dotenv()
token = os.getenv("OPENROUTER_API_KEY")

with open("uploaded_image.jpg", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

model = "openrouter/nvidia/nemotron-nano-12b-v2-vl:free"
print(f"Testing {model}...")

try:
    response = litellm.completion(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image? Answer in 1 short sentence."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                ]
            }
        ],
        api_key=token
    )
    print("Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Failed: {e}")
