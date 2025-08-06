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
