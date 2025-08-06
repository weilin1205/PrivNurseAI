import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "inference_db")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Ollama API configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
if not OLLAMA_BASE_URL:
    raise ValueError("OLLAMA_BASE_URL environment variable is required")
GENERATE_URL = f'{OLLAMA_BASE_URL}/api/generate'
TAGS_URL = f'{OLLAMA_BASE_URL}/api/tags'

# Gemma Audio API configuration
GEMMA_API_KEY = os.getenv("GEMMA3N_API_KEY", "your-gemma-api-key")
GEMMA_API_URL = os.getenv("GEMMA3N_API_URL")
if not GEMMA_API_URL:
    raise ValueError("GEMMA_API_URL environment variable is required")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

# Password hashing configuration
SEPARATOR = "@"  # Used for separating hash and salt

# Auto-login configuration for competition mode
AUTO_LOGIN_ENABLED = os.getenv("AUTO_LOGIN_ENABLED", "false").lower() == "true"
AUTO_LOGIN_USERNAME = os.getenv("AUTO_LOGIN_USERNAME", "admin")

# Demo mode configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"