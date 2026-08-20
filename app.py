import gradio as gr
import base64
import os
import time
import stripe
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from ui import (
    get_css, get_head, get_header_html, get_home_html, get_payment_html, get_success_html,
    format_recipe_output, format_analysis_output, extract_crew_output_dict
)

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# In-memory cache for Stripe payment history API calls to avoid repeated requests during UI polling
_stripe_sessions_cache = {"data": None, "time": 0}

def analyze_food(image, dietary_restrictions, workflow_type, clerk_user_id):
    """
    Main handler for Gradio interface.
    Performs user validation and credit deduction via local JSON database once before executing AI workflow.
    No Stripe network calls are made during this AI workflow.
    """
    import credits_manager
    
    if image is None:
        return "<div class='empty-state'>⚠️ Please upload a food image to analyze.</div>"

    print(f"[analyze_food] Received clerk_user_id: '{clerk_user_id}' (type: {type(clerk_user_id)})")

    if not clerk_user_id or clerk_user_id.strip() == "":
        return "<div class='empty-state'>⚠️ Session authentication error. Please log in again.</div>"

    # Check credit balance ONCE using local database
    balance = credits_manager.get_user_credits(clerk_user_id)
    if balance <= 0:
        return "<div class='empty-state' style='color: #ef4444;'>❌ Out of credits. Please purchase a plan in the billing panel above.</div>"

    # Deduct 1 credit ONCE using local database
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
        # Retrieve pre-loaded crew classes from app.state or lazy-import fallback
        try:
            RecipeCrew = getattr(app.state, "NourishBotRecipeCrew", None)
            AnalysisCrew = getattr(app.state, "NourishBotAnalysisCrew", None)
        except Exception:
            RecipeCrew = AnalysisCrew = None

        if RecipeCrew is None or AnalysisCrew is None:
            from src.crew import NourishBotRecipeCrew as RecipeCrew, NourishBotAnalysisCrew as AnalysisCrew

        if workflow_type == "recipe":
            crew_instance = RecipeCrew(
                image_data=temp_path,
                dietary_restrictions=dietary_restrictions
            )
        elif workflow_type == "analysis":
            crew_instance = AnalysisCrew(
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

# Check if key is not configured
is_clerk_configured = (
    clerk_publishable_key 
    and clerk_publishable_key != "your_clerk_publishable_key_here" 
    and clerk_publishable_key.strip() != ""
)

with gr.Blocks(title="AI Saad • Smart Nutrition Coach") as demo:
    gr.HTML(get_header_html())

    with gr.Tabs():
        with gr.Tab("🏠 Home"):
            gr.HTML(get_home_html())
            
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
            gr.HTML(get_payment_html())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for pre-loading heavy AI models, embeddings,
    and agent crew dependencies during startup without blocking global module import & port binding.
    """
    print("[lifespan] Pre-loading AI models, agent tools, and crews...")
    try:
        from src.crew import NourishBotRecipeCrew, NourishBotAnalysisCrew
        app.state.NourishBotRecipeCrew = NourishBotRecipeCrew
        app.state.NourishBotAnalysisCrew = NourishBotAnalysisCrew
        print("[lifespan] AI models and crews successfully pre-loaded.")
    except Exception as e:
        print(f"[lifespan] Warning: Error pre-loading AI models/crews during startup: {e}")
    yield
    print("[lifespan] Cleaning up application resources...")

# Initialize top-level FastAPI app with lifespan context manager
app = FastAPI(lifespan=lifespan)

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
        # 60-second in-memory cache for Stripe payment history API calls
        now = time.time()
        if _stripe_sessions_cache["data"] is None or (now - _stripe_sessions_cache["time"]) > 60:
            _stripe_sessions_cache["data"] = stripe.checkout.Session.list(limit=50)
            _stripe_sessions_cache["time"] = now
        sessions = _stripe_sessions_cache["data"]
        
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
                return HTMLResponse(content=get_success_html(credits_to_add))
        return HTMLResponse(content="<h3>Payment verification failed or session not paid.</h3>", status_code=400)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Error verifying payment: {str(e)}</h3>", status_code=500)

# Mount Gradio interface onto top-level FastAPI app
app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate"),
    css=get_css(),
    head=get_head(clerk_publishable_key, is_clerk_configured)
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

