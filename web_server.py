"""
AIOHTTP Web Server for Telegram File-to-Link Bot
Handles file streaming and download requests
"""

import asyncio
import logging
from typing import Optional
from aiohttp import web, ClientSession
from aiohttp.web_response import StreamResponse
from pyrogram import Client
from pyrogram.types import Message
import hashlib
import time
from config import Config

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class FileServer:
    """File server class to handle Telegram file operations"""
    
    def __init__(self, bot_client: Client):
        self.bot = bot_client
        self.file_cache = {}  # Simple in-memory cache for file metadata
        
    async def get_file_info(self, file_id: str) -> Optional[dict]:
        """Get file information from Telegram"""
        try:
            # Try to get file info from cache first
            if file_id in self.file_cache:
                cached_info = self.file_cache[file_id]
                # Check if cache is still valid (5 minutes)
                if time.time() - cached_info['cached_at'] < 300:
                    return cached_info['data']
            
            # Get file from Telegram
            message = await self.bot.get_messages(
                chat_id=int(file_id.split('_')[0]),
                message_ids=int(file_id.split('_')[1])
            )
            
            if not message or not (message.document or message.video or message.audio):
                return None
            
            # Extract file information
            if message.document:
                file_obj = message.document
                file_type = "document"
            elif message.video:
                file_obj = message.video
                file_type = "video"
            elif message.audio:
                file_obj = message.audio
                file_type = "audio"
            else:
                return None
            
            file_info = {
                'file_id': file_obj.file_id,
                'file_name': getattr(file_obj, 'file_name', f"{file_type}_{file_obj.file_id[:8]}"),
                'file_size': file_obj.file_size,
                'mime_type': getattr(file_obj, 'mime_type', 'application/octet-stream'),
                'message': message,
                'file_type': file_type
            }
            
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
        """Stream file directly from Telegram"""
        file_id = request.match_info['file_id']
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # Prepare response headers
            response = web.StreamResponse()
            response.headers['Content-Type'] = file_info['mime_type']
            response.headers['Content-Length'] = str(file_info['file_size'])
            response.headers['Content-Disposition'] = f'inline; filename="{file_info["file_name"]}"'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            
            # Handle range requests for video streaming
            range_header = request.headers.get('Range')
            if range_header:
                return await self._handle_range_request(request, response, file_info, range_header)
            
            await response.prepare(request)
            
            # Stream file in chunks
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
            
            await response.write_eof()
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error streaming file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def download_file(self, request: web.Request) -> web.StreamResponse:
        """Download file with proper headers"""
        file_id = request.match_info['file_id']
        
        try:
            file_info = await self.get_file_info(file_id)
            if not file_info:
                raise web.HTTPNotFound(text="File not found")
            
            # Check file size limit
            if file_info['file_size'] > Config.MAX_FILE_SIZE:
                raise web.HTTPBadRequest(text="File too large")
            
            # Prepare download response
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = str(file_info['file_size'])
            response.headers['Content-Disposition'] = f'attachment; filename="{file_info["file_name"]}"'
            
            await response.prepare(request)
            
            # Stream file in chunks
            async for chunk in self.bot.stream_media(file_info['message'], limit=Config.CHUNK_SIZE):
                await response.write(chunk)
            
            await response.write_eof()
            return response
            
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise web.HTTPInternalServerError(text="Internal server error")
    
    async def _handle_range_request(self, request: web.Request, response: web.StreamResponse, 
                                  file_info: dict, range_header: str) -> web.StreamResponse:
        """Handle HTTP range requests for video streaming"""
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
                    await response.write(chunk[chunk_start:chunk_end_trim])
                
                current_pos += len(chunk)
            
            await response.write_eof()
            return response
            
        except Exception as e:
            logger.error(f"Error handling range request: {e}")
            raise web.HTTPInternalServerError(text="Range request error")

async def create_app(bot_client: Client) -> web.Application:
    """Create and configure the AIOHTTP application"""
    app = web.Application()
    file_server = FileServer(bot_client)
    
    # Add routes
    app.router.add_get('/stream/{file_id}', file_server.stream_file)
    app.router.add_get('/download/{file_id}', file_server.download_file)
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({"status": "healthy", "service": "telegram-file-bot"})
    
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
    
    return runner
