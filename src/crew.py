import os
import yaml
import base64
from crewai import Agent, Crew, Process, Task, LLM
import crewai.llms.cache as _crewai_cache
# Disable cache_breakpoint flag injection for incompatible providers like Groq
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

# Disable native function calling for Groq models due to tool_use_failed errors
_original_supports_function_calling = LLM.supports_function_calling
def _custom_supports_function_calling(self) -> bool:
    if "groq" in getattr(self, "model", "").lower() or getattr(self, "provider", "").lower() == "groq":
        return False
    return _original_supports_function_calling(self)
LLM.supports_function_calling = _custom_supports_function_calling

from crewai.project import CrewBase, agent, crew, task
from src.tools import (
    ExtractIngredientsTool, 
    FilterIngredientsTool, 
    DietaryFilterTool,
    NutrientAnalysisTool
)
from src.models import RecipeSuggestionOutput, NutrientAnalysisOutput 
from dotenv import load_dotenv
load_dotenv()

# watsonx_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
# watsonx_apikey = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY", ""))
# project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")

# cred_args = {"url": watsonx_url}
# if watsonx_apikey:
#     cred_args["api_key"] = watsonx_apikey

# credentials = Credentials(**cred_args)
# client = APIClient(credentials) if watsonx_apikey else None


def get_agent_llm() -> LLM:
    print("=" * 50)
    print("LLM_PROVIDER =", os.getenv("LLM_PROVIDER"))
    print("GITHUB_BASE_URL =", os.getenv("GITHUB_BASE_URL"))
    print("GITHUB_API_KEY exists =", bool(os.getenv("GITHUB_API_KEY")))
    print("=" * 50)
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when using groq provider.")
        return LLM(model="groq/llama-3.3-70b-versatile", api_key=api_key)
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required when using gemini provider.")
        return LLM(model="gemini/gemini-1.5-flash", api_key=api_key)
    elif provider == "watsonx":
        api_key = os.getenv("IBM_WATSONX_APIKEY", os.getenv("WATSONX_APIKEY"))
        if not api_key:
            raise RuntimeError("IBM_WATSONX_APIKEY or WATSONX_APIKEY is required when using watsonx provider.")
        return LLM(
            model="watsonx/ibm/granite-3-8b-instruct",
            api_key=api_key,
            base_url=os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            project_id=os.getenv("IBM_WATSONX_PROJECT_ID", "skills-network")
        )
    elif provider == "github":
        api_key = os.getenv("GITHUB_API_KEY")
        return LLM(
            model="github/gpt-4o-mini",
            api_key=api_key,
            base_url="https://models.inference.ai.azure.com"
    )
    elif provider == "ollama":
        # Default local Ollama (100% free, no API key required)
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return LLM(
            model=f"ollama/{model}",
            base_url=host
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


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
