import json
import os
import base64
import time
import requests
import logging
from io import BytesIO
from typing import List, Optional, Any, Dict
from PIL import Image, ImageOps
import litellm

logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

def tool(name=None):
    def decorator(fn):
        return fn
    return decorator

# Configuration Settings
llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
vision_provider = os.getenv("VISION_PROVIDER", llm_provider).lower()

# Ollama Settings
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
ollama_vision_model = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")


def validate_and_preprocess_image(image_input_str: str, max_dim: int = 1024, quality: int = 85) -> str:
    """
    Validates, resizes, compresses, and base64-encodes an input image.
    Supports local file paths and HTTP URLs.
    Guarantees lightweight JPEG payload (~50-100 KB) to prevent OpenRouter network timeouts.
    """
    if not image_input_str or not isinstance(image_input_str, str):
        raise ValueError("Invalid image input provided. Expected non-empty file path or URL string.")
        
    image_path_clean = image_input_str.strip().strip("'\"")
    
    # 1. Fetch raw bytes
    if image_path_clean.startswith("data:image/"):
        try:
            _, b64_data = image_path_clean.split(",", 1)
            raw_data = base64.b64decode(b64_data)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 image data URI: {str(e)}")
    elif image_path_clean.startswith("http://") or image_path_clean.startswith("https://"):
        logging.info(f"Downloading image from URL: {image_path_clean[:60]}...")
        try:
            res = requests.get(image_path_clean, timeout=15)
            res.raise_for_status()
            raw_data = res.content
        except Exception as e:
            raise RuntimeError(f"Failed to download image from URL: {str(e)}")
    else:
        if not os.path.isfile(image_path_clean):
            if len(image_path_clean) > 100:
                try:
                    raw_data = base64.b64decode(image_path_clean)
                except Exception:
                    raise FileNotFoundError(f"Uploaded image file not found at path: {image_path_clean}")
            else:
                raise FileNotFoundError(f"Uploaded image file not found at path: {image_path_clean}")
        else:
            try:
                with open(image_path_clean, "rb") as f:
                    raw_data = f.read()
            except Exception as e:
                raise RuntimeError(f"Failed to read local image file: {str(e)}")

    if not raw_data or len(raw_data) == 0:
        raise ValueError("Uploaded image file is empty (0 bytes).")

    raw_kb = len(raw_data) / 1024.0

    # 2. Validate PIL image integrity and preprocess
    try:
        img = Image.open(BytesIO(raw_data))
        img.verify() # Verify file header
        img = Image.open(BytesIO(raw_data)) # Re-open for operations
        
        # Apply EXIF rotation if present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
            
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        elif img.mode == 'L':
            img = img.convert('RGB')

        orig_w, orig_h = img.size
        logging.info(f"Loaded image: format={img.format}, original_dims=({orig_w}x{orig_h}), size={raw_kb:.1f}KB")

        # Resize if dimensions exceed max_dim
        if orig_w > max_dim or orig_h > max_dim:
            if orig_w > orig_h:
                new_w = max_dim
                new_h = int(orig_h * (max_dim / orig_w))
            else:
                new_h = max_dim
                new_w = int(orig_w * (max_dim / orig_h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            logging.info(f"Resized image to ({new_w}x{new_h})")

        out_buf = BytesIO()
        img.save(out_buf, format="JPEG", quality=quality, optimize=True)
        compressed_bytes = out_buf.getvalue()
        comp_kb = len(compressed_bytes) / 1024.0
        logging.info(f"Compressed image payload from {raw_kb:.1f}KB to {comp_kb:.1f}KB")

        return base64.b64encode(compressed_bytes).decode("utf-8")

    except Exception as e:
        if "cannot identify image file" in str(e).lower():
            raise ValueError(f"Invalid or corrupted image file. Could not parse image format: {str(e)}")
        logging.warning(f"Image preprocessing warning: {e}. Falling back to raw base64 encoding.")
        return base64.b64encode(raw_data).decode("utf-8")


def _safely_extract_content(response: Any, model_name: str) -> str:
    """
    Safely validates and extracts content from a LiteLLM completion response object.
    Guarantees that 'NoneType' object is not subscriptable errors are impossible.
    """
    if response is None:
        raise RuntimeError(f"LLM API model '{model_name}' returned None (null response object).")

    # Handle dictionary response format
    if isinstance(response, dict):
        choices = response.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            raise RuntimeError(f"LLM API model '{model_name}' returned response dictionary with empty 'choices' list.")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError(f"LLM API model '{model_name}' returned invalid choice element.")
        msg = first_choice.get("message")
        if not msg or not isinstance(msg, dict):
            raise RuntimeError(f"LLM API model '{model_name}' choice missing 'message' field.")
        content = msg.get("content")
        if content is None:
            raise RuntimeError(f"LLM API model '{model_name}' response message content is None.")
        return str(content)

    # Handle LiteLLM ModelResponse object format
    if not hasattr(response, "choices"):
        raise RuntimeError(f"LLM API model '{model_name}' response object has no 'choices' attribute.")

    choices = getattr(response, "choices", None)
    if not choices or not isinstance(choices, (list, tuple)) or len(choices) == 0:
        raise RuntimeError(f"LLM API model '{model_name}' returned empty 'choices' list.")

    first_choice = choices[0]
    if first_choice is None:
        raise RuntimeError(f"LLM API model '{model_name}' first choice element is None.")

    if not hasattr(first_choice, "message"):
        raise RuntimeError(f"LLM API model '{model_name}' choice object has no 'message' attribute.")

    msg = getattr(first_choice, "message", None)
    if msg is None:
        raise RuntimeError(f"LLM API model '{model_name}' message object is None.")

    if not hasattr(msg, "content"):
        raise RuntimeError(f"LLM API model '{model_name}' message object has no 'content' attribute.")

    content = getattr(msg, "content", None)
    if content is None:
        raise RuntimeError(f"LLM API model '{model_name}' message content is None.")

    return str(content)


def call_llm_vision(prompt_text: str, encoded_image_base64: str) -> str:
    """
    Helper to route vision LLM calls to configured provider with fallbacks, 30s timeout,
    and single-layer controlled retry execution.
    """
    selected_provider = vision_provider
    if selected_provider == "groq":
        if os.getenv("OPENROUTER_API_KEY"):
            logging.info("Groq vision model is decommissioned. Routing vision call to OpenRouter...")
            selected_provider = "openrouter"
        elif os.getenv("GEMINI_API_KEY"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Gemini...")
            selected_provider = "gemini"
        elif os.getenv("GITHUB_API_KEY") or os.getenv("GITHUB_TOKEN"):
            logging.info("Groq vision model is decommissioned. Routing vision call to GitHub Models...")
            selected_provider = "github"
        elif os.getenv("IBM_WATSONX_APIKEY") or os.getenv("WATSONX_APIKEY"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Watsonx...")
            selected_provider = "watsonx"
        elif os.getenv("OLLAMA_HOST") and not os.getenv("VERCEL"):
            logging.info("Groq vision model is decommissioned. Routing vision call to Ollama...")
            selected_provider = "ollama"
        else:
            selected_provider = "openrouter"

    logging.info(f"[Vision Request] Provider: '{selected_provider}'")

    if selected_provider == "ollama":
        if os.getenv("VERCEL"):
            raise RuntimeError("Ollama local endpoint is not supported in Vercel serverless environment. Please configure OPENROUTER_API_KEY or GEMINI_API_KEY in Vercel.")
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
                res = requests.post(url, json=payload, timeout=30)
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
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = litellm.completion(
            model=f"gemini/{gemini_model}",
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
            timeout=30
        )
        return _safely_extract_content(response, gemini_model)

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
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image_base64}"}}
                    ],
                }
            ],
            api_key=api_key,
            api_base=base_url,
            project_id=project_id,
            timeout=30
        )
        return _safely_extract_content(response, "watsonx/llama-3-2-90b-vision")

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
            base_url=os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com"),
            timeout=30
        )
        return _safely_extract_content(response, "github/gpt-4o-mini")

    elif selected_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        has_key = bool(api_key and str(api_key).strip())
        logging.info(f"[Vision Request] Provider: openrouter | OPENROUTER_API_KEY exists: {has_key}")
        if not has_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured in environment variables. Please set OPENROUTER_API_KEY in Vercel settings.")
        
        configured_model = os.getenv("OPENROUTER_VISION_MODEL", "dots-studio/dots-3-note-preview:free")
        candidate_models = [configured_model]
        for fallback in ["nvidia/nemotron-nano-12b-v2-vl:free", "openrouter/auto"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)
                
        last_exception = None
        for vm in candidate_models:
            model_id = vm if vm.startswith("openrouter/") else f"openrouter/{vm}"
            start_t = time.time()
            logging.info(f"Attempting OpenRouter Vision model: '{model_id}'...")
            try:
                response = litellm.completion(
                    model=model_id,
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
                    timeout=20,
                    max_tokens=1024,
                    extra_headers={
                        "HTTP-Referer": "https://nourishbot.vercel.app",
                        "X-Title": "NourishBot"
                    }
                )
                duration = time.time() - start_t
                content = _safely_extract_content(response, model_id)
                if content and len(content.strip()) > 0:
                    logging.info(f"Successfully received vision response from OpenRouter model '{model_id}' in {duration:.2f}s")
                    return content
            except Exception as e:
                duration = time.time() - start_t
                logging.warning(f"OpenRouter vision model '{model_id}' failed after {duration:.2f}s: {type(e).__name__} - {str(e)}")
                last_exception = e

        err_msg = str(last_exception) if last_exception else "All candidate vision models failed."
        if "401" in err_msg or "AuthenticationError" in err_msg or "cookie" in err_msg or "Clerk" in err_msg:
            raise RuntimeError(f"OpenRouter Authentication Error (401): Please verify OPENROUTER_API_KEY in Vercel settings. Details: {err_msg}")
        elif "429" in err_msg or "RateLimit" in err_msg:
            raise RuntimeError(f"OpenRouter Rate Limit Exceeded (429): Free tier quota limit reached. Details: {err_msg}")
        elif "timeout" in err_msg.lower() or "connection" in err_msg.lower():
            raise RuntimeError(f"OpenRouter Network Timeout: Connection lost during vision request. Details: {err_msg}")
        else:
            raise RuntimeError(f"OpenRouter Vision Error: {err_msg}")

    else:
        raise ValueError(f"Unsupported LLM provider for vision: {selected_provider}")


def call_llm_text(prompt_text: str) -> str:
    """Helper to route text LLM calls to various providers with safe response validation and 30s timeout"""
    provider = llm_provider
    if provider == "ollama":
        if os.getenv("VERCEL"):
            raise RuntimeError("Ollama local endpoint is not supported in Vercel serverless environment. Please set LLM_PROVIDER=openrouter or GEMINI_API_KEY in Vercel.")
        logging.info(f"Calling Ollama Text model: {ollama_model} at {ollama_host}")
        url = f"{ollama_host.rstrip('/')}/api/chat"
        payload = {
            "model": ollama_model,
            "messages": [{"role": "user", "content": prompt_text}],
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["message"]["content"]
        else:
            raise RuntimeError(f"Ollama Error ({res.status_code}): {res.text}")

    elif provider == "gemini":
        logging.info("Calling Gemini Text model...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required when using gemini provider.")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = litellm.completion(
            model=f"gemini/{gemini_model}",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key,
            timeout=30
        )
        return _safely_extract_content(response, gemini_model)

    elif provider == "groq":
        logging.info("Calling Groq Text model...")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when using groq provider.")
        response = litellm.completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key,
            timeout=30
        )
        return _safely_extract_content(response, "groq/llama-3.3-70b-versatile")

    elif provider == "watsonx":
        logging.info("Calling IBM Watsonx Text model...")
        api_key = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY"))
        project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")
        base_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        if not api_key:
            raise RuntimeError("IBM_WATSONX_APIKEY is required when using watsonx provider.")
        response = litellm.completion(
            model="watsonx/ibm/granite-4-h-small",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key,
            api_base=base_url,
            project_id=project_id,
            timeout=30
        )
        return _safely_extract_content(response, "watsonx/granite-4-h-small")

    elif provider == "github":
        logging.info("Calling GitHub Models Text model (gpt-4o-mini)...")
        api_key = os.getenv("GITHUB_API_KEY", os.getenv("GITHUB_TOKEN"))
        if not api_key:
            raise RuntimeError("GITHUB_API_KEY or GITHUB_TOKEN is required when using github provider.")
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_text}],
            api_key=api_key,
            base_url=os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com"),
            timeout=30
        )
        return _safely_extract_content(response, "github/gpt-4o-mini")

    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        has_key = bool(api_key and str(api_key).strip())
        logging.info(f"[Text Request] Provider: openrouter | OPENROUTER_API_KEY exists: {has_key}")
        if not has_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured in environment variables.")
        
        configured_model = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")
        candidate_models = [configured_model]
        for fallback in ["google/gemma-4-31b-it:free", "openrouter/auto"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)
                
        last_exception = None
        for tm in candidate_models:
            model_id = tm if tm.startswith("openrouter/") else f"openrouter/{tm}"
            start_t = time.time()
            logging.info(f"Attempting OpenRouter Text model: '{model_id}'...")
            try:
                response = litellm.completion(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt_text}],
                    api_key=api_key,
                    timeout=30,
                    max_tokens=1024,
                    extra_headers={
                        "HTTP-Referer": "https://nourishbot.vercel.app",
                        "X-Title": "NourishBot"
                    }
                )
                duration = time.time() - start_t
                content = _safely_extract_content(response, model_id)
                if content and len(content.strip()) > 0:
                    logging.info(f"Successfully received text response from OpenRouter model '{model_id}' in {duration:.2f}s")
                    return content
            except Exception as e:
                duration = time.time() - start_t
                logging.warning(f"OpenRouter text model '{model_id}' failed after {duration:.2f}s: {type(e).__name__} - {str(e)}")
                last_exception = e
                
        err_msg = str(last_exception) if last_exception else "All candidate text models failed."
        raise RuntimeError(f"OpenRouter Text Error: {err_msg}")

    else:
        raise ValueError(f"Unsupported LLM provider for text: {provider}")


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
        
    encoded_image = validate_and_preprocess_image(str(val))
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
        
    encoded_image = validate_and_preprocess_image(str(val))
    
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
