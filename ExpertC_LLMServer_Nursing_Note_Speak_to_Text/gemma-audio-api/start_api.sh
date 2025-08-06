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
