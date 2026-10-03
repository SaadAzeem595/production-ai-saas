import os
import json
import re
import logging
from src.tools import (
    ExtractIngredientsTool, 
    FilterIngredientsTool, 
    DietaryFilterTool,
    NutrientAnalysisTool,
    call_llm_text,
    is_empty_or_refusal_response
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

    def _extract_recipes_from_text(self, text: str, compliant_ingredients=None) -> list:
        """
        Fallback parser to extract multiple individual recipes from raw LLM text or markdown responses.
        Filters out internal chain-of-thought meta-commentary ("We need answer JSON...", etc.).
        """
        if not text:
            return []
        
        cleaned_text = str(text).strip()
        lines = cleaned_text.splitlines()
        filtered_lines = []
        skipping_thoughts = True
        for l in lines:
            l_str = l.strip()
            if skipping_thoughts:
                if re.match(r"^(?:###?\s*|\d+[\.\)]\s*|Recipe\s*\d+:?\s*|[A-Z][a-z]+.*Recipe)", l_str, re.IGNORECASE) and not any(tp in l_str.lower() for tp in ["we need", "let's think", "available compliant", "given these"]):
                    skipping_thoughts = False
                    filtered_lines.append(l)
            else:
                filtered_lines.append(l)

        cleaned_text = "\n".join(filtered_lines if filtered_lines else lines).strip()
        raw_blocks = re.split(r"(?:\r?\n){1,2}(?=(?:###?\s*|\d+[\.\)]\s*|Recipe\s*\d+:?\s*))", cleaned_text, flags=re.IGNORECASE)
        
        recipes = []
        for block in raw_blocks:
            block = block.strip()
            if not block or len(block) < 15:
                continue
            
            block_lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not block_lines:
                continue
            
            first_line = block_lines[0]
            if any(tp in first_line.lower() for tp in ["we need", "let's think", "given these"]):
                continue

            title = re.sub(r"^(?:###?\s*|\d+[\.\)]\s*|Recipe\s*\d+:?\s*)", "", first_line, flags=re.IGNORECASE).strip(' "*#:')
            if not title or len(title) < 3:
                title = f"Recipe #{len(recipes)+1}"

            cal_match = re.search(r"(\d{2,4})\s*(?:kcal|calories|cal)", block, re.IGNORECASE)
            calorie_estimate = int(cal_match.group(1)) if cal_match else "N/A"

            ingredients = []
            ing_match = re.search(r"(?:🛒\s*|Ingredients:\s*)(.*?)(?:📜|Instructions:|Steps:|\n\n|\Z)", block, re.DOTALL | re.IGNORECASE)
            if ing_match:
                raw_ings = ing_match.group(1).strip()
                for line in raw_ings.splitlines():
                    line = re.sub(r"^[•\-\*\d+\.]\s*", "", line).strip()
                    if line and not any(k in line.lower() for k in ["instructions", "calorie"]):
                        ingredients.extend([i.strip(' "*#') for i in line.split(",") if i.strip()])

            if not ingredients and compliant_ingredients:
                if isinstance(compliant_ingredients, list):
                    ingredients = compliant_ingredients
                else:
                    ingredients = [i.strip() for i in str(compliant_ingredients).split(",") if i.strip()]

            inst_match = re.search(r"(?:📜\s*|Instructions:|Steps:\s*)(.*)", block, re.DOTALL | re.IGNORECASE)
            if inst_match:
                instructions = inst_match.group(1).strip()
            else:
                instructions = "\n".join([l for l in block_lines[1:] if not any(k in l.lower() for k in ["ingredients:", "calorie", "recipe"])])

            instructions = re.sub(r"(?:We need answer JSON|Need recipes using|Let's think|Need valid JSON).*", "", instructions, flags=re.DOTALL | re.IGNORECASE).strip()

            recipes.append({
                "title": title,
                "ingredients": ingredients or ["Mixed compliant ingredients"],
                "instructions": instructions or "Prepare and serve fresh.",
                "calorie_estimate": calorie_estimate
            })

        return recipes


class NourishBotRecipeCrew(BaseNourishBotCrew):
    def kickoff(self, inputs=None):
        inputs = inputs or {}
        image_path = inputs.get('uploaded_image', self.image_data)
        dietary = inputs.get('dietary_restrictions', self.dietary_restrictions)

        logging.info(f"[NourishBotRecipeCrew] Kickoff starting. Image: {image_path}, Dietary: {dietary}")

        # Step 1: Deterministic image ingredient extraction
        raw_ingredients = ExtractIngredientsTool.extract_ingredient(image_input=image_path)

        # Step 2: Filter raw ingredients
        if is_empty_or_refusal_response(raw_ingredients):
            logging.info("[NourishBotRecipeCrew] Vision tool flagged empty refrigerator or refusal.")
            empty_payload = {
                "recipes": [],
                "message": "No food ingredients or edible grocery items were detected in the uploaded image. The refrigerator appears to be empty."
            }
            return CrewOutput(data_dict=empty_payload, raw_text=json.dumps(empty_payload))

        filtered_ingredients = FilterIngredientsTool.filter_ingredients(raw_ingredients=raw_ingredients)

        # Handle empty refrigerator or non-food image
        if not filtered_ingredients or not filtered_ingredients.strip() or is_empty_or_refusal_response(filtered_ingredients):
            logging.info("[NourishBotRecipeCrew] No food ingredients detected in image. Refrigerator or space appears empty.")
            empty_payload = {
                "recipes": [],
                "message": "No food ingredients or edible grocery items were detected in the uploaded image. The refrigerator appears to be empty."
            }
            return CrewOutput(data_dict=empty_payload, raw_text=json.dumps(empty_payload))

        # Step 3: Filter based on dietary restrictions
        if dietary and str(dietary).strip():
            compliant_ingredients = DietaryFilterTool.filter_based_on_restrictions(
                ingredients=filtered_ingredients, 
                dietary_restrictions=dietary
            )
        else:
            compliant_ingredients = filtered_ingredients

        if not compliant_ingredients or not compliant_ingredients.strip() or is_empty_or_refusal_response(compliant_ingredients):
            logging.info("[NourishBotRecipeCrew] No ingredients remained after dietary filtering.")
            empty_payload = {
                "recipes": [],
                "message": f"None of the detected ingredients match your dietary restriction ({dietary}). Please try another meal image or adjust your dietary restrictions."
            }
            return CrewOutput(data_dict=empty_payload, raw_text=json.dumps(empty_payload))

        # Step 4: Recipe suggestion prompt using text LLM
        prompt = f"""You are an expert chef and nutritionist.
Given these available ingredients: {compliant_ingredients}
Dietary restrictions: {dietary or 'None'}

CRITICAL INSTRUCTIONS:
- You MUST generate 2 to 3 distinct, delicious recipes using ONLY the available ingredients.
- If the available ingredients list is empty or contains no edible food, output ONLY: {{"recipes": []}}
- Output ONLY a raw, valid JSON object with NO reasoning thoughts, NO chain-of-thought commentary, and NO markdown codeblock wrappers.
- Strictly match the JSON schema below:
{{
  "recipes": [
    {{
      "title": "Creative Recipe Name 1",
      "ingredients": ["ingredient 1", "ingredient 2"],
      "instructions": "Step 1... Step 2...",
      "calorie_estimate": 250
    }},
    {{
      "title": "Creative Recipe Name 2",
      "ingredients": ["ingredient 1", "ingredient 3"],
      "instructions": "Step 1... Step 2...",
      "calorie_estimate": 180
    }}
  ]
}}"""
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
            # Multi-recipe text fallback parser
            recipes = self._extract_recipes_from_text(response_text, compliant_ingredients)

        # Filter out joke / hallucinated empty fridge recipes
        valid_recipes = []
        for r in recipes:
            title = str(r.get("title", "")).lower()
            r_ings = r.get("ingredients", [])
            r_inst = str(r.get("instructions", "")).lower()
            if any(bad in title for bad in ["empty fridge", "clear ice", "cleaning", "consomme", "consommé", "silence", "nothing"]):
                continue
            if any(bad in r_inst for bad in ["empty refrigerator", "atmosphere of possibility", "clean glass shelves", "cleaning supplies"]):
                continue
            if not r_ings or (len(r_ings) == 1 and any(bad in str(r_ings[0]).lower() for bad in ["silence", "empty", "water"])):
                continue
            valid_recipes.append(r)
        recipes = valid_recipes

        if not recipes:
            empty_payload = {
                "recipes": [],
                "message": "No food ingredients or edible grocery items were detected in the uploaded image. The refrigerator appears to be empty."
            }
            return CrewOutput(data_dict=empty_payload, raw_text=json.dumps(empty_payload))

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
