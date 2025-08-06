#!/usr/bin/env python3
"""
Gemma-3n-E4B 音訊處理 API 後端
支援音訊輸入的多模態文字生成服務
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
import librosa
import tempfile
import io
from pydantic import BaseModel
import json
import subprocess
import shutil

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置
class Config:
    MODEL_ID = "google/gemma-3n-E4B-it"
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_NEW_TOKENS = 4096
    SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.flac', '.m4a', '.ogg', '.webm']
    API_KEY = os.getenv('GEMMA_API_KEY', secrets.token_urlsafe(32))
    RATE_LIMIT_PER_MINUTE = 25
    # 允許的主機列表，設為 None 表示允許所有主機
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', None)  # 例如: "localhost,127.0.0.1,140.128.197.212"
    
# 請求模型
class AudioTextRequest(BaseModel):
    text: str
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7

class TextOnlyRequest(BaseModel):
    text: str
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7

# 響應模型
class GenerationResponse(BaseModel):
    generated_text: str
    processing_time: float
    model_version: str

# 速率限制
rate_limit_storage = {}

def check_rate_limit(client_ip: str) -> bool:
    """檢查速率限制"""
    now = datetime.now()
    if client_ip not in rate_limit_storage:
        rate_limit_storage[client_ip] = []
    
    # 清理舊記錄
    rate_limit_storage[client_ip] = [
        timestamp for timestamp in rate_limit_storage[client_ip]
        if now - timestamp < timedelta(minutes=1)
    ]
    
    if len(rate_limit_storage[client_ip]) >= Config.RATE_LIMIT_PER_MINUTE:
        return False
    
    rate_limit_storage[client_ip].append(now)
    return True

# 身份驗證
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """驗證 API 金鑰"""
    if credentials.credentials != Config.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return credentials.credentials

# 全域變數儲存模型
processor = None
model = None

def check_ffmpeg():
    """檢查 FFmpeg 是否可用"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def convert_webm_to_wav(webm_path: str, output_path: str) -> bool:
    """使用 FFmpeg 將 WebM 轉換為 WAV"""
    try:
        cmd = [
            'ffmpeg', '-y',  # -y 覆蓋輸出檔案
            '-i', webm_path,  # 輸入檔案
            '-acodec', 'pcm_s16le',  # 音訊編解碼器
            '-ar', '16000',  # 取樣率 16kHz
            '-ac', '1',  # 單聲道
            output_path  # 輸出檔案
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30  # 30秒超時
        )
        
        return os.path.exists(output_path)
        
    except subprocess.TimeoutExpired:
        logger.error("WebM 轉換超時")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"WebM 轉換失敗: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"WebM 轉換異常: {e}")
        return False

async def load_model():
    """載入 Gemma 模型"""
    global processor, model
    
    try:
        logger.info(f"正在載入模型: {Config.MODEL_ID}")
        
        # 檢查 GPU 可用性
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"使用設備: {device}")
        
        # 檢查 FFmpeg（用於 WebM 支援）
        if check_ffmpeg():
            logger.info("FFmpeg 可用，支援 WebM 格式")
        else:
            logger.warning("FFmpeg 不可用，WebM 檔案可能無法處理")
        
        # 載入處理器和模型
        processor = AutoProcessor.from_pretrained(
            Config.MODEL_ID, 
            device_map="auto",
        )
        processor.tokenizer.padding_side = "right"
        
        model = AutoModelForImageTextToText.from_pretrained(
            Config.MODEL_ID,
            torch_dtype="auto",
            # attn_implementation='eager',
            device_map="cuda",
        )
        
        torch._dynamo.config.disable = True
        
        logger.info("模型載入完成")
        
    except Exception as e:
        logger.error(f"模型載入失敗: {e}")
        raise RuntimeError(f"Failed to load model: {e}")

def validate_audio_file(file: UploadFile) -> bool:
    """驗證音訊檔案"""
    if not file.filename:
        return False
    
    # 檢查檔案副檔名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in Config.SUPPORTED_AUDIO_FORMATS:
        return False
    
    # 檢查檔案大小
    if file.size and file.size > Config.MAX_AUDIO_SIZE:
        return False
    
    return True

async def process_audio_file(file: UploadFile) -> str:
    """處理音訊檔案並返回臨時檔案路徑"""
    try:
        # 創建臨時檔案
        file_ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # 如果是 WebM 格式，需要先轉換
        if file_ext == '.webm':
            if not check_ffmpeg():
                raise HTTPException(
                    status_code=500, 
                    detail="FFmpeg not available for WebM processing"
                )
            
            # 創建 WAV 輸出檔案
            wav_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            wav_temp.close()
            
            # 轉換 WebM 到 WAV
            if not convert_webm_to_wav(temp_path, wav_temp.name):
                # 清理檔案
                os.unlink(temp_path)
                if os.path.exists(wav_temp.name):
                    os.unlink(wav_temp.name)
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to convert WebM file"
                )
            
            # 清理原始 WebM 檔案
            os.unlink(temp_path)
            
            # 使用 librosa 載入轉換後的 WAV 檔案
            try:
                audio, sr = librosa.load(wav_temp.name, sr=16000)
            except Exception as e:
                os.unlink(wav_temp.name)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to load converted audio: {e}"
                )
            
            # 清理中間 WAV 檔案
            os.unlink(wav_temp.name)
            
        else:
            # 其他格式直接使用 librosa 處理
            try:
                audio, sr = librosa.load(temp_path, sr=16000)
            except Exception as e:
                os.unlink(temp_path)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to load audio file: {e}"
                )
            
            # 清理原始檔案
            os.unlink(temp_path)
        
        # 儲存處理後的音訊為標準 WAV 格式
        processed_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        processed_temp.close()
        
        # 使用 soundfile 寫入（librosa 的 write_wav 已棄用）
        import soundfile as sf
        sf.write(processed_temp.name, audio, sr)
        
        return processed_temp.name
        
    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        logger.error(f"音訊處理失敗: {e}")
        raise HTTPException(status_code=400, detail=f"Audio processing failed: {e}")

# 創建 FastAPI 應用
app = FastAPI(
    title="Gemma-3n-E4B Audio API",
    description="多模態文字生成 API，支援音訊輸入（包括 WebM 格式）",
    version="1.0.1"
)

# 中介軟體設定
# 只有在設定了 ALLOWED_HOSTS 環境變數時才啟用 TrustedHostMiddleware
if Config.ALLOWED_HOSTS:
    allowed_hosts = [host.strip() for host in Config.ALLOWED_HOSTS.split(",")]
    logger.info(f"啟用 TrustedHostMiddleware，允許的主機: {allowed_hosts}")
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=allowed_hosts
    )
else:
    logger.info("未設定 ALLOWED_HOSTS，允許所有主機連線")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8444"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """應用啟動時載入模型"""
    await load_model()

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "ffmpeg_available": check_ffmpeg(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/model/info", dependencies=[Depends(verify_api_key)])
async def model_info():
    """取得模型資訊"""
    return {
        "model_id": Config.MODEL_ID,
        "device": str(model.device) if model else "Not loaded",
        "supported_formats": Config.SUPPORTED_AUDIO_FORMATS,
        "max_audio_size_mb": Config.MAX_AUDIO_SIZE / (1024 * 1024),
        "webm_support": check_ffmpeg()
    }

@app.post("/generate/text", response_model=GenerationResponse)
async def generate_text_only(
    request: TextOnlyRequest,
    credentials: str = Depends(verify_api_key),
    client_ip: str = "127.0.0.1"
):
    """純文字生成"""
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if not model or not processor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = datetime.now()
    
    try:
        # 構建訊息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": request.text}
                ]
            }
        ]
        
        # 應用聊天模板
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device, dtype=model.dtype)

        input_len = inputs["input_ids"].shape[-1]
        
        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                do_sample=True,
                temperature=request.temperature,
                max_new_tokens=min(request.max_tokens, Config.MAX_NEW_TOKENS),
            )
            generation = generation[0][input_len:]
        
        generated_text = processor.decode(generation, skip_special_tokens=True)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return GenerationResponse(
            generated_text=generated_text.strip(),
            processing_time=processing_time,
            model_version=Config.MODEL_ID
        )
        
    except Exception as e:
        logger.error(f"文字生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

@app.post("/generate/audio-text", response_model=GenerationResponse)
async def generate_from_audio_text(
    audio_file: UploadFile = File(...),
    # text: str = Form(...),
    max_tokens: int = Form(128),
    temperature: float = Form(0.7),
    credentials: str = Depends(verify_api_key),
    client_ip: str = "127.0.0.1"
):
    """音訊+文字生成（支援 WebM）"""
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if not model or not processor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # 驗證音訊檔案
    if not validate_audio_file(audio_file):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid audio file. Supported formats: {Config.SUPPORTED_AUDIO_FORMATS}"
        )
    
    start_time = datetime.now()
    temp_audio_path = None
    
    try:
        # 處理音訊檔案
        temp_audio_path = await process_audio_file(audio_file)
        
        # 構建包含音訊的訊息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "audio": temp_audio_path},
                    {"type": "text", "text": """Please transcribe the provided audio into accurate written text. This is a medical/healthcare context where the speaker is a nursing professional.

## Instructions:
1. Convert the speech to text as accurately as possible
2. The speaker is a nurse, so expect medical terminology and nursing-related content
3. You may make minor adjustments to improve clarity and flow while maintaining the original meaning
4. Correct obvious speech errors, filler words, or unclear pronunciations to create a coherent transcript
5. Maintain professional medical language and terminology
6. Ensure the final transcript is readable and well-structured

## Output Requirements:
- Provide ONLY the clean, transcribed text
- Do not add commentary, explanations, or additional content
- Do not include timestamps or speaker labels
- Present the transcript as a flowing, coherent text document

Please transcribe the audio now."""}
                ]
            }
        ]

        # 應用聊天模板
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device, dtype=model.dtype)
        
        input_len = inputs["input_ids"].shape[-1]
        
        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                do_sample=True,
                temperature=temperature,
                max_new_tokens=min(max_tokens, Config.MAX_NEW_TOKENS),
                pad_token_id=processor.tokenizer.eos_token_id,
            )
            generation = generation[0][input_len:]
        
        generated_text = processor.decode(generation, skip_special_tokens=True)

        processing_time = (datetime.now() - start_time).total_seconds()
        
        return GenerationResponse(
            generated_text=generated_text.strip(),
            processing_time=processing_time,
            model_version=Config.MODEL_ID
        )
        
    except Exception as e:
        logger.error(f"音訊文字生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Audio-text generation failed: {e}")
    
    finally:
        # 清理臨時檔案
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except:
                pass

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全域異常處理"""
    logger.error(f"未處理的異常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    # 顯示 API 金鑰
    print(f"API Key: {Config.API_KEY}")
    print("請將此 API Key 用於身份驗證")
    print("=" * 50)
    
    # 啟動服務器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8444,
        log_level="info"
    )