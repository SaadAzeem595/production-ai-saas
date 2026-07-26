import os
from dotenv import load_dotenv
load_dotenv()

from src.crew import NourishBotAnalysisCrew

def run_test():
    image_path = "uploaded_image.jpg"
    print("Initializing NourishBotAnalysisCrew with LLM_PROVIDER=github...")
    
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
    
    # Try parsing
    from app import extract_crew_output_dict
    extracted = extract_crew_output_dict(final_output)
    print("\n--- Extracted Dictionary ---")
    print(extracted)

if __name__ == "__main__":
    run_test()
