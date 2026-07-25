# 🥗 AI Nutrition Coach Agent (Multi-Agent System using CrewAI)

An AI-powered Nutrition Coach built with CrewAI that analyzes food images, detects ingredients, filters them based on dietary restrictions, suggests recipes, and provides nutrient analysis.

This project demonstrates the use of Agentic AI and multi-agent collaboration to automate nutrition analysis and healthy meal recommendations.

##  🚀 Features

### ✅ Ingredient Detection from Food Images
Extracts ingredients from a given food image using AI tools.

### ✅ Ingredient Filtering
Removes irrelevant or duplicate ingredients.

### ✅ Dietary Restriction Filtering
Filters ingredients according to user dietary preferences such as:

Vegetarian
Vegan
Gluten-Free
Keto
Low-Carb

### ✅ Recipe Suggestions
Generates recipe recommendations using the filtered ingredients.

### ✅ Nutritional Analysis
Analyzes food and returns estimated:

Calories
Protein
Carbohydrates
Fats
Other nutrients

## ⚙️ Workflow

#### Recipe Suggestion Pipeline

Food Image
   ➡️
Ingredient Detection Agent
   ➡️
Ingredient Filtering
   ➡️
Dietary Restriction Filtering
   ➡️
Recipe Suggestion Agent
   ➡️
Recipe Output


#### Nutrient Analysis Pipeline

Food Image
   ➡️
Nutrient Analysis Agent
   ➡️
Nutrition Report

## 🛠 Tech Stack

Python, 
CrewAI (Multi-Agent Framework), 
IBM Watsonx AI, 
YAML Configuration, 
Pydantic (Structured Outputs)
