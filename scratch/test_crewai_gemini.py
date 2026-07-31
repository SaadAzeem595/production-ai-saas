import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

print("Initializing CrewAI LLM with gemini/gemini-flash-latest...")
try:
    llm = LLM(model="gemini/gemini-flash-latest", api_key=api_key)
    print("CrewAI LLM initialized successfully.")
    # Test generation
    print("Testing call...")
    response = llm.call(messages=[{"role": "user", "content": "Say Hello"}])
    print("Success! Response from CrewAI LLM:")
    print(response)
except Exception as e:
    print("Error calling CrewAI LLM:")
    print(e)
