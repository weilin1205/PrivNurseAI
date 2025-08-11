# 🏥 PrivNurse AI - Medical Information System

A comprehensive medical information system with AI-powered assistance for patient management, consultations, and medical record handling.

## 🏗️ System Architecture

The system consists of:
- **Backend**: FastAPI-based REST API with MySQL database
- **Frontend**: Next.js React application with Material-UI and Chakra UI
- **AI Integration**: Ollama for local LLM inference and Gemma audio processing

## 📋 Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- MySQL 5.7+ or compatible
- Ollama (for AI features)
- FFmpeg (for audio processing)

## ⚙️ Installation

### 🖥️ Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a Python virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix/macOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# MySQL Database Configuration
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=inference_db

# Ollama API Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Gemma Audio API Configuration (optional)
GEMMA3N_API_KEY=your-gemma-api-key
GEMMA3N_API_URL=your-gemma-api-url

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here

# Demo Mode Configuration
DEMO_MODE=false
AUTO_LOGIN_ENABLED=false
AUTO_LOGIN_USERNAME=admin
```

5. Start the backend server:
```bash
python main.py
```

### 💻 Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env.local.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## 🚀 Running the System

### 🧪 Development Mode

1. Start MySQL server
2. Start Ollama (if using AI features):
```bash
ollama serve
```
3. Start backend:
```bash
cd backend
python main.py
```
4. Start frontend:
```bash
cd frontend
npm run dev
```

### 📦 Production Build

Frontend:
```bash
cd frontend
npm run build
npm start
```

Backend:
```bash
cd backend
python main.py
```

## ✨ Features

- **Patient Management**: Register and manage patient records
- **Consultation System**: Record medical consultations and diagnoses
- **Nursing Records**: Track vital signs and nursing care
- **Laboratory Results**: Manage lab test results
- **Discharge Management**: Handle patient discharge summaries
- **AI Assistant**: Get AI-powered medical insights and recommendations
- **Audio Transcription**: Convert voice recordings to text via Gemma-3n FastAPI server
- **Demo Mode**: Test the system without modifying real data
- **Multi-user Support**: Role-based access control for administrators and users

## 🔑 Default Credentials

After initialization, use these credentials:
- Username: `admin`
- Password: `password`

**Important**: Change the default password immediately after first login.

## 🚨 Troubleshooting

### Database Connection Issues
- Verify MySQL is running
- Check database credentials in `.env`
- Ensure database exists: `CREATE DATABASE inference_db;`

### Ollama Connection Issues
- Verify Ollama is installed and running
- Check the `OLLAMA_BASE_URL` in `.env`
- Pull required models: `ollama pull <Modle_Name>` (or your preferred model)

### Frontend Connection Issues
- Verify backend is running on the correct port
- Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Clear browser cache and cookies
