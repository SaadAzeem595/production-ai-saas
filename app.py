import gradio as gr
import base64
import os
import time
import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from src.crew import NourishBotRecipeCrew, NourishBotAnalysisCrew

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def format_recipe_output(final_output):
    """
    Formats the recipe output into a modern, beautifully styled HTML/Markdown layout.
    """
    output = "<div class='results-container'>\n"
    output += "<h2 class='section-title'>🍽️ Chef Saad's Recommended Recipes</h2>\n\n"
    
    recipes = []
    if isinstance(final_output, dict):
        if "recipes" in final_output:
            recipes = final_output["recipes"]
        else:
            recipe_task_output = final_output.get("recipe_suggestion_task")
            if recipe_task_output and hasattr(recipe_task_output, "json_dict") and recipe_task_output.json_dict:
                recipes = recipe_task_output.json_dict.get("recipes", [])
    
    if recipes:
        for idx, recipe in enumerate(recipes, 1):
            title = recipe.get('title', f'Recipe #{idx}')
            calories = recipe.get('calorie_estimate', 'N/A')
            instructions = recipe.get('instructions', '').replace('\n', '<br>')
            ingredients = recipe.get('ingredients', [])
            
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
    else:
        output += "<div class='empty-state'>⚠️ No recipes could be generated with the given inputs. Please try another image.</div>"
    
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
    est_cal = final_output.get('estimated_calories') or final_output.get('total_calories') or 'N/A'

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


def analyze_food(image, dietary_restrictions, workflow_type, clerk_user_id):
    """
    Main handler for Gradio interface.
    """
    import credits_manager
    
    if image is None:
        return "<div class='empty-state'>⚠️ Please upload a food image to analyze.</div>"

    print(f"[analyze_food] Received clerk_user_id: '{clerk_user_id}' (type: {type(clerk_user_id)})")

    if not clerk_user_id or clerk_user_id.strip() == "":
        return "<div class='empty-state'>⚠️ Session authentication error. Please log in again.</div>"

    # Check credit balance
    balance = credits_manager.get_user_credits(clerk_user_id)
    if balance <= 0:
        return "<div class='empty-state' style='color: #ef4444;'>❌ Out of credits. Please purchase a plan in the billing panel above.</div>"

    # Deduct credit
    success = credits_manager.deduct_credit(clerk_user_id)
    if not success:
        return "<div class='empty-state' style='color: #ef4444;'>❌ Out of credits. Please purchase a plan in the billing panel above.</div>"

    temp_path = "uploaded_image.jpg"
    image.save(temp_path)

    inputs = {
        'uploaded_image': temp_path,
        'dietary_restrictions': dietary_restrictions,
        'workflow_type': workflow_type
    }

    try:
        if workflow_type == "recipe":
            crew_instance = NourishBotRecipeCrew(
                image_data=temp_path,
                dietary_restrictions=dietary_restrictions
            )
        elif workflow_type == "analysis":
            crew_instance = NourishBotAnalysisCrew(
                image_data=temp_path
            )
        else:
            return "<div class='empty-state'>Invalid workflow selection. Choose 'recipe' or 'analysis'.</div>"

        crew_obj = crew_instance.crew()
        final_output = crew_obj.kickoff(inputs=inputs)
        extracted_data = extract_crew_output_dict(final_output)

        if workflow_type == "recipe":
            return format_recipe_output(extracted_data)
        else:
            return format_analysis_output(extracted_data)
            
    except Exception as e:
        return f"<div class='empty-state'>❌ Error processing request: {str(e)}</div>"

# Custom Styling for modern dark glassmorphism theme and Clerk integration
clerk_publishable_key = os.getenv("CLERK_PUBLISHABLE_KEY", "your_clerk_publishable_key_here")

def get_clerk_frontend_api(publishable_key):
    try:
        parts = publishable_key.split('_')
        if len(parts) >= 3:
            encoded_val = parts[2].split('$')[0]
            missing_padding = len(encoded_val) % 4
            if missing_padding:
                encoded_val += '=' * (4 - missing_padding)
            decoded = base64.b64decode(encoded_val).decode('utf-8')
            return decoded
    except Exception as e:
        pass
    return "clerk.accounts.dev"

# Check if key is not configured
is_clerk_configured = (
    clerk_publishable_key 
    and clerk_publishable_key != "your_clerk_publishable_key_here" 
    and clerk_publishable_key.strip() != ""
)

if not is_clerk_configured:
    head = """
    <!-- Styles for Warning Overlay -->
    <style>
    /* Hide the main app container */
    gradio-app, .gradio-container, #app-container {
        display: none !important;
    }
    
    #clerk-auth-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background-color: #0f172a;
        font-family: 'Outfit', sans-serif;
        padding: 20px;
        box-sizing: border-box;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 999999;
        overflow-y: auto;
    }

    .setup-warning-card {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        max-width: 500px;
        width: 100%;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
        font-family: 'Outfit', sans-serif;
        color: #f8fafc;
    }

    .setup-warning-title {
        color: #ef4444;
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }

    .setup-warning-subtitle {
        color: #cbd5e1;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    .setup-steps {
        text-align: left;
        background: #0f172a;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #1e293b;
        margin-bottom: 1.5rem;
    }

    .setup-steps ol {
        margin: 0;
        padding-left: 1.25rem;
        color: #94a3b8;
    }

    .setup-steps li {
        margin-bottom: 0.75rem;
        line-height: 1.5;
    }

    .setup-steps li strong {
        color: #f8fafc;
    }

    .setup-code {
        background: #1e293b;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
        color: #34d399;
    }
    </style>
    <script>
    function showWarning() {
        if (document.getElementById('clerk-auth-container')) return;
        const warningContainer = document.createElement('div');
        warningContainer.id = 'clerk-auth-container';
        warningContainer.innerHTML = `
            <div class="setup-warning-card">
                <div class="setup-warning-title">
                    <span>⚠️</span> Authentication Setup Required
                </div>
                <div class="setup-warning-subtitle">
                    To access the AI Nutrition Coach, you need to configure your Clerk Publishable Key in your local environment.
                </div>
                <div class="setup-steps">
                    <ol>
                        <li>Go to <strong><a href="https://dashboard.clerk.com" target="_blank" style="color: #34d399; text-decoration: underline;">dashboard.clerk.com</a></strong> and create an application.</li>
                        <li>Copy your <strong>Publishable Key</strong> (typically starts with <span class="setup-code">pk_test_</span>).</li>
                        <li>Open the file <span class="setup-code">.env</span> in the project root directory.</li>
                        <li>Set <strong><span class="setup-code">CLERK_PUBLISHABLE_KEY=your_key_here</span></strong>.</li>
                        <li>Restart the backend server to apply the changes.</li>
                    </ol>
                </div>
                <div style="text-align: center; color: #64748b; font-size: 0.85rem;">
                    The app will automatically refresh once configured successfully.
                </div>
            </div>
        `;
        document.body.appendChild(warningContainer);
    }

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', showWarning);
    } else {
        showWarning();
    }
    </script>
    """
else:
    clerk_frontend_api = get_clerk_frontend_api(clerk_publishable_key)
    head = """
    <!-- Clerk SDK CDN -->
    <script src="https://cdn.jsdelivr.net/npm/@clerk/clerk-js@4/dist/clerk.browser.js" data-clerk-publishable-key="%CLERK_PUBLISHABLE_KEY%" crossorigin="anonymous"></script>

    <!-- Styles for Auth/App transitions and Layouts -->
    <style>
    /* Hide the main app container by default until user is authenticated */
    gradio-app, .gradio-container, #app-container {
        display: none !important;
    }

    body.clerk-authenticated gradio-app,
    body.clerk-authenticated .gradio-container,
    body.clerk-authenticated #app-container {
        display: block !important;
    }

    /* Unauthenticated State Styles */
    body.clerk-unauthenticated {
        background-color: #090d16 !important;
        overflow-y: auto !important;
    }

    #landing-page-container {
        display: none;
        min-height: 100vh;
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
        position: relative;
        overflow-x: hidden;
        background-color: #090d16;
    }

    body.clerk-unauthenticated #landing-page-container {
        display: block !important;
    }

    /* Navbar */
    .nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.5rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .nav-logo {
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #10b981, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .nav-links {
        display: flex;
        gap: 2rem;
    }
    .nav-links a {
        color: #94a3b8;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.2s ease;
    }
    .nav-links a:hover {
        color: #34d399;
    }
    .nav-btn {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        padding: 0.5rem 1.25rem;
        border-radius: 9999px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .nav-btn:hover {
        background: rgba(16, 185, 129, 0.2);
        transform: translateY(-1px);
    }

    /* Hero Section */
    .hero-section {
        max-width: 1000px;
        margin: 0 auto;
        padding: 6rem 1.5rem 4rem;
        text-align: center;
        position: relative;
    }
    .hero-bg-glows {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100%;
        height: 100%;
        z-index: 0;
        pointer-events: none;
    }
    .glow {
        position: absolute;
        width: 300px;
        height: 300px;
        border-radius: 50%;
        filter: blur(80px);
        opacity: 0.15;
    }
    .glow-1 {
        background: #10b981;
        top: 20%;
        left: 25%;
    }
    .glow-2 {
        background: #3b82f6;
        bottom: 20%;
        right: 25%;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 1.5rem;
        position: relative;
        z-index: 1;
        letter-spacing: -0.02em;
    }
    .gradient-text {
        background: linear-gradient(90deg, #34d399, #60a5fa, #34d399);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 4s linear infinite;
    }
    .hero-subtitle {
        font-size: 1.25rem;
        color: #94a3b8;
        line-height: 1.6;
        max-width: 750px;
        margin: 0 auto 2.5rem;
        position: relative;
        z-index: 1;
    }
    .hero-ctas {
        display: flex;
        justify-content: center;
        gap: 1rem;
        position: relative;
        z-index: 1;
    }
    .btn-cta-primary {
        background: linear-gradient(135deg, #10b981, #059669);
        border: none;
        color: white;
        padding: 0.875rem 2rem;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
        transition: all 0.2s ease;
    }
    .btn-cta-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6);
    }
    .btn-cta-secondary {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #cbd5e1;
        padding: 0.875rem 2rem;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
    }
    .btn-cta-secondary:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        transform: translateY(-2px);
    }

    /* Features Section */
    .features-section {
        max-width: 1200px;
        margin: 0 auto;
        padding: 4rem 2rem 6rem;
    }
    .features-title {
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 3rem;
        background: linear-gradient(90deg, #f8fafc, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
    }
    .feature-card {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 2.25rem 1.75rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        backdrop-filter: blur(12px);
    }
    .feature-card:hover {
        transform: translateY(-6px);
        background: rgba(30, 41, 59, 0.5);
        border-color: rgba(52, 211, 153, 0.2);
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.05);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1.25rem;
    }
    .feature-card h3 {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        color: #f8fafc;
    }
    .feature-card p {
        color: #94a3b8;
        line-height: 1.5;
        font-size: 0.95rem;
        margin-bottom: 1.25rem;
    }
    .feature-link {
        color: #34d399;
        font-weight: 600;
        font-size: 0.9rem;
        transition: gap 0.2s ease;
    }
    .feature-card:hover .feature-link {
        color: #10b981;
    }

    /* Landing Footer */
    .landing-footer {
        text-align: center;
        padding: 2.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        color: #475569;
        font-size: 0.9rem;
    }

    /* Modal Overlay */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(9, 13, 22, 0.8);
        backdrop-filter: blur(20px);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000000;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s ease;
    }
    .modal-overlay.active {
        opacity: 1;
        pointer-events: auto;
    }
    .modal-card {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 24px;
        padding: 3rem 2rem 2.5rem;
        max-width: 480px;
        width: 100%;
        position: relative;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        transform: scale(0.9);
        transition: transform 0.3s ease;
        text-align: center;
    }
    .modal-overlay.active .modal-card {
        transform: scale(1);
    }
    .modal-close {
        position: absolute;
        top: 1.25rem;
        right: 1.25rem;
        background: none;
        border: none;
        color: #94a3b8;
        font-size: 1.75rem;
        cursor: pointer;
        transition: color 0.2s ease;
        line-height: 1;
    }
    .modal-close:hover {
        color: #f8fafc;
    }
    .modal-logo {
        font-size: 3rem;
        display: block;
        margin-bottom: 1rem;
    }
    .modal-header h3 {
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #f8fafc;
    }
    .modal-header p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    /* Custom Credits Dashboard & Buy Badges Styling */
    .credits-badge {
        background: rgba(16, 185, 129, 0.15) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #34d399 !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
    }
    .credits-count {
        color: #f8fafc !important;
    }
    .buy-btn-group {
        display: inline-flex !important;
        gap: 8px !important;
    }
    .buy-badge {
        padding: 6px 12px !important;
        border-radius: 20px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-decoration: none !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    .buy-badge.pro {
        background: rgba(96, 165, 250, 0.15) !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        color: #60a5fa !important;
    }
    .buy-badge.pro:hover {
        background: rgba(96, 165, 250, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    .buy-badge.team {
        background: rgba(245, 158, 11, 0.15) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        color: #f59e0b !important;
    }
    .buy-badge.team:hover {
        background: rgba(245, 158, 11, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    </style>

    <script>
    function switchGradioTab(tabName) {
        const buttons = document.querySelectorAll('button');
        for (let button of buttons) {
            const isTabButton = button.classList.contains('tab-nav') || 
                                button.closest('.tab-nav') || 
                                (button.parentElement && button.parentElement.classList.contains('tab-nav')) ||
                                button.getAttribute('role') === 'tab';
            if (isTabButton && button.innerText.trim().includes(tabName)) {
                button.click();
                break;
            }
        }
    }

    async function fetchPaymentHistory(userId) {
        try {
            const response = await fetch(`/api/payment-history?user_id=${userId}`);
            const data = await response.json();
            const tableBody = document.getElementById('billing-history-body');
            if (!tableBody) return;
            
            if (!data.history || data.history.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #64748b; padding: 2rem;">No transaction history found.</td></tr>`;
                return;
            }
            
            let html = '';
            for (let tx of data.history) {
                const dateStr = new Date(tx.created * 1000).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                html += `
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
                        <td style="padding: 12px 14px; color: #cbd5e1; font-family: monospace; font-size: 0.85rem;">${tx.id.substring(0, 18)}...</td>
                        <td style="padding: 12px 14px; color: #34d399; font-weight: 600;">+${tx.credits} Credits</td>
                        <td style="padding: 12px 14px; color: #f8fafc;">$${tx.amount.toFixed(2)} ${tx.currency}</td>
                        <td style="padding: 12px 14px; color: #94a3b8;">${dateStr}</td>
                    </tr>
                `;
            }
            tableBody.innerHTML = html;
        } catch (err) {
            console.error("Error fetching payment history:", err);
            const tableBody = document.getElementById('billing-history-body');
            if (tableBody) {
                tableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #ef4444; padding: 2rem;">Error loading billing history.</td></tr>`;
            }
        }
    }

    function openAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    async function initClerk() {
        const publishableKey = "%CLERK_PUBLISHABLE_KEY%";
        
        // Wait for the Clerk class to be available on window
        let checkClerkInterval = setInterval(async () => {
            if (window.Clerk && window.Clerk.load) {
                clearInterval(checkClerkInterval);
                
                try {
                    await window.Clerk.load();
                    const clerk = window.Clerk;
                    
                    if (clerk.user) {
                        // Authenticated
                        document.body.classList.remove('clerk-unauthenticated');
                        document.body.classList.add('clerk-authenticated');
                        
                        // Set welcome user name
                        let welcomeInterval = setInterval(() => {
                            const welcomeNameEl = document.getElementById('welcome-user-name');
                            if (welcomeNameEl) {
                                welcomeNameEl.innerText = clerk.user.firstName || clerk.user.fullName || 'User';
                                clearInterval(welcomeInterval);
                            }
                        }, 100);
                        
                        // Periodically sync Clerk User ID to Gradio hidden input field
                        setInterval(() => {
                            const gradioInput = document.querySelector("#clerk-user-id-field textarea, #clerk-user-id-field input");
                            if (gradioInput) {
                                if (gradioInput.value !== clerk.user.id) {
                                    gradioInput.value = clerk.user.id;
                                    gradioInput.dispatchEvent(new Event('input', { bubbles: true }));
                                    console.log("[Clerk] Synced user ID:", clerk.user.id);
                                }
                            } else {
                                console.warn("[Clerk] #clerk-user-id-field input/textarea element not found in DOM");
                            }
                        }, 1000);
 
                        // Fetch and display user credits balance
                        const fetchCredits = async () => {
                            try {
                                const response = await fetch(`/api/credits?user_id=${clerk.user.id}`);
                                const data = await response.json();
                                
                                // Update header credits count
                                const valEl = document.getElementById('user-credits-val');
                                if (valEl) {
                                    valEl.innerText = data.credits;
                                }
                                
                                // Update dashboard credits count
                                const valEl2 = document.getElementById('payment-credits-val');
                                if (valEl2) {
                                    valEl2.innerText = data.credits;
                                }
                                
                                // Show badge and buy containers
                                const badgeContainer = document.getElementById('credits-badge-container');
                                const buyContainer = document.getElementById('buy-credits-btn-container');
                                if (badgeContainer) badgeContainer.style.display = 'flex';
                                if (buyContainer) buyContainer.style.display = 'flex';
                                
                                // Set Stripe Buy URLs
                                const buyPro = document.getElementById('buy-pro-link');
                                const buyTeam = document.getElementById('buy-team-link');
                                if (buyPro) buyPro.href = `/create-checkout-session?plan=pro&user_id=${clerk.user.id}`;
                                if (buyTeam) buyTeam.href = `/create-checkout-session?plan=team&user_id=${clerk.user.id}`;
                                
                                const dashBuyPro = document.getElementById('dashboard-buy-pro-link');
                                const dashBuyTeam = document.getElementById('dashboard-buy-team-link');
                                if (dashBuyPro) dashBuyPro.href = `/create-checkout-session?plan=pro&user_id=${clerk.user.id}`;
                                if (dashBuyTeam) dashBuyTeam.href = `/create-checkout-session?plan=team&user_id=${clerk.user.id}`;
                            } catch (err) {
                                console.error("Error fetching user credits:", err);
                            }
                        };
                        
                        fetchCredits();
                        // Poll credit balance to catch Stripe payment success callbacks
                        setInterval(fetchCredits, 5000);
                        
                        // Load billing history
                        fetchPaymentHistory(clerk.user.id);
                        setInterval(() => fetchPaymentHistory(clerk.user.id), 10000);
                        
                        // Periodically try to mount the user button in header banner
                        let mountInterval = setInterval(() => {
                            const mountPoint = document.getElementById('clerk-user-button-mount');
                            if (mountPoint) {
                                clearInterval(mountInterval);
                                clerk.mountUserButton(mountPoint, {
                                    appearance: {
                                        variables: {
                                            colorPrimary: '#10b981',
                                            colorBackground: '#1e293b',
                                            colorText: '#f8fafc',
                                            colorTextSecondary: '#94a3b8',
                                            colorInputBackground: '#0f172a',
                                            colorInputText: '#f8fafc',
                                            colorBorder: '#334155',
                                            borderRadius: '12px'
                                        },
                                        elements: {
                                            avatarBox: "w-8 h-8 rounded-full border border-emerald-500/50 hover:scale-105 transition-transform",
                                            userButtonPopoverCard: "bg-slate-800 border border-slate-700/50 shadow-2xl",
                                            userButtonPopoverActionButton: "hover:bg-slate-700/50 text-slate-200",
                                            userButtonPopoverActionButtonText: "text-slate-200",
                                            userButtonPopoverActionButtonIcon: "text-slate-400",
                                            userButtonPopoverFooter: "bg-slate-900/50 border-t border-slate-700/50",
                                            userPreviewSecondaryIdentifier: "text-slate-400",
                                            userPreviewMainIdentifier: "text-slate-100 font-semibold"
                                        }
                                    }
                                });
                            }
                        }, 100);
                    } else {
                        // Unauthenticated
                        document.body.classList.remove('clerk-authenticated');
                        document.body.classList.add('clerk-unauthenticated');
                        
                        if (document.getElementById('landing-page-container')) return;
                        
                        // Create unauthenticated screen structure
                        const landingContainer = document.createElement('div');
                        landingContainer.id = 'landing-page-container';
                        landingContainer.innerHTML = `
                            <nav class="nav-bar">
                                <div class="nav-logo">🥗 AI Saad</div>
                                <div class="nav-links">
                                    <a href="#features">Features</a>
                                    <a href="#pricing">Pricing</a>
                                </div>
                                <button class="nav-btn" onclick="openAuthModal()">Sign In</button>
                            </nav>
                            
                            <header class="hero-section">
                                <div class="hero-bg-glows">
                                    <div class="glow glow-1"></div>
                                    <div class="glow glow-2"></div>
                                </div>
                                <h1 class="hero-title">Your Personal AI<br><span class="gradient-text">Smart Nutrition Coach</span></h1>
                                <p class="hero-subtitle">Upload meal or fridge photos for instant ingredient recognition, comprehensive macro audits, and custom chef-designed recipes tailored to your dietary needs.</p>
                                <div class="hero-ctas">
                                    <button class="btn-cta-primary" onclick="openAuthModal()">Start Free Audit ⚡</button>
                                    <a href="#features" class="btn-cta-secondary">Explore Features</a>
                                </div>
                            </header>

                            <section id="features" class="features-section">
                                <h2 class="features-title">Core Capabilities</h2>
                                <div class="features-grid">
                                    <div class="feature-card" onclick="openAuthModal()">
                                        <div class="feature-icon">📸</div>
                                        <h3>Visual Meal Analysis</h3>
                                        <p>Detect food items and ingredients directly from photos using state-of-the-art vision models.</p>
                                        <span class="feature-link">Try it now &rarr;</span>
                                    </div>
                                    <div class="feature-card" onclick="openAuthModal()">
                                        <div class="feature-icon">📊</div>
                                        <h3>Macro & Micronutrient Audits</h3>
                                        <p>Analyze protein, fat, carbohydrates, vitamins, and minerals with detailed daily value estimates.</p>
                                        <span class="feature-link">Audit macros &rarr;</span>
                                    </div>
                                    <div class="feature-card" onclick="openAuthModal()">
                                        <div class="feature-icon">🍽️</div>
                                        <h3>Dietary-Filtered Recipes</h3>
                                        <p>Generate recipes instantly matching your exact dietary preferences (keto, vegan, low-carb, etc.).</p>
                                        <span class="feature-link">Get recipes &rarr;</span>
                                    </div>
                                    <div class="feature-card" onclick="openAuthModal()">
                                        <div class="feature-icon">🧠</div>
                                        <h3>Multi-Agent AI Reasoning</h3>
                                        <p>Powered by collaborative CrewAI agents orchestrating advanced data retrieval and synthesis.</p>
                                        <span class="feature-link">How it works &rarr;</span>
                                    </div>
                                </div>
                            </section>

                            <section id="pricing" class="features-section" style="border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 5rem;">
                                <h2 class="features-title">Simple, Flexible Pricing</h2>
                                <div class="features-grid" style="max-width: 900px; margin: 0 auto;">
                                    <div class="feature-card" onclick="openAuthModal()" style="text-align: center; border-color: rgba(16, 185, 129, 0.1);">
                                        <div class="feature-icon">🌱</div>
                                        <h3>Free Trial</h3>
                                        <p style="font-size: 2.25rem; font-weight: 800; color: #f8fafc; margin: 1rem 0;">$0</p>
                                        <p>Get started with <strong>1 free credit</strong> to test the AI meal recipe generator or macro audit.</p>
                                        <span class="feature-link" style="display: block; margin-top: 1.5rem;">Sign Up Free &rarr;</span>
                                    </div>
                                    <div class="feature-card" onclick="openAuthModal()" style="text-align: center; border-color: rgba(96, 165, 250, 0.3); background: rgba(30, 41, 59, 0.5);">
                                        <div class="feature-icon">🔥</div>
                                        <h3>Pro Plan</h3>
                                        <p style="font-size: 2.25rem; font-weight: 800; color: #60a5fa; margin: 1rem 0;">$5</p>
                                        <p>Purchase <strong>5 credits</strong> to analyze more dishes, unlock deeper nutrient analytics, and recipe ideas.</p>
                                        <span class="feature-link" style="display: block; margin-top: 1.5rem; color: #60a5fa;">Get Pro &rarr;</span>
                                    </div>
                                    <div class="feature-card" onclick="openAuthModal()" style="text-align: center; border-color: rgba(245, 158, 11, 0.2);">
                                        <div class="feature-icon">🚀</div>
                                        <h3>Team Plan</h3>
                                        <p style="font-size: 2.25rem; font-weight: 800; color: #f59e0b; margin: 1rem 0;">$20</p>
                                        <p>Best value. Receive <strong>25 credits</strong> for comprehensive recipe iteration and kitchen audits.</p>
                                        <span class="feature-link" style="display: block; margin-top: 1.5rem; color: #f59e0b;">Get Team &rarr;</span>
                                    </div>
                                </div>
                            </section>

                            <footer class="landing-footer">
                                <p>&copy; 2026 AI Saad Smart Nutrition Coach. All rights reserved.</p>
                            </footer>

                            <div id="auth-modal" class="modal-overlay">
                                <div class="modal-card">
                                    <button class="modal-close" onclick="closeAuthModal()">&times;</button>
                                    <div class="modal-header">
                                        <span class="modal-logo">🥗</span>
                                        <h3>Join AI Saad</h3>
                                        <p>Sign in or register to analyze your meals and recipes.</p>
                                    </div>
                                    <div id="clerk-sign-in-mount"></div>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(landingContainer);
                        
                        // Mount Clerk SignIn
                        clerk.mountSignIn(document.getElementById('clerk-sign-in-mount'), {
                            appearance: {
                                variables: {
                                    colorPrimary: '#10b981',
                                    colorBackground: '#1e293b',
                                    colorText: '#f8fafc',
                                    colorTextSecondary: '#94a3b8',
                                    colorInputBackground: '#0f172a',
                                    colorInputText: '#f8fafc',
                                    colorBorder: '#334155',
                                    borderRadius: '12px'
                                },
                                elements: {
                                    card: "bg-slate-800 border border-slate-700/50 shadow-2xl mx-auto",
                                    headerTitle: "text-slate-100 font-semibold",
                                    headerSubtitle: "text-slate-400",
                                    socialButtonsIconButton: "bg-slate-900 border border-slate-700 text-slate-100 hover:bg-slate-800",
                                    formButtonPrimary: "bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-md shadow-emerald-600/30",
                                    footerActionLink: "text-emerald-400 hover:text-emerald-300",
                                    dividerLine: "bg-slate-700",
                                    dividerText: "text-slate-400",
                                    formFieldLabel: "text-slate-300",
                                    formFieldInput: "bg-slate-900 border border-slate-700 text-slate-100 focus:border-emerald-500",
                                    identityPreviewText: "text-slate-300",
                                    identityPreviewEditButtonIcon: "text-emerald-400"
                                }
                            }
                        });
                    }
                } catch (err) {
                    console.error("Clerk load error:", err);
                    document.body.classList.remove('clerk-authenticated');
                    document.body.classList.add('clerk-unauthenticated');
                }
            }
        }, 100);
    }

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', initClerk);
    } else {
        initClerk();
    }
    </script>
    """.replace("%CLERK_PUBLISHABLE_KEY%", clerk_publishable_key)


css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

body, .gradio-container {
    font-family: 'Outfit', sans-serif !important;
    background-color: #0f172a !important;
    color: #f8fafc !important;
}

#clerk-user-id-field, .hidden-textbox {
    display: none !important;
}

.header-banner {
    text-align: center;
    padding: 2.5rem 1rem 1.8rem;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(59, 130, 246, 0.12));
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 2rem;
    backdrop-filter: blur(16px);
    position: relative;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
}

.header-auth-row {
    position: absolute;
    top: 1.25rem;
    right: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    z-index: 100;
}

#clerk-user-button-mount {
    min-width: 28px;
    min-height: 28px;
}

.header-title {
    font-size: 2.6rem !important;
    font-weight: 700 !important;
    background: linear-gradient(90deg, #10b981, #60a5fa, #34d399);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.75rem !important;
    animation: shine 4s linear infinite;
}

@keyframes shine {
    to { background-position: 200% center; }
}

.header-subtitle {
    font-size: 1.1rem;
    color: #94a3b8;
    max-width: 680px;
    margin: 0 auto;
    line-height: 1.6;
}

.btn-primary {
    background: linear-gradient(135deg, #059669, #10b981) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 22px rgba(16, 185, 129, 0.5) !important;
}

.btn-primary:active {
    transform: translateY(1px);
}

/* Custom Card Layout */
.results-container {
    padding: 0.5rem;
}

.section-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #34d399;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.summary-banner {
    display: flex;
    justify-content: space-around;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(8px);
}

.summary-item {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.summary-label {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.summary-val {
    font-size: 1.3rem;
    font-weight: 600;
    color: #f8fafc;
}

.summary-val.highlight {
    color: #f59e0b;
    text-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
}

.macro-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.macro-card {
    background: rgba(30, 41, 59, 0.6);
    border-radius: 16px;
    padding: 1.25rem;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(8px);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.macro-card:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.15);
}

.macro-card.protein { border-top: 4px solid #ef4444; }
.macro-card.carbs { border-top: 4px solid #3b82f6; }
.macro-card.fats { border-top: 4px solid #10b981; }

.macro-name {
    display: block;
    font-size: 0.9rem;
    color: #94a3b8;
    margin-bottom: 6px;
    font-weight: 500;
}

.macro-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f8fafc;
}

.recipe-card {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(8px);
    transition: all 0.3s ease;
}

.recipe-card:hover {
    border-color: rgba(56, 189, 248, 0.3);
    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.05);
}

.recipe-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 0.75rem;
}

.recipe-name {
    font-size: 1.4rem;
    color: #38bdf8;
    margin: 0;
    font-weight: 600;
}

.calorie-badge {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
}

.ingredient-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 1.25rem;
}

.chip {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    transition: all 0.2s ease;
}

.chip:hover {
    background: rgba(15, 23, 42, 0.9);
    border-color: rgba(52, 211, 153, 0.3);
    color: #34d399;
}

.instructions-text {
    color: #cbd5e1;
    line-height: 1.7;
    margin-top: 8px;
    font-size: 0.95rem;
}

.styled-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    background: rgba(15, 23, 42, 0.3);
    border-radius: 10px;
    overflow: hidden;
}

.styled-table th, .styled-table td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.styled-table th {
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(15, 23, 42, 0.5);
}

.styled-table tbody tr:last-child td {
    border-bottom: none;
}

.styled-table tbody tr:hover td {
    background: rgba(255, 255, 255, 0.02);
}

.health-eval-card {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1.5rem;
}

.health-eval-card h4 {
    color: #34d399;
    margin: 0 0 10px 0;
    font-size: 1.15rem;
    font-weight: 600;
}

.health-eval-card p {
    line-height: 1.6;
    color: #cbd5e1;
    margin: 0;
}

.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #64748b;
    font-size: 1.15rem;
}

/* Home & Payment Dashboard Styles */
.welcome-section {
    padding: 2.25rem 2rem;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(59, 130, 246, 0.08));
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px;
    margin-bottom: 2rem;
    backdrop-filter: blur(12px);
    text-align: left;
}

.welcome-title {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.5rem 0 !important;
    background: linear-gradient(90deg, #34d399, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.welcome-text {
    font-size: 1.1rem;
    color: #94a3b8;
    line-height: 1.6;
    margin: 0;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2.5rem;
}

.dashboard-card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px;
    padding: 2rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(12px);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    text-align: left;
}

.dashboard-card:hover {
    transform: translateY(-5px);
    border-color: rgba(52, 211, 153, 0.25);
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.05);
}

.card-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.card-title {
    font-size: 1.4rem;
    font-weight: 600;
    margin-top: 0;
    margin-bottom: 0.75rem;
    color: #f8fafc;
}

.card-description {
    color: #cbd5e1;
    font-size: 0.95rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

.card-action-btn {
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    color: white;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.75rem 1.5rem;
    border-radius: 10px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    transition: all 0.2s ease;
    text-align: center;
    width: fit-content;
    text-decoration: none;
}

.card-action-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.guide-section {
    background: rgba(30, 41, 59, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 2.5rem;
    text-align: left;
}

.guide-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #34d399;
    margin-top: 0;
    margin-bottom: 1.5rem;
}

.guide-steps {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.5rem;
}

.guide-step {
    position: relative;
    padding-left: 2.5rem;
}

.step-num {
    position: absolute;
    left: 0;
    top: 0;
    width: 1.8rem;
    height: 1.8rem;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 50%;
    color: #34d399;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
}

.step-title {
    font-weight: 600;
    font-size: 1.05rem;
    margin-top: 0;
    margin-bottom: 0.5rem;
    color: #f8fafc;
}

.step-desc {
    color: #94a3b8;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0;
}

/* Payment Dashboard Custom Layout */
.payment-balance-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.8));
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 2.5rem;
    text-align: center;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.balance-title {
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94a3b8;
    margin-bottom: 0.5rem;
}

.balance-value {
    font-size: 3rem;
    font-weight: 800;
    color: #10b981;
    text-shadow: 0 0 20px rgba(16, 185, 129, 0.25);
}

.balance-text {
    font-size: 1rem;
    color: #cbd5e1;
    margin-top: 0.5rem;
}

.plans-title {
    font-size: 1.6rem;
    font-weight: 700;
    text-align: center;
    color: #f8fafc;
    margin-top: 0;
    margin-bottom: 2rem;
}

.plans-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    max-width: 800px;
    margin: 0 auto 3rem;
}

.plan-card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.plan-card:hover {
    transform: translateY(-4px);
    border-color: rgba(59, 130, 246, 0.2);
}

.plan-card.popular {
    border: 1px solid rgba(16, 185, 129, 0.25);
    background: rgba(30, 41, 59, 0.6);
    position: relative;
}

.plan-badge {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: #10b981;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 12px;
    letter-spacing: 0.05em;
}

.plan-icon {
    font-size: 2.2rem;
    margin-bottom: 0.75rem;
}

.plan-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #f8fafc;
    margin-bottom: 0.5rem;
}

.plan-price {
    font-size: 2.5rem;
    font-weight: 800;
    margin: 1rem 0;
    color: #f8fafc;
}

.plan-features {
    list-style: none;
    padding: 0;
    margin: 0 0 1.5rem 0;
    color: #cbd5e1;
    font-size: 0.95rem;
    text-align: left;
}

.plan-features li {
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.plan-btn {
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    color: white;
    font-weight: 600;
    font-size: 1rem;
    padding: 0.85rem 1.5rem;
    border-radius: 12px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    transition: all 0.2s ease;
    text-decoration: none;
    display: block;
}

.plan-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.plan-btn.blue {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.plan-btn.blue:hover {
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.history-section {
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 2.5rem;
    text-align: left;
}

.history-title {
    font-size: 1.4rem;
    font-weight: 600;
    color: #cbd5e1;
    margin-top: 0;
    margin-bottom: 1.5rem;
}

/* Custom Gradio Tabs Override */
.tabs {
    border: none !important;
}

.tab-nav {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    gap: 8px !important;
    margin-bottom: 1.5rem !important;
    background: none !important;
    padding: 0 !important;
}

.tab-nav button {
    border: none !important;
    background: none !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    font-size: 1.05rem !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    transition: all 0.2s ease !important;
}

.tab-nav button:hover {
    color: #cbd5e1 !important;
}

.tab-nav button.selected {
    color: #34d399 !important;
    border-bottom: 2px solid #34d399 !important;
}
"""

with gr.Blocks(title="AI Saad • Smart Nutrition Coach") as demo:
    gr.HTML("""
    <div class="header-banner">
        <div class="header-auth-row" style="display: flex; align-items: center; gap: 15px;">
            <div id="credits-badge-container" class="credits-badge" style="display: none;">
                <span class="credits-label">Credits:</span>
                <span id="user-credits-val" class="credits-count">...</span>
            </div>
            <div id="buy-credits-btn-container" class="buy-btn-group" style="display: none;">
                <a id="buy-pro-link" href="#" target="_blank" class="buy-badge pro">Get Pro (5 credits)</a>
                <a id="buy-team-link" href="#" target="_blank" class="buy-badge team">Get Team (25 credits)</a>
            </div>
            <div id="clerk-user-button-mount"></div>
        </div>
        <h1 class="header-title" style="cursor: pointer;" onclick="switchGradioTab('Home')">🥗 AI Saad • Smart Nutrition Coach</h1>
        <p class="header-subtitle">Powered by Multi-Agent AI (CrewAI + IBM Watsonx). Upload a meal or fridge photo to receive instant recipe suggestions, macro breakdowns, and personalized dietary guidance.</p>
    </div>
    """)

    with gr.Tabs():
        with gr.Tab("🏠 Home"):
            gr.HTML("""
            <div class="welcome-section">
                <h2 class="welcome-title">Welcome back, <span id="welcome-user-name">...</span>! 🥗</h2>
                <p class="welcome-text">Explore smart nutrition tools, audit your daily meal logs, and generate chef-crafted recipes instantly.</p>
            </div>
            
            <div class="dashboard-grid">
                <div class="dashboard-card">
                    <div>
                        <div class="card-icon">🥗</div>
                        <h3 class="card-title">Nutrition Coach</h3>
                        <p class="card-description">Upload food photos to identify ingredients, perform detailed calorie and macro audits, and suggest customized recipes.</p>
                    </div>
                    <button class="card-action-btn" onclick="switchGradioTab('Nutrition Coach')">Start Analysis &rarr;</button>
                </div>
                
                <div class="dashboard-card">
                    <div>
                        <div class="card-icon">💳</div>
                        <h3 class="card-title">Payment & Credits</h3>
                        <p class="card-description">Top up your balance, view active subscription plans, and inspect your full transaction history logs.</p>
                    </div>
                    <button class="card-action-btn" onclick="switchGradioTab('Payment Dashboard')">Manage Payments &rarr;</button>
                </div>
            </div>
            
            <div class="guide-section">
                <h3 class="guide-title">🚀 How it Works</h3>
                <div class="guide-steps">
                    <div class="guide-step">
                        <div class="step-num">1</div>
                        <h4 class="step-title">Upload Photo</h4>
                        <p class="step-desc">Provide a clear photo of your cooked meal or ingredients in your fridge.</p>
                    </div>
                    <div class="guide-step">
                        <div class="step-num">2</div>
                        <h4 class="step-title">Specify Rules</h4>
                        <p class="step-desc">Enter any dietary preferences or constraints (e.g. keto, gluten-free).</p>
                    </div>
                    <div class="guide-step">
                        <div class="step-num">3</div>
                        <h4 class="step-title">Audit macros</h4>
                        <p class="step-desc">Let the collaborative AI agents recognize ingredients and audit nutritional statistics.</p>
                    </div>
                </div>
            </div>
            """)
            
        with gr.Tab("🥗 Nutrition Coach"):
            with gr.Row():
                with gr.Column(scale=5):
                    gr.Markdown("### 📸 Upload Meal or Fridge Photo")
                    image_input = gr.Image(type="pil", label="Drop food image here", height=320)
                    
                    gr.Markdown("### ⚙️ Analysis Preferences")
                    dietary_input = gr.Textbox(
                        label="Dietary Restrictions (Optional)",
                        placeholder="e.g. vegan, keto, gluten-free, low-carb",
                        info="Type dietary rules to filter recipe ingredients"
                    )
                    
                    workflow_radio = gr.Radio(
                        choices=[
                            ("🍽️ Recipe Recommendations", "recipe"),
                            ("📊 Nutrient & Macro Audit", "analysis")
                        ],
                        value="recipe",
                        label="Choose Workflow Type"
                    )
                    
                    clerk_user_id_input = gr.Textbox(visible=True, elem_id="clerk-user-id-field", elem_classes=["hidden-textbox"])
                    submit_btn = gr.Button("⚡ Analyze with AI Saad", variant="primary", elem_classes=["btn-primary"])

                    gr.Markdown("### 🧪 Try an Example Image")
                    gr.Examples(
                        examples=[
                            ["examples/food-1.jpg", "vegan", "recipe"],
                            ["examples/food-2.jpg", "", "analysis"],
                            ["examples/food-3.jpg", "keto", "recipe"],
                            ["examples/food-4.jpg", "", "analysis"],
                        ],
                        inputs=[image_input, dietary_input, workflow_radio],
                        label="Click an example below to auto-fill inputs:"
                    )

                with gr.Column(scale=7):
                    gr.Markdown("### 📈 Live AI Saad Insights")
                    result_display = gr.HTML(
                        value="<div class='empty-state'>👈 Upload an image on the left and click <b>Analyze with AI Saad</b> to see results here.</div>",
                        label="Results"
                    )
                    
            submit_btn.click(
                fn=analyze_food,
                inputs=[image_input, dietary_input, workflow_radio, clerk_user_id_input],
                outputs=result_display
            )
            
        with gr.Tab("💳 Payment Dashboard"):
            gr.HTML("""
            <div class="payment-balance-card">
                <div class="balance-title">Active Credits</div>
                <div class="balance-value"><span id="payment-credits-val">...</span></div>
                <div class="balance-text">credits available for deep-agent nutritional audits</div>
            </div>
            
            <h2 class="plans-title">Top Up Your Credits</h2>
            <div class="plans-grid">
                <div class="plan-card">
                    <div>
                        <div class="plan-icon">🌱</div>
                        <h3 class="plan-name">Pro Plan</h3>
                        <div class="plan-price">$5.00</div>
                        <ul class="plan-features">
                            <li><span>✅</span> 5 Food Analysis Credits</li>
                            <li><span>✅</span> Macro/Micronutrient Audits</li>
                            <li><span>✅</span> Chef Recipe Suggestions</li>
                            <li><span>✅</span> 100% Secure Checkout</li>
                        </ul>
                    </div>
                    <a id="dashboard-buy-pro-link" href="#" target="_blank" class="plan-btn">Buy Pro Plan ⚡</a>
                </div>
                
                <div class="plan-card popular">
                    <div class="plan-badge">Best Value</div>
                    <div>
                        <div class="plan-icon">🚀</div>
                        <h3 class="plan-name">Team Plan</h3>
                        <div class="plan-price">$20.00</div>
                        <ul class="plan-features">
                            <li><span>✅</span> 25 Food Analysis Credits</li>
                            <li><span>✅</span> Macro/Micronutrient Audits</li>
                            <li><span>✅</span> Chef Recipe Suggestions</li>
                            <li><span>✅</span> Shared family kitchen logs</li>
                        </ul>
                    </div>
                    <a id="dashboard-buy-team-link" href="#" target="_blank" class="plan-btn blue">Buy Team Plan 🚀</a>
                </div>
            </div>
            
            <div class="history-section">
                <h3 class="history-title">💳 Billing & Transaction Logs</h3>
                <table class="styled-table" style="width: 100%; border-collapse: collapse; background: rgba(15, 23, 42, 0.3); border-radius: 10px; overflow: hidden;">
                    <thead>
                        <tr style="background: rgba(15, 23, 42, 0.5);">
                            <th style="padding: 12px 14px; text-align: left; color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Session ID</th>
                            <th style="padding: 12px 14px; text-align: left; color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Credits Added</th>
                            <th style="padding: 12px 14px; text-align: left; color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Amount Paid</th>
                            <th style="padding: 12px 14px; text-align: left; color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Date</th>
                        </tr>
                    </thead>
                    <tbody id="billing-history-body">
                        <tr>
                            <td colspan="4" style="text-align: center; color: #64748b; padding: 2rem;">Loading transaction details...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Launch Gradio with prevent_thread_lock=True to build and run the FastAPI app
    demo.launch(
        server_name=host,
        server_port=port,
        prevent_thread_lock=True,
        theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate"),
        css=css,
        head=head
    )
    
    # Now that the server is built and running, register our dynamic FastAPI endpoints on it!
    app = demo.app
    
    @app.get("/api/credits")
    async def api_get_credits(user_id: str):
        import credits_manager
        if not user_id:
            return JSONResponse(status_code=400, content={"error": "Missing user_id"})
        credits = credits_manager.get_user_credits(user_id)
        return {"credits": credits}

    @app.get("/api/payment-history")
    async def api_payment_history(user_id: str):
        if not user_id:
            return JSONResponse(status_code=400, content={"error": "Missing user_id"})
        try:
            sessions = stripe.checkout.Session.list(limit=50)
            user_sessions = []
            for s in sessions.data:
                metadata = s.metadata.to_dict() if s.metadata else {}
                if metadata.get("user_id") == user_id and s.payment_status == "paid":
                    user_sessions.append({
                        "id": s.id,
                        "amount": s.amount_total / 100.0,
                        "currency": s.currency.upper(),
                        "status": s.status,
                        "created": s.created,
                        "credits": metadata.get("credits", "0")
                    })
            return {"history": user_sessions}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/create-checkout-session")
    async def create_checkout_session(plan: str, user_id: str, request: Request):
        if not user_id or plan not in ["pro", "team"]:
            return JSONResponse(status_code=400, content={"error": "Invalid plan or user_id"})
        try:
            base_url = str(request.base_url).rstrip('/')
            success_url = f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{base_url}/"
            
            amount = 500 if plan == "pro" else 2000
            credits_count = 5 if plan == "pro" else 25
            name = "AI Saad Pro Plan - 5 Credits" if plan == "pro" else "AI Saad Team Plan - 25 Credits"
            desc = "5 food analysis credits" if plan == "pro" else "25 food analysis credits"
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': name,
                            'description': desc,
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'plan': plan,
                    'credits': credits_count
                }
            )
            return RedirectResponse(url=session.url)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/payment-success")
    async def payment_success(session_id: str):
        import credits_manager
        if not session_id:
            return HTMLResponse(content="<h3>Error: Missing Session ID</h3>", status_code=400)
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                metadata = session.metadata.to_dict() if session.metadata else {}
                user_id = metadata.get("user_id")
                plan = metadata.get("plan")
                credits_to_add = int(metadata.get("credits", 0))
                customer_email = session.customer_details.email if session.customer_details else None
                
                if user_id and credits_to_add > 0:
                    credits_manager.add_credits_for_session(user_id, session_id, credits_to_add, customer_email)
                    
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Payment Successful</title>
                        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
                        <style>
                            body {{
                                background-color: #090d16;
                                color: #f8fafc;
                                font-family: 'Outfit', sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                            }}
                            .card {{
                                background: rgba(30, 41, 59, 0.7);
                                border: 1px solid rgba(16, 185, 129, 0.3);
                                padding: 3rem 2rem;
                                border-radius: 24px;
                                text-align: center;
                                max-width: 450px;
                                box-shadow: 0 10px 30px rgba(16, 185, 129, 0.1);
                                backdrop-filter: blur(16px);
                            }}
                            .icon {{
                                font-size: 4rem;
                                color: #10b981;
                                margin-bottom: 1.5rem;
                            }}
                            h1 {{
                                font-size: 2rem;
                                margin-bottom: 0.5rem;
                                background: linear-gradient(90deg, #34d399, #60a5fa);
                                -webkit-background-clip: text;
                                -webkit-text-fill-color: transparent;
                            }}
                            p {{
                                color: #94a3b8;
                                margin-bottom: 2rem;
                                line-height: 1.5;
                            }}
                            .btn {{
                                background: linear-gradient(135deg, #10b981, #059669);
                                color: white;
                                padding: 0.8rem 2rem;
                                border-radius: 12px;
                                text-decoration: none;
                                font-weight: 600;
                                box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
                                display: inline-block;
                            }}
                        </style>
                        <script>
                            setTimeout(() => {{
                                window.location.href = "/";
                            }}, 4000);
                        </script>
                    </head>
                    <body>
                        <div class="card">
                            <div class="icon">✨</div>
                            <h1>Payment Successful!</h1>
                            <p>Thank you for your purchase. We have successfully credited <strong>{credits_to_add} credits</strong> to your account.<br><br>Redirecting you back to the app in 4 seconds...</p>
                            <a href="/" class="btn">Go to Dashboard</a>
                        </div>
                    </body>
                    </html>
                    """
                    return HTMLResponse(content=html_content)
            return HTMLResponse(content="<h3>Payment verification failed or session not paid.</h3>", status_code=400)
        except Exception as e:
            return HTMLResponse(content=f"<h3>Error verifying payment: {str(e)}</h3>", status_code=500)

    # Keep the main thread blocked and running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        demo.close()
