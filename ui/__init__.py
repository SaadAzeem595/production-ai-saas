import os
import json

UI_DIR = os.path.dirname(os.path.abspath(__file__))

def read_ui_file(filename):
    """
    Helper function to read a UI template file from the ui/ directory.
    """
    path = os.path.join(UI_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def get_css():
    """
    Loads and returns the custom CSS styles.
    """
    return read_ui_file("style.css")

def get_head(clerk_publishable_key, is_clerk_configured):
    """
    Loads and returns the document <head> elements depending on Clerk setup state.
    """
    if not is_clerk_configured:
        return read_ui_file("head_warning.html")
    else:
        head_auth = read_ui_file("head_auth.html")
        return head_auth.replace("%CLERK_PUBLISHABLE_KEY%", clerk_publishable_key)

def get_header_html():
    """
    Loads and returns the HTML layout for the header banner.
    """
    return read_ui_file("header.html")

def get_home_html():
    """
    Loads and returns the HTML layout for the Home dashboard.
    """
    return read_ui_file("home.html")

def get_payment_html():
    """
    Loads and returns the HTML layout for the Payment dashboard.
    """
    return read_ui_file("payment.html")

def get_success_html(credits_to_add):
    """
    Loads and returns the formatted payment-success HTML page layout.
    """
    success_html = read_ui_file("success.html")
    return success_html.replace("{credits_to_add}", str(credits_to_add))


def format_recipe_output(final_output):
    """
    Formats the recipe output into a modern, beautifully styled HTML/Markdown layout.
    """
    output = "<div class='results-container'>\n"
    output += "<h2 class='section-title'>🍽️ Chef Saad's Recommended Recipes</h2>\n\n"
    
    recipes = []
    raw_text_fallback = ""
    
    if isinstance(final_output, dict):
        if "recipes" in final_output and isinstance(final_output["recipes"], list):
            recipes = final_output["recipes"]
        elif "recipe_suggestions" in final_output and isinstance(final_output["recipe_suggestions"], list):
            recipes = final_output["recipe_suggestions"]
        elif "title" in final_output:
            recipes = [final_output]
        
        if not recipes and "raw" in final_output and isinstance(final_output["raw"], str):
            raw_text_fallback = final_output["raw"].strip()
    elif isinstance(final_output, str) and len(final_output.strip()) > 0:
        raw_text_fallback = final_output.strip()

    if recipes:
        for idx, recipe in enumerate(recipes, 1):
            title = recipe.get('title', f'Recipe #{idx}')
            calories = recipe.get('calorie_estimate', 'N/A')
            instructions = str(recipe.get('instructions', '')).replace('\n', '<br>')
            ingredients = recipe.get('ingredients', [])
            if isinstance(ingredients, str):
                ingredients = [i.strip() for i in ingredients.split(",") if i.strip()]
            
            output += f"<div class='recipe-card'>\n"
            output += f"  <div class='recipe-header'>\n"
            output += f"    <h3 class='recipe-name'>{idx}. {title}</h3>\n"
            output += f"    <span class='calorie-badge'>🔥 {calories} kcal</span>\n"
            output += f"  </div>\n"
            
            output += f"  <div class='recipe-body'>\n"
            output += f"    <div class='ingredients-section'>\n"
            output += f"      <strong>🛒 Ingredients:</strong>\n"
            output += f"      <div class='ingredient-chips'>\n"
            for ing in ingredients:
                output += f"        <span class='chip'>{ing}</span>\n"
            output += f"      </div>\n"
            output += f"    </div>\n"
            
            output += f"    <div class='instructions-section'>\n"
            output += f"      <strong>📜 Step-by-Step Instructions:</strong>\n"
            output += f"      <p class='instructions-text'>{instructions}</p>\n"
            output += f"    </div>\n"
            output += f"  </div>\n"
            output += f"</div>\n<br>\n"
    elif isinstance(final_output, dict) and final_output.get("message"):
        output += f"<div class='empty-state'>⚠️ {final_output['message']}</div>"
    elif raw_text_fallback:
        formatted_raw = raw_text_fallback.replace("\n", "<br>")
        output += f"<div class='recipe-card'>\n"
        output += f"  <div class='recipe-header'><h3 class='recipe-name'>🍽️ Chef's Recommendations</h3></div>\n"
        output += f"  <div class='recipe-body'><p class='instructions-text'>{formatted_raw}</p></div>\n"
        output += f"</div><br>\n"
    else:
        output += "<div class='empty-state'>⚠️ No recipes could be generated with the given inputs. Please upload an image with visible food items or groceries.</div>"
    
    output += "</div>"
    return output


def format_analysis_output(final_output):
    """
    Formats nutritional analysis output into styled metric cards and tables.
    """
    output = "<div class='results-container'>\n"
    output += "<h2 class='section-title'>🥗 Nutritional & Macro Audit Report</h2>\n\n"
    
    if isinstance(final_output, str):
        try:
            final_output = json.loads(final_output)
        except Exception:
            pass

    if not isinstance(final_output, dict):
        return f"<div class='empty-state'>{str(final_output)}</div>"

    dish = final_output.get('dish') or 'Analyzed Meal'
    portion = final_output.get('portion_size') or 'Standard Portion'
    est_cal = final_output.get('estimated_calories')
    if est_cal is None:
        est_cal = final_output.get('total_calories') or 'N/A'

    # Check for empty / no food detected state
    dish_str = str(dish).strip().lower()
    if dish_str in ["no food detected", "no food", "none", "empty refrigerator", "empty fridge", "not food"]:
        eval_msg = final_output.get('health_evaluation') or "No food or meal was detected in the uploaded image. The refrigerator appears to be empty."
        output += f"<div class='empty-state' style='padding: 24px; text-align: center;'>\n"
        output += f"  <h3 style='margin-bottom: 8px; color: #f59e0b;'>⚠️ No Food Detected</h3>\n"
        output += f"  <p style='color: var(--text-secondary, #94a3b8); margin: 0;'>{eval_msg}</p>\n"
        output += f"</div>\n"
        output += "</div>"
        return output

    output += f"<div class='summary-banner'>\n"
    output += f"  <div class='summary-item'><span class='summary-label'>🍱 Identified Dish</span><span class='summary-val'>{dish}</span></div>\n"
    output += f"  <div class='summary-item'><span class='summary-label'>📏 Portion Size</span><span class='summary-val'>{portion}</span></div>\n"
    output += f"  <div class='summary-item'><span class='summary-label'>⚡ Total Energy</span><span class='summary-val highlight'>{est_cal} kcal</span></div>\n"
    output += f"</div>\n\n"

    nutrients = final_output.get('nutrients', {})
    if isinstance(nutrients, dict):
        protein = nutrients.get('protein') or 'N/A'
        carbs = nutrients.get('carbohydrates') or 'N/A'
        fats = nutrients.get('fats') or 'N/A'
        vitamins = nutrients.get('vitamins', [])
        minerals = nutrients.get('minerals', [])
    else:
        protein = carbs = fats = 'N/A'
        vitamins = minerals = []
    
    output += "<div class='macro-grid'>\n"
    output += f"  <div class='macro-card protein'><span class='macro-name'>💪 Protein</span><span class='macro-value'>{protein}</span></div>\n"
    output += f"  <div class='macro-card carbs'><span class='macro-name'>🍞 Carbs</span><span class='macro-value'>{carbs}</span></div>\n"
    output += f"  <div class='macro-card fats'><span class='macro-name'>🥑 Fats</span><span class='macro-value'>{fats}</span></div>\n"
    output += "</div>\n\n"

    if vitamins or minerals:
        output += "<div class='micro-section'>\n"
        if vitamins:
            output += "  <div class='micro-col'>\n"
            output += "    <h4>💊 Vitamins</h4>\n"
            output += "    <table class='styled-table'>\n"
            output += "      <thead><tr><th>Vitamin</th><th>% Daily Value</th></tr></thead><tbody>\n"
            for v in vitamins:
                name = v.get('name', 'N/A') if isinstance(v, dict) else str(v)
                dv = v.get('percentage_dv', 'N/A') if isinstance(v, dict) else ''
                output += f"      <tr><td>{name}</td><td>{dv}</td></tr>\n"
            output += "    </tbody></table>\n"
            output += "  </div>\n"
            
        if minerals:
            output += "  <div class='micro-col'>\n"
            output += "    <h4>🧪 Minerals</h4>\n"
            output += "    <table class='styled-table'>\n"
            output += "      <thead><tr><th>Mineral</th><th>Amount</th></tr></thead><tbody>\n"
            for m in minerals:
                name = m.get('name', 'N/A') if isinstance(m, dict) else str(m)
                amount = m.get('amount', 'N/A') if isinstance(m, dict) else ''
                output += f"      <tr><td>{name}</td><td>{amount}</td></tr>\n"
            output += "    </tbody></table>\n"
            output += "  </div>\n"
        output += "</div>\n\n"

    if health_eval := final_output.get('health_evaluation'):
        output += "<div class='health-eval-card'>\n"
        output += "  <h4>💚 Health & Nutritional Evaluation</h4>\n"
        output += f"  <p>{health_eval}</p>\n"
        output += "</div>\n"

    output += "</div>"
    return output


def extract_crew_output_dict(final_output):
    """
    Extracts the actual structured data dictionary from a CrewOutput object or dictionary.
    """
    if hasattr(final_output, "json_dict") and final_output.json_dict:
        return final_output.json_dict
    
    if hasattr(final_output, "pydantic") and final_output.pydantic:
        pyd = final_output.pydantic
        if hasattr(pyd, "model_dump"):
            return pyd.model_dump()
        elif hasattr(pyd, "dict"):
            return pyd.dict()
            
    if hasattr(final_output, "raw") and final_output.raw:
        raw_str = final_output.raw
        try:
            return json.loads(raw_str)
        except Exception:
            pass
 
    if isinstance(final_output, dict):
        if "json_dict" in final_output and final_output["json_dict"]:
            return final_output["json_dict"]
        if "pydantic" in final_output and final_output["pydantic"]:
            pyd = final_output["pydantic"]
            if isinstance(pyd, dict):
                return pyd
            if hasattr(pyd, "model_dump"):
                return pyd.model_dump()
            elif hasattr(pyd, "dict"):
                return pyd.dict()
        if "recipes" in final_output or "dish" in final_output or "nutrients" in final_output:
            return final_output
        if "raw" in final_output and isinstance(final_output["raw"], str):
            try:
                return json.loads(final_output["raw"])
            except Exception:
                pass

    return final_output
