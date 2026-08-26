import os
import base64
import logging
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from src.tools import call_llm_vision

# Test mock 403 error for restricted model, followed by success on fallback
original_completion = None

def mock_litellm_completion(model, **kwargs):
    if "qwen-2-vl-72b" in model:
        print(f"[TEST MOCK] Simulating 403 region error for model '{model}'")
        raise Exception("OpenrouterException - {'error':{'message':'This model is not available in your region.','code':403}}")
    return original_completion(model=model, **kwargs)

if __name__ == "__main__":
    test_img_path = "uploaded_image.jpg"
    with open(test_img_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode('utf-8')

    import litellm
    original_completion = litellm.completion

    print("\n--- Testing 403 Region Fallback Simulation ---")
    with patch("litellm.completion", side_effect=mock_litellm_completion):
        res = call_llm_vision("Describe this food item in 1 short sentence.", b64_img)
        print("Fallback Output:\n", res)
