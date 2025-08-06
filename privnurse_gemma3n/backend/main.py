import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal
from init_database import initialize_database
from models import User, SystemSetting
from auth import get_password_hash
from routes.auth_routes import router as auth_router
from routes.ai_routes import router as ai_router
from routes.patient_routes import router as patient_router
from routes.consultation_routes import router as consultation_router
from routes.nursing_routes import router as nursing_router
from routes.lab_routes import router as lab_router
from routes.discharge_routes import router as discharge_router
from routes.history_routes import router as history_router
from routes.sample_data_routes import router as sample_data_router
from routes.audio_routes import router as audio_router

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="PrivNurse AI API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(patient_router)
app.include_router(consultation_router)
app.include_router(nursing_router)
app.include_router(lab_router)
app.include_router(discharge_router)
app.include_router(history_router)
app.include_router(sample_data_router)
app.include_router(audio_router)

def create_default_admin():
    """Create default admin user if no users exist"""
    db = SessionLocal()
    try:
        # Check if any users exist
        user_count = db.query(User).count()
        if user_count == 0:
            # Create admin account with extended fields
            hashed_password = get_password_hash("password")
            admin_user = User(
                username="admin",
                password_hash=hashed_password,
                role="admin",
                full_name="System Administrator",
                email="admin@privnurse.ai",
                department="Administration",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default admin user")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()

def create_default_settings():
    """Create default system settings"""
    db = SessionLocal()
    try:
        # Check if settings exist
        settings_count = db.query(SystemSetting).count()
        if settings_count == 0:
            default_settings = [
                SystemSetting(
                    setting_key="app_name",
                    setting_value="PrivNurse AI",
                    setting_type="string",
                    description="Application name",
                    is_public=True
                ),
                SystemSetting(
                    setting_key="max_file_size",
                    setting_value="10485760",
                    setting_type="integer",
                    description="Maximum file upload size in bytes",
                    is_public=False
                ),
                SystemSetting(
                    setting_key="session_timeout",
                    setting_value="3600",
                    setting_type="integer",
                    description="Session timeout in seconds",
                    is_public=False
                ),
                SystemSetting(
                    setting_key="enable_audio_transcription",
                    setting_value="true",
                    setting_type="boolean",
                    description="Enable audio transcription features",
                    is_public=True
                ),
                SystemSetting(
                    setting_key="default_department",
                    setting_value="General Medicine",
                    setting_type="string",
                    description="Default department for new patients",
                    is_public=True
                )
            ]
            
            for setting in default_settings:
                db.add(setting)
            
            db.commit()
            logger.info("Created default system settings")
    except Exception as e:
        logger.error(f"Error creating default settings: {str(e)}")
        db.rollback()
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting PrivNurse AI API")
    initialize_database()  # This handles both table creation and enum migration
    create_default_admin()
    create_default_settings()
    logger.info("System initialization completed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "PrivNurse AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/endpoints")
async def list_endpoints():
    """List all available API endpoints"""
    return {
        "authentication": {
            "POST /api/login": "User login",
            "POST /api/users": "Create user (admin only)",
            "GET /api/users": "List users (admin only)",
            "POST /api/users/{user_id}/reset-password": "Reset password (admin only)"
        },
        "patients": {
            "GET /api/patients": "List patients with filtering and pagination",
            "POST /api/patients": "Create new patient",
            "GET /api/patients/{patient_id}": "Get patient details",
            "PUT /api/patients/{patient_id}": "Update patient",
            "DELETE /api/patients/{patient_id}": "Delete patient (admin only)",
            "GET /api/patients/{patient_id}/history": "Get patient change history",
            "GET /api/departments": "List all departments"
        },
        "consultations": {
            "GET /api/consultations": "List consultation records",
            "POST /api/consultations": "Create consultation record",
            "GET /api/consultations/{consultation_id}": "Get consultation details",
            "PUT /api/consultations/{consultation_id}": "Update consultation",
            "DELETE /api/consultations/{consultation_id}": "Delete consultation",
            "GET /api/patients/{patient_id}/consultations": "Get patient consultations"
        },
        "nursing_notes": {
            "GET /api/nursing-notes": "List nursing notes",
            "POST /api/nursing-notes": "Create nursing note",
            "GET /api/nursing-notes/{note_id}": "Get nursing note details",
            "PUT /api/nursing-notes/{note_id}": "Update nursing note",
            "DELETE /api/nursing-notes/{note_id}": "Delete nursing note",
            "GET /api/patients/{patient_id}/nursing-notes": "Get patient nursing notes",
            "POST /api/nursing-notes/{note_id}/transcription": "Create audio transcription",
            "GET /api/record-types": "List nursing note record types"
        },
        "lab_reports": {
            "GET /api/lab-reports": "List lab reports",
            "POST /api/lab-reports": "Create lab report",
            "GET /api/lab-reports/{report_id}": "Get lab report details",
            "DELETE /api/lab-reports/{report_id}": "Delete lab report (admin only)",
            "GET /api/patients/{patient_id}/lab-reports": "Get patient lab reports",
            "GET /api/lab-reports/critical": "Get critical lab reports"
        },
        "discharge_notes": {
            "GET /api/discharge-notes": "List discharge notes",
            "POST /api/discharge-notes": "Create discharge note",
            "GET /api/discharge-notes/{note_id}": "Get discharge note details",
            "PUT /api/discharge-notes/{note_id}": "Update discharge note",
            "DELETE /api/discharge-notes/{note_id}": "Delete discharge note",
            "GET /api/patients/{patient_id}/discharge-note": "Get patient discharge note",
            "POST /api/discharge-notes/{note_id}/approve": "Approve discharge note (admin only)",
            "GET /api/discharge-notes/pending-approval": "Get pending discharge notes (admin only)"
        },
        "history": {
            "GET /api/history": "Get inference history with filtering",
            "GET /api/history/{inference_id}": "Get inference details",
            "DELETE /api/history/{inference_id}": "Delete inference (admin only)",
            "GET /api/history/user/{user_id}": "Get user inference history (admin only)",
            "GET /api/history/patient/{patient_id}": "Get patient inference history",
            "GET /api/history/stats": "Get inference statistics"
        },
        "ai_processing": {
            "POST /gen-summary": "Generate AI summary (streaming)",
            "POST /gen-validation": "Generate AI validation",
            "POST /api/submit-confirmation": "Submit inference confirmation",
            "GET /api/tags": "List available Ollama models",
            "GET /api/active-models": "Get active AI models",
            "POST /api/active-models": "Update active models (admin only)"
        },
        "sample_data": {
            "POST /api/initialize-sample-data": "Create sample data (admin only)",
            "DELETE /api/clear-sample-data": "Clear sample data (admin only)"
        }
    }

if __name__ == '__main__':
    import uvicorn
    logger.info("Starting FastAPI server")
    uvicorn.run(app, host="0.0.0.0", port=8000)