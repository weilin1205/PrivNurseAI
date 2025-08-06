from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import math

from database import get_db
from models import NursingNote, Patient, User, AudioTranscription
from schemas import (
    NursingNoteCreate, NursingNoteUpdate, NursingNoteResponse, 
    PaginatedResponse
)
from auth import get_current_user
from demo_dependencies import check_demo_mode

router = APIRouter()

@router.post("/api/nursing-notes", response_model=NursingNoteResponse)
async def create_nursing_note(
    note_data: NursingNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create a new nursing note"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == note_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Create nursing note
        nursing_note = NursingNote(
            **note_data.dict(),
            created_by=current_user.id
        )
        
        db.add(nursing_note)
        db.commit()
        db.refresh(nursing_note)
        
        return nursing_note
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/nursing-notes", response_model=PaginatedResponse)
async def get_nursing_notes(
    patient_id: Optional[int] = Query(None),
    record_type: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of nursing notes with filtering"""
    try:
        # Base query
        query = db.query(NursingNote)
        
        # Apply filters
        if patient_id:
            query = query.filter(NursingNote.patient_id == patient_id)
        
        if record_type:
            query = query.filter(NursingNote.record_type == record_type)
        
        if shift:
            query = query.filter(NursingNote.shift == shift)
        
        if priority:
            query = query.filter(NursingNote.priority == priority)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        notes = query.order_by(
            NursingNote.record_time.desc()
        ).offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[NursingNoteResponse.from_orm(note) for note in notes],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/nursing-notes/{note_id}", response_model=NursingNoteResponse)
async def get_nursing_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific nursing note"""
    note = db.query(NursingNote).filter(NursingNote.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Nursing note not found")
    
    return note

@router.put("/api/nursing-notes/{note_id}", response_model=NursingNoteResponse)
async def update_nursing_note(
    note_id: int,
    note_data: NursingNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Update a nursing note"""
    try:
        note = db.query(NursingNote).filter(NursingNote.id == note_id).first()
        
        if not note:
            raise HTTPException(status_code=404, detail="Nursing note not found")
        
        # Check if user can edit (creator or admin)
        if note.created_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="You can only edit your own nursing notes"
            )
        
        # Update note fields
        update_data = note_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(note, field):
                setattr(note, field, value)
        
        db.commit()
        db.refresh(note)
        
        return note
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/nursing-notes/{note_id}")
async def delete_nursing_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Delete a nursing note"""
    note = db.query(NursingNote).filter(NursingNote.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Nursing note not found")
    
    # Check if user can delete (creator or admin)
    if note.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own nursing notes"
        )
    
    try:
        db.delete(note)
        db.commit()
        return {"message": "Nursing note deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}/nursing-notes", response_model=PaginatedResponse)
async def get_patient_nursing_notes(
    patient_id: int,
    record_type: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all nursing notes for a specific patient"""
    # Verify patient exists - use raw SQL to avoid JSON parsing issues
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT id FROM patients WHERE id = :patient_id"), {"patient_id": patient_id}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Patient not found")
    except Exception as e:
        print(f"DEBUG: Error checking patient existence: {str(e)}")
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Get nursing notes for patient
        query = db.query(NursingNote).filter(NursingNote.patient_id == patient_id)
        
        # Apply additional filters
        if record_type:
            query = query.filter(NursingNote.record_type == record_type)
        
        if shift:
            query = query.filter(NursingNote.shift == shift)
        
        total = query.count()
        offset = (page - 1) * limit
        notes = query.order_by(
            NursingNote.record_time.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[NursingNoteResponse.from_orm(note) for note in notes],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/nursing-notes/{note_id}/transcription")
async def create_audio_transcription(
    note_id: int,
    audio_file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create an audio transcription for a nursing note"""
    try:
        # Verify nursing note exists
        note = db.query(NursingNote).filter(NursingNote.id == note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Nursing note not found")
        
        # Create transcription record
        transcription = AudioTranscription(
            nursing_note_id=note_id,
            original_audio_path=audio_file_path,
            processing_status='pending'
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        return {
            "id": transcription.id,
            "nursing_note_id": note_id,
            "audio_file_path": audio_file_path,
            "status": "pending",
            "message": "Audio transcription queued for processing"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/record-types")
async def get_record_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all nursing note record types"""
    record_types = [
        'Vital Signs',
        'Medication Administration', 
        'Assessment',
        'Care Plan',
        'Patient Education',
        'Discharge Planning',
        'Incident Report'
    ]
    return record_types