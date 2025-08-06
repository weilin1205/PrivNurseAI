from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import json
import aiohttp
import logging

from database import get_db
from models import User, AIModel, ModelConfiguration, AIInference, ConsultationRecord
from schemas import ValidationRequest, SummaryRequest, ConfirmationRequest, ActiveModelsUpdate
from auth import get_current_user
from services.ollama_service import validation_text
from config import GENERATE_URL, TAGS_URL, OLLAMA_BASE_URL
from demo_dependencies import check_demo_mode

router = APIRouter()
logger = logging.getLogger(__name__)

def get_active_model_by_type(db: Session, model_type: str) -> str:
    """Get active model name by type"""
    active_model = (
        db.query(AIModel.model_name)
        .filter(AIModel.model_type == model_type)
        .filter(AIModel.is_active == True)
        .first()
    )
    
    if not active_model:
        raise HTTPException(
            status_code=400,
            detail=f"No active {model_type} model found"
        )
    
    return active_model[0]

@router.post("/gen-validation")
async def handle_validation_request(
    request: ValidationRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate validation for text"""
    if not request.original or not request.summary:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Use current logged-in user ID instead of request ID
    user_id = current_user.id

    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine validation model type based on content (for now use consultation_validation)
    # TODO: Add logic to determine if this is consultation vs discharge note validation
    validation_type = "consultation_validation"
    model_name = get_active_model_by_type(db, validation_type)
    
    # Log detailed debugging information
    logger.info("="*80)
    logger.info(f"VALIDATION REQUEST DEBUG - Start")
    logger.info(f"User ID: {user_id}, Username: {user.username}")
    logger.info(f"Validation Type: {validation_type}")
    logger.info(f"Model Name: {model_name}")
    logger.info(f"Original Text Length: {len(request.original)} characters")
    logger.info(f"Summary Text Length: {len(request.summary)} characters")
    logger.info(f"Original Text Preview: {request.original[:200]}..." if len(request.original) > 200 else f"Original Text: {request.original}")
    logger.info(f"Summary Text Preview: {request.summary[:200]}..." if len(request.summary) > 200 else f"Summary Text: {request.summary}")
    logger.info("="*80)
    
    # Process the text validation
    result = await validation_text(request.original, request.summary, model_name)
    
    # Log the result
    logger.info("="*80)
    logger.info(f"VALIDATION RESPONSE DEBUG")
    logger.info(f"Result keys: {list(result.keys())}")
    if "error" in result:
        logger.error(f"Validation Error: {result['error']}")
    else:
        logger.info(f"Validation Success")
        if "relevant_text" in result:
            logger.info(f"Relevant Text: {result['relevant_text']}")
    logger.info("="*80)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result

@router.options("/gen-validation")
async def handle_options():
    """Handle OPTIONS request for CORS"""
    return {}

@router.post("/gen-summary")
async def handle_summary_request(
    request: SummaryRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate summary using streaming response"""
    try:
        # Determine summary model type based on content (for now use consultation_summary)
        # TODO: Add logic to determine if this is consultation vs discharge note summary
        summary_type = "consultation_summary"
        model_name = get_active_model_by_type(db, summary_type)
        
        payload = {
            "model": model_name,
            "prompt": request.content,
            "stream": True
        }
        
        async def stream_response():
            async with aiohttp.ClientSession() as session:
                async with session.post(GENERATE_URL, json=payload) as response:
                    if response.status != 200:
                        error_detail = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Ollama API error: {error_detail}"
                        )
                    async for chunk in response.content:
                        if chunk:
                            yield chunk

        return StreamingResponse(stream_response(), media_type="application/json")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )

@router.post("/api/submit-confirmation")
async def submit_confirmation(
    request: ConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Submit confirmation for inference"""
    try:
        # Use current logged-in user ID instead of request ID
        request.user_id = current_user.id

        # Get active models (for now use consultation models)
        # TODO: Add logic to determine model type based on inference type
        summary_model_name = get_active_model_by_type(db, "consultation_summary")
        validation_model_name = get_active_model_by_type(db, "consultation_validation")

        # Compare AI generated result and nurse confirmation for consistency
        is_modified = request.ai_generated_result.strip() != request.nurse_confirmation.strip()

        # Create AI inference record
        inference = AIInference(
            user_id=request.user_id,
            patient_id=request.patient_id,  # Include patient_id from request
            inference_type=request.inference_type or "consultation_summary",  # Use provided type or default
            original_content=request.original_content,
            ai_generated_result=request.ai_generated_result,
            nurse_confirmation=request.nurse_confirmation,
            relevant_text={"relevant_highlights": request.relevant_text},
            model_used=summary_model_name,
            status="confirmed" if not is_modified else "completed"
        )
        
        db.add(inference)
        db.flush()  # Get the inference ID
        
        # Only create a consultation record for consultation-type submissions
        if request.patient_id and request.inference_type in [None, "consultation_summary"]:
            # Check for duplicate consultations - same patient and all same content fields
            existing_consultation = db.query(ConsultationRecord).filter(
                ConsultationRecord.patient_id == request.patient_id,
                ConsultationRecord.original_content == request.original_content,
                ConsultationRecord.ai_summary == request.ai_generated_result,
                ConsultationRecord.nurse_confirmation == request.nurse_confirmation,
                ConsultationRecord.doctor_name == "AI-Assisted Consultation",
                ConsultationRecord.department == "General",
                ConsultationRecord.consultation_type == "initial"
            ).first()
            
            logger.info(f"Checking for duplicate consultation - Patient ID: {request.patient_id}")
            logger.info(f"Checking fields: original_content, ai_summary, nurse_confirmation")
            
            if existing_consultation:
                logger.warning(f"Duplicate consultation detected for patient {request.patient_id}")
                logger.warning(f"Existing consultation ID: {existing_consultation.id}")
                # Rollback the inference we just added
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate consultation detected. This exact consultation record already exists in the database."
                )
            
            consultation = ConsultationRecord(
                patient_id=request.patient_id,
                doctor_name="AI-Assisted Consultation",  # Default doctor name
                department="General",  # Default department - could be enhanced to get from patient
                consultation_type="initial",  # Default type
                original_content=request.original_content,
                ai_summary=request.ai_generated_result,
                nurse_confirmation=request.nurse_confirmation,
                relevant_highlights={"relevant_highlights": request.relevant_text},
                status="confirmed",
                created_by=request.user_id,
                confirmed_by=request.user_id,
                confirmed_at=func.now()
            )
            
            db.add(consultation)
        
        db.commit()
        
        return {"message": "Confirmation submitted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in submit_confirmation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/tags")
async def list_local_models():
    """List available Ollama models"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(TAGS_URL) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch models from Ollama")
                
                data = await response.json()
                return JSONResponse(content=data)
        except aiohttp.ClientError as e:
            raise HTTPException(status_code=500, detail=f"Error connecting to Ollama: {str(e)}")

def ensure_ai_model_exists(db: Session, model_name: str, model_type: str) -> AIModel:
    """Ensure AI model exists, create if it doesn't"""
    existing_model = db.query(AIModel).filter(
        AIModel.model_name == model_name,
        AIModel.model_type == model_type
    ).first()
    
    if not existing_model:
        new_model = AIModel(
            model_name=model_name,
            model_type=model_type,
            description=f"Auto-added {model_type} model: {model_name}",
            endpoint_url=OLLAMA_BASE_URL,
            is_active=False
        )
        db.add(new_model)
        db.flush()  # Get ID without committing
        return new_model
    
    return existing_model

@router.post("/api/active-models")
async def update_active_models(
    models: ActiveModelsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Update active models (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can update active models"
        )
    
    try:
        # Map of model fields to their types
        model_mapping = {
            "consultation_summary_model": "consultation_summary",
            "consultation_validation_model": "consultation_validation", 
            "discharge_note_summary_model": "discharge_note_summary",
            "discharge_note_validation_model": "discharge_note_validation",
            "audio_model": "audio_transcription"
        }
        
        # Process each model type
        for field_name, model_type in model_mapping.items():
            model_name = getattr(models, field_name, None)
            if model_name:
                # Deactivate all models of this type
                db.query(AIModel).filter(AIModel.model_type == model_type).update({"is_active": False})
                
                # Ensure model exists and activate it
                ai_model = ensure_ai_model_exists(db, model_name, model_type)
                ai_model.is_active = True
        
            
        db.commit()
        return {"message": "Active models updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/active-models")
async def get_active_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get currently active models"""
    try:
        # Check user permissions
        if current_user.role not in ['admin', 'user']:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this resource"
            )

        # Get currently active AI models
        active_models = {}
        
        model_types = [
            "consultation_summary",
            "consultation_validation", 
            "discharge_note_summary",
            "discharge_note_validation",
            "audio_transcription"
        ]
        
        for model_type in model_types:
            model = db.query(AIModel.model_name).filter(
                AIModel.model_type == model_type,
                AIModel.is_active == True
            ).first()
            
            # Convert type to camelCase for frontend
            key_mapping = {
                "consultation_summary": "consultationSummaryModel",
                "consultation_validation": "consultationValidationModel",
                "discharge_note_summary": "dischargeNoteSummaryModel", 
                "discharge_note_validation": "dischargeNoteValidationModel",
                "audio_transcription": "audioModel"
            }
            
            key = key_mapping.get(model_type)
            if key:
                active_models[key] = model[0] if model else None
        
        return active_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))