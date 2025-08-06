from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
import math

from database import get_db
from models import AIInference, User, Patient
from schemas import AIInferenceResponse, PaginatedResponse
from auth import get_current_user

router = APIRouter()

@router.get("/api/history", response_model=PaginatedResponse)
async def get_inference_history(
    search_term: Optional[str] = Query(None),
    inference_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated inference history with filtering and search"""
    try:
        # Base query - join with Patient for search capabilities
        query = db.query(AIInference).join(
            Patient, AIInference.patient_id == Patient.id, isouter=True
        )
        
        # Apply search filter
        if search_term:
            query = query.filter(
                or_(
                    AIInference.original_content.ilike(f"%{search_term}%"),
                    AIInference.ai_generated_result.ilike(f"%{search_term}%"),
                    AIInference.nurse_confirmation.ilike(f"%{search_term}%"),
                    Patient.name.ilike(f"%{search_term}%"),
                    Patient.medical_record_no.ilike(f"%{search_term}%")
                )
            )
        
        # Apply filters
        if inference_type:
            query = query.filter(AIInference.inference_type == inference_type)
        
        if status:
            query = query.filter(AIInference.status == status)
        
        if patient_id:
            query = query.filter(AIInference.patient_id == patient_id)
        
        # Filter by user (non-admin users can only see their own records)
        if current_user.role != "admin":
            query = query.filter(AIInference.user_id == current_user.id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * limit
        inferences = query.order_by(
            AIInference.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[AIInferenceResponse.from_orm(inference) for inference in inferences],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/{inference_id}", response_model=AIInferenceResponse)
async def get_inference_details(
    inference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific inference"""
    inference = db.query(AIInference).filter(AIInference.id == inference_id).first()
    
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")
    
    # Check permissions (users can only view their own inferences)
    if current_user.role != "admin" and inference.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own inference history"
        )
    
    return inference

@router.delete("/api/history/{inference_id}")
async def delete_inference(
    inference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an inference record (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can delete inference records"
        )
    
    inference = db.query(AIInference).filter(AIInference.id == inference_id).first()
    
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")
    
    try:
        db.delete(inference)
        db.commit()
        return {"message": "Inference record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/user/{user_id}", response_model=PaginatedResponse)
async def get_user_inference_history(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inference history for a specific user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view other users' history"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        query = db.query(AIInference).filter(AIInference.user_id == user_id)
        
        total = query.count()
        offset = (page - 1) * limit
        inferences = query.order_by(
            AIInference.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[AIInferenceResponse.from_orm(inference) for inference in inferences],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/patient/{patient_id}", response_model=PaginatedResponse)
async def get_patient_inference_history(
    patient_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inference history for a specific patient"""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        query = db.query(AIInference).filter(AIInference.patient_id == patient_id)
        
        # Non-admin users can only see their own inferences for the patient
        if current_user.role != "admin":
            query = query.filter(AIInference.user_id == current_user.id)
        
        total = query.count()
        offset = (page - 1) * limit
        inferences = query.order_by(
            AIInference.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[AIInferenceResponse.from_orm(inference) for inference in inferences],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/stats")
async def get_inference_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inference statistics and metrics"""
    try:
        base_query = db.query(AIInference)
        
        # Filter by user for non-admin users
        if current_user.role != "admin":
            base_query = base_query.filter(AIInference.user_id == current_user.id)
        
        # Total inferences
        total_inferences = base_query.count()
        
        # Inferences by status
        status_counts = {}
        for status in ['pending', 'processing', 'completed', 'confirmed', 'rejected']:
            count = base_query.filter(AIInference.status == status).count()
            status_counts[status] = count
        
        # Inferences by type
        type_counts = {}
        for inf_type in ['consultation_summary', 'discharge_note', 'validation', 'transcription']:
            count = base_query.filter(AIInference.inference_type == inf_type).count()
            type_counts[inf_type] = count
        
        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_count = base_query.filter(AIInference.created_at >= week_ago).count()
        
        return {
            "total_inferences": total_inferences,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "recent_activity": recent_count,
            "user_id": current_user.id,
            "is_admin": current_user.role == "admin"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))