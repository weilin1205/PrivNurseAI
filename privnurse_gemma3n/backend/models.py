from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Date, DECIMAL, Enum, JSON, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
import json

class SafeJSON(TypeDecorator):
    """A JSON column type that safely handles null and empty values"""
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, return None instead of raising an error
            return None

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'user', name='user_role'), nullable=False, default='user', index=True)
    email = Column(String(100))
    full_name = Column(String(100))
    license_number = Column(String(50))
    department = Column(String(100), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP)

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    ip_address = Column(String(45))
    user_agent = Column(Text)

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    medical_record_no = Column(String(50), nullable=False, unique=True, index=True)
    patient_category = Column(Enum('NHI General', 'NHI Injury', 'Self-Pay', name='patient_category'), nullable=False)
    name = Column(String(100), nullable=False, index=True)
    gender = Column(Enum('M', 'F', name='gender'), nullable=False)
    weight = Column(DECIMAL(5,2))
    department = Column(String(100), nullable=False, index=True)
    birthday = Column(Date, nullable=False)
    admission_time = Column(TIMESTAMP, index=True)
    discharge_time = Column(TIMESTAMP)
    bed_number = Column(String(20))
    status = Column(Enum('HOSPITALIZED', 'DISCHARGED', 'TRANSFERRED', name='patient_status'), default='HOSPITALIZED', index=True)
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    insurance_number = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('users.id'))

class PatientHistory(Base):
    __tablename__ = "patient_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    field_name = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    changed_at = Column(TIMESTAMP, server_default=func.now(), index=True)

class AIModel(Base):
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False, unique=True)
    model_type = Column(Enum('discharge_note_summary', 'discharge_note_validation', 
                            'consultation_summary', 'consultation_validation', 
                            'audio_transcription', 'general', name='model_type'), 
                       nullable=False, index=True)
    model_version = Column(String(50))
    description = Column(Text)
    endpoint_url = Column(String(255))
    is_active = Column(Boolean, default=False, index=True)
    performance_metrics = Column(SafeJSON)
    configuration = Column(SafeJSON)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class ModelConfiguration(Base):
    __tablename__ = "model_configurations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discharge_note_summary_model_id = Column(Integer, ForeignKey('ai_models.id'))
    discharge_note_validation_model_id = Column(Integer, ForeignKey('ai_models.id'))
    consultation_summary_model_id = Column(Integer, ForeignKey('ai_models.id'))
    consultation_validation_model_id = Column(Integer, ForeignKey('ai_models.id'))
    audio_transcription_model_id = Column(Integer, ForeignKey('ai_models.id'))
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)

class ConsultationRecord(Base):
    __tablename__ = "consultation_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_name = Column(String(100))
    consultation_date = Column(TIMESTAMP, server_default=func.now(), index=True)
    department = Column(String(100), index=True)
    consultation_type = Column(Enum('initial', 'follow_up', 'emergency', 'specialist', name='consultation_type'), default='initial')
    original_content = Column(Text, nullable=False)
    ai_summary = Column(Text)
    nurse_confirmation = Column(Text)
    relevant_highlights = Column(SafeJSON)
    status = Column(Enum('draft', 'confirmed', 'archived', name='consultation_status'), default='draft', index=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    confirmed_by = Column(Integer, ForeignKey('users.id'))
    confirmed_at = Column(TIMESTAMP)

class DischargeNote(Base):
    __tablename__ = "discharge_notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    chief_complaint = Column(Text)
    diagnosis = Column(JSON, nullable=False)  # Store as list of {category, diagnosis, code, date_diagnosed}
    treatment_course = Column(Text)
    discharge_date = Column(TIMESTAMP, index=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id'))
    approved_at = Column(TIMESTAMP)
    status = Column(Enum('draft', 'pending_approval', 'approved', name='discharge_status'), default='draft', index=True)

class LabReport(Base):
    __tablename__ = "lab_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    test_name = Column(String(100), nullable=False)
    test_date = Column(Date, nullable=False, index=True)
    result_value = Column(String(50), nullable=False)
    result_unit = Column(String(20))
    normal_range = Column(String(50))
    flag = Column(Enum('HIGH', 'LOW', 'CRITICAL', 'NORMAL', name='result_flag'), default='NORMAL', index=True)
    lab_technician = Column(String(100))
    ordered_by = Column(Integer, ForeignKey('users.id'))

class NursingNote(Base):
    __tablename__ = "nursing_notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    record_time = Column(TIMESTAMP, server_default=func.now(), index=True)
    record_type = Column(Enum('Subjective', 'Objective', 'Intervention', 
                             'Evaluation', 'NarrativeNote', 'VitalSign', 
                             name='nursing_record_type'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    audio_file_path = Column(String(255))
    transcription_text = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    shift = Column(Enum('day', 'evening', 'night', name='shift'))
    priority = Column(Enum('low', 'medium', 'high', name='priority'), default='medium')

class AudioTranscription(Base):
    __tablename__ = "audio_transcriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nursing_note_id = Column(Integer, ForeignKey('nursing_notes.id', ondelete='CASCADE'), index=True)
    original_audio_path = Column(String(255), nullable=False)
    transcription_text = Column(Text)
    transcription_confidence = Column(DECIMAL(3,2))
    processing_status = Column(Enum('pending', 'processing', 'completed', 'failed', name='processing_status'), default='pending', index=True)
    model_used = Column(String(100))
    processed_at = Column(TIMESTAMP)
    error_message = Column(Text)

class AIInference(Base):
    __tablename__ = "ai_inferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='SET NULL'), index=True)
    inference_type = Column(Enum('consultation_summary', 'discharge_note', 'validation', 'transcription', name='inference_type'), nullable=False, index=True)
    original_content = Column(Text, nullable=False)
    ai_generated_result = Column(Text)
    nurse_confirmation = Column(Text)
    relevant_text = Column(SafeJSON)
    model_used = Column(String(100))
    processing_time_ms = Column(Integer)
    confidence_score = Column(DECIMAL(3,2))
    status = Column(Enum('pending', 'processing', 'completed', 'confirmed', 'rejected', name='inference_status'), default='pending', index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    confirmed_at = Column(TIMESTAMP)

class AIProcessingLog(Base):
    __tablename__ = "ai_processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    inference_id = Column(Integer, ForeignKey('ai_inferences.id', ondelete='CASCADE'), index=True)
    model_name = Column(String(100), nullable=False, index=True)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    processing_time_ms = Column(Integer)
    api_endpoint = Column(String(255))
    request_payload = Column(SafeJSON)
    response_payload = Column(SafeJSON)
    error_message = Column(Text)
    status = Column(Enum('success', 'failure', 'timeout', name='log_status'), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), nullable=False, unique=True, index=True)
    setting_value = Column(Text)
    setting_type = Column(Enum('string', 'integer', 'boolean', 'json', name='setting_type'), default='string')
    description = Column(Text)
    is_public = Column(Boolean, default=False, index=True)
    updated_by = Column(Integer, ForeignKey('users.id'))
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    action = Column(String(100), nullable=False, index=True)
    table_name = Column(String(100), index=True)
    record_id = Column(Integer)
    old_values = Column(SafeJSON)
    new_values = Column(SafeJSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

