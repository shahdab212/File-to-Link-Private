#!/usr/bin/env python3
"""
Deployment readiness test for Telegram File-to-Link Bot
Verifies all components are ready for production deployment
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_structure():
    """Test that all required files exist"""
    print("📁 Testing File Structure...")
    
    required_files = [
        'bot_main.py',
        'web_server.py',
        'config.py',
        'requirements.txt',
        '.env.example',
        'README.md',
        'DEPLOYMENT_GUIDE.md',
        'render.yaml',
        'Makefile'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
        else:
            print(f"   ✅ {file}")
    
    if missing_files:
        print(f"   ❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def test_python_syntax():
    """Test Python syntax of all Python files"""
    print("🐍 Testing Python Syntax...")
    
    python_files = [
        'bot_main.py',
        'web_server.py',
        'config.py',
        'start.py',
        'test_bot.py',
        'test_comprehensive.py',
        'test_streaming.py'
    ]
    
    for file in python_files:
        try:
            with open(file, 'r') as f:
                compile(f.read(), file, 'exec')
            print(f"   ✅ {file}")
        except SyntaxError as e:
            print(f"   ❌ {file}: {e}")
            return False
        except Exception as e:
            print(f"   ⚠️  {file}: {e}")
    
    print("✅ All Python files have valid syntax")
    return True

def test_dependencies():
    """Test that all dependencies can be imported"""
    print("📦 Testing Dependencies...")
    
    # Set test environment to avoid missing env vars
    os.environ.update({
        'API_ID': '123456',
        'API_HASH': 'test_hash',
        'BOT_TOKEN': '123456789:TEST_TOKEN',
        'BASE_URL': 'http://localhost:8080',
        'SECRET_KEY': 'test-secret-key'
    })
    
    dependencies = [
        ('pyrogram', 'pyrogram'),
        ('aiohttp', 'aiohttp'),
        ('asyncio', 'asyncio'),
        ('logging', 'logging'),
        ('os', 'os'),
        ('sys', 'sys'),
        ('pathlib', 'pathlib'),
        ('time', 'time'),
        ('hashlib', 'hashlib'),
        ('typing', 'typing')
    ]
    
    for dep_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"   ✅ {dep_name}")
        except ImportError as e:
            print(f"   ❌ {dep_name}: {e}")
            return False
    
    print("✅ All dependencies available")
    return True

def test_configuration_loading():
    """Test configuration loading"""
    print("🔧 Testing Configuration Loading...")
    
    try:
        from config import Config
        
        # Test basic attributes
        assert hasattr(Config, 'API_ID')
        assert hasattr(Config, 'API_HASH')
        assert hasattr(Config, 'BOT_TOKEN')
        assert hasattr(Config, 'BASE_URL')
        assert hasattr(Config, 'HOST')
        assert hasattr(Config, 'PORT')
        
        # Test methods
        assert hasattr(Config, 'validate')
        assert hasattr(Config, 'get_download_url')
        assert hasattr(Config, 'get_stream_url')
        
        print("   ✅ Configuration class structure")
        
        # Test URL generation
        download_url = Config.get_download_url("test_123")
        stream_url = Config.get_stream_url("test_123")
        
        assert "download" in download_url
        assert "stream" in stream_url
        assert "test_123" in download_url
        assert "test_123" in stream_url
        
        print("   ✅ URL generation methods")
        
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False
    
    print("✅ Configuration loading successful")
    return True

def test_bot_imports():
    """Test bot module imports"""
    print("🤖 Testing Bot Imports...")
    
    try:
        from bot_main import FileLinkBot
        print("   ✅ FileLinkBot import")
        
        from web_server import FileServer, create_app, start_web_server
        print("   ✅ Web server imports")
        
        # Test bot instantiation
        bot = FileLinkBot()
        assert bot is not None
        print("   ✅ Bot instantiation")
        
    except Exception as e:
        print(f"   ❌ Bot imports failed: {e}")
        return False
    
    print("✅ Bot imports successful")
    return True

def test_requirements_file():
    """Test requirements.txt format"""
    print("📋 Testing Requirements File...")
    
    try:
        with open('requirements.txt', 'r') as f:
            lines = f.readlines()
        
        required_packages = ['pyrogram', 'aiohttp', 'tgcrypto']
        found_packages = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                package_name = line.split('==')[0].split('>=')[0].split('<=')[0]
                found_packages.append(package_name)
        
        for package in required_packages:
            if package in found_packages:
                print(f"   ✅ {package}")
            else:
                print(f"   ❌ Missing {package}")
                return False
        
        print(f"   ✅ Total packages: {len(found_packages)}")
        
    except Exception as e:
        print(f"   ❌ Requirements file test failed: {e}")
        return False
    
    print("✅ Requirements file valid")
    return True

def test_render_config():
    """Test Render deployment configuration"""
    print("🌐 Testing Render Configuration...")
    
    try:
        with open('render.yaml', 'r') as f:
            content = f.read()
        
        required_fields = [
            'services:',
            'type: web',
            'env: python',
            'buildCommand:',
            'startCommand:',
            'healthCheckPath:'
        ]
        
        for field in required_fields:
            if field in content:
                print(f"   ✅ {field}")
            else:
                print(f"   ❌ Missing {field}")
                return False
        
        # Check start command
        if 'python bot_main.py' in content:
            print("   ✅ Correct start command")
        else:
            print("   ❌ Incorrect start command")
            return False
        
    except Exception as e:
        print(f"   ❌ Render config test failed: {e}")
        return False
    
    print("✅ Render configuration valid")
    return True

def test_documentation():
    """Test documentation completeness"""
    print("📖 Testing Documentation...")
    
    try:
        # Test README.md
        with open('README.md', 'r') as f:
            readme_content = f.read()
        
        readme_sections = [
            '# 🤖 Telegram File-to-Link Bot',
            '## ✨ Features',
            '## 🚀 Quick Start',
            '## 🌐 Deployment on Render',
            '## 📱 How to Use'
        ]
        
        for section in readme_sections:
            if section in readme_content:
                print(f"   ✅ README: {section}")
            else:
                print(f"   ❌ README missing: {section}")
                return False
        
        # Test deployment guide
        with open('DEPLOYMENT_GUIDE.md', 'r') as f:
            deploy_content = f.read()
        
        if 'step-by-step' in deploy_content.lower() and 'Render' in deploy_content:
            print("   ✅ Deployment guide complete")
        else:
            print("   ❌ Deployment guide incomplete")
            return False
        
    except Exception as e:
        print(f"   ❌ Documentation test failed: {e}")
        return False
    
    print("✅ Documentation complete")
    return True

def test_environment_template():
    """Test environment template"""
    print("🔐 Testing Environment Template...")
    
    try:
        with open('.env.example', 'r') as f:
            env_content = f.read()
        
        required_vars = [
            'API_ID=',
            'API_HASH=',
            'BOT_TOKEN=',
            'BASE_URL=',
            'SECRET_KEY='
        ]
        
        for var in required_vars:
            if var in env_content:
                print(f"   ✅ {var}")
            else:
                print(f"   ❌ Missing {var}")
                return False
        
    except Exception as e:
        print(f"   ❌ Environment template test failed: {e}")
        return False
    
    print("✅ Environment template valid")
    return True

async def main():
    """Run deployment readiness tests"""
    print("🚀 Deployment Readiness Test Suite")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Syntax", test_python_syntax),
        ("Dependencies", test_dependencies),
        ("Configuration Loading", test_configuration_loading),
        ("Bot Imports", test_bot_imports),
        ("Requirements File", test_requirements_file),
        ("Render Configuration", test_render_config),
        ("Documentation", test_documentation),
        ("Environment Template", test_environment_template),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Deployment Readiness: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Bot is ready for deployment!")
        print("\n📋 Next Steps:")
        print("1. Set up your Telegram API credentials")
        print("2. Create a bot with @BotFather")
        print("3. Deploy to Render using the deployment guide")
        print("4. Configure environment variables")
        print("5. Test with real files!")
        return True
    else:
        print("⚠️  Some deployment readiness tests failed.")
        print("Please fix the issues before deploying.")
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
