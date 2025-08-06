import requests
import os
from typing import Optional
import logging
from fastapi import UploadFile
import tempfile
import aiofiles
from config import GEMMA_API_KEY, GEMMA_API_URL
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available - audio conversion disabled")

# Debug logging
logger.info(f"GEMMA_API_KEY from config: {GEMMA_API_KEY[:10]}..." if GEMMA_API_KEY != "your-gemma-api-key" else "Using default key")
logger.info(f"GEMMA_API_URL from config: {GEMMA_API_URL}")

class GemmaAudioClient:
    """Gemma Audio API client for STT processing"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or GEMMA_API_KEY
        self.base_url = (base_url or GEMMA_API_URL).rstrip('/')
        logger.info(f"GemmaAudioClient initialized with API key: {self.api_key[:10]}..." if self.api_key != "your-gemma-api-key" else "Using default key")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            # Note: The implementation shows no headers on health check
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Gemma API connection successful")
                return True
            else:
                logger.error(f"❌ Gemma API connection failed: {response.status_code}")
                try:
                    logger.error(f"   Response: {response.text}")
                except:
                    pass
                return False
        except Exception as e:
            logger.error(f"❌ Gemma API connection error: {e}")
            return False
    
    async def transcribe_audio(self, audio_file: UploadFile, context_text: str = "") -> Optional[dict]:
        """Send audio file to Gemma API for transcription"""
        try:
            logger.info(f"📤 Sending audio to Gemma API...")
            logger.info(f"   API URL: {self.base_url}")
            logger.info(f"   Filename: {audio_file.filename}")
            logger.info(f"   Content Type: {audio_file.content_type}")
            logger.info(f"   Context: {context_text}")
            
            # Save uploaded file temporarily
            file_extension = Path(audio_file.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                content = await audio_file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
                logger.info(f"   Temp file: {tmp_file_path}")
                logger.info(f"   File size: {len(content)} bytes")
                logger.info(f"   File extension: {file_extension}")
            
            # Convert to supported format if needed
            supported_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
            final_audio_path = tmp_file_path
            
            if file_extension not in supported_extensions:
                if PYDUB_AVAILABLE and file_extension in ['.webm']:
                    try:
                        logger.info(f"   Converting {file_extension} to .ogg...")
                        logger.info(f"   Input file size: {os.path.getsize(tmp_file_path)} bytes")
                        
                        # Try conversion with error handling
                        audio = AudioSegment.from_file(tmp_file_path, format=file_extension[1:])
                        ogg_path = tmp_file_path.replace(file_extension, '.ogg')
                        audio.export(ogg_path, format='ogg', codec='libvorbis')
                        
                        if os.path.exists(ogg_path):
                            final_audio_path = ogg_path
                            logger.info(f"   ✅ Conversion successful!")
                            logger.info(f"   Output file: {final_audio_path}")
                            logger.info(f"   Output size: {os.path.getsize(ogg_path)} bytes")
                        else:
                            logger.error("   ❌ Conversion failed: Output file not created")
                    except Exception as e:
                        logger.error(f"   ❌ Conversion failed: {e}")
                        logger.info("   Possible causes:")
                        logger.info("   1. ffmpeg not installed")
                        logger.info("   2. Invalid audio data")
                        logger.info("   Sending original file anyway...")
                else:
                    if not PYDUB_AVAILABLE:
                        logger.warning(f"   ⚠️ pydub not available for {file_extension} conversion")
                        logger.warning("   Install with: pip install pydub")
                    logger.warning(f"   Unsupported format {file_extension}, sending anyway...")
            
            try:
                # Send to Gemma API with transcription-only instruction
                with open(final_audio_path, 'rb') as f:
                    files = {'audio_file': f}
                    
                    # Add instruction text to ensure pure transcription
                    data = {
                        'instruction': 'IMPORTANT: Return ONLY the exact words spoken in the audio. Do NOT add phrases like "Here is the transcription" or "Okay" or any other text. Start directly with the first word spoken. Example: If audio says "Record time 11 pm", return exactly "Record time 11 pm" without any additions.',
                        'system_prompt': 'You are a medical transcription system. Output only the exact spoken words without any additions or modifications.',
                        'context': context_text
                    }
                    
                    logger.info(f"   Sending POST request to: {self.base_url}/generate/audio-text")
                    logger.info(f"   Headers: {self.headers}")
                    logger.info(f"   Instruction: {data['instruction']}")
                    logger.info(f"   Context: {data['context']}")
                    
                    response = requests.post(
                        f"{self.base_url}/generate/audio-text",
                        headers=self.headers,
                        files=files,
                        data=data,
                        timeout=120  # 2 minutes timeout
                    )
                
                logger.info(f"   Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("✅ Gemma API response successful")
                    logger.info(f"   Response data: {result}")
                    return result
                else:
                    logger.error(f"❌ Gemma API error: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"   Error details: {error_detail}")
                    except:
                        logger.error(f"   Response text: {response.text}")
                    return None
                    
            finally:
                # Clean up temp files
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                if final_audio_path != tmp_file_path and os.path.exists(final_audio_path):
                    os.unlink(final_audio_path)
                
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return None

# Singleton instance
gemma_client = GemmaAudioClient()