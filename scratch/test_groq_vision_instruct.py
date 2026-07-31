import os
import base64
from dotenv import load_dotenv
import litellm
load_dotenv()

token = os.getenv("GROQ_API_KEY")
image_path = "uploaded_image.jpg"

with open(image_path, "rb") as f:
    encoded_image_base64 = base64.b64encode(f.read()).decode("utf-8")

try:
    print("Testing Groq llama-3.2-11b-vision-instruct...")
    response = litellm.completion(
        model="groq/llama-3.2-11b-vision-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image_base64}"}}
                ]
            }
        ],
        api_key=token
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error during Groq vision call:")
    print(e)
