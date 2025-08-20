"""
Enhanced AIOHTTP Web Server for Telegram File-to-Link Bot
Handles advanced file streaming, download requests, and media player
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

class EnhancedFileServer:
    """Enhanced file server class with advanced features"""
    
    def __init__(self, bot_client: Client):
        self.bot = bot_client
        self.file_cache = {}  # Enhanced in-memory cache for file metadata
        self.media_processor = MediaProcessor()
        
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get enhanced file information from Telegram"""
        try:
            # Try to get file info from cache first
            if file_id in self.file_cache:
                cached_info = self.file_cache[file_id]
                # Check if cache is still valid (10 minutes for enhanced cache)
                if time.time() - cached_info['cached_at'] < 600:
                    return cached_info['data']
            
            # Get file from Telegram
            message = await self.bot.get_messages(
                chat_id=int(file_id.split('_')[0]),
                message_ids=int(file_id.split('_')[1])
            )
            
            if not message or not (message.document or message.video or message.audio or message.photo):
                return None
            
            # Extract enhanced file metadata
            file_info = self.media_processor.extract_file_metadata(message)
            file_info['message'] = message
            file_info['file_hash'] = self.media_processor.generate_file_hash(file_id, file_info['file_size'])
            
            # Generate enhanced URLs
            urls = self.media_processor.generate_enhanced_urls(file_id, file_info['file_name'], Config.BASE_URL)
            file_info['urls'] = urls
            
            # Get quality options
            file_info['quality_options'] = self.media_processor.get_quality_options(
                file_info['file_type'], file_info['file_size']
            )
            
            # Cache the enhanced file info
            self.file_cache[file_id] = {
                'data': file_info,
                'cached_at': time.time()
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {e}")
            return None
    
    async def stream_file(self, request: web.Request) -> web.StreamResponse:
        """Enhanced file streaming with advanced features"""
        file_id = request.match_info['file_id']
        filename = request.match_info.get('filename', '')
        
        try:
            # Validate file access
            user_ip = request.remote
            if not self.media_processor.validate_file_access(file_id, user_ip):
                raise web.HTTPForbidden(text="Access denied")
            
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # If no filename in URL, redirect to URL with filename for better SEO and user experience
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/stream/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Detect mobile user agent
            user_agent = request.headers.get('User-Agent', '')
            is_mobile = self.media_processor.is_mobile_user_agent(user_agent)
            
            # Get optimized streaming headers
            headers = self.media_processor.get_streaming_headers(
                file_info['file_type'], 
                file_info['file_name'], 
                file_info['file_size'],
                is_mobile
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
            
            # Stream file in chunks with progress tracking
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
        """Enhanced download with proper filename handling"""
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
            
            # Prepare download response with enhanced headers
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = str(file_info['file_size'])
            response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['X-File-Name'] = safe_filename
            response.headers['X-File-Size'] = str(file_info['file_size'])
            response.headers['X-File-Type'] = file_info['file_type']
            
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
    
    async def file_info_api(self, request: web.Request) -> web.Response:
        """API endpoint for file information"""
        file_id = request.match_info['file_id']
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Remove message object for JSON serialization
            api_info = {k: v for k, v in file_info.items() if k != 'message'}
            
            # Add formatted file size
            api_info['formatted_size'] = self.media_processor.format_file_size(file_info['file_size'])
            
            # Add upload date if available
            if file_info.get('date'):
                api_info['upload_date'] = file_info['date'].isoformat()
            
            return web.json_response(api_info)
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info API for {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def _handle_range_request(self, request: web.Request, response: web.StreamResponse, 
                                  file_info: dict, range_header: str) -> web.StreamResponse:
        """Enhanced range request handling"""
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
            
            # Stream the requested range with better chunk handling
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
    """Create and configure the enhanced AIOHTTP application"""
    app = web.Application()
    app['bot_client'] = bot_client
    file_server = EnhancedFileServer(bot_client)
    
    # Static files serving
    static_dir = Path(__file__).parent / 'static'
    if static_dir.exists():
        app.router.add_static('/static/', static_dir, name='static')
    
    # Enhanced file routes
    app.router.add_get('/stream/{file_id}', file_server.stream_file)
    app.router.add_get('/stream/{file_id}/{filename}', file_server.stream_file)
    app.router.add_get('/download/{file_id}', file_server.download_file)
    app.router.add_get('/download/{file_id}/{filename}', file_server.download_file)
    app.router.add_get('/direct/{file_id}/{filename}', file_server.direct_link)
    app.router.add_get('/info/{file_id}', file_server.file_info_api)
    
    # Enhanced player routes
    async def advanced_player_page(request):
        file_id = request.match_info.get('file_id', '')
        filename = request.match_info.get('filename', '')
        
        if not file_id:
            return web.Response(text="No file ID provided", status=400)
            
        try:
            # Get enhanced file info
            file_info = await file_server.get_file_info(file_id)
            if not file_info:
                return web.Response(text="File not found", status=404)
            
            # If no filename in URL, redirect to URL with filename for better SEO and user experience
            if not filename:
                from urllib.parse import quote
                safe_filename = quote(file_info['file_name'], safe='')
                redirect_url = f"/play/{file_id}/{safe_filename}"
                raise web.HTTPFound(location=redirect_url)
            
            # Prepare template context
            context = {
                'file_id': file_id,
                'file_name': file_info['file_name'],
                'file_type': file_info['file_type'],
                'file_size': MediaProcessor.format_file_size(file_info['file_size']),
                'upload_date': file_info.get('date', 'Unknown').strftime('%Y-%m-%d') if file_info.get('date') else 'Unknown',
                'download_url': file_info['urls']['download_named'],
                'stream_url': file_info['urls']['stream_named'],
                'player_url': file_info['urls']['player_named'],
                'direct_url': file_info['urls']['direct'],
                'mime_type': file_info['mime_type'],
                'duration': file_info.get('duration'),
                'width': file_info.get('width'),
                'height': file_info.get('height')
            }
            
            # Load and render template
            template_path = Path(__file__).parent / 'templates' / 'advanced_player.html'
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Simple template rendering (replace placeholders)
                for key, value in context.items():
                    if value is not None:
                        template_content = template_content.replace(f'{{{{ {key} }}}}', str(value))
                
                return web.Response(text=template_content, content_type='text/html')
            else:
                # Fallback to basic player if template not found
                return await basic_player_fallback(file_id, file_info)
                
        except Exception as e:
            logger.error(f"Error serving advanced player page: {e}")
            return web.Response(text="Error loading player", status=500)
    
    async def basic_player_fallback(file_id: str, file_info: dict):
        """Fallback basic player if advanced template fails"""
        file_name = file_info['file_name'] if file_info else f"File_{file_id}"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{file_name} - Media Player</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/player.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1><i class="fas fa-play-circle"></i> Media Player</h1>
            <p>{file_name}</p>
        </header>
        
        <main class="player-container">
            <div id="mediaContainer" class="loading">
                <div class="spinner"></div>
                <p>Loading media player...</p>
            </div>
            
            <div class="action-buttons">
                <a href="/download/{file_id}" class="btn btn-primary">
                    <i class="fas fa-download"></i> Download
                </a>
                <a href="/stream/{file_id}" class="btn btn-success">
                    <i class="fas fa-external-link-alt"></i> Direct Stream
                </a>
            </div>
        </main>
    </div>
    
    <script src="/static/js/player.js"></script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    # Add player routes
    app.router.add_get('/play/{file_id}', advanced_player_page)
    app.router.add_get('/play/{file_id}/{filename}', advanced_player_page)
    app.router.add_get('/player/{file_id}', advanced_player_page)
    app.router.add_get('/player/{file_id}/{filename}', advanced_player_page)
    
    # Embed player route (for iframe embedding)
    async def embed_player(request):
        file_id = request.match_info.get('file_id', '')
        if not file_id:
            return web.Response(text="No file ID provided", status=400)
        
        try:
            file_info = await file_server.get_file_info(file_id)
            if not file_info:
                return web.Response(text="File not found", status=404)
            
            # Simple embed player
            embed_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Embedded Player</title>
    <style>
        body {{ margin: 0; padding: 0; background: #000; }}
        video, audio {{ width: 100%; height: 100%; }}
    </style>
</head>
<body>
    <div id="player"></div>
    <script>
        const fileType = '{file_info['file_type']}';
        const streamUrl = '/stream/{file_id}';
        const player = document.getElementById('player');
        
        if (fileType === 'video') {{
            player.innerHTML = '<video controls autoplay><source src="' + streamUrl + '"></video>';
        }} else if (fileType === 'audio') {{
            player.innerHTML = '<audio controls autoplay><source src="' + streamUrl + '"></audio>';
        }} else {{
            player.innerHTML = '<p style="color: white; text-align: center; padding: 20px;">File type not supported for embedding</p>';
        }}
    </script>
</body>
</html>
            """
            return web.Response(text=embed_html, content_type='text/html')
            
        except Exception as e:
            logger.error(f"Error serving embed player: {e}")
            return web.Response(text="Error loading embed player", status=500)
    
    app.router.add_get('/embed/{file_id}', embed_player)
    
    # Thumbnail route (placeholder for future implementation)
    async def thumbnail(request):
        file_id = request.match_info.get('file_id', '')
        # For now, return a default thumbnail
        return web.Response(text="Thumbnail generation not implemented yet", status=501)
    
    app.router.add_get('/thumb/{file_id}', thumbnail)
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({
            "status": "healthy", 
            "service": "telegram-file-bot-enhanced",
            "version": "2.0.0",
            "features": [
                "advanced_player",
                "enhanced_streaming",
                "mobile_optimization",
                "range_requests",
                "file_info_api",
                "direct_links",
                "embed_support"
            ]
        })
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    # API status endpoint
    async def api_status(request):
        return web.json_response({
            "api_version": "2.0",
            "endpoints": {
                "stream": "/stream/{file_id}[/{filename}]",
                "download": "/download/{file_id}[/{filename}]",
                "player": "/play/{file_id}[/{filename}]",
                "direct": "/direct/{file_id}/{filename}",
                "info": "/info/{file_id}",
                "embed": "/embed/{file_id}",
                "thumbnail": "/thumb/{file_id}"
            },
            "features": {
                "range_requests": True,
                "mobile_optimization": True,
                "advanced_player": True,
                "file_info_api": True,
                "embed_support": True
            }
        })
    
    app.router.add_get('/api', api_status)
    
    return app

async def start_web_server(bot_client: Client):
    """Start the enhanced web server"""
    app = await create_app(bot_client)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, Config.HOST, Config.PORT)
    await site.start()
    
    logger.info(f"🚀 Enhanced Web server started on {Config.HOST}:{Config.PORT}")
    logger.info(f"🔗 Base URL: {Config.BASE_URL}")
    logger.info(f"✨ Features: Advanced Player, Enhanced Streaming, Mobile Optimization")
    logger.info(f"📱 Static files served from: /static/")
    logger.info(f"🎮 Player URL format: {Config.BASE_URL}/play/{{file_id}}/{{filename}}")
    logger.info(f"📥 Download URL format: {Config.BASE_URL}/download/{{file_id}}/{{filename}}")
    logger.info(f"🔗 Direct URL format: {Config.BASE_URL}/direct/{{file_id}}/{{filename}}")
    
    return runner
