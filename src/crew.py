import os
import yaml
import base64
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from src.tools import (
    ExtractIngredientsTool, 
    FilterIngredientsTool, 
    DietaryFilterTool,
    NutrientAnalysisTool
)
from ibm_watsonx_ai import Credentials, APIClient
from src.models import RecipeSuggestionOutput, NutrientAnalysisOutput 
from dotenv import load_dotenv
load_dotenv()

watsonx_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
watsonx_apikey = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY", ""))
project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")

cred_args = {"url": watsonx_url}
if watsonx_apikey:
    cred_args["api_key"] = watsonx_apikey

credentials = Credentials(**cred_args)
client = APIClient(credentials) if watsonx_apikey else None


def get_agent_llm() -> LLM:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    if provider == "groq" and os.getenv("GROQ_API_KEY"):
        return LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    elif provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        return LLM(model="gemini/gemini-1.5-flash", api_key=os.getenv("GEMINI_API_KEY"))
    elif provider == "watsonx" and (os.getenv("IBM_WATSONX_APIKEY") or os.getenv("WATSONX_APIKEY")):
        return LLM(
            model="watsonx/ibm/granite-3-8b-instruct",
            api_key=os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY")),
            base_url=os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            project_id=os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")
        )
    else:
        # Default fallback to local Ollama (100% free, no API key required)
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return LLM(
            model=f"ollama/{model}",
            base_url=host
        )


# Get the absolute path to the config directory (located at root)
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))

@CrewBase
class BaseNourishBotCrew:
    agents_config = os.path.join(CONFIG_DIR, 'agents.yaml')
    tasks_config = os.path.join(CONFIG_DIR, 'tasks.yaml')
    
    def __init__(self, image_data, dietary_restrictions: str = None):
        self.image_data = image_data
        self.dietary_restrictions = dietary_restrictions

        if isinstance(self.agents_config, str) and os.path.exists(self.agents_config):
            with open(self.agents_config, 'r') as f:
                self.agents_config = yaml.safe_load(f)
        
        if isinstance(self.tasks_config, str) and os.path.exists(self.tasks_config):
            with open(self.tasks_config, 'r') as f:
                self.tasks_config = yaml.safe_load(f)

    @agent
    def ingredient_detection_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['ingredient_detection_agent'],
            tools=[
                ExtractIngredientsTool.extract_ingredient, 
                FilterIngredientsTool.filter_ingredients
            ],
            allow_delegation=False,
            max_iter=5,
            verbose=True,
            llm=get_agent_llm()
        )

    @agent
    def dietary_filtering_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['dietary_filtering_agent'],
            tools=[DietaryFilterTool.filter_based_on_restrictions],
            allow_delegation=True,
            max_iter=6,
            verbose=True,
            llm=get_agent_llm()
        )

    @agent
    def nutrient_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['nutrient_analysis_agent'],
            tools=[NutrientAnalysisTool.analyze_image],
            allow_delegation=False,
            max_iter=4,
            verbose=True,
            llm=get_agent_llm()
        )

    @agent
    def recipe_suggestion_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['recipe_suggestion_agent'],
            allow_delegation=False,
            verbose=True,
            llm=get_agent_llm()
        )

    @task
    def ingredient_detection_task(self) -> Task:
        task_config = self.tasks_config['ingredient_detection_task']

        return Task(
            description=task_config['description'],
            agent=self.ingredient_detection_agent(),
            expected_output=task_config['expected_output']
        )

    @task
    def dietary_filtering_task(self) -> Task:
        task_config = self.tasks_config['dietary_filtering_task']

        return Task(
            description=task_config['description'],
            agent=self.dietary_filtering_agent(),
            context=[self.ingredient_detection_task()],
            expected_output=task_config['expected_output']
        )

    @task
    def nutrient_analysis_task(self) -> Task:
        task_config = self.tasks_config['nutrient_analysis_task']

        return Task(
            description=task_config['description'],
            agent=self.nutrient_analysis_agent(),
            expected_output=task_config['expected_output'],
            output_json=NutrientAnalysisOutput
        )

    @task
    def recipe_suggestion_task(self) -> Task:
        task_config = self.tasks_config['recipe_suggestion_task']

        return Task(
            description=task_config['description'],
            agent=self.recipe_suggestion_agent(),
            context=[self.dietary_filtering_task()],
            expected_output=task_config['expected_output'],
            output_json=RecipeSuggestionOutput
        )


@CrewBase
class NourishBotRecipeCrew(BaseNourishBotCrew):
    agents_config = os.path.join(CONFIG_DIR, 'agents.yaml')
    tasks_config = os.path.join(CONFIG_DIR, 'tasks.yaml')

    @crew
    def crew(self) -> Crew:
        tasks = [
            self.ingredient_detection_task(),
            self.dietary_filtering_task(),
            self.recipe_suggestion_task()
        ]

        agents = [
            self.ingredient_detection_agent(),
            self.dietary_filtering_agent(),
            self.recipe_suggestion_agent()
        ]

        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )


@CrewBase
class NourishBotAnalysisCrew(BaseNourishBotCrew):
    agents_config = os.path.join(CONFIG_DIR, 'agents.yaml')
    tasks_config = os.path.join(CONFIG_DIR, 'tasks.yaml')

    @crew
    def crew(self) -> Crew:
        tasks = [
            self.nutrient_analysis_task(),
        ]

        agents = [
            self.nutrient_analysis_agent(),
        ]

        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
