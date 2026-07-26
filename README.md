# 🥗 AI Nutrition Coach Agent (Multi-Agent System using CrewAI)

An AI-powered Nutrition Coach built with CrewAI that analyzes food images, detects ingredients, filters them based on dietary restrictions, suggests recipes, and provides nutrient analysis.

This project demonstrates the use of Agentic AI and multi-agent collaboration to automate nutrition analysis and healthy meal recommendations.

> 🚀 Production-Ready Multi-Agent AI SaaS for Intelligent Nutrition Analysis, Recipe Generation, and Personalized Dietary Guidance.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-green)
![Railway](https://img.shields.io/badge/Deployment-Railway-purple)
![Clerk](https://img.shields.io/badge/Auth-Clerk-orange)
![Stripe](https://img.shields.io/badge/Payments-Stripe-blue)
![GitHub Models](https://img.shields.io/badge/LLM-GitHub%20Models-black)
![License](https://img.shields.io/badge/License-MIT-success)

## 🌐 Live Demo

**Website:** https://saadai.me

---

# 📖 Overview

AI Saad is a production-ready AI SaaS application that helps users analyze food images, understand nutritional information, and generate healthy recipes using a Multi-Agent AI workflow powered by CrewAI.

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
- Ingredient Detection
- Nutrition Analysis
- Healthy Recipe Generation
- Dietary Restriction Filtering
- Structured JSON Outputs
- GPT-4o Mini via GitHub Models

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

# 🧠 AI Workflow

```text
          Upload Food Image
                  │
                  ▼
      Ingredient Detection Agent
                  │
                  ▼
      Dietary Filtering Agent
                  │
                  ▼
      Nutrition Analysis Agent
                  │
                  ▼
       Recipe Suggestion Agent
                  │
                  ▼
        Personalized Results
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

- GitHub Models
- OpenAI GPT-4o Mini
- Multi-Agent System
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

✅ Migrated to GitHub Models

✅ GPT-4o Mini Integration

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
LLM_PROVIDER=github

GITHUB_TOKEN=your_github_models_token

CLERK_PUBLISHABLE_KEY=...

CLERK_SECRET_KEY=...

STRIPE_SECRET_KEY=...

STRIPE_PUBLISHABLE_KEY=...

HOST=https://saadai.me
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
