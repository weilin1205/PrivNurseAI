from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
import math
import json
from datetime import datetime

from database import get_db
from models import DischargeNote, Patient, User, NursingNote, AIInference, AIModel, ConsultationRecord, LabReport
from schemas import (
    DischargeNoteCreate, DischargeNoteUpdate, DischargeNoteResponse, 
    PaginatedResponse, DischargeNoteRequest, DischargeValidationRequest
)
from auth import get_current_user
from services.ollama_service import OllamaService
from demo_dependencies import check_demo_mode
import re
from typing import List, Tuple
from config import OLLAMA_BASE_URL

router = APIRouter()

# XML Generation Functions (based on reference_xml_generator.py)

def clean_text(text):
    """Clean text by removing HTML tags and ensuring string format"""
    if text is None or (hasattr(text, '__len__') and len(text) == 0):
        return ""
    text_str = str(text)
    # Remove <p> and </p> tags
    text_str = re.sub(r'</?p>', '', text_str).strip()
    # Escape XML special characters
    text_str = text_str.replace('&', '&amp;')
    text_str = text_str.replace('<', '&lt;')
    text_str = text_str.replace('>', '&gt;')
    text_str = text_str.replace('"', '&quot;')
    text_str = text_str.replace("'", '&apos;')
    return text_str

def get_length_hint(content_length: int) -> str:
    """Return length hint based on content character count"""
    if content_length < 1200:  # Adjusted for character count vs word count
        return "short"
    elif 1200 <= content_length < 2100:
        return "medium"
    else:
        return "long"

def format_diagnosis_list(diagnosis_data) -> Tuple[str, str, str, str]:
    """Extract diagnosis data by category: Primary, Secondary, Past, Present"""
    primary_diagnosis = ""
    secondary_diagnosis = ""
    past_medical_history = ""
    present_illness = ""
    
    try:
        if diagnosis_data:
            if isinstance(diagnosis_data, str):
                # Try to parse as JSON
                try:
                    import json
                    parsed = json.loads(diagnosis_data)
                    if isinstance(parsed, list):
                        primary_diagnoses = []
                        secondary_diagnoses = []
                        past_diagnoses = []
                        present_diagnoses = []
                        
                        for d in parsed:
                            if isinstance(d, dict):
                                category = d.get('category', '').lower()
                                diagnosis_text = d.get('diagnosis', '')
                                code = d.get('code', '')
                                
                                # Format diagnosis with code if available
                                if code and diagnosis_text:
                                    formatted_diagnosis = f"{diagnosis_text} ({code})"
                                elif diagnosis_text:
                                    formatted_diagnosis = diagnosis_text
                                else:
                                    formatted_diagnosis = str(d)
                                
                                # Categorize diagnosis
                                if 'primary' in category:
                                    primary_diagnoses.append(formatted_diagnosis)
                                elif 'secondary' in category:
                                    secondary_diagnoses.append(formatted_diagnosis)
                                elif 'past' in category:
                                    past_diagnoses.append(formatted_diagnosis)
                                elif 'present' in category or 'current' in category:
                                    present_diagnoses.append(formatted_diagnosis)
                                else:
                                    # Default to secondary if category unknown
                                    secondary_diagnoses.append(formatted_diagnosis)
                            else:
                                # If not a dict, convert to string and add to primary
                                primary_diagnoses.append(str(d))
                        
                        # Join diagnoses with semicolon separator
                        primary_diagnosis = "; ".join(primary_diagnoses)
                        secondary_diagnosis = "; ".join(secondary_diagnoses)
                        past_medical_history = "; ".join(past_diagnoses)
                        present_illness = "; ".join(present_diagnoses)
                    else:
                        # If parsed is not a list, treat as primary diagnosis
                        primary_diagnosis = str(parsed)
                except Exception as json_error:
                    # If JSON parsing fails, treat as primary diagnosis
                    print(f"DEBUG: JSON parsing failed: {str(json_error)}")
                    primary_diagnosis = str(diagnosis_data)
            elif isinstance(diagnosis_data, list):
                # If it's already a list (not JSON string), process it directly
                primary_diagnoses = []
                secondary_diagnoses = []
                past_diagnoses = []
                present_diagnoses = []
                
                for d in diagnosis_data:
                    if isinstance(d, dict):
                        category = d.get('category', '').lower()
                        diagnosis_text = d.get('diagnosis', '')
                        code = d.get('code', '')
                        
                        # Format diagnosis with code if available
                        if code and diagnosis_text:
                            formatted_diagnosis = f"{diagnosis_text} ({code})"
                        elif diagnosis_text:
                            formatted_diagnosis = diagnosis_text
                        else:
                            formatted_diagnosis = str(d)
                        
                        # Categorize diagnosis
                        if 'primary' in category:
                            primary_diagnoses.append(formatted_diagnosis)
                        elif 'secondary' in category:
                            secondary_diagnoses.append(formatted_diagnosis)
                        elif 'past' in category:
                            past_diagnoses.append(formatted_diagnosis)
                        elif 'present' in category or 'current' in category:
                            present_diagnoses.append(formatted_diagnosis)
                        else:
                            # Default to secondary if category unknown
                            secondary_diagnoses.append(formatted_diagnosis)
                    else:
                        # If not a dict, convert to string and add to primary
                        primary_diagnoses.append(str(d))
                
                # Join diagnoses with semicolon separator
                primary_diagnosis = "; ".join(primary_diagnoses)
                secondary_diagnosis = "; ".join(secondary_diagnoses)
                past_medical_history = "; ".join(past_diagnoses)
                present_illness = "; ".join(present_diagnoses)
            else:
                # For any other type, convert to string
                primary_diagnosis = str(diagnosis_data)
    except Exception as e:
        print(f"DEBUG: Error parsing diagnosis: {str(e)}")
        # In case of any error, try to convert to string
        try:
            primary_diagnosis = str(diagnosis_data)
        except:
            primary_diagnosis = "Error parsing diagnosis data"
    
    return clean_text(primary_diagnosis), clean_text(secondary_diagnosis), clean_text(past_medical_history), clean_text(present_illness)

def format_nursing_events(nursing_notes: List) -> List[Tuple[datetime, str]]:
    """Convert nursing notes to chronological XML events"""
    events = []
    
    for note in nursing_notes:
        try:
            timestamp = note.record_time
            if not timestamp:
                continue
            
            record_type = note.record_type
            content = clean_text(note.content)
            
            # Format based on record type
            if record_type == 'VitalSign':
                # Parse vital sign format from content
                # Expected format: "type:BP|value:120/80 mmHg" or just direct content
                vital_type = record_type
                vital_value = content
                
                # Try to parse structured format
                if '|' in content and 'type:' in content and 'value:' in content:
                    parts = content.split('|')
                    for part in parts:
                        if part.startswith('type:'):
                            vital_type = part.replace('type:', '').strip()
                        elif part.startswith('value:'):
                            vital_value = part.replace('value:', '').strip()
                
                xml_string = f"""<NursingEvent timestamp="{timestamp.strftime('%Y-%m-%d %H:%M:%S')}">
    <VitalSign type="{vital_type}" value="{vital_value}" />
</NursingEvent>"""
            
            else:
                # For SOAP categories (Subjective, Objective, Intervention, Evaluation, NarrativeNote)
                soap_elements = []
                
                if record_type in ['Subjective', 'Objective', 'Intervention', 'Evaluation']:
                    soap_elements.append(f"    <{record_type}>{content}</{record_type}>")
                elif record_type == 'NarrativeNote':
                    soap_elements.append(f"    <NarrativeNote>{content}</NarrativeNote>")
                else:
                    # Default to NarrativeNote if unknown type
                    soap_elements.append(f"    <NarrativeNote>{content}</NarrativeNote>")
                
                soap_content = '\n'.join(soap_elements)
                xml_string = f"""<NursingEvent timestamp="{timestamp.strftime('%Y-%m-%d %H:%M:%S')}">
    <SOAPNote>
{soap_content}
    </SOAPNote>
</NursingEvent>"""
            
            events.append((timestamp, xml_string))
        except Exception as e:
            print(f"DEBUG: Error formatting nursing event: {str(e)}")
            continue
    
    return events

def format_lab_events(lab_reports: List) -> List[Tuple[datetime, str]]:
    """Convert lab reports to chronological XML events"""
    events = []
    
    if not lab_reports:
        print("DEBUG: No lab reports to format")
        return events
    
    print(f"DEBUG: Formatting {len(lab_reports)} lab reports")
    
    # Group by date
    date_groups = {}
    for report in lab_reports:
        try:
            test_date = report.test_date
            if test_date not in date_groups:
                date_groups[test_date] = []
            date_groups[test_date].append(report)
        except Exception as e:
            print(f"DEBUG: Error grouping lab report: {str(e)}")
            continue
    
    print(f"DEBUG: Lab reports grouped into {len(date_groups)} date groups")
    
    # Create XML for each date group
    for date, reports in date_groups.items():
        try:
            items_xml = []
            for report in reports:
                test_name = clean_text(report.test_name)
                result_value = clean_text(report.result_value)
                if report.result_unit:
                    result_value += f" {clean_text(report.result_unit)}"
                if report.flag and report.flag != 'NORMAL':
                    result_value += f" ({report.flag})"
                
                items_xml.append(f'    <Item name="{test_name}">{result_value}</Item>')
            
            xml_string = f"""<LabReportGroup date="{date.strftime('%Y-%m-%d')}">
{chr(10).join(items_xml)}
</LabReportGroup>"""
            
            # Use date as timestamp (morning time)
            timestamp = datetime.combine(date, datetime.min.time())
            events.append((timestamp, xml_string))
        except Exception as e:
            print(f"DEBUG: Error formatting lab events for date {date}: {str(e)}")
            continue
    
    return events

def format_consultation_events(consultations: List) -> List[Tuple[datetime, str]]:
    """Convert consultation records to chronological XML events"""
    events = []
    
    for consultation in consultations:
        try:
            timestamp = consultation.consultation_date
            if not timestamp:
                continue
                
            # Only use nurse confirmation for consultation content
            content = clean_text(consultation.nurse_confirmation) if consultation.nurse_confirmation else ""
            
            # Skip if no nurse confirmation available
            if not content:
                continue
            
            xml_string = f"""<Consultation timestamp="{timestamp.strftime('%Y-%m-%d %H:%M:%S')}">
    <Content>
    {content}
    </Content>
</Consultation>"""
            
            events.append((timestamp, xml_string))
        except Exception as e:
            print(f"DEBUG: Error formatting consultation event: {str(e)}")
            continue
    
    return events

def generate_discharge_xml(patient, discharge_note, nursing_notes: List, lab_reports: List, consultations: List) -> str:
    """Generate the complete XML structure for discharge note LLM input"""
    
    try:
        # Extract diagnosis information - first from discharge note, then from patient
        diagnosis_data = None
        if discharge_note and hasattr(discharge_note, 'diagnosis'):
            diagnosis_data = discharge_note.diagnosis
        elif patient and hasattr(patient, 'diagnosis'):
            diagnosis_data = patient.diagnosis
            
        primary_diagnosis, secondary_diagnosis, past_medical_history, present_illness_from_diagnosis = format_diagnosis_list(diagnosis_data)
        
        # Get chief complaint - first from discharge note, then from patient
        chief_complaint = ''
        if discharge_note and hasattr(discharge_note, 'chief_complaint'):
            chief_complaint = discharge_note.chief_complaint
        elif patient and hasattr(patient, 'chief_complaint'):
            chief_complaint = patient.chief_complaint
        
        # For PresentIllness, prioritize diagnosis-based present illness, then patient notes
        present_illness = present_illness_from_diagnosis
        if not present_illness:
            if patient and hasattr(patient, 'notes'):
                present_illness = patient.notes
        
        # Collect all chronological events
        all_events = []
        
        # Add nursing events
        nursing_events = format_nursing_events(nursing_notes)
        all_events.extend(nursing_events)
        print(f"DEBUG: Added {len(nursing_events)} nursing events")
        
        # Add lab events
        lab_events = format_lab_events(lab_reports)
        all_events.extend(lab_events)
        print(f"DEBUG: Added {len(lab_events)} lab events")
        
        # Add consultation events
        consultation_events = format_consultation_events(consultations)
        all_events.extend(consultation_events)
        print(f"DEBUG: Added {len(consultation_events)} consultation events")
        
        # Sort all events by timestamp
        all_events.sort(key=lambda x: x[0])
        print(f"DEBUG: Total events to include in XML: {len(all_events)}")
        
        # Extract sorted XML strings
        sorted_events_xml = "\n".join([event[1] for event in all_events])
        
        # Calculate total content length for length hint
        total_content = f"{chief_complaint or ''} {primary_diagnosis} {secondary_diagnosis} {past_medical_history} {present_illness} {sorted_events_xml}"
        length_hint = get_length_hint(len(total_content))
        
        # Generate the complete XML structure
        xml_content = f"""<PatientEncounter summary_length_style="{length_hint}">
    <Summary>
        <PrimaryDiagnosis>{primary_diagnosis}</PrimaryDiagnosis>
        <SecondaryDiagnosis>{secondary_diagnosis}</SecondaryDiagnosis>
        <PastMedicalHistory>{past_medical_history}</PastMedicalHistory>
        <ChiefComplaint>{clean_text(chief_complaint or '')}</ChiefComplaint>
        <PresentIllness>{clean_text(present_illness or '')}</PresentIllness>
    </Summary>
    <ChronologicalEvents>
        {sorted_events_xml}
    </ChronologicalEvents>
</PatientEncounter>"""
        
        return xml_content
        
    except Exception as e:
        print(f"DEBUG: Error generating discharge XML: {str(e)}")
        # Return a minimal XML structure in case of errors
        return f"""<PatientEncounter summary_length_style="short">
    <Summary>
        <PrimaryDiagnosis></PrimaryDiagnosis>
        <SecondaryDiagnosis></SecondaryDiagnosis>
        <PastMedicalHistory></PastMedicalHistory>
        <ChiefComplaint></ChiefComplaint>
        <PresentIllness></PresentIllness>
    </Summary>
    <ChronologicalEvents>
    </ChronologicalEvents>
</PatientEncounter>"""

@router.post("/api/discharge-notes", response_model=DischargeNoteResponse)
async def create_discharge_note(
    discharge_data: DischargeNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create a new discharge note"""
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == discharge_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check if discharge note already exists for patient
        existing_note = db.query(DischargeNote).filter(
            DischargeNote.patient_id == discharge_data.patient_id
        ).first()
        
        if existing_note:
            raise HTTPException(
                status_code=400,
                detail="Discharge note already exists for this patient"
            )
        
        # Create discharge note
        # Convert diagnosis list to JSON for storage
        discharge_dict = discharge_data.dict()
        if 'diagnosis' in discharge_dict and isinstance(discharge_dict['diagnosis'], list):
            discharge_dict['diagnosis'] = json.dumps([d.dict() if hasattr(d, 'dict') else d for d in discharge_dict['diagnosis']])
        
        discharge_note = DischargeNote(
            **discharge_dict,
            created_by=current_user.id
        )
        
        db.add(discharge_note)
        db.commit()
        db.refresh(discharge_note)
        
        return discharge_note
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/discharge-notes", response_model=PaginatedResponse)
async def get_discharge_notes(
    patient_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of discharge notes with filtering"""
    try:
        # Base query
        query = db.query(DischargeNote)
        
        # Apply filters
        if patient_id:
            query = query.filter(DischargeNote.patient_id == patient_id)
        
        if status:
            query = query.filter(DischargeNote.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        notes = query.order_by(
            DischargeNote.discharge_date.desc()
        ).offset(offset).limit(limit).all()
        
        # Calculate total pages
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[DischargeNoteResponse.from_orm(note) for note in notes],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug-discharge-setup")
async def debug_discharge_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check discharge note setup"""
    try:
        # Check if there are any AI models
        all_models = db.query(AIModel).all()
        discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary'
        ).all()
        active_discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary',
            AIModel.is_active == True
        ).all()
        
        # Check if there are any patients
        patients = db.query(Patient).limit(5).all()
        
        return {
            "total_ai_models": len(all_models),
            "discharge_note_models": len(discharge_models),
            "active_discharge_models": len(active_discharge_models),
            "model_details": [
                {
                    "id": model.id,
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "is_active": model.is_active
                } for model in all_models
            ],
            "total_patients": db.query(Patient).count(),
            "sample_patients": [
                {
                    "id": patient.id,
                    "name": patient.name
                } for patient in patients
            ],
            "ollama_config": {
                "base_url": OLLAMA_BASE_URL,
                "generate_url": f"{OLLAMA_BASE_URL}/api/generate"
            }
        }
    except Exception as e:
        return {"error": str(e)}

# AI Generation Endpoints

@router.post("/gen-discharge-summary")
async def generate_discharge_summary(
    request: DischargeNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate discharge note summary by stitching patient data from MySQL and sending to LLM"""
    try:
        print(f"DEBUG: Received request for patient_id: {request.patient_id}")
        
        # Verify patient exists - handle JSON parsing errors
        try:
            patient = db.query(Patient).filter(Patient.id == request.patient_id).first()
        except Exception as e:
            print(f"DEBUG: Error querying patient: {str(e)}")
            # If JSON parsing fails, try to get patient with raw SQL
            from sqlalchemy import text
            result = db.execute(text("SELECT * FROM patients WHERE id = :patient_id"), {"patient_id": request.patient_id}).fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # Create a mock patient object with the basic info we need
            class MockPatient:
                def __init__(self, row):
                    self.id = row[0]
                    self.medical_record_no = row[1] if len(row) > 1 else ""
                    self.name = row[4] if len(row) > 4 else "Unknown"
                    self.gender = row[5] if len(row) > 5 else "Unknown"
                    self.weight = row[7] if len(row) > 7 else 0
                    self.department = row[8] if len(row) > 8 else ""
                    self.bed_number = row[9] if len(row) > 9 else ""
                    self.birthday = row[6] if len(row) > 6 else None
                    self.admission_time = row[10] if len(row) > 10 else None
                    self.status = row[11] if len(row) > 11 else "HOSPITALIZED"
                    self.chief_complaint = row[12] if len(row) > 12 else ""
                    self.diagnosis = "[]"  # Default to empty JSON array
                    self.notes = row[14] if len(row) > 14 else ""
            
            patient = MockPatient(result)
            print(f"DEBUG: Using mock patient object due to JSON parsing error")
        
        if not patient:
            print(f"DEBUG: Patient not found for ID: {request.patient_id}")
            raise HTTPException(status_code=404, detail="Patient not found")

        print(f"DEBUG: Found patient: {patient.name}")

        # Get active discharge note summary model
        discharge_model = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary',
            AIModel.is_active == True
        ).first()
        
        if not discharge_model:
            print("DEBUG: No active discharge note summary model found")
            raise HTTPException(status_code=400, detail="No active discharge note summary model configured")

        print(f"DEBUG: Using model: {discharge_model.model_name}")

        # Gather patient data and generate XML structure
        try:
            nursing_notes, lab_reports, consultations = await stitch_discharge_data_for_xml(db, patient)
            print(f"DEBUG: Gathered data - Nursing: {len(nursing_notes)}, Labs: {len(lab_reports)}, Consultations: {len(consultations)}")
            
            # Get existing discharge note for this patient (if any)
            discharge_note = db.query(DischargeNote).filter(
                DischargeNote.patient_id == patient.id
            ).first()
            
            # Generate XML formatted input
            xml_input = generate_discharge_xml(patient, discharge_note, nursing_notes, lab_reports, consultations)
            print(f"DEBUG: Generated XML length: {len(xml_input)}")
            # Print first 2000 characters of XML to check lab reports
            print(f"DEBUG: XML preview:\n{xml_input[:2000]}...")
            
            # Create the prompt for discharge note LLM
            prompt = create_discharge_xml_prompt(xml_input)
            print(f"DEBUG: Final prompt length: {len(prompt)}")
            
        except Exception as e:
            print(f"DEBUG: Error preparing XML data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error preparing patient data: {str(e)}")
        
        # Initialize Ollama service
        try:
            ollama_service = OllamaService()
            print("DEBUG: Ollama service initialized")
        except Exception as e:
            print(f"DEBUG: Error initializing Ollama service: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error initializing Ollama service: {str(e)}")
        
        # Stream response from Ollama
        async def generate():
            print("Prompt:", prompt)  # Log first 1000 characters of prompt for debugging
            try:
                print("DEBUG: Starting stream generation")
                chunk_count = 0
                async for chunk in ollama_service.generate_stream(
                    model=discharge_model.model_name,
                    prompt=prompt
                ):
                    chunk_count += 1
                    if chunk_count <= 3:  # Log first few chunks
                        print(f"DEBUG: Chunk {chunk_count}: {chunk[:100]}...")
                    yield chunk
                print(f"DEBUG: Stream completed with {chunk_count} chunks")
            except Exception as e:
                print(f"DEBUG: Error in stream generation: {str(e)}")
                error_response = {
                    "model": discharge_model.model_name,
                    "created_at": "2024-01-01T00:00:00Z",
                    "response": f"Error generating discharge summary: {str(e)}",
                    "done": True
                }
                yield f"{json.dumps(error_response)}\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/gen-discharge-validation")
async def validate_discharge_note(
    request: DischargeValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate discharge note and return relevant text highlighting"""
    try:
        # Get active discharge note validation model
        validation_model = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_validation',
            AIModel.is_active == True
        ).first()
        
        if not validation_model:
            raise HTTPException(status_code=400, detail="No active discharge note validation model configured")

        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == request.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Get existing discharge note for this patient (if any)
        discharge_note = db.query(DischargeNote).filter(
            DischargeNote.patient_id == patient.id
        ).first()

        # Gather patient data and generate XML structure
        nursing_notes, lab_reports, consultations = await stitch_discharge_data_for_xml(db, patient)
        
        # Generate XML formatted input (same as for summary generation)
        xml_input = generate_discharge_xml(patient, discharge_note, nursing_notes, lab_reports, consultations)
        
        # Create validation prompt using XML format
        validation_prompt = f"{xml_input}\n<Discharge_Summary>\n{request.treatment_course}\n</Discharge_Summary>"
        
        print(f"DEBUG: Validation prompt length: {len(validation_prompt)}")
        print(f"\n{'='*80}")
        print("DEBUG: VALIDATION PROMPT:")
        print(f"{'='*80}")
        print(validation_prompt)
        print(f"{'='*80}\n")
        
        # Initialize Ollama service
        ollama_service = OllamaService()
        
        # Get validation response
        validation_response = await ollama_service.generate_completion(
            model=validation_model.model_name,
            prompt=validation_prompt
        )
        
        print(f"\n{'='*80}")
        print("DEBUG: VALIDATION RESPONSE:")
        print(f"{'='*80}")
        print(validation_response)
        print(f"{'='*80}\n")
        
        # Extract relevant text for highlighting
        relevant_text = extract_relevant_text_from_validation(validation_response, xml_input)
        
        print(f"\n{'='*80}")
        print(f"DEBUG: EXTRACTED RELEVANT TERMS ({len(relevant_text)} terms):")
        print(f"{'='*80}")
        for i, term in enumerate(relevant_text, 1):
            print(f"{i}. {term}")
        print(f"{'='*80}\n")
        
        return {
            "relevant_text": relevant_text,
            "validation_model": validation_model.model_name,
            "patient_id": request.patient_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug-discharge-setup")
async def debug_discharge_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check discharge note setup"""
    try:
        # Check if there are any AI models
        all_models = db.query(AIModel).all()
        discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary'
        ).all()
        active_discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary',
            AIModel.is_active == True
        ).all()
        
        # Check if there are any patients
        patients = db.query(Patient).limit(5).all()
        
        return {
            "total_ai_models": len(all_models),
            "discharge_note_models": len(discharge_models),
            "active_discharge_models": len(active_discharge_models),
            "model_details": [
                {
                    "id": model.id,
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "is_active": model.is_active
                } for model in all_models
            ],
            "total_patients": db.query(Patient).count(),
            "sample_patients": [
                {
                    "id": patient.id,
                    "name": patient.name
                } for patient in patients
            ],
            "ollama_config": {
                "base_url": OLLAMA_BASE_URL,
                "generate_url": f"{OLLAMA_BASE_URL}/api/generate"
            }
        }
    except Exception as e:
        return {"error": str(e)}

def safe_isoformat(date_obj):
    """Safely convert date to isoformat string"""
    if date_obj is None:
        return None
    if isinstance(date_obj, str):
        return date_obj  # Already a string
    if hasattr(date_obj, 'isoformat'):
        return date_obj.isoformat()
    return str(date_obj)


async def stitch_discharge_data_for_xml(db: Session, patient) -> Tuple[List, List, List]:
    """Gather all relevant patient data for XML generation"""
    
    # Get recent nursing notes (last 20 for comprehensive data)
    try:
        nursing_notes = db.query(NursingNote).filter(
            NursingNote.patient_id == patient.id
        ).order_by(NursingNote.record_time.desc()).limit(20).all()
    except Exception as e:
        print(f"DEBUG: Error querying nursing notes: {str(e)}")
        nursing_notes = []
    
    # Get recent lab reports (last 365 days to ensure we get all relevant data)
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=365)
        lab_reports = db.query(LabReport).filter(
            LabReport.patient_id == patient.id,
            LabReport.test_date >= cutoff_date.date()
        ).order_by(LabReport.test_date.desc()).all()
        print(f"DEBUG: Lab reports query - found {len(lab_reports) if lab_reports else 0} reports for patient {patient.id}")
    except Exception as e:
        print(f"DEBUG: Error querying lab reports: {str(e)}")
        lab_reports = []
    
    # Get recent consultation records (last 10)
    try:
        consultations = db.query(ConsultationRecord).filter(
            ConsultationRecord.patient_id == patient.id
        ).order_by(ConsultationRecord.consultation_date.desc()).limit(10).all()
    except Exception as e:
        print(f"DEBUG: Error querying consultations: {str(e)}")
        consultations = []
    
    return nursing_notes, lab_reports, consultations

async def stitch_discharge_data(db: Session, patient) -> dict:
    """Stitch together all relevant patient data for discharge note generation"""
    
    # Get recent nursing notes (last 10) - handle potential JSON errors
    try:
        nursing_notes = db.query(NursingNote).filter(
            NursingNote.patient_id == patient.id
        ).order_by(NursingNote.record_time.desc()).limit(10).all()
    except Exception as e:
        print(f"DEBUG: Error querying nursing notes: {str(e)}")
        nursing_notes = []
    
    # Get recent consultation inferences - handle potential JSON errors  
    try:
        consultation_inferences = db.query(AIInference).filter(
            AIInference.patient_id == patient.id,
            AIInference.inference_type == 'consultation_summary'
        ).order_by(AIInference.created_at.desc()).limit(5).all()
    except Exception as e:
        print(f"DEBUG: Error querying consultation inferences: {str(e)}")
        consultation_inferences = []
    
    # Stitch together the comprehensive discharge data
    discharge_data = {
        # Patient Basic Information
        "patient_info": {
            "id": patient.id,
            "name": patient.name,
            "medical_record_no": patient.medical_record_no,
            "gender": patient.gender,
            "age": calculate_age(patient.birthday) if patient.birthday else "Unknown",
            "weight": patient.weight,
            "department": patient.department,
            "bed_number": patient.bed_number,
            "admission_time": safe_isoformat(patient.admission_time),
            "status": patient.status
        },
        
        # Medical History - will be fetched from discharge_notes table now
        "medical_info": {
            "chief_complaint": "",  # Now stored in discharge_notes
            "diagnosis": "",        # Now stored in discharge_notes
            "notes": ""            # Now stored in discharge_notes
        },
        
        # Nursing Notes Summary
        "nursing_notes": [
            {
                "record_time": safe_isoformat(note.record_time),
                "record_type": note.record_type,
                "content": note.content,
                "priority": note.priority
            }
            for note in nursing_notes
        ],
        
        # Recent Consultation Summaries
        "consultation_summaries": [
            {
                "created_at": safe_isoformat(inf.created_at),
                "ai_generated_result": inf.ai_generated_result,
                "nurse_confirmation": inf.nurse_confirmation,
                "status": inf.status
            }
            for inf in consultation_inferences
        ],
        
        # Additional metadata
        "discharge_preparation": {
            "total_nursing_notes": len(nursing_notes),
            "total_consultations": len(consultation_inferences),
            "last_nursing_note": safe_isoformat(nursing_notes[0].record_time) if nursing_notes else None,
            "last_consultation": safe_isoformat(consultation_inferences[0].created_at) if consultation_inferences else None
        }
    }
    
    return discharge_data

def create_discharge_xml_prompt(xml_input: str) -> str:
    """Create a prompt for discharge note generation using XML structured input"""
    
    return xml_input

def create_discharge_summary_prompt(discharge_data: dict) -> str:
    """Create a comprehensive prompt for discharge note generation"""
    
    patient_info = discharge_data["patient_info"]
    medical_info = discharge_data["medical_info"]
    nursing_notes = discharge_data["nursing_notes"]
    consultations = discharge_data["consultation_summaries"]
    
    prompt = f"""Generate a comprehensive discharge note treatment course for the following patient:

PATIENT INFORMATION:
- Name: {patient_info['name']}
- Medical Record No: {patient_info['medical_record_no']}
- Age: {patient_info['age']}, Gender: {patient_info['gender']}, Weight: {patient_info['weight']}kg
- Department: {patient_info['department']}, Bed: {patient_info['bed_number']}
- Admission Date: {patient_info['admission_time']}
- Current Status: {patient_info['status']}

MEDICAL HISTORY:
- Chief Complaint: {medical_info['chief_complaint']}
- Diagnosis: {medical_info['diagnosis']}
- Additional Notes: {medical_info['notes']}

NURSING NOTES SUMMARY ({len(nursing_notes)} recent notes):"""

    # Add nursing notes
    for i, note in enumerate(nursing_notes[:5], 1):  # Limit to 5 most recent
        prompt += f"""
{i}. [{note['record_time']}] {note['record_type']} - Priority: {note['priority']}
   {note['content']}"""

    # Add consultation summaries
    if consultations:
        prompt += f"""

RECENT CONSULTATION SUMMARIES ({len(consultations)} summaries):"""
        for i, consultation in enumerate(consultations[:3], 1):  # Limit to 3 most recent
            prompt += f"""
{i}. [{consultation['created_at']}] Status: {consultation['status']}
   AI Summary: {consultation['ai_generated_result'][:500]}...
   Nurse Confirmation: {consultation['nurse_confirmation'][:300]}..."""

    prompt += """

Based on all the above information, please generate a comprehensive TREATMENT COURSE for this patient's discharge note. The treatment course should include:

1. Initial Assessment and Stabilization
2. Diagnostic Workup and Monitoring
3. Treatment Implementation and Interventions
4. Patient Response and Progress
5. Discharge Planning and Follow-up Care
6. Patient Education and Home Care Instructions
7. Follow-up Appointments and Monitoring

Please provide a detailed, professional treatment course that synthesizes all the available patient information."""

    return prompt

def create_discharge_validation_prompt(original_data: dict, treatment_course: str) -> str:
    """Create validation prompt for discharge note highlighting"""
    
    prompt = f"""Please validate the following discharge note treatment course against the original patient data.

ORIGINAL PATIENT DATA:
{json.dumps(original_data, indent=2)}

GENERATED TREATMENT COURSE:
{treatment_course}

Please identify key terms and phrases from the treatment course that are directly supported by or derived from the original patient data. Focus on:
1. Medical conditions and diagnoses
2. Treatment interventions mentioned in nursing notes
3. Patient responses and progress indicators
4. Discharge planning elements
5. Follow-up care recommendations

Return the key terms that should be highlighted for validation."""

    return prompt

def extract_relevant_text_from_validation(validation_response: str, xml_input: str) -> list:
    """Extract relevant text for highlighting from validation response"""
    
    # Parse validation response to extract key terms
    # The validation model should return JSON-like structure with relevant terms
    relevant_terms = []
    
    try:
        # Try to parse JSON from validation response
        import json
        
        # Look for JSON structure in the response
        json_start = validation_response.find('{')
        json_end = validation_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = validation_response[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Extract relevant terms from parsed JSON
            if 'relevant_text' in parsed:
                relevant_terms = parsed['relevant_text']
            elif 'highlights' in parsed:
                relevant_terms = parsed['highlights']
            elif 'key_terms' in parsed:
                relevant_terms = parsed['key_terms']
            elif 'relevant_highlights' in parsed:
                relevant_terms = parsed['relevant_highlights']
        else:
            # Fallback: extract key medical terms from the response
            import re
            
            # Extract terms in quotes
            quoted_terms = re.findall(r'"([^"]+)"', validation_response)
            relevant_terms.extend(quoted_terms[:20])
            
            # Extract medical terms (basic pattern)
            medical_pattern = r'\b(?:diagnosis|medication|treatment|symptom|procedure|test|result):\s*([^,\n]+)'
            medical_matches = re.findall(medical_pattern, validation_response, re.IGNORECASE)
            relevant_terms.extend([m.strip() for m in medical_matches[:10]])
    
    except Exception as e:
        print(f"DEBUG: Error parsing validation response: {str(e)}")
        # Fallback to simple extraction
        words = validation_response.split()
        relevant_terms = [w for w in words if len(w) > 5][:20]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_terms = []
    for term in relevant_terms:
        if term and term not in seen:
            seen.add(term)
            unique_terms.append(term)
    
    return unique_terms

def calculate_age(birthday) -> str:
    """Calculate age from birthday"""
    
    if not birthday:
        return "Unknown"
    
    try:
        if isinstance(birthday, str):
            birthday = datetime.fromisoformat(birthday.replace('Z', '+00:00'))
        
        today = datetime.now()
        age = today.year - birthday.year
        
        if today.month < birthday.month or (today.month == birthday.month and today.day < birthday.day):
            age -= 1
            
        return str(age)
    except:
        return "Unknown"

@router.get("/api/discharge-notes/{note_id}", response_model=DischargeNoteResponse)
async def get_discharge_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific discharge note"""
    note = db.query(DischargeNote).filter(DischargeNote.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Discharge note not found")
    
    return note

@router.put("/api/discharge-notes/{note_id}", response_model=DischargeNoteResponse)
async def update_discharge_note(
    note_id: int,
    discharge_data: DischargeNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Update a discharge note"""
    try:
        note = db.query(DischargeNote).filter(DischargeNote.id == note_id).first()
        
        if not note:
            raise HTTPException(status_code=404, detail="Discharge note not found")
        
        # Check if user can edit (creator or admin)
        if note.created_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="You can only edit your own discharge notes"
            )
        
        # Update note fields
        update_data = discharge_data.dict(exclude_unset=True)
        
        # Convert diagnosis list to JSON for storage
        if 'diagnosis' in update_data and isinstance(update_data['diagnosis'], list):
            update_data['diagnosis'] = json.dumps([d.dict() if hasattr(d, 'dict') else d for d in update_data['diagnosis']])
        
        for field, value in update_data.items():
            if hasattr(note, field):
                setattr(note, field, value)
        
        # If approving, set approval details
        if discharge_data.status == "approved":
            note.approved_by = current_user.id
            note.approved_at = func.now()
        
        db.commit()
        db.refresh(note)
        
        return note
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/discharge-notes/{note_id}")
async def delete_discharge_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Delete a discharge note"""
    note = db.query(DischargeNote).filter(DischargeNote.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Discharge note not found")
    
    # Check if user can delete (creator or admin)
    if note.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own discharge notes"
        )
    
    try:
        db.delete(note)
        db.commit()
        return {"message": "Discharge note deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/patients/{patient_id}/discharge-note", response_model=DischargeNoteResponse)
async def get_patient_discharge_note(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get discharge note for a specific patient"""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get discharge note for patient
    note = db.query(DischargeNote).filter(
        DischargeNote.patient_id == patient_id
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Discharge note not found for this patient")
    
    return note

@router.post("/api/discharge-notes/{note_id}/approve")
async def approve_discharge_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Approve a discharge note (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can approve discharge notes"
        )
    
    note = db.query(DischargeNote).filter(DischargeNote.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Discharge note not found")
    
    try:
        note.status = "approved"
        note.approved_by = current_user.id
        note.approved_at = func.now()
        
        db.commit()
        db.refresh(note)
        
        return {
            "message": "Discharge note approved successfully",
            "note_id": note_id,
            "approved_by": current_user.id,
            "approved_at": note.approved_at
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/discharge-notes/{patient_id}/submit-final")
async def submit_final_discharge_note(
    patient_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Submit final discharge note with treatment course"""
    try:
        # Check if discharge note exists for this patient
        discharge_note = db.query(DischargeNote).filter(
            DischargeNote.patient_id == patient_id
        ).first()
        
        if not discharge_note:
            # Create new discharge note if it doesn't exist
            discharge_note = DischargeNote(
                patient_id=patient_id,
                created_by=current_user.id,
                chief_complaint=request.get('chiefComplaint', ''),
                diagnosis=json.dumps(request.get('diagnosis', [])),
                discharge_date=datetime.now().date()
            )
            db.add(discharge_note)
        
        # Update treatment course and diagnosis
        discharge_note.treatment_course = request.get('treatmentCourse', '')
        discharge_note.chief_complaint = request.get('chiefComplaint', '')
        
        # Handle diagnosis - convert to JSON string if it's a list
        diagnosis = request.get('diagnosis', [])
        if isinstance(diagnosis, list):
            discharge_note.diagnosis = json.dumps(diagnosis)
        else:
            discharge_note.diagnosis = diagnosis
            
        discharge_note.status = 'approved'  # Use valid status
        discharge_note.discharge_date = datetime.now()
        
        db.commit()
        db.refresh(discharge_note)
        
        return {
            "message": "Discharge note submitted successfully",
            "discharge_note_id": discharge_note.id,
            "patient_id": patient_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/discharge-notes/pending-approval", response_model=PaginatedResponse)
async def get_pending_discharge_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get discharge notes pending approval (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view pending discharge notes"
        )
    
    try:
        query = db.query(DischargeNote).filter(
            DischargeNote.status == "pending_approval"
        )
        
        total = query.count()
        offset = (page - 1) * limit
        notes = query.order_by(
            DischargeNote.discharge_date.desc()
        ).offset(offset).limit(limit).all()
        
        pages = math.ceil(total / limit)
        
        return PaginatedResponse(
            items=[DischargeNoteResponse.from_orm(note) for note in notes],
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug-discharge-setup")
async def debug_discharge_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check discharge note setup"""
    try:
        # Check if there are any AI models
        all_models = db.query(AIModel).all()
        discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary'
        ).all()
        active_discharge_models = db.query(AIModel).filter(
            AIModel.model_type == 'discharge_note_summary',
            AIModel.is_active == True
        ).all()
        
        # Check if there are any patients
        patients = db.query(Patient).limit(5).all()
        
        return {
            "total_ai_models": len(all_models),
            "discharge_note_models": len(discharge_models),
            "active_discharge_models": len(active_discharge_models),
            "model_details": [
                {
                    "id": model.id,
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "is_active": model.is_active
                } for model in all_models
            ],
            "total_patients": db.query(Patient).count(),
            "sample_patients": [
                {
                    "id": patient.id,
                    "name": patient.name
                } for patient in patients
            ],
            "ollama_config": {
                "base_url": OLLAMA_BASE_URL,
                "generate_url": f"{OLLAMA_BASE_URL}/api/generate"
            }
        }
    except Exception as e:
        return {"error": str(e)}