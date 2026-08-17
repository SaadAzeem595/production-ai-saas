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
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned)
            cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
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
        
        # Ensure 'recipes' key exists
        if "recipes" not in parsed_json or not isinstance(parsed_json["recipes"], list):
            parsed_json = {"recipes": [], "raw": response_text}

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
