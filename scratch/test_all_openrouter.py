import os
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv

load_dotenv()

# Force LLM_PROVIDER to openrouter
os.environ["LLM_PROVIDER"] = "openrouter"
os.environ["VISION_PROVIDER"] = "openrouter"

from src.tools import call_llm_vision, call_llm_text, validate_and_preprocess_image

def test_vision():
    print("\n=== Testing Vision Call ===")
    img_path = "uploaded_image.jpg"
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return
    encoded = validate_and_preprocess_image(img_path)
    print(f"Encoded image base64 length: {len(encoded)}")
    prompt = "Extract ingredients from the food item image. List them concisely."
    result = call_llm_vision(prompt, encoded)
    print("Vision Output Result:")
    print(result)

def test_text():
    print("\n=== Testing Text Call ===")
    prompt = "Suggest 2 quick healthy breakfast ideas. Respond in JSON."
    result = call_llm_text(prompt)
    print("Text Output Result:")
    print(result)

if __name__ == "__main__":
    test_vision()
    test_text()
