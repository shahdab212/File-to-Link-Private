"""
Media utilities for file processing and metadata extraction
"""

import os
import hashlib
import mimetypes
from typing import Optional, Dict, Any
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Media processing utilities"""
    
    # Supported media types
    MEDIA_TYPES = {
        'video': {
            'extensions': ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v'],
            'mime_types': ['video/mp4', 'video/x-matroska', 'video/x-msvideo', 'video/quicktime', 
                          'video/webm', 'video/x-flv', 'video/x-ms-wmv'],
            'icon': 'fas fa-video',
            'color': '#e74c3c'
        },
        'audio': {
            'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
            'mime_types': ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 
                          'audio/ogg', 'audio/mp4', 'audio/x-ms-wma'],
            'icon': 'fas fa-music',
            'color': '#9b59b6'
        },
        'document': {
            'extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
            'mime_types': ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/plain', 'application/rtf', 'application/vnd.oasis.opendocument.text'],
            'icon': 'fas fa-file-alt',
            'color': '#3498db'
        },
        'archive': {
            'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'mime_types': ['application/zip', 'application/x-rar-compressed', 
                          'application/x-7z-compressed', 'application/x-tar',
                          'application/gzip', 'application/x-bzip2'],
            'icon': 'fas fa-file-archive',
            'color': '#f39c12'
        },
        'image': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 
                          'image/webp', 'image/svg+xml'],
            'icon': 'fas fa-image',
            'color': '#2ecc71'
        },
        'application': {
            'extensions': ['.apk', '.exe', '.dmg', '.deb', '.rpm'],
            'mime_types': ['application/vnd.android.package-archive', 
                          'application/x-msdownload', 'application/x-apple-diskimage',
                          'application/x-debian-package', 'application/x-rpm'],
            'icon': 'fas fa-cog',
            'color': '#95a5a6'
        }
    }
    
    @classmethod
    def detect_media_type(cls, filename: str, mime_type: str = None) -> Dict[str, Any]:
        """
        Detect media type and return metadata
        """
        filename_lower = filename.lower()
        
        # Try to detect by file extension first
        for media_type, info in cls.MEDIA_TYPES.items():
            for ext in info['extensions']:
                if filename_lower.endswith(ext):
                    return {
                        'type': media_type,
                        'icon': info['icon'],
                        'color': info['color'],
                        'extension': ext,
                        'is_streamable': media_type in ['video', 'audio']
                    }
        
        # Try to detect by MIME type
        if mime_type:
            for media_type, info in cls.MEDIA_TYPES.items():
                if mime_type in info['mime_types']:
                    return {
                        'type': media_type,
                        'icon': info['icon'],
                        'color': info['color'],
                        'mime_type': mime_type,
                        'is_streamable': media_type in ['video', 'audio']
                    }
        
        # Default fallback
        return {
            'type': 'unknown',
            'icon': 'fas fa-file',
            'color': '#95a5a6',
            'is_streamable': False
        }
    
    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    @classmethod
    def generate_safe_filename(cls, filename: str) -> str:
        """Generate URL-safe filename"""
        # Remove or replace unsafe characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.() "
        safe_filename = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Remove multiple consecutive underscores and spaces
        while '__' in safe_filename:
            safe_filename = safe_filename.replace('__', '_')
        while '  ' in safe_filename:
            safe_filename = safe_filename.replace('  ', ' ')
        
        # Trim and ensure it's not empty
        safe_filename = safe_filename.strip('_. ')
        if not safe_filename:
            safe_filename = 'unnamed_file'
        
        return safe_filename
    
    @classmethod
    def generate_enhanced_urls(cls, file_id: str, filename: str, base_url: str) -> Dict[str, str]:
        """Generate essential URLs for download and streaming"""
        safe_filename = cls.generate_safe_filename(filename)
        encoded_filename = quote(safe_filename, safe='')
        
        urls = {
            'download': f"{base_url}/download/{file_id}",
            'download_named': f"{base_url}/download/{file_id}/{encoded_filename}",
            'stream': f"{base_url}/stream/{file_id}",
            'stream_named': f"{base_url}/stream/{file_id}/{encoded_filename}",
            'play': f"{base_url}/play/{file_id}",
            'play_named': f"{base_url}/play/{file_id}/{encoded_filename}"
        }
        
        return urls
    
    @classmethod
    def is_streamable(cls, filename: str, mime_type: str = None) -> bool:
        """Check if a file is streamable (video or audio)"""
        media_info = cls.detect_media_type(filename, mime_type)
        return media_info.get('is_streamable', False)
    
    @classmethod
    def get_file_type_display(cls, filename: str, mime_type: str = None) -> str:
        """Get display-friendly file type"""
        media_info = cls.detect_media_type(filename, mime_type)
        file_type = media_info.get('type', 'unknown')
        
        type_mapping = {
            'video': 'Video',
            'audio': 'Audio',
            'document': 'Document',
            'image': 'Image',
            'archive': 'Archive',
            'application': 'Application',
            'unknown': 'File'
        }
        
        return type_mapping.get(file_type, 'File')
    
    @classmethod
    def extract_file_metadata(cls, message) -> Dict[str, Any]:
        """Extract file metadata from Telegram message"""
        metadata = {
            'file_id': None,
            'file_name': 'Unknown File',
            'file_size': 0,
            'mime_type': 'application/octet-stream',
            'file_type': 'unknown',
            'duration': None,
            'width': None,
            'height': None,
            'thumbnail': None,
            'performer': None,
            'title': None,
            'date': None
        }
        
        try:
            if message.document:
                file_obj = message.document
                metadata.update({
                    'file_id': file_obj.file_id,
                    'file_name': file_obj.file_name or f"document_{file_obj.file_id[:8]}",
                    'file_size': file_obj.file_size,
                    'mime_type': file_obj.mime_type or 'application/octet-stream',
                    'file_type': 'document',
                    'thumbnail': getattr(file_obj, 'thumbs', None)
                })
                
            elif message.video:
                file_obj = message.video
                metadata.update({
                    'file_id': file_obj.file_id,
                    'file_name': file_obj.file_name or f"video_{file_obj.file_id[:8]}.mp4",
                    'file_size': file_obj.file_size,
                    'mime_type': file_obj.mime_type or 'video/mp4',
                    'file_type': 'video',
                    'duration': file_obj.duration,
                    'width': file_obj.width,
                    'height': file_obj.height,
                    'thumbnail': getattr(file_obj, 'thumbs', None)
                })
                
            elif message.audio:
                file_obj = message.audio
                metadata.update({
                    'file_id': file_obj.file_id,
                    'file_name': file_obj.file_name or f"audio_{file_obj.file_id[:8]}.mp3",
                    'file_size': file_obj.file_size,
                    'mime_type': file_obj.mime_type or 'audio/mpeg',
                    'file_type': 'audio',
                    'duration': file_obj.duration,
                    'performer': file_obj.performer,
                    'title': file_obj.title,
                    'thumbnail': getattr(file_obj, 'thumbs', None)
                })
                
            elif message.photo:
                file_obj = message.photo
                metadata.update({
                    'file_id': file_obj.file_id,
                    'file_name': f"photo_{file_obj.file_id[:8]}.jpg",
                    'file_size': file_obj.file_size,
                    'mime_type': 'image/jpeg',
                    'file_type': 'image',
                    'width': file_obj.width,
                    'height': file_obj.height
                })
            
            # Add message date
            if message.date:
                metadata['date'] = message.date
                
            # Enhance with media type detection
            media_info = cls.detect_media_type(metadata['file_name'], metadata['mime_type'])
            metadata.update(media_info)
            
        except Exception as e:
            logger.error(f"Error extracting file metadata: {e}")
        
        return metadata
    
    @classmethod
    def get_streaming_headers(cls, file_type: str, filename: str, file_size: int) -> Dict[str, str]:
        """Get headers for streaming"""
        headers = {
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Range, Content-Type',
            'X-Content-Type-Options': 'nosniff'
        }
        
        # Set appropriate MIME type
        mime_type = mimetypes.guess_type(filename)[0]
        if not mime_type:
            if file_type == 'video':
                mime_type = 'video/mp4'
            elif file_type == 'audio':
                mime_type = 'audio/mpeg'
            else:
                mime_type = 'application/octet-stream'
        
        headers['Content-Type'] = mime_type
        headers['Content-Length'] = str(file_size)
        
        return headers
