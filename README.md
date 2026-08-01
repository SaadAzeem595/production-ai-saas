# 🥗 AI Saad — Production-Ready Multi-Agent AI Nutrition Coach

An AI-powered Nutrition Coach built with CrewAI that analyzes food images, detects ingredients, filters them based on dietary restrictions, suggests recipes, and provides nutrient analysis.

This project demonstrates the use of Agentic AI and multi-agent collaboration to automate nutrition analysis and healthy meal recommendations.

> 🚀 Production-Ready Multi-Agent AI SaaS for Intelligent Nutrition Analysis, Recipe Generation, and Personalized Dietary Guidance.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-green)
![Railway](https://img.shields.io/badge/Deployment-Railway-purple)
![Clerk](https://img.shields.io/badge/Auth-Clerk-orange)
![Stripe](https://img.shields.io/badge/Payments-Stripe-blue)
![OpenRouter](https://img.shields.io/badge/OpenRouter-API-blueviolet)
![Gemma](https://img.shields.io/badge/Model-Gemma%204%2026B-success)
![Vision](https://img.shields.io/badge/Vision-Nemotron%20Nano-orange)
![License](https://img.shields.io/badge/License-MIT-success)

## 🌐 Live Demo

**Website:** https://saadflask.me

---

# 📖 Overview

AI Saad is a production-ready AI SaaS application that helps users analyze food images, understand nutritional information, and generate healthy recipes using a CrewAI-powered Multi-Agent workflow with OpenRouter LLMs for intelligent ingredient detection, nutrition analysis, and personalized recipe generation.

Simply upload a meal or refrigerator image, and AI Saad automatically:

- 🥗 Detects ingredients
- 🍎 Performs nutritional analysis
- 📊 Estimates calories and macros
- 🧠 Applies dietary restrictions
- 👨‍🍳 Generates personalized recipes

Unlike the original IBM watsonx academic project, this version has been completely redesigned into a scalable SaaS platform with authentication, subscriptions, cloud deployment, and production infrastructure.

---

# ✨ Features

## 🤖 AI Features

- Multi-Agent AI Architecture (CrewAI)
- Image-based Ingredient Detection
- AI-powered Nutrition Analysis
- Personalized Healthy Recipe Generation
- Dietary Restriction Filtering
- Structured JSON Responses
- Vision + Language AI Pipeline
- OpenRouter API Integration
- Gemma 4 26B (Google DeepMind)
- NVIDIA Nemotron Nano Vision Model

---

## ☁️ SaaS Features

- Clerk Authentication
- Protected Dashboard
- Stripe Subscription Integration
- Railway Cloud Deployment
- Custom Domain
- Environment Variable Management
- Production Configuration
- Responsive UI

---

## 👤 Authentication

Powered by Clerk

- Sign Up
- Login
- Logout
- Secure Session Management

---

## 💳 Payments

Powered by Stripe

- Subscription Checkout
- Secure Payment Processing
- Premium Plan Ready
- Customer Portal Ready

---

# 🧠 AI Models Used

### Language Model

- **Google Gemma 4 26B A4B IT**
  - Provider: OpenRouter
  - Purpose:
    - Nutrition reasoning
    - Recipe generation
    - Dietary analysis
    - Structured JSON responses

### Vision Model

- **NVIDIA Nemotron Nano 12B Vision**
  - Provider: OpenRouter
  - Purpose:
    - Food image understanding
    - Ingredient detection
    - Visual analysis

# 🧠 AI Workflow

```text
                Upload Food Image
                        │
                        ▼
      NVIDIA Nemotron Nano Vision Model
          (Ingredient Detection)
                        │
                        ▼
        CrewAI Multi-Agent Workflow
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
 Dietary Agent   Nutrition Agent   Recipe Agent
        │               │               │
        └───────────────┼───────────────┘
                        ▼
      Google Gemma 4 26B via OpenRouter
                        │
                        ▼
           Personalized Nutrition Report
```

---

# 🏗️ Tech Stack

## Backend

- Python
- CrewAI
- Gradio
- LangChain
- Pydantic

## AI

- OpenRouter API
- Google Gemma 4 26B A4B IT
- NVIDIA Nemotron Nano 12B Vision
- CrewAI Multi-Agent System
- Prompt Engineering

## Authentication

- Clerk

## Payments

- Stripe

## Deployment

- Railway

## Domain

- Namecheap

---

# 📂 Project Structure

```
.
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
│
├── src/
│   ├── crew.py
│   ├── models.py
│   ├── tools.py
│   └── app.py
│
├── requirements.txt
└── README.md
```

---

# 🚀 Production Improvements

This project originally used IBM watsonx credentials from the IBM RAG & Agentic AI course.

The production version includes:

✅ Migrated to OpenRouter

✅ Google Gemma 4 26B Integration

✅ NVIDIA Vision Model Integration

✅ Production Environment Variables

✅ Clerk Authentication

✅ Stripe Payment System

✅ Railway Deployment

✅ Custom Domain

✅ Secure Configuration

✅ Cloud Ready

---

# ⚙️ Environment Variables

```env
OPENROUTER_API_KEY=your_openrouter_api_key

OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free

OPENROUTER_VISION_MODEL=nvidia/nemotron-nano-12b-v2-vl:free

CLERK_PUBLISHABLE_KEY=...

CLERK_SECRET_KEY=...

STRIPE_SECRET_KEY=...

STRIPE_PUBLISHABLE_KEY=...

HOST=https://saadflask.me
```

---

# 💻 Local Installation

```bash
git clone https://github.com/yourusername/production-ai-saas.git

cd production-ai-saas

pip install -r requirements.txt

python app.py
```

---

# 🌍 Live Application

https://saadai.me

---

# 📸 Screenshots

(Add screenshots here)

- Home Page
- Dashboard
- AI Nutrition Analysis
- Recipe Generation
- Stripe Checkout

---

# 📈 Future Improvements

- RAG Knowledge Base
- Meal History
- PDF Nutrition Reports
- Fitness Tracking
- AI Meal Planner
- Voice Assistant
- Mobile App
- Admin Dashboard
- Usage Analytics

---

# 👨‍💻 Author

**Saad Azeem**

BS Computer Science Student

AI Engineer | Machine Learning | Generative AI | Multi-Agent Systems

GitHub:
https://github.com/yourusername

LinkedIn:
https://linkedin.com/in/yourprofile

---

# ⭐ If you found this project helpful

Please consider giving it a ⭐ on GitHub!
