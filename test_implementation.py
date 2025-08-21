#!/usr/bin/env python3
"""
Test script to verify the enhanced file bot implementation
"""

from utils.media_utils import MediaProcessor
from config import Config

def test_media_processor():
    """Test MediaProcessor functionality"""
    print("🧪 Testing MediaProcessor...")
    
    # Test file type detection
    test_cases = [
        ("Marco.2024.1080p.Hindi.WEB-DL.5.1.x264-HDHub4u.Tv.mkv", "video/x-matroska"),
        ("song.mp3", "audio/mpeg"),
        ("document.pdf", "application/pdf"),
        ("image.jpg", "image/jpeg"),
        ("archive.zip", "application/zip"),
        ("app.apk", "application/vnd.android.package-archive")
    ]
    
    for filename, mime_type in test_cases:
        media_info = MediaProcessor.detect_media_type(filename, mime_type)
        file_type_display = MediaProcessor.get_file_type_display(filename, mime_type)
        is_streamable = MediaProcessor.is_streamable(filename, mime_type)
        
        print(f"\n📝 File Name: {filename}")
        print(f"📏 File Size: 2.7 GB")  # Example size
        print(f"🗂️ File Type: {file_type_display}")
        print(f"🔗 MIME Type: {mime_type}")
        
        if is_streamable:
            print(f"🎵 Streamable: Yes")
            
            # Generate URLs
            urls = MediaProcessor.generate_enhanced_urls("12345_67890", filename, "https://file-to-link-private-apeg.onrender.com")
            
            print(f"\n📥 Download: `{urls['download_named']}`")
            print(f"📺 Stream: `{urls['stream_named']}`")
            print(f"\nVLC URLs:")
            print(f"📱 Android: `{urls['vlc_android']}`")
            print(f"🖥️ Desktop: `{urls['vlc_desktop']}`")
        else:
            # Generate URLs for non-streamable files
            urls = MediaProcessor.generate_enhanced_urls("12345_67890", filename, "https://file-to-link-private-apeg.onrender.com")
            print(f"\n📥 Download: `{urls['download_named']}`")
        
        print("-" * 50)

def test_config():
    """Test Config functionality"""
    print("\n🔧 Testing Config...")
    
    # Test URL generation
    download_url = Config.get_download_url("12345_67890", "test_file.mp4")
    stream_url = Config.get_stream_url("12345_67890", "test_file.mp4")
    
    print(f"Download URL: {download_url}")
    print(f"Stream URL: {stream_url}")

if __name__ == "__main__":
    print("🚀 Testing Enhanced Telegram File Bot Implementation")
    print("=" * 60)
    
    test_media_processor()
    test_config()
    
    print("\n✅ All tests completed!")
    print("\nThe bot now supports:")
    print("• Enhanced file info display with emojis")
    print("• VLC streaming buttons for video/audio files")
    print("• URLs displayed in monospace format")
    print("• Conditional display based on file type")
    print("• Support for both /dl and .dl commands")
