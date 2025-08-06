from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from decimal import Decimal
import json

# Legacy schemas for backward compatibility
class ValidationRequest(BaseModel):
    original: str
    summary: str
    user_id: int
    highlighted_result: str | None = None 

class SummaryRequest(BaseModel):
    content: str

class ConfirmationRequest(BaseModel):
    user_id: int
    patient_id: Optional[int] = None
    inference_type: Optional[str] = "consultation_summary"  # Default to consultation_summary for backward compatibility
    original_content: str
    nurse_confirmation: str
    ai_generated_result: str
    relevant_text: List[str]

class ActiveModelsUpdate(BaseModel):
    summary_model: Optional[str] = None
    validation_model: Optional[str] = None
    audio_model: Optional[str] = None
    consultation_summary_model: Optional[str] = None
    consultation_validation_model: Optional[str] = None
    discharge_note_summary_model: Optional[str] = None
    discharge_note_validation_model: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    user_id: int
    new_password: str

# New comprehensive schemas

# Diagnosis schemas
class Diagnosis(BaseModel):
    category: str  # 'Primary', 'Secondary', 'Past', 'Current'
    diagnosis: str
    code: Optional[str] = None  # ICD-10 or other medical codes
    date_diagnosed: Optional[date] = None

# Patient schemas
class PatientCreate(BaseModel):
    medical_record_no: str
    patient_category: str  # 'NHI General', 'NHI Injury', 'Self-Pay'
    name: str
    gender: str  # 'M', 'F'
    weight: Optional[Decimal] = None
    department: str
    birthday: date
    admission_time: Optional[datetime] = None
    bed_number: Optional[str] = None
    status: str = 'HOSPITALIZED'  # 'HOSPITALIZED', 'DISCHARGED', 'TRANSFERRED'
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    insurance_number: Optional[str] = None

class PatientUpdate(BaseModel):
    medical_record_no: Optional[str] = None
    patient_category: Optional[str] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    weight: Optional[Decimal] = None
    department: Optional[str] = None
    birthday: Optional[date] = None
    admission_time: Optional[datetime] = None
    discharge_time: Optional[datetime] = None
    bed_number: Optional[str] = None
    status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    insurance_number: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    medical_record_no: str
    patient_category: str
    name: str
    gender: str
    weight: Optional[Decimal]
    department: str
    birthday: date
    admission_time: Optional[datetime]
    discharge_time: Optional[datetime]
    bed_number: Optional[str]
    status: str
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    insurance_number: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]

    class Config:
        from_attributes = True

# User Management schemas
class UserCreateExtended(BaseModel):
    username: str
    password: str
    role: str = 'user'
    email: Optional[str] = None
    full_name: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True

class UserUpdateExtended(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: Optional[str]
    full_name: Optional[str]
    license_number: Optional[str]
    department: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

# Consultation Records schemas
class ConsultationRecordCreate(BaseModel):
    patient_id: int
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    consultation_type: str = 'initial'  # 'initial', 'follow_up', 'emergency', 'specialist'
    original_content: str
    ai_summary: Optional[str] = None
    nurse_confirmation: Optional[str] = None
    relevant_highlights: Optional[Dict[str, Any]] = None

class ConsultationRecordUpdate(BaseModel):
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    consultation_type: Optional[str] = None
    original_content: Optional[str] = None
    ai_summary: Optional[str] = None
    nurse_confirmation: Optional[str] = None
    relevant_highlights: Optional[Dict[str, Any]] = None
    status: Optional[str] = None  # 'draft', 'confirmed', 'archived'

class ConsultationRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_name: Optional[str]
    consultation_date: datetime
    department: Optional[str]
    consultation_type: str
    original_content: str
    ai_summary: Optional[str]
    nurse_confirmation: Optional[str]
    relevant_highlights: Optional[Dict[str, Any]]
    status: str
    created_by: int
    confirmed_by: Optional[int]
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True

# Discharge Notes schemas
class DischargeNoteCreate(BaseModel):
    patient_id: int
    chief_complaint: Optional[str] = None
    diagnosis: List[Diagnosis]
    treatment_course: Optional[str] = None
    discharge_date: Optional[datetime] = None

class DischargeNoteUpdate(BaseModel):
    chief_complaint: Optional[str] = None
    diagnosis: Optional[List[Diagnosis]] = None
    treatment_course: Optional[str] = None
    discharge_date: Optional[datetime] = None
    status: Optional[str] = None  # 'draft', 'pending_approval', 'approved'

class DischargeNoteResponse(BaseModel):
    id: int
    patient_id: int
    chief_complaint: Optional[str]
    diagnosis: List[Diagnosis]
    treatment_course: Optional[str]
    discharge_date: Optional[datetime]
    created_by: int
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    status: str

    @validator('diagnosis', pre=True)
    def parse_diagnosis(cls, v):
        """Convert JSON string to list of Diagnosis objects"""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [Diagnosis(**item) if isinstance(item, dict) else item for item in parsed]
                return []
            except:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True

# Nursing Notes schemas
class NursingNoteCreate(BaseModel):
    patient_id: int
    record_type: str  # Accept any string, will be mapped in the route
    content: str
    audio_file_path: Optional[str] = None
    transcription_text: Optional[str] = None
    shift: Optional[Literal['day', 'evening', 'night']] = None
    priority: Literal['low', 'medium', 'high'] = 'medium'
    
    @validator('record_type')
    def validate_and_map_record_type(cls, v):
        """Map old record types to new categories"""
        # Mapping dictionary
        mapping = {
            'Vital Signs': 'VitalSign',
            'vital signs': 'VitalSign',
            'VitalSigns': 'VitalSign',
            'Assessment': 'Objective',
            'assessment': 'Objective',
            'Patient Education': 'Intervention',
            'patient education': 'Intervention',
            'Medication Administration': 'Intervention',
            'medication administration': 'Intervention',
            'Procedure': 'Intervention',
            'procedure': 'Intervention',
            'Treatment': 'Intervention',
            'treatment': 'Intervention',
            'Care Plan': 'Intervention',
            'care plan': 'Intervention',
            'Observation': 'Objective',
            'observation': 'Objective',
            'Patient Complaint': 'Subjective',
            'patient complaint': 'Subjective',
            'Patient Response': 'Evaluation',
            'patient response': 'Evaluation',
            'Shift Report': 'NarrativeNote',
            'shift report': 'NarrativeNote',
            'Progress Note': 'NarrativeNote',
            'progress note': 'NarrativeNote',
            'General Note': 'NarrativeNote',
            'general note': 'NarrativeNote',
            'Discharge Planning': 'Intervention',
            'discharge planning': 'Intervention',
            'Incident Report': 'NarrativeNote',
            'incident report': 'NarrativeNote',
            # Already valid types
            'Subjective': 'Subjective',
            'Objective': 'Objective',
            'Intervention': 'Intervention',
            'Evaluation': 'Evaluation',
            'NarrativeNote': 'NarrativeNote',
            'VitalSign': 'VitalSign'
        }
        
        # Map the value
        mapped = mapping.get(v, 'NarrativeNote')  # Default to NarrativeNote
        
        # Validate it's a valid new type
        valid_types = ['Subjective', 'Objective', 'Intervention', 'Evaluation', 'NarrativeNote', 'VitalSign']
        if mapped not in valid_types:
            raise ValueError(f"Invalid record type: {v}")
        
        return mapped

class NursingNoteUpdate(BaseModel):
    record_type: Optional[str] = None
    content: Optional[str] = None
    audio_file_path: Optional[str] = None
    transcription_text: Optional[str] = None
    shift: Optional[Literal['day', 'evening', 'night']] = None
    priority: Optional[Literal['low', 'medium', 'high']] = None
    
    @validator('record_type')
    def validate_and_map_record_type(cls, v):
        """Map old record types to new categories"""
        if v is None:
            return None
            
        # Use the same mapping as NursingNoteCreate
        mapping = {
            'Vital Signs': 'VitalSign',
            'vital signs': 'VitalSign',
            'VitalSigns': 'VitalSign',
            'Assessment': 'Objective',
            'assessment': 'Objective',
            'Patient Education': 'Intervention',
            'patient education': 'Intervention',
            'Medication Administration': 'Intervention',
            'medication administration': 'Intervention',
            'Procedure': 'Intervention',
            'procedure': 'Intervention',
            'Treatment': 'Intervention',
            'treatment': 'Intervention',
            'Care Plan': 'Intervention',
            'care plan': 'Intervention',
            'Observation': 'Objective',
            'observation': 'Objective',
            'Patient Complaint': 'Subjective',
            'patient complaint': 'Subjective',
            'Patient Response': 'Evaluation',
            'patient response': 'Evaluation',
            'Shift Report': 'NarrativeNote',
            'shift report': 'NarrativeNote',
            'Progress Note': 'NarrativeNote',
            'progress note': 'NarrativeNote',
            'General Note': 'NarrativeNote',
            'general note': 'NarrativeNote',
            'Discharge Planning': 'Intervention',
            'discharge planning': 'Intervention',
            'Incident Report': 'NarrativeNote',
            'incident report': 'NarrativeNote',
            # Already valid types
            'Subjective': 'Subjective',
            'Objective': 'Objective',
            'Intervention': 'Intervention',
            'Evaluation': 'Evaluation',
            'NarrativeNote': 'NarrativeNote',
            'VitalSign': 'VitalSign'
        }
        
        # Map the value
        mapped = mapping.get(v, 'NarrativeNote')  # Default to NarrativeNote
        
        # Validate it's a valid new type
        valid_types = ['Subjective', 'Objective', 'Intervention', 'Evaluation', 'NarrativeNote', 'VitalSign']
        if mapped not in valid_types:
            raise ValueError(f"Invalid record type: {v}")
        
        return mapped

class NursingNoteResponse(BaseModel):
    id: int
    patient_id: int
    record_time: datetime
    record_type: str
    content: str
    audio_file_path: Optional[str]
    transcription_text: Optional[str]
    created_by: int
    shift: Optional[str]
    priority: str

    class Config:
        from_attributes = True

# Lab Reports schemas
class LabReportCreate(BaseModel):
    patient_id: int
    test_name: str
    test_date: date
    result_value: str
    result_unit: Optional[str] = None
    normal_range: Optional[str] = None
    flag: str = 'NORMAL'  # 'HIGH', 'LOW', 'CRITICAL', 'NORMAL'
    lab_technician: Optional[str] = None

class LabReportResponse(BaseModel):
    id: int
    patient_id: int
    test_name: str
    test_date: date
    result_value: str
    result_unit: Optional[str]
    normal_range: Optional[str]
    flag: str
    lab_technician: Optional[str]
    ordered_by: Optional[int]

    class Config:
        from_attributes = True

# AI Model Management schemas
class AIModelCreate(BaseModel):
    model_name: str
    model_type: str  # 'discharge_note_summary', 'discharge_note_validation', etc.
    model_version: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_active: bool = False
    performance_metrics: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None

class AIModelUpdate(BaseModel):
    model_name: Optional[str] = None
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_active: Optional[bool] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None

class AIModelResponse(BaseModel):
    id: int
    model_name: str
    model_type: str
    model_version: Optional[str]
    description: Optional[str]
    endpoint_url: Optional[str]
    is_active: bool
    performance_metrics: Optional[Dict[str, Any]]
    configuration: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# AI Inference schemas
class AIInferenceCreate(BaseModel):
    patient_id: Optional[int] = None
    inference_type: str  # 'consultation_summary', 'discharge_note', 'validation', 'transcription'
    original_content: str
    ai_generated_result: Optional[str] = None
    nurse_confirmation: Optional[str] = None
    relevant_text: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    confidence_score: Optional[Decimal] = None

class AIInferenceResponse(BaseModel):
    id: int
    user_id: int
    patient_id: Optional[int]
    inference_type: str
    original_content: str
    ai_generated_result: Optional[str]
    nurse_confirmation: Optional[str]
    relevant_text: Optional[Dict[str, Any]]
    model_used: Optional[str]
    processing_time_ms: Optional[int]
    confidence_score: Optional[Decimal]
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True

# Search and Filter schemas
class PatientSearchRequest(BaseModel):
    search_term: Optional[str] = None
    status: Optional[str] = None
    department: Optional[str] = None
    page: int = 1
    limit: int = 10

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int

# Discharge Note AI Generation schemas
class DischargeNoteRequest(BaseModel):
    patient_id: int

class DischargeValidationRequest(BaseModel):
    patient_id: int
    treatment_course: str