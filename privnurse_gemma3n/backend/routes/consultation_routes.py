from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime, timedelta
import math

from database import get_db
from models import ConsultationRecord, Patient, User
from schemas import (
    ConsultationRecordCreate, ConsultationRecordUpdate, 
    ConsultationRecordResponse, PaginatedResponse
)
from auth import get_current_user
from demo_dependencies import check_demo_mode

router = APIRouter()

@router.post("/api/consultations", response_model=ConsultationRecordResponse)
async def create_consultation_record(
    consultation_data: ConsultationRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create a new consultation record"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == consultation_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check for duplicate consultations - exact same record (except id and timestamps)
        query = db.query(ConsultationRecord).filter(
            ConsultationRecord.patient_id == consultation_data.patient_id,
            ConsultationRecord.original_content == consultation_data.original_content
        )
        
        # Add optional field checks if they are provided
        if consultation_data.doctor_name is not None:
            query = query.filter(ConsultationRecord.doctor_name == consultation_data.doctor_name)
        if consultation_data.department is not None:
            query = query.filter(ConsultationRecord.department == consultation_data.department)
        if consultation_data.ai_summary is not None:
            query = query.filter(ConsultationRecord.ai_summary == consultation_data.ai_summary)
        if consultation_data.nurse_confirmation is not None:
            query = query.filter(ConsultationRecord.nurse_confirmation == consultation_data.nurse_confirmation)
        
        query = query.filter(ConsultationRecord.consultation_type == consultation_data.consultation_type)
        
        existing_consultation = query.first()
        
        if existing_consultation:
            raise HTTPException(
                status_code=400,
                detail="Duplicate consultation detected. This exact consultation record already exists in the database."
            )
        
        # Create consultation record
        consultation = ConsultationRecord(
            **consultation_data.dict(),
            created_by=current_user.id
        )
        
        db.add(consultation)
        db.commit()
        db.refresh(consultation)
        
        return consultation
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/consultations", response_model=PaginatedResponse)
async def get_consultation_records(
    patient_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of consultation records with filtering"""
    try:
        # Base query
        query = db.query(ConsultationRecord)
        
        # Apply filters
        if patient_id:
            query = query.filter(ConsultationRecord.patient_id == patient_id)
        
        if department:
            query = query.filter(ConsultationRecord.department == department)
        
        if status:
            query = query.filter(ConsultationRecord.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        consultations = query.order_by(
            ConsultationRecord.consultation_date.desc()
        ).offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[ConsultationRecordResponse.from_orm(c) for c in consultations],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/consultations/{consultation_id}", response_model=ConsultationRecordResponse)
async def get_consultation_record(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific consultation record"""
    consultation = db.query(ConsultationRecord).filter(
        ConsultationRecord.id == consultation_id
    ).first()
    
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation record not found")
    
    return consultation

@router.put("/api/consultations/{consultation_id}", response_model=ConsultationRecordResponse)
async def update_consultation_record(
    consultation_id: int,
    consultation_data: ConsultationRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Update a consultation record"""
    try:
        consultation = db.query(ConsultationRecord).filter(
            ConsultationRecord.id == consultation_id
        ).first()
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation record not found")
        
        # Check if user can edit (creator or admin)
        if consultation.created_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="You can only edit your own consultation records"
            )
        
        # Update consultation fields
        update_data = consultation_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(consultation, field):
                setattr(consultation, field, value)
        
        # If confirming, set confirmation details
        if consultation_data.status == "confirmed":
            consultation.confirmed_by = current_user.id
            consultation.confirmed_at = func.now()
        
        db.commit()
        db.refresh(consultation)
        
        return consultation
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/consultations/{consultation_id}")
async def delete_consultation_record(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Delete a consultation record"""
    consultation = db.query(ConsultationRecord).filter(
        ConsultationRecord.id == consultation_id
    ).first()
    
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation record not found")
    
    # Check if user can delete (creator or admin)
    if consultation.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own consultation records"
        )
    
    try:
        db.delete(consultation)
        db.commit()
        return {"message": "Consultation record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}/consultations", response_model=PaginatedResponse)
async def get_patient_consultations(
    patient_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all consultation records for a specific patient"""
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
        # Get consultation records for patient
        query = db.query(ConsultationRecord).filter(
            ConsultationRecord.patient_id == patient_id
        )
        
        total = query.count()
        offset = (page - 1) * limit
        consultations = query.order_by(
            ConsultationRecord.consultation_date.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[ConsultationRecordResponse.from_orm(c) for c in consultations],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))