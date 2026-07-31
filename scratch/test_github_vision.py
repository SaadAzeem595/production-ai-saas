from dotenv import load_dotenv
import os
import base64
import litellm
load_dotenv()

token = os.getenv("GITHUB_API_KEY")
image_path = "uploaded_image.jpg"

try:
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    print("Testing GPT-4o mini vision completion via GitHub Models...")
    response = litellm.completion(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                ]
            }
        ],
        api_key=token,
        base_url="https://models.inference.ai.azure.com"
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error during completion:")
    print(e)
