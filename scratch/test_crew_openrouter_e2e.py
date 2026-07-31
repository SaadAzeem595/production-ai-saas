import os
from dotenv import load_dotenv
load_dotenv()

from crewai import LLM
# Monkeypatch LLM.supports_function_calling to return False for OpenRouter
_original_supports_function_calling = LLM.supports_function_calling
def _custom_supports_function_calling(self) -> bool:
    model_str = getattr(self, "model", "").lower()
    provider_str = getattr(self, "provider", "").lower()
    if "openrouter" in model_str or provider_str == "openrouter":
        print("[Debug] Disabling function calling for OpenRouter model:", model_str)
        return False
    return _original_supports_function_calling(self)
LLM.supports_function_calling = _custom_supports_function_calling

from src.crew import NourishBotAnalysisCrew
from ui import extract_crew_output_dict

def run_test():
    image_path = "uploaded_image.jpg"
    print("Initializing NourishBotAnalysisCrew with LLM_PROVIDER=openrouter...")
    
    crew_instance = NourishBotAnalysisCrew(
        image_data=image_path
    )
    
    inputs = {
        'uploaded_image': image_path,
        'dietary_restrictions': '',
        'workflow_type': 'analysis'
    }
    
    print("Running crew kickoff...")
    crew_obj = crew_instance.crew()
    final_output = crew_obj.kickoff(inputs=inputs)
    
    print("\n--- Kickoff Raw Output ---")
    print(final_output)
    
    extracted = extract_crew_output_dict(final_output)
    print("\n--- Extracted Dictionary ---")
    print(extracted)

if __name__ == "__main__":
    run_test()
