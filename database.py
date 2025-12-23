from typing import Any, Dict, List, Optional
import datetime
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use Service Role Key for backend operations to bypass RLS if needed, 
# or Anon key if policies are sufficient. For a bot backend, service role is often safer/easier 
# to ensure full access to all users' data without auth tokens.
# Check if SERVICE_ROLE_KEY exists, else fall back to ANON (which might fail if RLS blocks)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase credentials not found in env. Database operations will fail.")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Simple check
    # supabase.table("users").select("count", count="exact").execute()
    print("Supabase client initialized.")
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    supabase = None

# Projects and Activities collections were previously defined but seem unused in main bot logic
# We will keep the functions but map them to potential tables or logging for now.

def get_or_create_user(
    user_id: int, username: Optional[str], first_name: str
) -> Dict[str, Any]:
    """Get existing user or create a new one"""
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data:
            return _map_user_from_db(response.data[0])
        
        # Create new user
        new_user = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "created_at": datetime.datetime.now().isoformat(),
            # Other fields default to 0/empty in DB schema
        }
        
        data = supabase.table("users").insert(new_user).execute()
        if data.data:
            return _map_user_from_db(data.data[0])
        return {}
    except Exception as e:
        print(f"Error in get_or_create_user: {e}")
        return {}


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data:
            return _map_user_from_db(response.data[0])
        return None
    except Exception as e:
        print(f"Error in get_user: {e}")
        return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by Telegram username"""
    try:
        # Note: username is not unique in schema, but we take first
        # Also remove '@' if present
        if username.startswith("@"):
            username = username[1:]
            
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data:
            return _map_user_from_db(response.data[0])
        return None
    except Exception as e:
        print(f"Error in get_user_by_username: {e}")
        return None


def get_all_users() -> List[Dict[str, Any]]:
    """Get all users"""
    try:
        # Warning: This might be slow if many users, consider pagination
        response = supabase.table("users").select("*").execute()
        return [_map_user_from_db(u) for u in response.data]
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []


def update_user_github(user_id: int, github_username: str) -> bool:
    """Update user's GitHub username"""
    try:
        supabase.table("users").update({"github_username": github_username}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating github: {e}")
        return False


def update_user_wallet(user_id: int, wallet_address: str) -> bool:
    """Update user's wallet address"""
    try:
        supabase.table("users").update({"wallet_address": wallet_address}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating wallet: {e}")
        return False


def update_telegram_activity(user_id: int, activity_type: str) -> bool:
    """
    Update user's Telegram activity. 
    In Mongo this was a nested object, in Postgres we have flat columns.
    """
    if activity_type not in ["messages", "replies"]:
        print(f"Invalid activity type: {activity_type}")
        return False
    
    col_name = f"telegram_{activity_type}" # telegram_messages or telegram_replies
    
    try:
        # Supabase doesn't support atomic increment easily via simple client update without RPC
        # But for this bot, strictly atomic might not be critical, or we can read-modify-write
        # Better approach: Create a simple postgres function `increment_counter` or read-update.
        # For now, read-update (optimistic)
        
        # Or better: Use user-defined function if possible?
        # Let's stick to read-update for simplicity in migration unless high concurrency
        
        user = get_user(user_id)
        if not user:
            return False
            
        current_val = user["telegram_activity"].get(activity_type, 0)
        
        supabase.table("users").update({col_name: current_val + 1}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating telegram activity: {e}")
        return False


def update_user_builder_score(user_id: int, score: float) -> bool:
    """Update user's builder score"""
    try:
        supabase.table("users").update({"builder_score": score}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating score: {e}")
        return False


def add_nomination(nominator_id: int, nominee_username: str) -> dict:
    """Add a nomination"""
    if nominee_username.startswith("@"):
        nominee_username = nominee_username[1:]

    nominator = get_user(nominator_id)
    if not nominator:
         return {"status": "error", "message": "You must set up your profile before nominating others"}
         
    nominee = get_user_by_username(nominee_username)
    if not nominee:
        return {"status": "error", "message": f"User @{nominee_username} not found. Make sure they have set up their profile."}

    if nominator_id == nominee["user_id"]:
        return {"status": "error", "message": "You cannot nominate yourself"}

    nominations_given = nominator.get("nominations_given", [])
    if nominee_username in nominations_given:
        return {"status": "error", "message": f"You have already nominated @{nominee_username}"}

    try:
        # Update nominator
        new_nominations = nominations_given + [nominee_username]
        supabase.table("users").update({"nominations_given": new_nominations}).eq("id", nominator_id).execute()
        
        # Update nominee (increment count)
        current_received = nominee.get("nominations_received", 0)
        supabase.table("users").update({"nominations_received": current_received + 1}).eq("id", nominee["user_id"]).execute()
        
        updated_nominee = get_user_by_username(nominee_username)
        return {
            "status": "success", 
            "message": f"You have successfully nominated @{nominee_username}",
            "nominee": updated_nominee
        }
    except Exception as e:
        print(f"Error adding nomination: {e}")
        return {"status": "error", "message": "Database error"}


def get_user_by_github_username(github_username: str) -> Optional[Dict[str, Any]]:
    """Get user by GitHub username"""
    try:
        response = supabase.table("users").select("*").eq("github_username", github_username).execute()
        if response.data:
            return _map_user_from_db(response.data[0])
        return None
    except Exception as e:
        print(f"Error get_user_by_github_username: {e}")
        return None


def update_github_contribution(github_username: str, contribution_type: str) -> bool:
    """Update GitHub contributions"""
    if contribution_type not in ["commits", "prs", "issues"]:
        print(f"Invalid contribution type: {contribution_type}")
        return False
        
    col_name = f"github_{contribution_type}"
    
    user = get_user_by_github_username(github_username)
    if not user:
        print(f"No user found with GitHub username: {github_username}")
        return False
        
    try:
        # Read-update
        current_val = user["github_contributions"].get(contribution_type, 0)
        supabase.table("users").update({col_name: current_val + 1}).eq("github_username", github_username).execute()
        return True
    except Exception as e:
        print(f"Error updating github contribution: {e}")
        return False


def get_top_builders(limit=10):
    """Get top builders"""
    try:
        response = supabase.table("users").select("*").order("builder_score", desc=True).limit(limit).execute()
        return [_map_user_from_db(u) for u in response.data]
    except Exception as e:
        print(f"Error get_top_builders: {e}")
        return []

def save_project(project_data):
    """
    Save project. Assuming 'projects' table or similar. 
    If not using projects table, we might skip or log.
    Schema assumed: projects(id, data jsonb, created_at)
    """
    try:
        # Wrap data in a JSON structure if needed, or insert directly if columns match
        # Since we defined projects(data JSONB), let's just dump it there
        payload = {"data": project_data}
        supabase.table("projects").insert(payload).execute()
        return True
    except Exception as e:
        print(f"Error saving project: {e}")
        return False


def get_projects(limit=10):
    """Get recent projects"""
    try:
        response = supabase.table("projects").select("*").order("created_at", desc=True).limit(limit).execute()
        # Return list of data objects
        return [r["data"] for r in response.data]
    except Exception as e:
        print(f"Error get_projects: {e}")
        return []


def _map_user_from_db(db_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to map Supabase flat row to the nested dictionary structure 
    expected by the bot (to maintain backward compatibility).
    """
    return {
        "user_id": db_row["id"],
        "username": db_row["username"],
        "first_name": db_row["first_name"],
        "github_username": db_row["github_username"],
        "wallet_address": db_row["wallet_address"],
        "builder_score": db_row["builder_score"],
        "created_at": db_row["created_at"], # ISO string
        "nominations_received": db_row.get("nominations_received", 0),
        "nominations_given": db_row.get("nominations_given", []),
        
        # Reconstruct nested objects
        "telegram_activity": {
            "messages": db_row.get("telegram_messages", 0),
            "replies": db_row.get("telegram_replies", 0)
        },
        "github_contributions": {
            "commits": db_row.get("github_commits", 0),
            "prs": db_row.get("github_prs", 0),
            "issues": db_row.get("github_issues", 0)
        }
    }

