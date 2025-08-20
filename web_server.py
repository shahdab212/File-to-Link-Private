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
