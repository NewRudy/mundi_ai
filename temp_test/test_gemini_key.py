#!/usr/bin/env python3
"""
测试 Gemini API Key 是否配置正确
"""
import os
import asyncio
from openai import AsyncOpenAI

async def test_gemini_api():
    """测试 Gemini API 连接"""
    
    # 从环境变量读取配置（与 Mundi 一致）
    api_key = "sk-bpbznxvencyxnyjstpdlandiisuxeygpyzybdlizxnzzlfso"
    # base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    base_url = "https://api.siliconflow.cn"
    model = "deepseek-ai/DeepSeek-v3"
    # api_key = "AIzaSyDVsXIp4X1XiRMnPgPnruyJoJ11g5kGi5Q"
    # # base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # model = "gemini-2.5-pro"
    
    print("=" * 60)
    print("🔍 Gemini API 配置测试")
    print("=" * 60)
    print(f"API Key: {api_key[:20]}... (已隐藏)" if api_key else "❌ 未设置 OPENAI_API_KEY")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print("=" * 60)
    
    if not api_key:
        print("\n❌ 错误: OPENAI_API_KEY 环境变量未设置")
        print("\n请先设置环境变量:")
        print("  $env:OPENAI_API_KEY='your-gemini-api-key'")
        return False
    
    try:
        print("\n📡 正在测试 API 连接...")
        
        # 创建客户端（与 Mundi 的 get_openai_client 一致）
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # 发送简单的测试请求
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, this is a test!' in one sentence."}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        
        print("\n✅ API 连接成功！")
        print(f"\n📝 模型响应:\n{result}")
        print("\n" + "=" * 60)
        print("✅ 配置正确，可以在 Mundi 中使用")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ API 连接失败!")
        print(f"\n错误信息: {str(e)}")
        print("\n" + "=" * 60)
        print("可能的问题:")
        print("1. API Key 不正确")
        print("2. OPENAI_BASE_URL 配置错误（Gemini 需要特定的 URL）")
        print("3. OPENAI_MODEL 不支持或拼写错误")
        print("4. 网络连接问题")
        print("\n对于 Gemini API:")
        print("  - Base URL 应该是: https://generativelanguage.googleapis.com/v1beta/openai/")
        print("  - Model 可能是: gemini-1.5-flash, gemini-1.5-pro 等")
        print("=" * 60)
        return False

if __name__ == "__main__":
    asyncio.run(test_gemini_api())

