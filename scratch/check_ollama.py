import requests
try:
    res = requests.get("http://localhost:11434/api/tags")
    res.raise_for_status()
    models = [m["name"] for m in res.json().get("models", [])]
    print("Ollama is RUNNING. Installed models:", models)
except Exception as e:
    print("Ollama is NOT running or failed:", e)
