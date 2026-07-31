from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Recipe(BaseModel):
    title: str = Field(default="", description="Recipe title")
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients required for the recipe")
    instructions: str = Field(default="", description="Step-by-step cooking instructions")
    calorie_estimate: int = Field(default=0, description="Estimated calories per serving")

class RecipeSuggestionOutput(BaseModel):
    # Flattened recipes to avoid $defs and nested schema validation issues on OpenRouter
    recipes: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of suggested recipes. Each recipe is a dictionary containing 'title' (string), 'ingredients' (list of strings), 'instructions' (string), and 'calorie_estimate' (integer)."
    )

class VitaminInfo(BaseModel):
    name: str = Field(default="", description="Name of the vitamin")
    percentage_dv: str = Field(default="", description="Percentage of the Daily Value")

class MineralInfo(BaseModel):
    name: str = Field(default="", description="Name of the mineral")
    amount: str = Field(default="", description="Amount and unit of the mineral")

class NutrientBreakdown(BaseModel):
    protein: str = Field(default="", description="Protein content")
    carbohydrates: str = Field(default="", description="Carbohydrates content")
    fats: str = Field(default="", description="Fats content")
    vitamins: List[Dict[str, Any]] = Field(default_factory=list, description="List of vitamins and their %DV. Each item is a dictionary with 'name' (string) and 'percentage_dv' (string).")
    minerals: List[Dict[str, Any]] = Field(default_factory=list, description="List of minerals and their amounts. Each item is a dictionary with 'name' (string) and 'amount' (string).")

class NutrientAnalysisOutput(BaseModel):
    dish: str = Field(default="", description="Identified dish")
    portion_size: str = Field(default="", description="Portion size description")
    estimated_calories: int = Field(default=0, description="Estimated calories per portion")
    # Flattened nutrients to avoid $defs and nested schema validation issues
    nutrients: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed nutrient breakdown. A dictionary containing 'protein' (string), 'carbohydrates' (string), 'fats' (string), 'vitamins' (list of dictionaries with keys 'name' and 'percentage_dv'), and 'minerals' (list of dictionaries with keys 'name' and 'amount')."
    )
    health_evaluation: str = Field(default="", description="Health evaluation summary")
