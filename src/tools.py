import json
import os
import base64
import requests
from crewai.tools import tool
from PIL import Image
import litellm
from io import BytesIO
from typing import List, Optional, Any
import logging
logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

# Configuration Settings
llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
vision_provider = os.getenv("VISION_PROVIDER", llm_provider).lower()

# Ollama Settings
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
ollama_vision_model = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")


def call_llm_vision(prompt_text: str, encoded_image_base64: str) -> str:
    """Helper to route vision LLM calls to different providers"""
    selected_provider = vision_provider
    if selected_provider == "groq":
        if os.getenv("GEMINI_API_KEY"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Gemini...")
            selected_provider = "gemini"
        elif os.getenv("GITHUB_API_KEY") or os.getenv("GITHUB_TOKEN"):
            logging.info("Groq vision model is decommissioned. Routing vision call to GitHub Models...")
            selected_provider = "github"
        elif os.getenv("IBM_WATSONX_APIKEY") or os.getenv("WATSONX_APIKEY"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Watsonx...")
            selected_provider = "watsonx"
        elif os.getenv("OLLAMA_HOST"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Ollama...")
            selected_provider = "ollama"
        else:
            raise RuntimeError(
                "Groq has decommissioned all vision models. To analyze images in production, "
                "please configure GEMINI_API_KEY, GITHUB_API_KEY, IBM_WATSONX_APIKEY, or a remote OLLAMA_HOST in your .env file. "
                "The application will automatically use the configured provider for image analysis while keeping Groq as the main text LLM."
            )

    if selected_provider == "ollama":
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
    elif selected_provider == "gemini":
        logging.info("Calling Gemini Vision model...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required when using gemini provider.")
        response = litellm.completion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image_base64}"}}
                    ]
                }
            ],
            api_key=api_key
        )
        return response.choices[0].message.content
    elif selected_provider == "groq":
        logging.info("Calling Groq Vision model...")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when using groq provider.")
        response = litellm.completion(
            model="groq/llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image_base64}"}}
                    ]
                }
            ],
            api_key=api_key
        )
        return response.choices[0].message.content
    elif selected_provider == "watsonx":
        logging.info("Calling IBM Watsonx Vision model...")
        api_key = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY"))
        project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")
        base_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        if not api_key:
            raise RuntimeError("IBM_WATSONX_APIKEY is required when using watsonx provider.")
        response = litellm.completion(
            model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded_image_base64}}
                    ],
                }
            ],
            api_key=api_key,
            api_base=base_url,
            project_id=project_id
        )
        return response.choices[0].message.content
    elif selected_provider == "github":
        logging.info("Calling GitHub Models Vision model (gpt-4o-mini)...")
        api_key = os.getenv("GITHUB_API_KEY", os.getenv("GITHUB_TOKEN"))
        if not api_key:
            raise RuntimeError("GITHUB_API_KEY or GITHUB_TOKEN is required when using github provider.")
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image_base64}"}}
                    ]
                }
            ],
            api_key=api_key,
            base_url=os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM provider for vision: {selected_provider}")



def call_llm_text(prompt_text: str) -> str:
    """Helper to route text LLM calls to various providers"""
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
    elif llm_provider == "gemini":
        logging.info("Calling Gemini Text model...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required when using gemini provider.")
        response = litellm.completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key
        )
        return response.choices[0].message.content
    elif llm_provider == "groq":
        logging.info("Calling Groq Text model...")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when using groq provider.")
        response = litellm.completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key
        )
        return response.choices[0].message.content
    elif llm_provider == "watsonx":
        logging.info("Calling IBM Watsonx Text model...")
        api_key = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY"))
        project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")
        base_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        if not api_key:
            raise RuntimeError("IBM_WATSONX_APIKEY is required when using watsonx provider.")
        response = litellm.completion(
            model="watsonx/ibm/granite-4-h-small",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt_text}],
                }
            ],
            api_key=api_key,
            api_base=base_url,
            project_id=project_id
        )
        return response.choices[0].message.content
    elif llm_provider == "github":
        logging.info("Calling GitHub Models Text model (gpt-4o-mini)...")
        api_key = os.getenv("GITHUB_API_KEY", os.getenv("GITHUB_TOKEN"))
        if not api_key:
            raise RuntimeError("GITHUB_API_KEY or GITHUB_TOKEN is required when using github provider.")
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key,
            base_url=os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM provider for text: {llm_provider}")


@tool("Extract ingredients")
def _extract_ingredient_fn(image_input: str = None, **kwargs) -> str:
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
def _filter_ingredients_fn(raw_ingredients: str = None, **kwargs) -> str:
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
def _filter_based_on_restrictions_fn(ingredients: str = None, dietary_restrictions: Optional[str] = None, **kwargs) -> str:
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
def _analyze_image_fn(image_input: str = None, **kwargs) -> str:
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
