from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import math

from database import get_db
from models import Patient, User, PatientHistory
from schemas import (
    PatientCreate, PatientUpdate, PatientResponse, 
    PatientSearchRequest, PaginatedResponse, UserResponse
)
from auth import get_current_user
from utils.validators import validate_patient_category
from demo_dependencies import check_demo_mode

router = APIRouter()

@router.post("/api/patients", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create a new patient record"""
    try:
        # Check if medical record number already exists
        existing_patient = db.query(Patient).filter(
            Patient.medical_record_no == patient_data.medical_record_no
        ).first()
        
        if existing_patient:
            raise HTTPException(
                status_code=400,
                detail="Patient with this medical record number already exists"
            )
        
        # Validate patient category
        patient_dict = patient_data.dict()
        patient_dict['patient_category'] = validate_patient_category(patient_dict['patient_category'])
        
        # Create new patient
        new_patient = Patient(
            **patient_dict,
            created_by=current_user.id
        )
        
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        
        return new_patient
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients", response_model=PaginatedResponse)
async def get_patients(
    search_term: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of patients with filtering"""
    try:
        # Base query
        query = db.query(Patient)
        
        # Apply search filter
        if search_term:
            query = query.filter(
                or_(
                    Patient.name.ilike(f"%{search_term}%"),
                    Patient.medical_record_no.ilike(f"%{search_term}%"),
                    Patient.bed_number.ilike(f"%{search_term}%")
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(Patient.status == status)
        
        # Apply department filter
        if department:
            query = query.filter(Patient.department == department)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        patients = query.offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[PatientResponse.from_orm(patient) for patient in patients],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific patient by ID"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return patient

@router.put("/api/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Update a patient record"""
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Store old values for history tracking
        old_values = {
            "medical_record_no": patient.medical_record_no,
            "name": patient.name,
            "department": patient.department,
            "status": patient.status,
            "bed_number": patient.bed_number
        }
        
        # Update patient fields
        update_data = patient_data.dict(exclude_unset=True)
        
        # Validate patient category if it's being updated
        if 'patient_category' in update_data and update_data['patient_category'] is not None:
            update_data['patient_category'] = validate_patient_category(update_data['patient_category'])
        
        for field, value in update_data.items():
            if hasattr(patient, field):
                setattr(patient, field, value)
        
        db.commit()
        db.refresh(patient)
        
        # Create history entries for changed fields
        for field, old_value in old_values.items():
            new_value = getattr(patient, field)
            if str(old_value) != str(new_value):
                history_entry = PatientHistory(
                    patient_id=patient.id,
                    field_name=field,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    changed_by=current_user.id
                )
                db.add(history_entry)
        
        db.commit()
        return patient
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/patients/{patient_id}")
async def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Delete a patient record (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can delete patients"
        )
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        db.delete(patient)
        db.commit()
        return {"message": "Patient deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}/history")
async def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get patient change history"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history = db.query(PatientHistory).filter(
        PatientHistory.patient_id == patient_id
    ).order_by(PatientHistory.changed_at.desc()).all()
    
    return {
        "patient_id": patient_id,
        "history": [
            {
                "id": h.id,
                "field_name": h.field_name,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at
            }
            for h in history
        ]
    }

@router.get("/api/departments")
async def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all departments"""
    departments = db.query(Patient.department).distinct().all()
    return [dept[0] for dept in departments if dept[0]]