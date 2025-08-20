#!/usr/bin/env python3
"""
Test script for Telegram File-to-Link Bot
Verifies configuration and basic functionality
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env file loading")

from config import Config

async def test_configuration():
    """Test configuration validation"""
    print("🔧 Testing Configuration...")
    
    if Config.validate():
        print("✅ Configuration is valid")
        return True
    else:
        print("❌ Configuration validation failed")
        return False

async def test_web_server():
    """Test web server health endpoint"""
    print("🌐 Testing Web Server...")
    
    try:
        health_url = f"{Config.BASE_URL}/health"
        print(f"📡 Checking: {health_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "healthy":
                        print("✅ Web server is healthy")
                        return True
                    else:
                        print(f"❌ Unexpected response: {data}")
                        return False
                else:
                    print(f"❌ HTTP {response.status}: {await response.text()}")
                    return False
                    
    except aiohttp.ClientError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_telegram_connection():
    """Test Telegram API connection"""
    print("📱 Testing Telegram Connection...")
    
    try:
        from pyrogram import Client
        
        bot = Client(
            "test_session",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Connected to Telegram as @{me.username}")
        await bot.stop()
        
        # Clean up test session
        session_files = [
            "test_session.session",
            "test_session.session-journal"
        ]
        for file in session_files:
            if os.path.exists(file):
                os.remove(file)
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram connection failed: {e}")
        return False

def print_environment_info():
    """Print environment information"""
    print("📊 Environment Information:")
    print(f"   🐍 Python: {sys.version.split()[0]}")
    print(f"   📁 Working Directory: {os.getcwd()}")
    print(f"   🌐 Base URL: {Config.BASE_URL}")
    print(f"   🔧 Host: {Config.HOST}:{Config.PORT}")
    print(f"   📏 Max File Size: {Config.MAX_FILE_SIZE / (1024*1024*1024):.1f} GB")
    print(f"   📦 Chunk Size: {Config.CHUNK_SIZE / (1024*1024):.1f} MB")
    print(f"   📝 Log Level: {Config.LOG_LEVEL}")

async def main():
    """Main test function"""
    print("🧪 Telegram File-to-Link Bot - Test Suite")
    print("=" * 50)
    
    print_environment_info()
    print()
    
    tests = [
        ("Configuration", test_configuration),
        ("Telegram Connection", test_telegram_connection),
        ("Web Server Health", test_web_server),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🔍 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("📋 Test Results Summary:")
    print("-" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your bot is ready to deploy.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix the issues before deploying.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
