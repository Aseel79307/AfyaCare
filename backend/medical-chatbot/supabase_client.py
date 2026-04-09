"""
Simple Supabase Client - REST API based, no C++ dependencies!
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            print("⚠️ Supabase credentials not found in .env")
            self.enabled = False
            return
        
        # Remove trailing slash if present
        self.url = self.url.rstrip('/')
        self.enabled = True
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        print(f"✅ Supabase client ready")
        print(f"   URL: {self.url}")
    
    def create_user(self, name: str, email: str, password_hash: str) -> Optional[Dict]:
        """Create a new user"""
        if not self.enabled:
            print("⚠️ Supabase not enabled")
            return None
            
        try:
            response = requests.post(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                json={
                    "name": name,
                    "email": email,
                    "password_hash": password_hash
                }
            )
            if response.status_code == 201:
                print(f"✅ User created: {email}")
                return response.json()
            else:
                print(f"❌ Failed to create user: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        if not self.enabled:
            return None
            
        try:
            response = requests.get(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                params={"email": f"eq.{email}"}
            )
            if response.status_code == 200 and response.json():
                return response.json()[0]
            return None
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None
    
    def add_medication(self, user_id: str, medication_data: Dict) -> Optional[Dict]:
        """Add a medication for a user"""
        if not self.enabled:
            return None
            
        try:
            response = requests.post(
                f"{self.url}/rest/v1/medications",
                headers=self.headers,
                json={
                    "user_id": user_id,
                    "name": medication_data.get("name"),
                    "dosage": medication_data.get("dosage"),
                    "frequency": medication_data.get("frequency"),
                    "time_of_day": medication_data.get("time_of_day", [])
                }
            )
            if response.status_code == 201:
                print(f"✅ Medication added: {medication_data.get('name')}")
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Error adding medication: {e}")
            return None
    
    def get_user_medications(self, user_id: str) -> list:
        """Get all medications for a user"""
        if not self.enabled:
            return []
            
        try:
            response = requests.get(
                f"{self.url}/rest/v1/medications",
                headers=self.headers,
                params={"user_id": f"eq.{user_id}"}
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"❌ Error getting medications: {e}")
            return []
    
    def save_chat(self, user_id: str, question: str, answer: str, user_type: str, processing_time: float):
        """Save chat history"""
        if not self.enabled:
            return
            
        try:
            response = requests.post(
                f"{self.url}/rest/v1/chat_history",
                headers=self.headers,
                json={
                    "user_id": user_id,
                    "question": question,
                    "answer": answer[:1000],  # Limit length
                    "user_type": user_type,
                    "processing_time": processing_time
                }
            )
            if response.status_code == 201:
                print(f"✅ Chat saved")
        except Exception as e:
            print(f"❌ Error saving chat: {e}")
    
    def test_connection(self) -> bool:
        """Test if Supabase is reachable"""
        if not self.enabled:
            return False
            
        try:
            response = requests.get(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                params={"limit": "1"}
            )
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

# Create global instance
supabase = SupabaseClient()

# Test connection on import
if supabase.enabled:
    if supabase.test_connection():
        print("✅ Supabase connection successful!")
    else:
        print("⚠️ Supabase connection failed - check your URL and key")