import os
import json
import threading

DB_FILE = "user_credits.json"
db_lock = threading.Lock()

def _load_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            return {"users": {}, "processed_sessions": []}
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if "users" not in data:
                    data = {"users": data, "processed_sessions": []}
                return data
        except Exception:
            return {"users": {}, "processed_sessions": []}

def _save_db(data):
    with db_lock:
        try:
            with open(DB_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving credits DB: {e}")

def get_user_credits(user_id: str) -> int:
    """
    Get the credit balance for a user. Initialised to 1 if user is new.
    """
    if not user_id:
        return 0
    data = _load_db()
    users = data.get("users", {})
    if user_id not in users:
        # Initialize new user with 1 free credit
        users[user_id] = {"credits": 1, "email": ""}
        data["users"] = users
        _save_db(data)
        return 1
    return users[user_id].get("credits", 0)

def deduct_credit(user_id: str) -> bool:
    """
    Deduct 1 credit from the user's balance. Returns True if successful, False if out of credits.
    """
    if not user_id:
        return False
    data = _load_db()
    users = data.get("users", {})
    if user_id not in users:
        users[user_id] = {"credits": 1, "email": ""}
    
    current_credits = users[user_id].get("credits", 0)
    if current_credits <= 0:
        return False
        
    users[user_id]["credits"] = current_credits - 1
    data["users"] = users
    _save_db(data)
    return True

def add_credits_for_session(user_id: str, session_id: str, count: int, email: str = None) -> bool:
    """
    Add credits to a user after a successful Stripe payment.
    Ensures session_id is only processed once (idempotent).
    Returns True if credits were added, False if the session was already processed.
    """
    if not user_id or not session_id:
        return False
    
    data = _load_db()
    processed = data.setdefault("processed_sessions", [])
    if session_id in processed:
        return False  # Already credited!
        
    users = data.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {"credits": 1, "email": email or ""}
        
    users[user_id]["credits"] = users[user_id].get("credits", 0) + count
    if email:
        users[user_id]["email"] = email
        
    processed.append(session_id)
    _save_db(data)
    return True
