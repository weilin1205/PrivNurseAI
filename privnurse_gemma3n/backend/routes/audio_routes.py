from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database import get_db
from models import User, NursingNote, Patient
from auth import get_current_user
from services.gemma_audio_service import gemma_client

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/audio/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    patient_id: int = Form(...),
    record_type: Optional[str] = Form(None),
    context: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transcribe audio file using Gemma Audio API - returns transcription only"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Validate file type (more lenient)
        allowed_types = [
            'audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/mp4',
            'audio/ogg', 'audio/x-m4a', 'audio/x-wav', 'application/octet-stream'
        ]
        # Some browsers might not set content type correctly
        if audio_file.content_type and audio_file.content_type not in allowed_types:
            logger.warning(f"Unusual audio content type: {audio_file.content_type}, allowing anyway")
            # Don't block - let Gemma API handle it
        
        # Check file size (max 10MB)
        file_size = 0
        temp_file = await audio_file.read()
        file_size = len(temp_file)
        await audio_file.seek(0)  # Reset file pointer
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Create context text for better transcription
        context_text = f"Patient: {patient.name}"
        if record_type:
            context_text += f", Record Type: {record_type}"
        if context:
            context_text += f", {context}"
        
        # Send to Gemma API for transcription
        logger.info(f"Attempting to transcribe audio for patient {patient.name}")
        result = await gemma_client.transcribe_audio(audio_file, context_text)
        
        if not result:
            logger.error("Gemma API returned no result")
            raise HTTPException(status_code=500, detail="Failed to transcribe audio - no response from Gemma API")
        
        # Extract transcribed text from Gemma response
        transcribed_text = result.get('generated_text', '') or result.get('text', '') or result.get('transcription', '')
        
        if not transcribed_text:
            logger.error(f"No transcription in result: {result}")
            raise HTTPException(status_code=500, detail="No transcription generated - check response format")
        
        # Clean up common unwanted prefixes that models might add
        unwanted_prefixes = [
            "Okay, here's the transcription of the audio:",
            "Here's the transcription:",
            "Here is the transcription:",
            "Transcription:",
            "Okay,",
            "Sure,",
            "The transcription is:",
            "I've transcribed the following:",
            "The audio says:",
        ]
        
        cleaned_text = transcribed_text.strip()
        for prefix in unwanted_prefixes:
            if cleaned_text.lower().startswith(prefix.lower()):
                cleaned_text = cleaned_text[len(prefix):].strip()
                logger.info(f"Removed unwanted prefix: '{prefix}'")
                break
        
        # Return just the transcription without creating a nursing note
        return {
            "success": True,
            "transcription": cleaned_text,
            "gemma_response": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in audio transcription: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/audio/test-connection")
async def test_gemma_connection(
    current_user: User = Depends(get_current_user)
):
    """Test connection to Gemma Audio API"""
    logger.info(f"Testing Gemma API connection at {gemma_client.base_url}")
    if gemma_client.test_connection():
        return {
            "status": "connected", 
            "message": "Gemma Audio API is accessible",
            "api_url": gemma_client.base_url,
            "has_api_key": bool(gemma_client.api_key and gemma_client.api_key != "your-gemma-api-key")
        }
    else:
        raise HTTPException(
            status_code=503, 
            detail=f"Cannot connect to Gemma Audio API at {gemma_client.base_url}"
        )