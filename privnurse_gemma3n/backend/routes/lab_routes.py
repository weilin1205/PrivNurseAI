from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import math

from database import get_db
from models import LabReport, Patient, User
from schemas import LabReportCreate, LabReportResponse, PaginatedResponse
from auth import get_current_user
from demo_dependencies import check_demo_mode

router = APIRouter()

@router.post("/api/lab-reports", response_model=LabReportResponse)
async def create_lab_report(
    report_data: LabReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create a new lab report"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == report_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Create lab report
        lab_report = LabReport(
            **report_data.dict(),
            ordered_by=current_user.id
        )
        
        db.add(lab_report)
        db.commit()
        db.refresh(lab_report)
        
        return lab_report
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/lab-reports", response_model=PaginatedResponse)
async def get_lab_reports(
    patient_id: Optional[int] = Query(None),
    test_name: Optional[str] = Query(None),
    flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of lab reports with filtering"""
    try:
        # Base query
        query = db.query(LabReport)
        
        # Apply filters
        if patient_id:
            query = query.filter(LabReport.patient_id == patient_id)
        
        if test_name:
            query = query.filter(LabReport.test_name.ilike(f"%{test_name}%"))
        
        if flag:
            query = query.filter(LabReport.flag == flag)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        reports = query.order_by(
            LabReport.test_date.desc()
        ).offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[LabReportResponse.from_orm(report) for report in reports],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/lab-reports/{report_id}", response_model=LabReportResponse)
async def get_lab_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lab report"""
    report = db.query(LabReport).filter(LabReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Lab report not found")
    
    return report

@router.delete("/api/lab-reports/{report_id}")
async def delete_lab_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Delete a lab report (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can delete lab reports"
        )
    
    report = db.query(LabReport).filter(LabReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Lab report not found")
    
    try:
        db.delete(report)
        db.commit()
        return {"message": "Lab report deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}/lab-reports", response_model=PaginatedResponse)
async def get_patient_lab_reports(
    patient_id: int,
    test_name: Optional[str] = Query(None),
    flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all lab reports for a specific patient"""
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
        # Get lab reports for patient
        query = db.query(LabReport).filter(LabReport.patient_id == patient_id)
        
        # Apply additional filters
        if test_name:
            query = query.filter(LabReport.test_name.ilike(f"%{test_name}%"))
        
        if flag:
            query = query.filter(LabReport.flag == flag)
        
        total = query.count()
        offset = (page - 1) * limit
        reports = query.order_by(
            LabReport.test_date.desc(),
            LabReport.id.desc()  # Secondary sort by ID to ensure consistent ordering for same date
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[LabReportResponse.from_orm(report) for report in reports],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/lab-reports/critical")
async def get_critical_lab_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get critical lab reports across all patients"""
    try:
        query = db.query(LabReport).filter(LabReport.flag == 'CRITICAL')
        
        total = query.count()
        offset = (page - 1) * limit
        reports = query.order_by(
            LabReport.test_date.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[LabReportResponse.from_orm(report) for report in reports],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))