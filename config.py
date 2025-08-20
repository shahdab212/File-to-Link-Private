"""
Configuration module for Telegram File-to-Link Bot
Handles environment variables and application settings
"""

import os
from typing import Optional

class Config:
    """Configuration class for the Telegram bot and web server"""
    
    # Telegram Bot Configuration
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Web Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    BASE_URL: str = os.getenv("BASE_URL", f"http://localhost:{PORT}")
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # File Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "4294967296"))  # 4GB in bytes
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1048576"))  # 1MB chunks
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Session Configuration
    SESSION_NAME: str = os.getenv("SESSION_NAME", "file_bot_session")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = ["API_ID", "API_HASH", "BOT_TOKEN"]
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var) or getattr(cls, var) == "0":
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        print("✅ Configuration validation passed")
        return True
    
    @classmethod
    def get_download_url(cls, file_id: str, filename: str = None) -> str:
        """Generate download URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/download/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/download/{file_id}"
    
    @classmethod
    def get_stream_url(cls, file_id: str, filename: str = None) -> str:
        """Generate streaming URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/stream/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/stream/{file_id}"
    
    @classmethod
    def get_player_url(cls, file_id: str, filename: str = None) -> str:
        """Generate player URL for a file"""
        if filename:
            # URL encode the filename and add it as a path parameter
            import urllib.parse
            safe_filename = urllib.parse.quote(filename, safe='')
            return f"{cls.BASE_URL}/play/{file_id}/{safe_filename}"
        return f"{cls.BASE_URL}/play/{file_id}"
