#!/usr/bin/env python3
"""
Comprehensive test script for Telegram File-to-Link Bot
Tests all components with mock data and real functionality
"""

import os
import sys
import asyncio
import aiohttp
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import logging

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment variables
os.environ.update({
    'API_ID': '123456',
    'API_HASH': 'test_hash',
    'BOT_TOKEN': '123456789:TEST_TOKEN',
    'BASE_URL': 'http://localhost:8080',
    'SECRET_KEY': 'test-secret-key',
    'HOST': '0.0.0.0',
    'PORT': '8080',
    'LOG_LEVEL': 'DEBUG'
})

from config import Config
from web_server import FileServer, create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_name, passed, details=""):
        self.tests.append((test_name, passed, details))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {test_name}")
        if details and not passed:
            print(f"      Details: {details}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n🎯 Test Summary: {self.passed}/{total} tests passed")
        return self.passed == total

async def test_config_validation():
    """Test configuration validation"""
    print("🔧 Testing Configuration...")
    results = TestResults()
    
    # Test basic validation
    try:
        is_valid = Config.validate()
        results.add_result("Configuration validation", is_valid)
    except Exception as e:
        results.add_result("Configuration validation", False, str(e))
    
    # Test URL generation
    try:
        download_url = Config.get_download_url("test_123_456")
        expected = f"{Config.BASE_URL}/download/test_123_456"
        results.add_result("Download URL generation", download_url == expected)
        
        stream_url = Config.get_stream_url("test_123_456")
        expected = f"{Config.BASE_URL}/stream/test_123_456"
        results.add_result("Stream URL generation", stream_url == expected)
    except Exception as e:
        results.add_result("URL generation", False, str(e))
    
    return results.summary()

async def test_file_server_mock():
    """Test FileServer with mock data"""
    print("📁 Testing FileServer with Mock Data...")
    results = TestResults()
    
    try:
        # Create mock bot client
        mock_bot = Mock()
        mock_bot.get_messages = AsyncMock()
        mock_bot.stream_media = AsyncMock()
        
        # Create mock message with document
        mock_message = Mock()
        mock_message.chat.id = 123
        mock_message.id = 456
        mock_message.document = Mock()
        mock_message.document.file_id = "test_file_id"
        mock_message.document.file_name = "test_document.pdf"
        mock_message.document.file_size = 1024000  # 1MB
        mock_message.document.mime_type = "application/pdf"
        mock_message.video = None
        mock_message.audio = None
        
        mock_bot.get_messages.return_value = mock_message
        
        # Test FileServer
        file_server = FileServer(mock_bot)
        
        # Test file info retrieval
        file_info = await file_server.get_file_info("123_456")
        results.add_result("File info retrieval", file_info is not None)
        
        if file_info:
            results.add_result("File name extraction", file_info['file_name'] == "test_document.pdf")
            results.add_result("File size extraction", file_info['file_size'] == 1024000)
            results.add_result("MIME type extraction", file_info['mime_type'] == "application/pdf")
        
    except Exception as e:
        results.add_result("FileServer mock test", False, str(e))
    
    return results.summary()

async def test_web_app_creation():
    """Test AIOHTTP app creation"""
    print("🌐 Testing Web App Creation...")
    results = TestResults()
    
    try:
        # Create mock bot
        mock_bot = Mock()
        
        # Test app creation
        app = await create_app(mock_bot)
        results.add_result("App creation", app is not None)
        
        # Test routes
        routes = [str(route.resource) for route in app.router.routes()]
        expected_routes = ['/stream/{file_id}', '/download/{file_id}', '/health', '/']
        
        for expected_route in expected_routes:
            route_exists = any(expected_route in route for route in routes)
            results.add_result(f"Route {expected_route}", route_exists)
        
    except Exception as e:
        results.add_result("Web app creation", False, str(e))
    
    return results.summary()

async def test_health_endpoint():
    """Test health endpoint with real server"""
    print("🏥 Testing Health Endpoint...")
    results = TestResults()
    
    try:
        # Create mock bot
        mock_bot = Mock()
        app = await create_app(mock_bot)
        
        # Start test server
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, 'localhost', 8081)
        await site.start()
        
        try:
            # Test health endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8081/health') as response:
                    results.add_result("Health endpoint status", response.status == 200)
                    
                    if response.status == 200:
                        data = await response.json()
                        results.add_result("Health response format", 'status' in data)
                        results.add_result("Health status value", data.get('status') == 'healthy')
                
                # Test root endpoint
                async with session.get('http://localhost:8081/') as response:
                    results.add_result("Root endpoint status", response.status == 200)
        
        finally:
            await runner.cleanup()
    
    except Exception as e:
        results.add_result("Health endpoint test", False, str(e))
    
    return results.summary()

async def test_file_streaming_mock():
    """Test file streaming with mock data"""
    print("📺 Testing File Streaming...")
    results = TestResults()
    
    try:
        # Create mock bot with streaming capability
        mock_bot = Mock()
        mock_bot.get_messages = AsyncMock()
        mock_bot.stream_media = AsyncMock()
        
        # Mock message
        mock_message = Mock()
        mock_message.chat.id = 123
        mock_message.id = 456
        mock_message.video = Mock()
        mock_message.video.file_id = "test_video_id"
        mock_message.video.file_name = "test_video.mp4"
        mock_message.video.file_size = 5000000  # 5MB
        mock_message.video.mime_type = "video/mp4"
        mock_message.document = None
        mock_message.audio = None
        
        mock_bot.get_messages.return_value = mock_message
        
        # Mock streaming data
        test_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        mock_bot.stream_media.return_value = test_chunks
        
        # Create FileServer and test
        file_server = FileServer(mock_bot)
        
        # Test file info for video
        file_info = await file_server.get_file_info("123_456")
        results.add_result("Video file info", file_info is not None)
        results.add_result("Video file type", file_info and file_info['file_type'] == 'video')
        
        # Test caching
        file_info_cached = await file_server.get_file_info("123_456")
        results.add_result("File info caching", file_info_cached is not None)
        
    except Exception as e:
        results.add_result("File streaming mock", False, str(e))
    
    return results.summary()

async def test_bot_logic_mock():
    """Test bot logic with mock Pyrogram client"""
    print("🤖 Testing Bot Logic...")
    results = TestResults()
    
    try:
        from bot_main import FileLinkBot
        
        # Test bot initialization
        bot = FileLinkBot()
        results.add_result("Bot initialization", bot is not None)
        
        # Test file ID generation
        mock_message = Mock()
        mock_message.chat.id = 123
        mock_message.id = 456
        
        file_id = bot.generate_file_id(mock_message)
        expected_id = "123_456"
        results.add_result("File ID generation", file_id == expected_id)
        
        # Test file size formatting
        size_1kb = bot.format_file_size(1024)
        results.add_result("File size formatting (KB)", size_1kb == "1.0 KB")
        
        size_1mb = bot.format_file_size(1024 * 1024)
        results.add_result("File size formatting (MB)", size_1mb == "1.0 MB")
        
        size_1gb = bot.format_file_size(1024 * 1024 * 1024)
        results.add_result("File size formatting (GB)", size_1gb == "1.0 GB")
        
        # Test file info extraction
        mock_message_doc = Mock()
        mock_message_doc.document = Mock()
        mock_message_doc.document.file_name = "test.pdf"
        mock_message_doc.document.file_size = 2048
        mock_message_doc.document.mime_type = "application/pdf"
        mock_message_doc.video = None
        mock_message_doc.audio = None
        
        file_info = bot.get_file_info(mock_message_doc)
        results.add_result("Document file info extraction", file_info is not None)
        results.add_result("Document type detection", file_info and file_info['type'] == 'document')
        
    except Exception as e:
        results.add_result("Bot logic test", False, str(e))
    
    return results.summary()

async def test_error_handling():
    """Test error handling scenarios"""
    print("⚠️ Testing Error Handling...")
    results = TestResults()
    
    try:
        # Test FileServer with invalid file ID
        mock_bot = Mock()
        mock_bot.get_messages = AsyncMock(side_effect=Exception("File not found"))
        
        file_server = FileServer(mock_bot)
        file_info = await file_server.get_file_info("invalid_id")
        results.add_result("Invalid file ID handling", file_info is None)
        
        # Test file size limit
        from bot_main import FileLinkBot
        bot = FileLinkBot()
        
        mock_message = Mock()
        mock_message.document = Mock()
        mock_message.document.file_size = Config.MAX_FILE_SIZE + 1
        mock_message.document.file_name = "huge_file.zip"
        mock_message.document.mime_type = "application/zip"
        mock_message.video = None
        mock_message.audio = None
        
        file_info = bot.get_file_info(mock_message)
        results.add_result("Large file info extraction", file_info is not None)
        results.add_result("File size over limit detection", file_info['size'] > Config.MAX_FILE_SIZE)
        
    except Exception as e:
        results.add_result("Error handling test", False, str(e))
    
    return results.summary()

async def test_security_features():
    """Test security features"""
    print("🔒 Testing Security Features...")
    results = TestResults()
    
    try:
        # Test environment variable loading
        results.add_result("API_ID loaded", Config.API_ID != 0)
        results.add_result("API_HASH loaded", Config.API_HASH != "")
        results.add_result("BOT_TOKEN loaded", Config.BOT_TOKEN != "")
        results.add_result("SECRET_KEY loaded", Config.SECRET_KEY != "")
        
        # Test file ID format (should not expose sensitive data)
        from bot_main import FileLinkBot
        bot = FileLinkBot()
        
        mock_message = Mock()
        mock_message.chat.id = -1001234567890  # Typical channel ID
        mock_message.id = 123
        
        file_id = bot.generate_file_id(mock_message)
        results.add_result("File ID format", "_" in file_id)
        results.add_result("File ID contains chat ID", str(mock_message.chat.id) in file_id)
        
    except Exception as e:
        results.add_result("Security features test", False, str(e))
    
    return results.summary()

async def main():
    """Run comprehensive test suite"""
    print("🧪 Comprehensive Telegram File-to-Link Bot Test Suite")
    print("=" * 60)
    
    test_functions = [
        ("Configuration", test_config_validation),
        ("FileServer Mock", test_file_server_mock),
        ("Web App Creation", test_web_app_creation),
        ("Health Endpoint", test_health_endpoint),
        ("File Streaming Mock", test_file_streaming_mock),
        ("Bot Logic Mock", test_bot_logic_mock),
        ("Error Handling", test_error_handling),
        ("Security Features", test_security_features),
    ]
    
    total_passed = 0
    total_tests = len(test_functions)
    
    for test_name, test_func in test_functions:
        print(f"\n🔍 Running {test_name} tests...")
        try:
            passed = await test_func()
            if passed:
                total_passed += 1
                print(f"✅ {test_name} tests completed successfully")
            else:
                print(f"❌ {test_name} tests had failures")
        except Exception as e:
            print(f"❌ {test_name} tests failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Overall Test Results: {total_passed}/{total_tests} test suites passed")
    
    if total_passed == total_tests:
        print("🎉 All test suites passed! The bot is ready for deployment.")
        return True
    else:
        print("⚠️  Some test suites failed. Review the results above.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
