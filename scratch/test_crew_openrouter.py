import os
from dotenv import load_dotenv
from crewai import LLM, Agent, Task, Crew

load_dotenv()

token = os.getenv("OPENROUTER_API_KEY")
print("OPENROUTER_API_KEY present:", bool(token))

try:
    print("Initializing CrewAI LLM for OpenRouter...")
    llm = LLM(
        model="openrouter/google/gemma-4-26b-a4b-it:free",
        api_key=token
    )
    
    agent = Agent(
        role="Test Agent",
        goal="Say hello",
        backstory="A helpful test agent",
        llm=llm
    )
    
    task = Task(
        description="Explain what water is in one short sentence.",
        expected_output="A single sentence explaining water.",
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task]
    )
    
    print("Kicking off crew...")
    result = crew.kickoff()
    print("Result:")
    print(result)
except Exception as e:
    print("Error during CrewAI execution:")
    print(e)
