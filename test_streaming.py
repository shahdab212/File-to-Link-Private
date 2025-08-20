#!/usr/bin/env python3
"""
Advanced streaming and HTTP range request testing
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment
os.environ.update({
    'API_ID': '123456',
    'API_HASH': 'test_hash',
    'BOT_TOKEN': '123456789:TEST_TOKEN',
    'BASE_URL': 'http://localhost:8082',
    'SECRET_KEY': 'test-secret-key',
    'HOST': '0.0.0.0',
    'PORT': '8082',
    'LOG_LEVEL': 'INFO'
})

from web_server import create_app, FileServer

async def test_range_requests():
    """Test HTTP range request handling"""
    print("📺 Testing HTTP Range Requests...")
    
    # Create mock bot with large file
    mock_bot = Mock()
    mock_bot.get_messages = AsyncMock()
    mock_bot.stream_media = AsyncMock()
    
    # Mock large video file
    mock_message = Mock()
    mock_message.chat.id = 123
    mock_message.id = 456
    mock_message.video = Mock()
    mock_message.video.file_id = "large_video_id"
    mock_message.video.file_name = "large_video.mp4"
    mock_message.video.file_size = 10000000  # 10MB
    mock_message.video.mime_type = "video/mp4"
    mock_message.document = None
    mock_message.audio = None
    
    mock_bot.get_messages.return_value = mock_message
    
    # Create test data (10MB worth)
    test_data = b"0123456789" * 1000000  # 10MB of test data
    chunks = [test_data[i:i+1048576] for i in range(0, len(test_data), 1048576)]  # 1MB chunks
    
    # Create async generator for streaming
    async def mock_stream_media(*args, **kwargs):
        for chunk in chunks:
            yield chunk
    
    mock_bot.stream_media = mock_stream_media
    
    # Create app and start server
    app = await create_app(mock_bot)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, 'localhost', 8082)
    await site.start()
    
    try:
        async with aiohttp.ClientSession() as session:
            file_id = "123_456"
            
            # Test 1: Full file request
            print("   Testing full file request...")
            async with session.get(f'http://localhost:8082/stream/{file_id}') as response:
                assert response.status == 200, f"Expected 200, got {response.status}"
                assert response.headers['Content-Length'] == '10000000'
                assert response.headers['Content-Type'] == 'video/mp4'
                print("   ✅ Full file request successful")
            
            # Test 2: Range request - first 1MB
            print("   Testing range request (first 1MB)...")
            headers = {'Range': 'bytes=0-1048575'}
            async with session.get(f'http://localhost:8082/stream/{file_id}', headers=headers) as response:
                assert response.status == 206, f"Expected 206, got {response.status}"
                assert 'Content-Range' in response.headers
                assert response.headers['Content-Length'] == '1048576'
                print("   ✅ Range request (first 1MB) successful")
            
            # Test 3: Range request - middle portion
            print("   Testing range request (middle portion)...")
            headers = {'Range': 'bytes=2097152-4194303'}  # 2MB-4MB
            async with session.get(f'http://localhost:8082/stream/{file_id}', headers=headers) as response:
                assert response.status == 206, f"Expected 206, got {response.status}"
                assert response.headers['Content-Length'] == '2097152'  # 2MB
                print("   ✅ Range request (middle portion) successful")
            
            # Test 4: Range request - last bytes
            print("   Testing range request (last bytes)...")
            headers = {'Range': 'bytes=9999000-'}  # Last 1000 bytes
            async with session.get(f'http://localhost:8082/stream/{file_id}', headers=headers) as response:
                assert response.status == 206, f"Expected 206, got {response.status}"
                assert response.headers['Content-Length'] == '1000'
                print("   ✅ Range request (last bytes) successful")
            
            # Test 5: Invalid range request
            print("   Testing invalid range request...")
            headers = {'Range': 'bytes=20000000-30000000'}  # Beyond file size
            async with session.get(f'http://localhost:8082/stream/{file_id}', headers=headers) as response:
                assert response.status == 416, f"Expected 416, got {response.status}"
                print("   ✅ Invalid range request handled correctly")
            
            # Test 6: Download endpoint
            print("   Testing download endpoint...")
            async with session.get(f'http://localhost:8082/download/{file_id}') as response:
                assert response.status == 200, f"Expected 200, got {response.status}"
                assert response.headers['Content-Type'] == 'application/octet-stream'
                assert 'attachment' in response.headers['Content-Disposition']
                print("   ✅ Download endpoint successful")
    
    finally:
        await runner.cleanup()
    
    print("✅ All streaming tests passed!")
    return True

async def test_different_file_types():
    """Test different file types handling"""
    print("📁 Testing Different File Types...")
    
    file_types = [
        {
            'type': 'document',
            'file_name': 'document.pdf',
            'mime_type': 'application/pdf',
            'size': 5000000
        },
        {
            'type': 'audio',
            'file_name': 'audio.mp3',
            'mime_type': 'audio/mpeg',
            'size': 8000000
        },
        {
            'type': 'video',
            'file_name': 'video.mkv',
            'mime_type': 'video/x-matroska',
            'size': 50000000
        }
    ]
    
    for i, file_type in enumerate(file_types):
        print(f"   Testing {file_type['type']} file...")
        
        # Create mock bot
        mock_bot = Mock()
        mock_bot.get_messages = AsyncMock()
        mock_bot.stream_media = AsyncMock()
        
        # Create mock message
        mock_message = Mock()
        mock_message.chat.id = 123
        mock_message.id = 456 + i
        
        # Set file attributes based on type
        if file_type['type'] == 'document':
            mock_message.document = Mock()
            mock_message.document.file_id = f"doc_id_{i}"
            mock_message.document.file_name = file_type['file_name']
            mock_message.document.file_size = file_type['size']
            mock_message.document.mime_type = file_type['mime_type']
            mock_message.video = None
            mock_message.audio = None
        elif file_type['type'] == 'audio':
            mock_message.audio = Mock()
            mock_message.audio.file_id = f"audio_id_{i}"
            mock_message.audio.file_name = file_type['file_name']
            mock_message.audio.file_size = file_type['size']
            mock_message.audio.mime_type = file_type['mime_type']
            mock_message.document = None
            mock_message.video = None
        elif file_type['type'] == 'video':
            mock_message.video = Mock()
            mock_message.video.file_id = f"video_id_{i}"
            mock_message.video.file_name = file_type['file_name']
            mock_message.video.file_size = file_type['size']
            mock_message.video.mime_type = file_type['mime_type']
            mock_message.document = None
            mock_message.audio = None
        
        mock_bot.get_messages.return_value = mock_message
        
        # Test file server
        file_server = FileServer(mock_bot)
        file_info = await file_server.get_file_info(f"123_{456 + i}")
        
        assert file_info is not None, f"File info should not be None for {file_type['type']}"
        assert file_info['file_type'] == file_type['type'], f"File type mismatch for {file_type['type']}"
        assert file_info['file_name'] == file_type['file_name'], f"File name mismatch for {file_type['type']}"
        assert file_info['file_size'] == file_type['size'], f"File size mismatch for {file_type['type']}"
        assert file_info['mime_type'] == file_type['mime_type'], f"MIME type mismatch for {file_type['type']}"
        
        print(f"   ✅ {file_type['type']} file handling successful")
    
    print("✅ All file type tests passed!")
    return True

async def test_caching_system():
    """Test file info caching system"""
    print("🗄️ Testing Caching System...")
    
    # Create mock bot
    mock_bot = Mock()
    mock_bot.get_messages = AsyncMock()
    
    # Mock message
    mock_message = Mock()
    mock_message.chat.id = 123
    mock_message.id = 456
    mock_message.document = Mock()
    mock_message.document.file_id = "cached_file_id"
    mock_message.document.file_name = "cached_file.pdf"
    mock_message.document.file_size = 1000000
    mock_message.document.mime_type = "application/pdf"
    mock_message.video = None
    mock_message.audio = None
    
    mock_bot.get_messages.return_value = mock_message
    
    # Create file server
    file_server = FileServer(mock_bot)
    
    # First call - should call get_messages
    print("   Testing first file info call...")
    file_info1 = await file_server.get_file_info("123_456")
    assert file_info1 is not None
    assert mock_bot.get_messages.call_count == 1
    print("   ✅ First call successful")
    
    # Second call - should use cache
    print("   Testing cached file info call...")
    file_info2 = await file_server.get_file_info("123_456")
    assert file_info2 is not None
    assert mock_bot.get_messages.call_count == 1  # Should still be 1 (cached)
    assert file_info1['file_name'] == file_info2['file_name']
    print("   ✅ Cached call successful")
    
    # Test cache expiration (simulate time passage)
    print("   Testing cache expiration...")
    import time
    # Manually expire cache
    file_server.file_cache["123_456"]['cached_at'] = time.time() - 400  # 400 seconds ago
    
    file_info3 = await file_server.get_file_info("123_456")
    assert file_info3 is not None
    assert mock_bot.get_messages.call_count == 2  # Should be 2 now (cache expired)
    print("   ✅ Cache expiration successful")
    
    print("✅ All caching tests passed!")
    return True

async def test_error_scenarios():
    """Test various error scenarios"""
    print("⚠️ Testing Error Scenarios...")
    
    # Create mock bot that fails
    mock_bot = Mock()
    mock_bot.get_messages = AsyncMock(side_effect=Exception("Network error"))
    
    # Create app
    app = await create_app(mock_bot)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, 'localhost', 8083)
    await site.start()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Non-existent file
            print("   Testing non-existent file...")
            async with session.get('http://localhost:8083/stream/nonexistent') as response:
                assert response.status == 404, f"Expected 404, got {response.status}"
                print("   ✅ Non-existent file handled correctly")
            
            # Test 2: Invalid file ID format
            print("   Testing invalid file ID format...")
            async with session.get('http://localhost:8083/stream/invalid_format') as response:
                assert response.status == 404, f"Expected 404, got {response.status}"
                print("   ✅ Invalid file ID format handled correctly")
            
            # Test 3: Download endpoint with error
            print("   Testing download endpoint with error...")
            async with session.get('http://localhost:8083/download/error_file') as response:
                assert response.status == 404, f"Expected 404, got {response.status}"
                print("   ✅ Download endpoint error handled correctly")
    
    finally:
        await runner.cleanup()
    
    print("✅ All error scenario tests passed!")
    return True

async def main():
    """Run streaming tests"""
    print("🧪 Advanced Streaming Test Suite")
    print("=" * 50)
    
    tests = [
        ("HTTP Range Requests", test_range_requests),
        ("Different File Types", test_different_file_types),
        ("Caching System", test_caching_system),
        ("Error Scenarios", test_error_scenarios),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} completed successfully")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"🎯 Streaming Tests: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All streaming tests passed!")
        return True
    else:
        print("⚠️  Some streaming tests failed.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
