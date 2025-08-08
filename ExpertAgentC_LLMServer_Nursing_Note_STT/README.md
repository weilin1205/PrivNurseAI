# PrivNurse Gemma-3n Speech-to-Text Server

A production-ready FastAPI service for Google's Gemma-3n-E4B model with full audio processing capabilities. This API provides multimodal text generation supporting both text-only and audio+text inputs.

![Nursing Note STT Demo](/assets/nursing_note_stt_demo.png)

## ✨Features

- **🎵 Audio Processing**: Support for `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg` audio formats
- **🔐 Secure Authentication**: Bearer token authentication with API key management
- **⚡ Rate Limiting**: Built-in rate limiting to prevent abuse
- **📊 Health Monitoring**: Comprehensive health checks and monitoring
- **🌐 CORS Support**: Cross-origin resource sharing for web applications
- **📝 Auto Documentation**: Interactive API documentation with Swagger UI

## 📋 System Requirements

- **OS**: Ubuntu 20.04+
- **Hardware**: 
  - CPU: 8+ cores
  - RAM: 16GB+ (32GB recommended)
  - GPU: NVIDIA GPU with 8GB+ VRAM (highly recommended)
  - Storage: 50GB+ available space
- **Network**: Stable internet connection (initial model download ~8GB)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/weilin1205/PrivNurseAI.git
cd PrivNurseAI/ExpertAgentC_LLMServer_Nursing_Note_STT
```

### 2. System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl wget
sudo apt install -y ffmpeg libsndfile1 libasound2-dev portaudio19-dev

# Install NVIDIA drivers (if using GPU)
sudo apt install -y nvidia-driver-535 nvidia-cuda-toolkit
```

### 3.1. Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

During setup, you'll need to:
- Enter your Hugging Face Access Token
- Get access to Gemma model at [Hugging Face](https://huggingface.co/google/gemma-3n-E4B-it)

## 3.2. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow ssh
sudo ufw allow 8444/tcp
sudo ufw --force enable
```

### 4. Start Service
```bash
cd gemma-audio-api
./start_api.sh
```

The service will be available at:
- **API**: http://localhost:8444
- **Documentation**: http://localhost:8444/docs
- **Health Check**: http://localhost:8444/health

## 📡 API Usage

### Authentication
All API requests require a Bearer token:
```http
Authorization: Bearer <your_api_key>
```

### Endpoints

#### Text Generation
```http
POST /generate/text
Content-Type: application/json

{
    "text": "Explain artificial intelligence",
    "max_tokens": 200,
    "temperature": 0.7
}
```

#### Audio + Text Generation
```http
POST /generate/audio-text
Content-Type: multipart/form-data

audio_file: <audio_file>
text: "Transcribe and summarize this audio"
max_tokens: 200
temperature: 0.7
```

#### Model Information
```http
GET /model/info
Authorization: Bearer <your_api_key>
```

### Python Client Example
```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "http://localhost:8444"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Text generation
response = requests.post(
    f"{BASE_URL}/generate/text",
    headers=headers,
    json={
        "text": "What is machine learning?",
        "max_tokens": 150
    }
)

print(response.json())
```

### JavaScript Client Example
```javascript
const API_KEY = 'your_api_key_here';
const BASE_URL = 'http://localhost:8444';

async function generateText(prompt) {
    const response = await fetch(`${BASE_URL}/generate/text`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            text: prompt,
            max_tokens: 150,
            temperature: 0.7
        })
    });
    
    return await response.json();
}

// Audio processing
async function processAudio(audioFile, prompt) {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    formData.append('text', prompt);
    
    const response = await fetch(`${BASE_URL}/generate/audio-text`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`
        },
        body: formData
    });
    
    return await response.json();
}
```

## 🔧 Configuration

### Environment Variables
Create a `config.env` file:
```env
GEMMA_API_KEY=your_generated_api_key
HF_TOKEN=your_huggingface_token
MODEL_ID=google/gemma-3n-E4B-it
MAX_AUDIO_SIZE=52428800
RATE_LIMIT_PER_MINUTE=10
```

### Security Settings
- **Firewall**: Only port 8444 is exposed
- **Authentication**: Bearer token required for all API calls
- **Rate Limiting**: 10 requests/minute (configurable)
- **File Validation**: Audio files are validated for format and size

## 🛠️ Testing

### Run API Tests
```bash
python3 test_api.py
```

### Open Web Interface
```bash
# Open the test frontend in your browser
firefox test_frontend.html
```

## 📊 Monitoring and Maintenance

### View Logs
```bash
tail -f /var/log/gemma-api.log
```

### Check System Resources
```bash
# GPU usage
nvidia-smi

# System resources
htop

# Network connections
netstat -tulpn | grep 8444
```

### Update Model
```bash
# Clear model cache to download latest version
rm -rf ~/.cache/huggingface/transformers/
# Restart service to auto-download new version
```

## 🚨 Troubleshooting

### Common Issues

#### Model Loading Fails
```bash
# Check Hugging Face permissions
huggingface-cli whoami

# Re-login
huggingface-cli login
```

#### Memory Issues
- Ensure sufficient RAM (32GB+ recommended)
- Use GPU to reduce CPU memory requirements
- Adjust `torch_dtype` to `torch.float16` in code

#### Audio Processing Errors
- Verify supported audio formats (.wav, .mp3, .flac, .m4a, .ogg)
- Check file size limits (default 50MB)
- Ensure ffmpeg is installed

#### API Connection Issues
- Check firewall settings
- Verify service is running
- Validate API key

### Debug Commands
```bash
# Check service status
curl http://localhost:8444/health

# Check GPU availability
python3 -c "import torch; print(torch.cuda.is_available())"

# Test model access
python3 -c "from transformers import AutoProcessor; AutoProcessor.from_pretrained('google/gemma-3n-E4B-it')"
```

## ⚡ Performance Optimization

### Hardware Recommendations
- **CPU**: AMD Ryzen 9 or Intel i9
- **GPU**: NVIDIA RTX 4060Ti, 4090, 5090, A100, or H100
- **RAM**: 64GB DDR4/DDR5
- **Storage**: NVMe SSD

### Software Optimizations
```python
# Adjust these parameters in gemma_api.py for better performance

# Use float16 to reduce memory usage
torch_dtype=torch.float16

# Enable model quantization
load_in_8bit=True

# Adjust batch size
batch_size=1
```

## 📚 Project Structure
```
gemma-audio-api/
├── gemma_api.py           # Main API service
├── start_api.sh           # Service startup script
├── test_api.py            # API testing script
├── test_frontend.html     # Web test interface
├── requirements.txt       # Python dependencies
├── config.env            # Environment configuration
├── gemma-api.service     # Systemd service file
└── README.md             # This file
```

## System Service Setup (Optional)

To run as a system service:
```bash
sudo cp gemma-api.service /etc/systemd/system/
sudo systemctl enable gemma-api
sudo systemctl start gemma-api
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the Apache-2.0 License - see the [LICENSE](https://github.com/weilin1205/PrivNurseAI/blob/main/LICENSE) file for details.

## 🙏 Acknowledgments

- Google for the Gemma-3n-E4B model
- Hugging Face for the Transformers library
- FastAPI for the excellent web framework

## 📞 Support

If you encounter issues:
1. Check the [troubleshooting section](#troubleshooting)
2. Review [Gemma documentation](https://deepmind.google/models/gemma/)
3. Check [Transformers documentation](https://huggingface.co/docs/transformers/index)
4. Open an issue in this repository

- **Documentation**: [Full Deployment Guide](https://github.com/weilin1205/PrivNurseAI/tree/main/ExpertAgentC_LLMServer_Nursing_Note_STT/README.md)
- **Issues**: [GitHub Issues](https://github.com/weilin1205/PrivNurseAI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/weilin1205/PrivNurseAI/discussions)

---

**⚠️ Note**: This API service includes complete authentication, rate limiting, error handling, and security measures suitable for production use. Please ensure regular updates of dependencies and model versions.

## 🔒 API Key Security Warning
**Important**: Your API key will be displayed when starting the service. Keep it secure and never commit it to version control.
