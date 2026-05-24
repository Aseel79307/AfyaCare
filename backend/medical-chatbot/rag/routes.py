from fastapi import APIRouter, HTTPException
import time
import os
import requests
import logging
import json
import re
from typing import Optional
from pydantic import BaseModel

from core.state import initialization_status, embedding_manager, validate_environment
from rag.models import (
    ChatRequest, ChatResponse, DailyReportRequest, DailyReportResponse,
    QuestionnaireRequest, MedicationScheduleRequest, MedicationScheduleResponse
)
from rag.services import (
    _build_medications_summary, _build_questionnaire_summary, _get_medical_context,
    _parse_ai_response, _build_treatment_analysis_prompt, _build_prevention_analysis_prompt,
    _generate_welcome_message, _generate_personalized_advice
)
from agent.core import run_agentic_chat

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze_daily_report", response_model=DailyReportResponse)
async def analyze_daily_report(request: DailyReportRequest):
    """تحليل تقرير نهاية اليوم باستخدام الذكاء الاصطناعي"""
    start_time = time.time()
    
    if not initialization_status["is_initialized"]:
        raise HTTPException(status_code=503, detail=initialization_status.get("message", "التطبيق قيد الإعداد. حاول لاحقاً"))
    
    if not os.getenv('OPENROUTER_API_KEY'):
        raise HTTPException(status_code=500, detail="مفتاح OpenRouter API غير موجود. تأكد من إعداد ملف .env")
    
    try:
        medications_summary = _build_medications_summary(request.medications)
        questionnaire_summary = _build_questionnaire_summary(request.questionnaire_answers)
        medical_context = _get_medical_context(request.medications, request.questionnaire_answers)
        
        messages = [
            {
                "role": "system",
                "content": f"أنت مساعد طبي ذكي متخصص في تحليل التقارير الصحية اليومية.\n\n🎯 **المهمة**: تحليل تقرير المستخدم الصحي اليومي وإعطاء تحليل مفيد وتوصيات عملية.\n\n👤 **المستخدم**: {request.user_name}\n\n📊 **معلومات التقرير**:\n{medications_summary}\n{questionnaire_summary}\n\n🎯 **تعليمات التحليل**:\n1. حلل حالة الالتزام بالأدوية\n2. تقييم الأعراض الجانبية المبلغ عنها\n3. تقييم الحالة العامة للمستخدم\n4. أعط توصيات عملية ومحددة\n5. حدد مستوى الإنذار (منخفض، متوسط، عالي)\n\n📐 **معايير الدرجة الصحية**:\n- 90-100: ممتاز\n- 80-89: جيد جداً\n- 70-79: جيد\n- 60-69: مقبول\n- 50-59: يحتاج تحسين\n- 0-49: يحتاج عناية فورية\n\n📝 **تنسيق الإجابة المطلوب**:\n\n**التحليل:**\n[اكتب التحليل المفصل هنا]\n\n**التوصيات:**\n[اكتب التوصيات هنا]\n\n**الدرجة الصحية:** [رقم من 0 إلى 100]\n\n**مستوى الإنذار:** [منخفض أو متوسط أو عالي]"
            },
            {
                "role": "user",
                "content": f"**السياق الطبي ذو الصلة:**\n{medical_context}\n\n**طلب التحليل:**\nقم بتحليل التقرير الصحي اليومي للمستخدم وأعطني التحليل بالتنسيق المطلوب بالضبط"
            }
        ]
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AFYA CARE - Medical RAG Chatbot",
            },
            json={
                "model": "openai/gpt-oss-120b:free",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1500,
                "top_p": 0.9,
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text[:200])
        
        response_data = response.json()
        ai_response = response_data["choices"][0]["message"]["content"]
        
        analysis, recommendations, health_score, warning_level = _parse_ai_response(ai_response)
        total_time = time.time() - start_time
        
        return DailyReportResponse(
            analysis=analysis,
            recommendations=recommendations,
            health_score=health_score,
            warning_level=warning_level,
            processing_time=total_time
        )
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع في تحليل تقرير اليوم: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ داخلي في المعالجة: {str(e)}")

@router.post("/analyze_questionnaire")
async def analyze_questionnaire(request: QuestionnaireRequest):
    """تحليل إجابات الاستبيان باستخدام الذكاء الاصطناعي"""
    start_time = time.time()
    
    if not initialization_status["is_initialized"]:
        raise HTTPException(status_code=503, detail=initialization_status.get("message", "التطبيق قيد الإعداد. حاول لاحقاً"))
    
    if not os.getenv('OPENROUTER_API_KEY'):
        raise HTTPException(status_code=500, detail="مفتاح OpenRouter API غير موجود.")
    
    try:
        if request.user_type == "treatment":
            analysis_prompt = _build_treatment_analysis_prompt(request.answers)
        else:
            analysis_prompt = _build_prevention_analysis_prompt(request.answers)
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AFYA CARE - Questionnaire Analysis",
            },
            json={
                "model": "openai/gpt-oss-120b:free",
                "messages": analysis_prompt,
                "temperature": 0.3,
                "max_tokens": 1500,
                "top_p": 0.9,
            },
            timeout=45
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text[:200])
        
        response_data = response.json()
        ai_analysis = response_data["choices"][0]["message"]["content"]
        
        welcome_message = _generate_welcome_message(request.user_type, request.answers)
        total_time = time.time() - start_time
        
        return {
            "analysis": ai_analysis,
            "personalized_advice": _generate_personalized_advice(request.user_type, request.answers),
            "welcome_message": welcome_message,
            "processing_time": total_time
        }
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع في تحليل الاستبيان: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ داخلي في المعالجة: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    logger.info(f"🔍 CHAT REQUEST: user_id={request.user_id}, question={request.question[:50]}")
    """الإجابة على الأسئلة الطبية باستخدام Agent"""
    start_time = time.time()
    
    if not initialization_status["is_initialized"]:
        raise HTTPException(status_code=503, detail=initialization_status.get("message", "التطبيق قيد الإعداد"))
    
    if not os.getenv('OPENROUTER_API_KEY'):
        raise HTTPException(status_code=500, detail="مفتاح OpenRouter API غير موجود")
    
    try:
        chat_history = getattr(request, 'chat_history', [])
        answer, sources_response = run_agentic_chat(
            question=request.question,
            user_type=request.user_type,
            chat_history=chat_history
        )

        try:
            from supabase_client import supabase
            from datetime import datetime
            
            # Get user_id from request if available (you may need to add this to ChatRequest model)
            user_id = getattr(request, 'user_id', None)
            if user_id is None:
                # Temporary: use a default or get from token
                user_id = "anonymous"
            
            supabase.client.table("chat_history").insert({
                "user_id": user_id,
                "question": request.question,
                "answer": answer[:1000],  # Limit length
                "user_type": request.user_type,
                "created_at": datetime.now().isoformat()
            }).execute()
            logger.info(f"✅ Chat saved to database for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save chat to database: {e}")


        total_time = time.time() - start_time
        
        return ChatResponse(
            answer=answer,
            sources=sources_response,
            processing_time=total_time,
            user_type=request.user_type
        )
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ داخلي: {str(e)}")

@router.post("/suggest_medication_schedule", response_model=MedicationScheduleResponse)
async def suggest_medication_schedule(request: MedicationScheduleRequest):
    """اقتراح جدول مواعيد الأدوية"""
    start_time = time.time()
    
    if not initialization_status["is_initialized"]:
        raise HTTPException(status_code=503, detail="التطبيق قيد الإعداد")
    
    try:
        medications_list = "\n".join([f"• {med}" for med in request.medications])
        preferences_text = "\n".join([f"• {k}: {v}" for k,v in request.user_preferences.items()]) if request.user_preferences else "لا توجد تفضيلات إضافية"
        
        messages = [
            {
                "role": "system",
                "content": "أنت مساعد طبي ذكي متخصص في جدولة الأدوية.\nاقترح جدول مثالي مع شرح موجز."
            },
            {
                "role": "user",
                "content": f"وقت النوم: {request.sleep_time}\nوقت الاستيقاظ: {request.wake_up_time}\n\nالأدوية:\n{medications_list}\n\nتفضيلات:\n{preferences_text}"
            }
        ]
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AFYA CARE - Scheduler",
            },
            json={
                "model": "openai/gpt-oss-120b:free",
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 1200,
                "top_p": 0.9,
            },
            timeout=45
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text[:200])
        
        response_data = response.json()
        ai_response = response_data["choices"][0]["message"]["content"]
        total_time = time.time() - start_time
        
        return MedicationScheduleResponse(
            suggested_schedule=ai_response,
            explanation="تم إنشاء الاقتراح بناءً على معلوماتك",
            processing_time=total_time
        )
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ داخلي: {str(e)}")

# ========== MEDICATION ENDPOINTS ==========

class MedicationCreate(BaseModel):
    user_id: str
    name: str
    dosage: str = ""
    frequency: str = "daily"
    time_of_day: list[str]

class MedicationUpdate(BaseModel):
    is_taken: Optional[bool] = None
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None

@router.post("/medications")
async def create_medication(medication: MedicationCreate):
    """Create a new medication"""
    try:
        import uuid
        from datetime import datetime
        
        medication_id = str(uuid.uuid4())
        
        # Get Supabase client from your supabase_client module
        from supabase_client import supabase
        
        data = {
            "id": medication_id,
            "user_id": medication.user_id,
            "name": medication.name,
            "dosage": medication.dosage,
            "frequency": medication.frequency,
            "time": medication.time_of_day[0] if medication.time_of_day else "08:00",
            "is_taken": False,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.client.table("medications").insert(data).execute()
        
        if result.data:
            return {"success": True, "id": medication_id, **result.data[0]}
        return {"success": False, "error": "Failed to create medication"}
    except Exception as e:
        logger.error(f"Error creating medication: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/medications")
async def get_medications(user_id: str):
    """Get all medications for a user"""
    try:
        from supabase_client import supabase
        
        result = supabase.client.table("medications")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=False)\
            .execute()
        
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Error getting medications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/medications/{medication_id}")
async def update_medication(medication_id: str, update: MedicationUpdate):
    """Update a medication (e.g., toggle is_taken)"""
    try:
        from supabase_client import supabase
        
        update_data = {k: v for k, v in update.dict().items() if v is not None}
        
        result = supabase.client.table("medications")\
            .update(update_data)\
            .eq("id", medication_id)\
            .execute()
        
        if result.data:
            return {"success": True, **result.data[0]}
        return {"success": False, "error": "Medication not found"}
    except Exception as e:
        logger.error(f"Error updating medication: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/medications/{medication_id}")
async def delete_medication(medication_id: str):
    """Delete a medication"""
    try:
        from supabase_client import supabase
        
        result = supabase.client.table("medications")\
            .delete()\
            .eq("id", medication_id)\
            .execute()
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting medication: {e}")
        raise HTTPException(status_code=500, detail=str(e))