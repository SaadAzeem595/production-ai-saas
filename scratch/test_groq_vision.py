import os
import base64
from dotenv import load_dotenv
import litellm
load_dotenv()

token = os.getenv("GROQ_API_KEY")

# Create a small dummy base64 image or load uploaded_image.jpg
image_path = "uploaded_image.jpg"
if not os.path.exists(image_path):
    # create a dummy 1x1 image
    from PIL import Image
    im = Image.new("RGB", (1, 1), "red")
    im.save(image_path)

with open(image_path, "rb") as f:
    encoded_image_base64 = base64.b64encode(f.read()).decode("utf-8")

try:
    print("Testing Groq llama-3.2-11b-vision-preview...")
    response = litellm.completion(
        model="groq/llama-3.2-11b-vision-preview",
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
