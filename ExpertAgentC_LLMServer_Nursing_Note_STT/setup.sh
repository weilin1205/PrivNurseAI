#!/bin/bash

# Gemma-3n-E4B API 設置腳本
# Ubuntu 環境自動安裝腳本

set -e

echo "=== Gemma-3n-E4B API 安裝腳本 ==="
echo "開始安裝依賴項目..."

# 更新系統
# sudo apt update && sudo apt upgrade -y

# 安裝基本依賴
sudo apt install -y python3 python3-pip python3-venv git curl wget

# 安裝音訊處理依賴
sudo apt install -y ffmpeg libsndfile1 libasound2-dev portaudio19-dev

# 創建項目目錄
PROJECT_DIR="gemma-audio-api"
if [ -d "$PROJECT_DIR" ]; then
    echo "目錄 $PROJECT_DIR 已存在，正在清理..."
    rm -rf "$PROJECT_DIR"
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 創建虛擬環境
echo "創建 Python 虛擬環境..."
python3 -m venv venv
source venv/bin/activate

# 升級 pip
pip install --upgrade pip

# 創建 requirements.txt
cat > requirements.txt << EOF
# 核心依賴
torch>=2.4.0
transformers>=4.53.0
accelerate>=0.20.0

# API 框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# 音訊處理
librosa>=0.10.0
soundfile>=0.12.0

# 工具庫
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0

# Hugging Face
huggingface-hub>=0.17.0
datasets>=2.14.0

# Timm
timm
EOF

# 安裝 Python 依賴
echo "安裝 Python 依賴..."
pip install -r requirements.txt

# 設置 Hugging Face 令牌
echo ""
echo "請輸入您的 Hugging Face Access Token："
echo "（在 https://huggingface.co/settings/tokens 獲取）"
read -s HF_TOKEN

if [ -z "$HF_TOKEN" ]; then
    echo "警告：未設置 Hugging Face Token，您需要手動登入"
else
    echo "設置 Hugging Face Token..."
    export HF_TOKEN="$HF_TOKEN"
    echo "export HF_TOKEN=\"$HF_TOKEN\"" >> ~/.bashrc
fi

# 生成 API 金鑰
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export GEMMA_API_KEY="$API_KEY"
echo "export GEMMA_API_KEY=\"$API_KEY\"" >> ~/.bashrc

# 創建配置檔案
cat > config.env << EOF
# Gemma API 配置
GEMMA_API_KEY=$API_KEY
HF_TOKEN=$HF_TOKEN
MODEL_ID=google/gemma-3n-E4B-it
MAX_AUDIO_SIZE=52428800
RATE_LIMIT_PER_MINUTE=10
EOF

# 創建啟動腳本
cat > start_api.sh << 'EOF'
#!/bin/bash

# 載入環境變數
source ./venv/bin/activate
source ./config.env

echo "=== 啟動 Gemma-3n-E4B API 服務 ==="
echo "API Key: $GEMMA_API_KEY"
echo "模型: $MODEL_ID"
echo "服務地址: http://localhost:8444"
echo "文檔地址: http://localhost:8444/docs"
echo ""

# 登入 Hugging Face（如果有令牌）
if [ ! -z "$HF_TOKEN" ]; then
    echo "登入 Hugging Face..."
    python3 -c "from huggingface_hub import login; login('$HF_TOKEN')"
fi

# 啟動 API 服務
python3 gemma_api.py
EOF

chmod +x start_api.sh

# 創建系統服務檔案
cat > gemma-api.service << EOF
[Unit]
Description=Gemma-3n-E4B Audio API Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/gemma_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 設置防火牆規則
echo "設置防火牆規則..."
sudo ufw allow 8444/tcp
sudo ufw --force enable

# 創建測試腳本
cat > test_api.py << 'EOF'
#!/usr/bin/env python3
"""
API 測試腳本
"""

import requests
import json
import os

API_KEY = os.getenv('GEMMA_API_KEY')
BASE_URL = "http://localhost:8444"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_health():
    """測試健康檢查"""
    response = requests.get(f"{BASE_URL}/health")
    print("健康檢查:", response.json())

def test_text_generation():
    """測試純文字生成"""
    data = {
        "text": "請介紹一下台灣的美食文化",
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    response = requests.post(
        f"{BASE_URL}/generate/text",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("文字生成成功:")
        print(f"生成文字: {result['generated_text']}")
        print(f"處理時間: {result['processing_time']}秒")
    else:
        print("文字生成失敗:", response.text)

def test_model_info():
    """測試模型資訊"""
    response = requests.get(f"{BASE_URL}/model/info", headers=headers)
    if response.status_code == 200:
        print("模型資訊:", response.json())
    else:
        print("獲取模型資訊失敗:", response.text)

if __name__ == "__main__":
    print("=== API 測試 ===")
    print(f"API Key: {API_KEY}")
    print(f"服務地址: {BASE_URL}")
    print()
    
    try:
        test_health()
        print()
        test_model_info()
        print()
        test_text_generation()
    except requests.exceptions.ConnectionError:
        print("無法連接到 API 服務，請確保服務正在運行")
    except Exception as e:
        print(f"測試失敗: {e}")
EOF

chmod +x test_api.py

# 創建前端測試頁面
cat > test_frontend.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemma-3n-E4B API 測試</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, button { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { background: #007bff; color: white; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .error { background: #f8d7da; color: #721c24; }
        .success { background: #d4edda; color: #155724; }
    </style>
</head>
<body>
    <h1>Gemma-3n-E4B API 測試介面</h1>
    
    <div class="form-group">
        <label>API Key:</label>
        <input type="password" id="apiKey" placeholder="請輸入 API Key">
    </div>
    
    <h2>純文字生成測試</h2>
    <div class="form-group">
        <label>輸入文字:</label>
        <textarea id="textInput" rows="4" placeholder="請輸入您想要的提示文字..."></textarea>
    </div>
    
    <div class="form-group">
        <label>最大令牌數:</label>
        <input type="number" id="maxTokens" value="128" min="1" max="512">
    </div>
    
    <button onclick="testTextGeneration()">生成文字</button>
    
    <h2>音訊 + 文字生成測試</h2>
    <div class="form-group">
        <label>選擇音訊檔案:</label>
        <input type="file" id="audioFile" accept=".wav,.mp3,.flac,.m4a,.ogg">
    </div>
    
    <div class="form-group">
        <label>附加文字:</label>
        <textarea id="audioText" rows="2" placeholder="請描述您希望對音訊做什麼處理..."></textarea>
    </div>
    
    <button onclick="testAudioGeneration()">處理音訊</button>
    
    <div id="result"></div>

    <script>
        const API_BASE = 'http://localhost:8444';
        
        async function makeRequest(endpoint, options) {
            const apiKey = document.getElementById('apiKey').value;
            if (!apiKey) {
                showResult('請先輸入 API Key', 'error');
                return;
            }
            
            const headers = {
                'Authorization': `Bearer ${apiKey}`,
                ...options.headers
            };
            
            try {
                const response = await fetch(`${API_BASE}${endpoint}`, {
                    ...options,
                    headers
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    return data;
                } else {
                    throw new Error(data.detail || '請求失敗');
                }
            } catch (error) {
                showResult(`錯誤: ${error.message}`, 'error');
                throw error;
            }
        }
        
        async function testTextGeneration() {
            const text = document.getElementById('textInput').value;
            const maxTokens = parseInt(document.getElementById('maxTokens').value);
            
            if (!text) {
                showResult('請輸入文字', 'error');
                return;
            }
            
            showResult('正在生成文字...', '');
            
            try {
                const result = await makeRequest('/generate/text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        max_tokens: maxTokens,
                        temperature: 0.7
                    })
                });
                
                showResult(`
                    <h3>生成結果:</h3>
                    <p><strong>生成文字:</strong> ${result.generated_text}</p>
                    <p><strong>處理時間:</strong> ${result.processing_time.toFixed(2)} 秒</p>
                    <p><strong>模型版本:</strong> ${result.model_version}</p>
                `, 'success');
                
            } catch (error) {
                // 錯誤已在 makeRequest 中處理
            }
        }
        
        async function testAudioGeneration() {
            const audioFile = document.getElementById('audioFile').files[0];
            const text = document.getElementById('audioText').value;
            
            if (!audioFile) {
                showResult('請選擇音訊檔案', 'error');
                return;
            }
            
            if (!text) {
                showResult('請輸入附加文字', 'error');
                return;
            }
            
            showResult('正在處理音訊...', '');
            
            try {
                const formData = new FormData();
                formData.append('audio_file', audioFile);
                formData.append('text', text);
                formData.append('max_tokens', '128');
                formData.append('temperature', '0.7');
                
                const result = await makeRequest('/generate/audio-text', {
                    method: 'POST',
                    body: formData
                });
                
                showResult(`
                    <h3>音訊處理結果:</h3>
                    <p><strong>生成文字:</strong> ${result.generated_text}</p>
                    <p><strong>處理時間:</strong> ${result.processing_time.toFixed(2)} 秒</p>
                    <p><strong>模型版本:</strong> ${result.model_version}</p>
                `, 'success');
                
            } catch (error) {
                // 錯誤已在 makeRequest 中處理
            }
        }
        
        function showResult(message, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = message;
            resultDiv.className = `result ${type}`;
        }
        
        // 頁面載入時進行健康檢查
        window.onload = async function() {
            try {
                const response = await fetch(`${API_BASE}/health`);
                const data = await response.json();
                console.log('服務狀態:', data);
            } catch (error) {
                console.log('無法連接到服務');
            }
        };
    </script>
</body>
</html>
EOF

echo ""
echo "=== 安裝完成 ==="
echo "項目目錄: $(pwd)"
echo "API Key: $API_KEY"
echo ""
echo "下一步："
echo "1. 啟動服務: ./start_api.sh"
echo "2. 測試 API: python3 test_api.py"
echo "3. 開啟前端測試頁面: test_frontend.html"
echo "4. API 文檔: http://localhost:8444/docs"
echo ""
echo "安全設置："
echo "- 防火牆已配置僅允許端口 8444"
echo "- API 使用 Bearer Token 認證"
echo "- 已設置速率限制 (每分鐘 ${RATE_LIMIT_PER_MINUTE:-10} 次請求)"
echo ""
echo "系統服務設置 (可選)："
echo "sudo cp gemma-api.service /etc/systemd/system/"
echo "sudo systemctl enable gemma-api"
echo "sudo systemctl start gemma-api"
echo ""
echo "重要提醒："
echo "- 請妥善保管您的 API Key: $API_KEY"
echo "- 請確保已獲得 Gemma 模型的 Hugging Face 授權"
echo "- 首次運行會下載約 8GB 的模型檔案"
echo "- 建議使用 GPU 以獲得更好的性能"
echo ""