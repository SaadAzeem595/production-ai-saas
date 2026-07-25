import json
import os
import base64
import requests
from crewai.tools import tool
from PIL import Image
from ibm_watsonx_ai import Credentials, APIClient
from ibm_watsonx_ai.foundation_models import ModelInference
from io import BytesIO
from typing import List, Optional, Any
import logging
logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

# Configuration Settings
llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()

# IBM Watsonx AI Settings
watsonx_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
watsonx_apikey = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY", ""))
project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")

# Ollama Settings
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
ollama_vision_model = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")

cred_args = {"url": watsonx_url}
if watsonx_apikey:
    cred_args["api_key"] = watsonx_apikey

credentials = Credentials(**cred_args) if watsonx_apikey else None
client = APIClient(credentials) if watsonx_apikey else None


def call_llm_vision(prompt_text: str, encoded_image_base64: str) -> str:
    """Helper to route vision LLM calls to either IBM Watsonx or Ollama"""
    if llm_provider == "ollama":
        url = f"{ollama_host.rstrip('/')}/api/chat"
        models_to_try = [ollama_vision_model, "llama3.2-vision", "llama3.2-vision:latest", "llava"]
        
        last_error = None
        for m in models_to_try:
            try:
                logging.info(f"Trying Ollama Vision model '{m}' at {ollama_host}")
                payload = {
                    "model": m,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt_text,
                            "images": [encoded_image_base64]
                        }
                    ],
                    "stream": False
                }
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()["message"]["content"]
                else:
                    last_error = res.text
            except Exception as e:
                last_error = str(e)
                
        raise RuntimeError(f"Ollama Vision error: {last_error}.")
    else:
        logging.info("Calling IBM Watsonx Vision model...")
        if not credentials:
            raise RuntimeError("IBM_WATSONX_APIKEY is required when using watsonx provider.")
        model = ModelInference(
            model_id="meta-llama/llama-3-2-90b-vision-instruct",
            credentials=credentials,
            project_id=project_id,
            params={"max_tokens": 300},
        )
        response = model.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded_image_base64}}
                    ],
                }
            ]
        )
        return response['choices'][0]['message']['content']


def call_llm_text(prompt_text: str) -> str:
    """Helper to route text LLM calls to either IBM Watsonx or Ollama"""
    if llm_provider == "ollama":
        logging.info(f"Calling Ollama Text model: {ollama_model} at {ollama_host}")
        url = f"{ollama_host.rstrip('/')}/api/chat"
        payload = {
            "model": ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            "stream": False
        }
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return res.json()["message"]["content"]
        else:
            raise RuntimeError(f"Ollama Error ({res.status_code}): {res.text}")
    else:
        logging.info("Calling IBM Watsonx Text model...")
        if not credentials:
            raise RuntimeError("IBM_WATSONX_APIKEY is required when using watsonx provider.")
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            credentials=credentials,
            project_id=project_id,
            params={"max_tokens": 150},
        )
        response = model.chat(
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt_text}],
                }
            ]
        )
        return response['choices'][0]['message']['content']


@tool("Extract ingredients")
def _extract_ingredient_fn(image_input: Any = None, **kwargs) -> str:
    """Extract ingredients from a food item image. Pass the image path as 'image_input'."""
    val = image_input
    if val is None:
        for k, v in kwargs.items():
            if v is not None:
                val = v
                break
                
    if val is None:
        raise ValueError("No image path provided to the extract ingredients tool.")
        
    image_input_str = str(val).strip().strip("'\"")
    if image_input_str.startswith("http"):
        response = requests.get(image_input_str)
        response.raise_for_status()
        raw_data = response.content
    else:
        if not os.path.isfile(image_input_str):
            raise FileNotFoundError(f"No file found at path: {image_input_str}")
        with open(image_input_str, "rb") as file:
            raw_data = file.read()

    encoded_image = base64.b64encode(raw_data).decode("utf-8")
    return call_llm_vision("Extract ingredients from the food item image", encoded_image)


class ExtractIngredientsTool:
    extract_ingredient = _extract_ingredient_fn


@tool("Filter ingredients")
def _filter_ingredients_fn(raw_ingredients: Any = None, **kwargs) -> str:
    """Processes raw ingredient data (either as a list or a text block/string) and filters out non-food items or noise.
    Returns a clean, comma-separated string of ingredients."""
    val = raw_ingredients
    if val is None:
        for k, v in kwargs.items():
            if v is not None:
                val = v
                break
                
    if val is None:
        return ""
        
    if isinstance(val, list):
        cleaned = ", ".join([str(i) for i in val])
    else:
        cleaned = str(val)
        
    cleaned = cleaned.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
    
    lines = []
    for part in cleaned.split('\n'):
        for subpart in part.split(','):
            s = subpart.strip().strip('-*•0123456789. ')
            if s:
                lines.append(s.lower())
                
    return ", ".join(lines)


class FilterIngredientsTool:
    filter_ingredients = _filter_ingredients_fn


@tool("Filter based on dietary restrictions")
def _filter_based_on_restrictions_fn(ingredients: Any = None, dietary_restrictions: Optional[str] = None, **kwargs) -> str:
    """Uses an LLM model to filter ingredients based on dietary restrictions.
    Accepts ingredients (either a list of strings or a comma-separated string) and dietary_restrictions,
    and returns only the compliant ingredients as a clean comma-separated string."""
    val = ingredients
    if val is None:
        for k, v in kwargs.items():
            if k != "dietary_restrictions" and v is not None:
                val = v
                break
                
    if val is None:
        return ""
        
    if isinstance(val, list):
        ingredients_str = ", ".join([str(i) for i in val])
    else:
        ingredients_str = str(val)
        
    if not dietary_restrictions:
        return ingredients_str
        
    prompt = f"""
    You are an AI nutritionist specialized in dietary restrictions. 
    Given the following list of ingredients: {ingredients_str}, 
    and the dietary restriction: {dietary_restrictions}, 
    remove any ingredient that does not comply with this restriction. 
    Return only the compliant ingredients as a comma-separated list with no additional commentary.
    """

    filtered = call_llm_text(prompt).strip().lower()
    return filtered


class DietaryFilterTool:
    filter_based_on_restrictions = _filter_based_on_restrictions_fn


@tool("Analyze nutritional values and calories of the dish from uploaded image")
def _analyze_image_fn(image_input: Any = None, **kwargs) -> str:
    """Provide a detailed nutrient breakdown and estimate the total calories of all ingredients from the uploaded image. Pass the image path as 'image_input'."""
    val = image_input
    if val is None:
        for k, v in kwargs.items():
            if v is not None:
                val = v
                break
                
    if val is None:
        raise ValueError("No image path provided to the nutrient analysis tool.")
        
    image_input_str = str(val).strip().strip("'\"")
    if image_input_str.startswith("http"):
        response = requests.get(image_input_str)
        response.raise_for_status()
        raw_data = response.content
    else:
        if not os.path.isfile(image_input_str):
            raise FileNotFoundError(f"No file found at path: {image_input_str}")
        with open(image_input_str, "rb") as file:
            raw_data = file.read()

    encoded_image = base64.b64encode(raw_data).decode("utf-8")
    
    assistant_prompt = """
    You are an expert nutritionist. Analyze the food items displayed in the image and provide a JSON response strictly adhering to the JSON schema below with no Markdown formatting or codeblock wrappers:
    {
      "dish": "<Identified dish name, e.g. Corn Dogs>",
      "portion_size": "<Portion size description, e.g. 3 corn dogs>",
      "estimated_calories": <Total calories as integer, e.g. 450>,
      "nutrients": {
        "protein": "<Protein amount with units, e.g. 14g>",
        "carbohydrates": "<Carbohydrates amount with units, e.g. 48g>",
        "fats": "<Fats amount with units, e.g. 22g>",
        "vitamins": [
          {"name": "Vitamin Name", "percentage_dv": "10%"}
        ],
        "minerals": [
          {"name": "Mineral Name", "amount": "150mg"}
        ]
      },
      "health_evaluation": "<One paragraph health & nutritional evaluation summary>"
    }
    Ensure valid JSON output.
    """
    return call_llm_vision(assistant_prompt, encoded_image)


class NutrientAnalysisTool:
    analyze_image = _analyze_image_fn
