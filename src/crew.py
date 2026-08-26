import os
import json
import re
import logging
from src.tools import (
    ExtractIngredientsTool, 
    FilterIngredientsTool, 
    DietaryFilterTool,
    NutrientAnalysisTool,
    call_llm_text
)
from src.models import RecipeSuggestionOutput, NutrientAnalysisOutput 
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

# Try importing crewai; if unavailable or in serverless environment, use native deterministic runner
try:
    from crewai import Agent, Crew, Process, Task, LLM
    from crewai.project import CrewBase, agent, crew, task
    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
    HAS_CREWAI = True
except Exception:
    HAS_CREWAI = False


class CrewOutput:
    def __init__(self, data_dict, raw_text=""):
        self.json_dict = data_dict if isinstance(data_dict, dict) else {}
        self.pydantic = self.json_dict
        self.raw = raw_text or (json.dumps(data_dict) if isinstance(data_dict, dict) else str(data_dict))


class BaseNourishBotCrew:
    def __init__(self, image_data, dietary_restrictions: str = None):
        self.image_data = image_data
        self.dietary_restrictions = dietary_restrictions

    def crew(self):
        return self

    def _parse_json(self, text):
        if not text:
            return {}
        cleaned = str(text).strip()
        
        # Pass 1: Extract content inside markdown ```json ... ``` code fence
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            try:
                res = json.loads(fence_match.group(1).strip())
                if isinstance(res, dict):
                    return res
                if isinstance(res, list):
                    return {"recipes": res}
            except Exception:
                pass

        # Pass 2: Direct JSON parsing
        try:
            res = json.loads(cleaned)
            if isinstance(res, dict):
                return res
            if isinstance(res, list):
                return {"recipes": res}
        except Exception:
            pass

        # Pass 3: Search for explicit JSON dictionary containing "recipes"
        dict_match = re.search(r"(\{[\s\S]*\"recipes\"[\s\S]*\})", cleaned)
        if dict_match:
            try:
                res = json.loads(dict_match.group(1).strip())
                if isinstance(res, dict):
                    return res
            except Exception:
                pass

        # Pass 4: Generic JSON object or array match
        for pattern in [r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"]:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    res = json.loads(match.group(1).strip())
                    if isinstance(res, dict):
                        return res
                    if isinstance(res, list):
                        return {"recipes": res}
                except Exception:
                    pass

        return {"raw": text}


class NourishBotRecipeCrew(BaseNourishBotCrew):
    def kickoff(self, inputs=None):
        inputs = inputs or {}
        image_path = inputs.get('uploaded_image', self.image_data)
        dietary = inputs.get('dietary_restrictions', self.dietary_restrictions)

        logging.info(f"[NourishBotRecipeCrew] Kickoff starting. Image: {image_path}, Dietary: {dietary}")

        # Step 1: Deterministic image ingredient extraction
        raw_ingredients = ExtractIngredientsTool.extract_ingredient(image_input=image_path)

        # Step 2: Filter raw ingredients
        filtered_ingredients = FilterIngredientsTool.filter_ingredients(raw_ingredients=raw_ingredients)

        # Step 3: Filter based on dietary restrictions
        if dietary and str(dietary).strip():
            compliant_ingredients = DietaryFilterTool.filter_based_on_restrictions(
                ingredients=filtered_ingredients, 
                dietary_restrictions=dietary
            )
        else:
            compliant_ingredients = filtered_ingredients

        # Step 4: Recipe suggestion prompt using text LLM
        prompt = f"""
You are an expert chef and nutritionist. Given these available compliant ingredients:
{compliant_ingredients}

And dietary restrictions: {dietary or 'None'}

Suggest 2 to 3 creative, healthy, and delicious recipes. Return a valid JSON response strictly matching the schema below with no Markdown formatting or codeblock wrappers:
{{
  "recipes": [
    {{
      "title": "Recipe Title",
      "ingredients": ["ingredient 1", "ingredient 2"],
      "instructions": "Step 1... Step 2...",
      "calorie_estimate": 450
    }}
  ]
}}
"""
        response_text = call_llm_text(prompt)
        parsed_json = self._parse_json(response_text)
        
        # Normalize recipe output dictionary
        recipes = []
        if isinstance(parsed_json, dict):
            if "recipes" in parsed_json and isinstance(parsed_json["recipes"], list):
                recipes = parsed_json["recipes"]
            elif "recipe_suggestions" in parsed_json and isinstance(parsed_json["recipe_suggestions"], list):
                recipes = parsed_json["recipe_suggestions"]
            elif "title" in parsed_json:
                recipes = [parsed_json]

        if not recipes and response_text and len(str(response_text).strip()) > 0:
            # Construct fallback recipe from text response
            recipes = [{
                "title": "Chef's Recommended Recipe",
                "ingredients": [ing.strip() for ing in str(compliant_ingredients).split(",") if ing.strip()],
                "instructions": str(response_text).strip(),
                "calorie_estimate": "N/A"
            }]

        parsed_json = {"recipes": recipes, "raw": response_text}
        return CrewOutput(data_dict=parsed_json, raw_text=response_text)


class NourishBotAnalysisCrew(BaseNourishBotCrew):
    def kickoff(self, inputs=None):
        inputs = inputs or {}
        image_path = inputs.get('uploaded_image', self.image_data)

        logging.info(f"[NourishBotAnalysisCrew] Kickoff starting. Image: {image_path}")

        # Deterministic Nutrient Analysis call
        response_text = NutrientAnalysisTool.analyze_image(image_input=image_path)
        parsed_json = self._parse_json(response_text)

        return CrewOutput(data_dict=parsed_json, raw_text=response_text)
