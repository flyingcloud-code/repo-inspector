import os
import requests
from dotenv import load_dotenv, find_dotenv

# 加载环境变量
load_dotenv(find_dotenv())

api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    print('❌ OPENROUTER_API_KEY 未设置')
    exit(1)

print('🧪 测试OpenRouter API连接...')

# 测试API连接
url = 'https://openrouter.ai/api/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
data = {
    'model': 'google/gemini-2.0-flash-001',
    'messages': [
        {'role': 'user', 'content': '请用一句话介绍你自己'}
    ],
    'max_tokens': 100
}

try:
    response = requests.post(url, json=data, headers=headers, timeout=30)
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print('✅ OpenRouter API工作正常！')
        print(f'📨 响应内容: {content[:100]}...')
        print(f'🤖 使用模型: {result.get("model", "未知")}')
    else:
        print(f'❌ API请求失败: {response.status_code}')
        print(f'📄 错误信息: {response.text[:200]}')
        
except Exception as e:
    print(f'❌ OpenRouter API测试失败: {e}')