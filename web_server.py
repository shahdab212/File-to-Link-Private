"""
AIOHTTP Web Server for Telegram File-to-Link Bot
Handles file streaming and download requests
"""

import asyncio
import logging
import os
import sys
import mimetypes
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession
from aiohttp.web_response import StreamResponse
from pyrogram import Client
from pyrogram.types import Message
import hashlib
import time
from pathlib import Path
from urllib.parse import unquote
import json

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from utils.media_utils import MediaProcessor

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class FileServer:
    """File server class for basic streaming and downloads"""
    
    def __init__(self, bot_client: Client):
        self.bot = bot_client
        self.file_cache = {}  # In-memory cache for file metadata
        self.media_processor = MediaProcessor()
        
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Telegram"""
        try:
            # Try to get file info from cache first
            if file_id in self.file_cache:
                cached_info = self.file_cache[file_id]
                # Check if cache is still valid (10 minutes)
                if time.time() - cached_info['cached_at'] < 600:
                    return cached_info['data']
            
            # Get file from Telegram
            message = await self.bot.get_messages(
                chat_id=int(file_id.split('_')[0]),
                message_ids=int(file_id.split('_')[1])
            )
            
            if not message or not (message.document or message.video or message.audio or message.photo):
                return None
            
            # Extract file metadata
            file_info = self.media_processor.extract_file_metadata(message)
            file_info['message'] = message
            
            # Cache the file info
            self.file_cache[file_id] = {
                'data': file_info,
                'cached_at': time.time()
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {e}")
            return None
    
    async def stream_file(self, request: web.Request) -> web.StreamResponse:
        """File streaming with basic features"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # If no filename in URL, redirect to URL with filename
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/stream/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Get streaming headers
            headers = self.media_processor.get_streaming_headers(
                file_info['file_type'], 
                file_info['file_name'], 
                file_info['file_size']
            )
            
            # Prepare response
            response = web.StreamResponse()
            for key, value in headers.items():
                response.headers[key] = value
            
            # Handle range requests for video streaming
            range_header = request.headers.get('Range')
            if range_header:
                return await self._handle_range_request(request, response, file_info, range_header)
            
            await response.prepare(request)
            
            # Stream file in chunks
            bytes_sent = 0
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
                bytes_sent += len(chunk)
            
            await response.write_eof()
            
            # Log streaming statistics
            logger.info(f"Streamed {bytes_sent} bytes for file: {file_info['file_name']}")
            
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error streaming file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def download_file(self, request: web.Request) -> web.StreamResponse:
        """Download file with proper filename handling"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # If no filename in URL, redirect to URL with filename
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/download/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Use provided filename or original filename
            download_filename = unquote(filename) if filename else file_info['file_name']
            safe_filename = self.media_processor.generate_safe_filename(download_filename)
            
            # Prepare download response
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = str(file_info['file_size'])
            response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response.headers['Cache-Control'] = 'no-cache'
            
            await response.prepare(request)
            
            # Stream file in chunks
            bytes_sent = 0
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
                bytes_sent += len(chunk)
            
            await response.write_eof()
            
            # Log download statistics
            logger.info(f"Downloaded {bytes_sent} bytes for file: {safe_filename}")
            
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def direct_link(self, request: web.Request) -> web.Response:
        """Direct link with filename for better compatibility"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Redirect to stream URL with proper filename
            stream_url = f"/stream/{file_id}/{filename}" if filename else f"/stream/{file_id}"
            raise web.HTTPFound(location=stream_url)
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating direct link for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def web_player(self, request: web.Request) -> web.Response:
        """Web player interface for streaming files"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Get file details
            display_name = unquote(filename) if filename else file_info['file_name']
            file_size = self.media_processor.format_file_size(file_info['file_size'])
            stream_url = f"/stream/{file_id}/{filename}" if filename else f"/stream/{file_id}"
            download_url = f"/download/{file_id}/{filename}" if filename else f"/download/{file_id}"
            
            # Check if file is streamable
            is_video = file_info['file_type'] == 'video'
            is_audio = file_info['file_type'] == 'audio'
            is_streamable = is_video or is_audio
            
            if not is_streamable:
                # For non-streamable files, redirect to download
                raise web.HTTPFound(location=download_url)
            
            # Generate HTML player page
            html_content = self._generate_player_html(
                display_name, file_size, stream_url, download_url, is_video, is_audio
            )
            
            return web.Response(text=html_content, content_type='text/html')
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating web player for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    def _generate_player_html(self, filename: str, file_size: str, stream_url: str, 
                            download_url: str, is_video: bool, is_audio: bool) -> str:
        """Generate HTML for the web player"""
        
        # Determine player type and settings
        if is_video:
            player_element = f'''
                <video id="mediaPlayer" controls preload="metadata" style="width: 100%; max-width: 800px; height: auto;">
                    <source src="{stream_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            '''
            media_icon = "🎬"
            media_type = "Video"
        else:  # is_audio
            player_element = f'''
                <audio id="mediaPlayer" controls preload="metadata" style="width: 100%; max-width: 600px;">
                    <source src="{stream_url}" type="audio/mpeg">
                    Your browser does not support the audio tag.
                </audio>
            '''
            media_icon = "🎵"
            media_type = "Audio"
        
        html_template = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
            max-width: 900px;
            width: 100%;
        }}
        
        .header {{
            margin-bottom: 30px;
        }}
        
        .file-icon {{
            font-size: 3rem;
            margin-bottom: 15px;
        }}
        
        .file-name {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 10px;
            word-break: break-word;
        }}
        
        .file-info {{
            font-size: 1rem;
            opacity: 0.8;
            margin-bottom: 5px;
        }}
        
        .player-container {{
            margin: 30px 0;
            display: flex;
            justify-content: center;
        }}
        
        video, audio {{
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .controls {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 30px;
        }}
        
        .btn {{
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .btn-primary {{
            background: rgba(74, 144, 226, 0.8);
            border-color: rgba(74, 144, 226, 1);
        }}
        
        .btn-primary:hover {{
            background: rgba(74, 144, 226, 1);
        }}
        
        .footer {{
            margin-top: 30px;
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
                margin: 10px;
            }}
            
            .file-name {{
                font-size: 1.2rem;
            }}
            
            .controls {{
                flex-direction: column;
                align-items: center;
            }}
            
            .btn {{
                width: 200px;
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="file-icon">{media_icon}</div>
            <div class="file-name">{filename}</div>
            <div class="file-info">{media_type} • {file_size}</div>
        </div>
        
        <div class="player-container">
            {player_element}
        </div>
        
        <div class="controls">
            <a href="{download_url}" class="btn btn-primary">
                📥 Download
            </a>
            <a href="{stream_url}" class="btn" target="_blank">
                🔗 Direct Link
            </a>
            <button onclick="copyToClipboard('{stream_url}')" class="btn">
                📋 Copy Link
            </button>
        </div>
        
        <div class="footer">
            <p>🤖 Powered by Telegram File-to-Link Bot</p>
        </div>
    </div>
    
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(window.location.origin + text).then(function() {{
                // Create a temporary notification
                const btn = event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                btn.style.background = 'rgba(46, 204, 113, 0.8)';
                
                setTimeout(() => {{
                    btn.innerHTML = originalText;
                    btn.style.background = '';
                }}, 2000);
            }}).catch(function(err) {{
                console.error('Could not copy text: ', err);
                alert('Failed to copy link to clipboard');
            }});
        }}
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            const player = document.getElementById('mediaPlayer');
            if (!player) return;
            
            switch(e.code) {{
                case 'Space':
                    e.preventDefault();
                    if (player.paused) {{
                        player.play();
                    }} else {{
                        player.pause();
                    }}
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    player.currentTime = Math.max(0, player.currentTime - 10);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    player.currentTime = Math.min(player.duration, player.currentTime + 10);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    player.volume = Math.min(1, player.volume + 0.1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    player.volume = Math.max(0, player.volume - 0.1);
                    break;
            }}
        }});
        
        // Add loading indicator
        const player = document.getElementById('mediaPlayer');
        if (player) {{
            player.addEventListener('loadstart', function() {{
                console.log('Loading started...');
            }});
            
            player.addEventListener('canplay', function() {{
                console.log('Can start playing');
            }});
            
            player.addEventListener('error', function(e) {{
                console.error('Media error:', e);
                alert('Error loading media. Please try downloading the file instead.');
            }});
        }}
    </script>
</body>
</html>
        '''
        
        return html_template
    
    async def _handle_range_request(self, request: web.Request, response: web.StreamResponse, 
                                  file_info: dict, range_header: str) -> web.StreamResponse:
        """Range request handling for video streaming"""
        try:
            # Parse range header
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_info['file_size'] - 1
            
            # Validate range
            if start >= file_info['file_size'] or end >= file_info['file_size'] or start > end:
                response.set_status(416)  # Range Not Satisfiable
                response.headers['Content-Range'] = f'bytes */{file_info["file_size"]}'
                await response.prepare(request)
                return response
            
            # Set partial content headers
            response.set_status(206)  # Partial Content
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_info["file_size"]}'
            response.headers['Content-Length'] = str(end - start + 1)
            
            await response.prepare(request)
            
            # Stream the requested range
            current_pos = 0
            bytes_sent = 0
            
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                chunk_end = current_pos + len(chunk)
                
                # Skip chunks before the requested range
                if chunk_end <= start:
                    current_pos = chunk_end
                    continue
                
                # Stop if we've passed the requested range
                if current_pos > end:
                    break
                
                # Trim chunk to fit the requested range
                chunk_start = max(0, start - current_pos)
                chunk_end_trim = min(len(chunk), end - current_pos + 1)
                
                if chunk_start < chunk_end_trim:
                    chunk_data = chunk[chunk_start:chunk_end_trim]
                    await response.write(chunk_data)
                    bytes_sent += len(chunk_data)
                
                current_pos += len(chunk)
            
            await response.write_eof()
            
            logger.debug(f"Range request served: {bytes_sent} bytes ({start}-{end})")
            return response
            
        except Exception as e:
            logger.error(f"Error handling range request: {e}")
            raise web.HTTPInternalServerError(text="Range request error")

async def create_app(bot_client: Client) -> web.Application:
    """Create and configure the AIOHTTP application"""
    app = web.Application()
    app['bot_client'] = bot_client
    file_server = FileServer(bot_client)
    
    # Basic file routes
    app.router.add_get('/stream/{file_id}', file_server.stream_file)
    app.router.add_get('/stream/{file_id}/{filename}', file_server.stream_file)
    app.router.add_get('/download/{file_id}', file_server.download_file)
    app.router.add_get('/download/{file_id}/{filename}', file_server.download_file)
    app.router.add_get('/direct/{file_id}/{filename}', file_server.direct_link)
    app.router.add_get('/play/{file_id}', file_server.web_player)
    app.router.add_get('/play/{file_id}/{filename}', file_server.web_player)
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({
            "status": "healthy", 
            "service": "telegram-file-bot",
            "version": "1.0.0",
            "features": [
                "file_streaming",
                "file_download",
                "direct_links"
            ]
        })
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    return app

async def start_web_server(bot_client: Client):
    """Start the web server"""
    app = await create_app(bot_client)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, Config.HOST, Config.PORT)
    await site.start()
    
    logger.info(f"🚀 Web server started on {Config.HOST}:{Config.PORT}")
    logger.info(f"🔗 Base URL: {Config.BASE_URL}")
    logger.info(f"📥 Download URL format: {Config.BASE_URL}/download/{{file_id}}/{{filename}}")
    logger.info(f"📺 Stream URL format: {Config.BASE_URL}/stream/{{file_id}}/{{filename}}")
    logger.info(f"🔗 Direct URL format: {Config.BASE_URL}/direct/{{file_id}}/{{filename}}")
    
    return runner
