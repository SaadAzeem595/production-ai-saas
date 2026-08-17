import os
import sys
import unittest
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from src.tools import validate_and_preprocess_image, _safely_extract_content
from src.crew import NourishBotRecipeCrew, NourishBotAnalysisCrew
from ui import extract_crew_output_dict

class TestAIRequestDiagnostics(unittest.TestCase):

    def test_1_image_validation_and_compression(self):
        print("\n--- Test 1: Image Validation & Compression ---")
        image_path = "uploaded_image.jpg"
        self.assertTrue(os.path.exists(image_path), f"Sample image {image_path} missing!")
        
        b64_payload = validate_and_preprocess_image(image_path)
        payload_size_kb = len(b64_payload) / 1024.0
        print(f"Compressed image base64 size: {payload_size_kb:.2f} KB")
        self.assertLess(payload_size_kb, 150.0, "Compressed image payload exceeds size target!")

    def test_2_litellm_null_handling(self):
        print("\n--- Test 2: LiteLLM Null Handling ---")
        with self.assertRaises(RuntimeError) as ctx:
            _safely_extract_content(None, "test-model")
        print(f"Caught expected controlled exception: {ctx.exception}")
        self.assertIn("returned None", str(ctx.exception))

        class MockEmptyChoices:
            choices = []

        with self.assertRaises(RuntimeError) as ctx2:
            _safely_extract_content(MockEmptyChoices(), "test-model")
        print(f"Caught expected controlled exception: {ctx2.exception}")
        self.assertIn("empty 'choices' list", str(ctx2.exception))

    def test_3_e2e_crew_workflows(self):
        print("\n--- Test 3: E2E Crew Workflows ---")
        image_path = "uploaded_image.jpg"
        
        # Test Analysis Crew
        analysis_crew = NourishBotAnalysisCrew(image_data=image_path)
        out_analysis = analysis_crew.kickoff({"uploaded_image": image_path})
        dict_analysis = extract_crew_output_dict(out_analysis)
        print("Analysis Crew Result Dict Keys:", list(dict_analysis.keys()))
        self.assertIsInstance(dict_analysis, dict)

        # Test Recipe Crew
        recipe_crew = NourishBotRecipeCrew(image_data=image_path, dietary_restrictions="vegan")
        out_recipe = recipe_crew.kickoff({"uploaded_image": image_path, "dietary_restrictions": "vegan"})
        dict_recipe = extract_crew_output_dict(out_recipe)
        print("Recipe Crew Result Dict Keys:", list(dict_recipe.keys()))
        self.assertIsInstance(dict_recipe, dict)

if __name__ == "__main__":
    unittest.main()
