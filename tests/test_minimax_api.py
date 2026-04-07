"""
Minimax API 测试脚本
用于诊断 MiniMax-M2.7 模型连接问题
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ultra_reader.llm.minimax import MinimaxLLM


async def test_minimax():
    """测试 Minimax API 连接"""
    
    print("=" * 60)
    print("Minimax API 诊断测试")
    print("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("MINIMAX_API_KEY")
    
    print(f"\n[1] 环境变量检查:")
    print(f"    ANTHROPIC_API_KEY: {'✓ 已设置' if api_key else '✗ 未设置'}")
    print(f"    MINIMAX_API_KEY: {'✓ 已设置' if os.getenv('MINIMAX_API_KEY') else '✗ 未设置'}")
    
    if not api_key:
        print("\n⚠️  未设置 API Key!")
        print("   请创建 .env 文件并设置 ANTHROPIC_API_KEY")
        return False
    
    # 隐藏 API key 打印
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"    API Key: {masked_key}")
    
    # 创建 LLM 实例 - 标准模型名称
    print(f"\n[2] 初始化 Minimax LLM:")
    llm = MinimaxLLM(
        base_url="https://api.minimaxi.com/anthropic",
        model="MiniMax-M2.7",
        api_key=api_key,
        timeout=60,
    )
    print(f"    Base URL: {llm.base_url}")
    print(f"    Model: {llm.model}")
    print(f"    Provider: {llm.provider}")
    
    # 测试连接并获取详细状态
    print(f"\n[3] 测试 API 连接和模型可用性...")
    try:
        success = await llm.check_connection()
        print(f"    {'✓ 连接可用' if success else '✗ 无法连接'}")
    except Exception as e:
        print(f"    ✗ 连接异常: {e}")
    
    # 测试简单聊天
    print(f"\n[4] 测试聊天请求:")
    test_messages = [
        {"role": "user", "content": "请回复'测试成功'"}
    ]
    
    try:
        print("    发送测试请求...")
        response = await llm.chat(test_messages, temperature=0.7, max_tokens=50)
        print(f"    ✓ 收到响应 ({len(response)} 字符):")
        print(f"    {response[:200]}...")
    except Exception as e:
        print(f"    ✗ 请求失败: {e}")
        print(f"\n    错误类型: {type(e).__name__}")
    
    await llm.close()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    
    return True


async def test_all_models():
    """测试所有支持的模型名称"""
    import httpx
    
    print("\n" + "=" * 60)
    print("模型名称测试")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("✗ 缺少 API Key")
        return False
    
    base_url = "https://api.minimaxi.com/anthropic"
    models = ["MiniMax-M2.7"]
    
    print(f"\n测试模型名称:")
    
    async with httpx.AsyncClient(timeout=60) as client:
        for model in models:
            try:
                response = await client.post(
                    f"{base_url}/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 10,
                    },
                )
                status = response.status_code
                if status == 200:
                    print(f"  ✓ {model}: 可用")
                elif status == 404:
                    print(f"  ✗ {model}: 模型不存在")
                else:
                    print(f"  ! {model}: HTTP {status}")
            except Exception as e:
                print(f"  ✗ {model}: {e}")
    
    return True


async def test_different_endpoints():
    """测试不同的 API 端点"""
    import httpx
    
    print("\n" + "=" * 60)
    print("API 端点测试")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("✗ 缺少 API Key")
        return False
    
    endpoints = [
        "https://api.minimaxi.com/anthropic",
        "https://api.minimax.chat/anthropic",
        "https://api.minimax.com/anthropic",
    ]
    
    print(f"\n测试端点:")
    
    async with httpx.AsyncClient(timeout=30) as client:
        for endpoint in endpoints:
            try:
                response = await client.post(
                    f"{endpoint}/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "MiniMax-M2.7",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 10,
                    },
                )
                status = response.status_code
                if status == 200:
                    print(f"  ✓ {endpoint}")
                else:
                    print(f"  ! {endpoint}: HTTP {status}")
            except httpx.ConnectError:
                print(f"  ✗ {endpoint}: 连接失败")
            except Exception as e:
                print(f"  ✗ {endpoint}: {e}")
    
    return True


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("#  MiniMax API 诊断工具")
    print("#" * 60)
    
    # 运行主测试
    asyncio.run(test_minimax())
    
    # 测试所有模型名称
    asyncio.run(test_all_models())
    
    # 测试不同端点
    asyncio.run(test_different_endpoints())
