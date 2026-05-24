"""
Supabase Client - Using official Supabase Python library
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            print("⚠️ Supabase credentials not found in .env")
            self.enabled = False
            self.client = None
            return
        
        self.enabled = True
        self.client: Client = create_client(self.url, self.key)
        print(f"✅ Supabase client ready")
        print(f"   URL: {self.url}")
    
    # ========== AUTHENTICATION METHODS ==========
    
    def sign_up(self, email: str, password: str, user_data: dict = None) -> dict:
        """Register a new user"""
        if not self.enabled:
            return {"success": False, "error": "Supabase not enabled"}
        
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_data or {}
                }
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session,
                "access_token": response.session.access_token if response.session else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sign_in(self, email: str, password: str) -> dict:
        """Login existing user"""
        if not self.enabled:
            return {"success": False, "error": "Supabase not enabled"}
        
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session,
                "access_token": response.session.access_token
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sign_out(self, access_token: str) -> dict:
        """Logout user"""
        if not self.enabled:
            return {"success": False, "error": "Supabase not enabled"}
        
        try:
            self.client.auth.set_session(access_token, None)
            self.client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_current_user(self, access_token: str) -> dict:
        """Get current user from token"""
        if not self.enabled:
            return {"success": False, "error": "Supabase not enabled"}
        
        try:
            self.client.auth.set_session(access_token, None)
            user = self.client.auth.get_user()
            return {"success": True, "user": user}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== USER PROFILE METHODS ==========
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from profiles table"""
        if not self.enabled:
            return None
        
        try:
            response = self.client.table("profiles").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Error getting profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """Update user profile"""
        if not self.enabled:
            return None
        
        try:
            response = self.client.table("profiles").update(profile_data).eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error updating profile: {e}")
            return None
    
    # ========== MEDICATION METHODS ==========
    
    def add_medication(self, user_id: str, medication_data: Dict) -> Optional[Dict]:
        """Add a medication for a user"""
        if not self.enabled:
            return None
            
        try:
            data = {
                "user_id": user_id,
                "name": medication_data.get("name"),
                "dosage": medication_data.get("dosage"),
                "frequency": medication_data.get("frequency"),
                "time_of_day": medication_data.get("time_of_day", [])
            }
            response = self.client.table("medications").insert(data).execute()
            if response.data:
                print(f"✅ Medication added: {medication_data.get('name')}")
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Error adding medication: {e}")
            return None
    
    def get_user_medications(self, user_id: str, active_only: bool = True) -> List[Dict]:
        """Get all medications for a user"""
        if not self.enabled:
            return []
            
        try:
            query = self.client.table("medications").select("*").eq("user_id", user_id)
            if active_only:
                query = query.eq("is_active", True)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error getting medications: {e}")
            return []
    
    # ========== CHAT HISTORY METHODS ==========
    
    def save_chat(self, user_id: str, question: str, answer: str, user_type: str, processing_time: float):
        """Save chat history"""
        if not self.enabled:
            return
            
        try:
            data = {
                "user_id": user_id,
                "question": question,
                "answer": answer[:1000],
                "user_type": user_type,
                "processing_time": processing_time
            }
            self.client.table("chat_history").insert(data).execute()
            print(f"✅ Chat saved")
        except Exception as e:
            print(f"❌ Error saving chat: {e}")
    
    def get_user_chats(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's chat history"""
        if not self.enabled:
            return []
            
        try:
            response = self.client.table("chat_history")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error getting chats: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if Supabase is reachable"""
        if not self.enabled:
            return False
            
        try:
            response = self.client.table("users").select("*").limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

# Create global instance
supabase = SupabaseClient()

if supabase.enabled:
    if supabase.test_connection():
        print("✅ Supabase connection successful!")
    else:
        print("⚠️ Supabase connection failed - check your URL and key")