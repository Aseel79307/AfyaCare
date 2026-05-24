"""
Authentication Routes for AfyaCare
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from supabase_client import supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ========== Request Models ==========

class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None

class SignInRequest(BaseModel):
    email: str
    password: str

class SignOutRequest(BaseModel):
    access_token: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None

class CheckEmailRequest(BaseModel):
    email: str

@router.post("/check-email")
async def check_email(request: CheckEmailRequest):
    """Check if email already exists"""
    try:
        # Check in auth.users
        result = supabase.client.table("users").select("*").eq("email", request.email).execute()
        
        if result.data and len(result.data) > 0:
            return {"exists": True, "message": "Email already registered"}
        return {"exists": False, "message": "Email available"}
    except Exception as e:
        return {"exists": False, "message": "Error checking email"}

# ========== Endpoints ==========

@router.post("/signup")
async def sign_up(request: SignUpRequest):
    """Register a new user - with OTP verification"""
    
    # Sign up with Supabase (this automatically sends OTP email)
    result = supabase.sign_up(
        email=request.email,
        password=request.password,
        user_data={
            "name": request.name,
            "age": request.age,
            "gender": request.gender
        }
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Signup failed")
        )
    
    # Don't set is_verified = False here - wait for OTP verification
    
    return {
        "success": True,
        "message": "Verification code sent to your email. Please enter it to complete signup.",
        "user": {
            "id": result["user"].id,
            "email": result["user"].email,
            "name": request.name,
        },
        "requires_verification": True
    }

    

@router.post("/signin")
async def sign_in(request: SignInRequest):
    """Login existing user"""

     # Check if user is verified
    user_result = supabase.client.table("users").select("*").eq("email", request.email).execute()
    
    if user_result.data:
        user = user_result.data[0]
        if user.get("is_verified") == False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email before logging in. Check your inbox."
            )
    
    result = supabase.sign_in(email=request.email, password=request.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user_data = result["user"].user_metadata
    
    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": result["user"].id,
            "email": result["user"].email,
            "name": user_data.get("name", ""),
            "age": user_data.get("age"),
            "gender": user_data.get("gender")
        },
        "access_token": result["access_token"]

    }
class VerifyOTPRequest(BaseModel):
    email: str
    token: str  # The 6-digit code

@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """Verify user's email with OTP code"""
    try:
        # Verify the OTP code with Supabase
        result = supabase.client.auth.verify_otp({
            "email": request.email,
            "token": request.token,
            "type": "signup"
        })
        
        # Update users table to verified
        supabase.client.table("users").update({
            "is_verified": True,
        }).eq("email", request.email).execute()
        
        return {
            "success": True,
            "message": "Email verified successfully!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    


@router.post("/signout")
async def sign_out(request: SignOutRequest):
    """Logout user"""
    
    result = supabase.sign_out(request.access_token)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Logout failed")
        )
    
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me/{access_token}")
async def get_current_user(access_token: str):
    """Get current user info"""
    
    result = supabase.get_current_user(access_token)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = result["user"]
    user_data = user.user_metadata
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user_data.get("name", ""),
            "age": user_data.get("age"),
            "gender": user_data.get("gender")
        }
    }

@router.get("/test")
async def test_auth():
    """Test if auth routes are working"""
    return {"message": "Auth routes are working!"}

# ========== Password Reset Endpoints ==========

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email"""
    try:
        # Send password reset email via Supabase
        supabase.client.auth.reset_password_for_email(request.email)
        return {
            "success": True, 
            "message": "Password reset email sent. Please check your inbox."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token from email"""
    try:
        # Update the user's password
        supabase.client.auth.update_user(
            {"password": request.new_password},
            request.token
        )
        return {
            "success": True,
            "message": "Password updated successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    