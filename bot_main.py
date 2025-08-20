"""
Main Telegram Bot Logic for File-to-Link Bot
Handles user interactions and command processing
"""

import asyncio
import logging
import hashlib
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified
from config import Config
from web_server import start_web_server

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileLinkBot:
    """Main bot class handling all Telegram interactions"""
    
    def __init__(self):
        self.bot = Client(
            Config.SESSION_NAME,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.web_runner = None
        
    def generate_file_id(self, message: Message) -> str:
        """Generate a unique file ID for the message"""
        return f"{message.chat.id}_{message.id}"
    
    def get_file_info(self, message: Message) -> Optional[dict]:
        """Extract file information from message"""
        if message.document:
            return {
                'type': 'document',
                'file': message.document,
                'name': message.document.file_name or f"document_{message.document.file_id[:8]}",
                'size': message.document.file_size,
                'mime_type': message.document.mime_type or 'application/octet-stream'
            }
        elif message.video:
            return {
                'type': 'video',
                'file': message.video,
                'name': message.video.file_name or f"video_{message.video.file_id[:8]}.mp4",
                'size': message.video.file_size,
                'mime_type': message.video.mime_type or 'video/mp4'
            }
        elif message.audio:
            return {
                'type': 'audio',
                'file': message.audio,
                'name': message.audio.file_name or f"audio_{message.audio.file_id[:8]}.mp3",
                'size': message.audio.file_size,
                'mime_type': message.audio.mime_type or 'audio/mpeg'
            }
        return None
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    async def setup_handlers(self):
        """Setup all bot command and message handlers"""
        
        @self.bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            welcome_text = (
                "🤖 **Welcome to File-to-Link Bot!**\n\n"
                "📁 I can generate direct download and streaming links for your Telegram files.\n\n"
                "**How to use:**\n"
                "1. Forward or send any video, audio, or document file\n"
                "2. Reply to that message with `/fdl`\n"
                "3. Get instant download and streaming links!\n\n"
                "**Supported files:**\n"
                "• 📹 Videos (up to 4GB)\n"
                "• 🎵 Audio files\n"
                "• 📄 Documents\n\n"
                "**Features:**\n"
                "• ⚡ Fast streaming without downloading\n"
                "• 📱 Mobile-friendly links\n"
                "• 🔒 Secure file handling\n\n"
                "Try it now by sending a file and replying with `/fdl`!"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 Help", callback_data="help")],
                [InlineKeyboardButton("ℹ️ About", callback_data="about")]
            ])
            
            await message.reply_text(welcome_text, reply_markup=keyboard)
        
        @self.bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            """Handle /help command"""
            help_text = (
                "📖 **Help - How to Use File-to-Link Bot**\n\n"
                "**Step-by-step guide:**\n\n"
                "1️⃣ **Send a file**: Upload any video, audio, or document to the chat\n"
                "2️⃣ **Reply with /fdl**: Reply to the file message with the command `/fdl`\n"
                "3️⃣ **Get your links**: Receive download and streaming links instantly!\n\n"
                "**Supported file types:**\n"
                "• 🎬 Video files (.mp4, .mkv, .avi, etc.)\n"
                "• 🎵 Audio files (.mp3, .flac, .wav, etc.)\n"
                "• 📄 Document files (.pdf, .zip, .apk, etc.)\n\n"
                "**File size limit:** Up to 4GB per file\n\n"
                "**Example usage:**\n"
                "```\n"
                "User: [sends video.mp4]\n"
                "User: /fdl (as reply to the video)\n"
                "Bot: [generates links with buttons]\n"
                "```\n\n"
                "**Need more help?** Contact support or check our documentation."
            )
            
            await message.reply_text(help_text)
        
        @self.bot.on_message(filters.command("fdl"))
        async def fdl_command(client: Client, message: Message):
            """Handle /fdl command - main functionality"""
            try:
                # Check if this is a reply to a message
                if not message.reply_to_message:
                    await message.reply_text(
                        "❌ **Please reply to a file message with `/fdl`**\n\n"
                        "📝 **How to use:**\n"
                        "1. Find a message with a video, audio, or document\n"
                        "2. Reply to that message with `/fdl`\n"
                        "3. Get your download links!\n\n"
                        "💡 **Tip:** You can forward files from other chats and then use `/fdl`"
                    )
                    return
                
                replied_message = message.reply_to_message
                file_info = self.get_file_info(replied_message)
                
                if not file_info:
                    await message.reply_text(
                        "❌ **No supported file found!**\n\n"
                        "📁 **Supported file types:**\n"
                        "• 📹 Videos\n"
                        "• 🎵 Audio files\n"
                        "• 📄 Documents\n\n"
                        "Please reply to a message containing one of these file types."
                    )
                    return
                
                # Check file size
                if file_info['size'] > Config.MAX_FILE_SIZE:
                    max_size_formatted = self.format_file_size(Config.MAX_FILE_SIZE)
                    await message.reply_text(
                        f"❌ **File too large!**\n\n"
                        f"📏 **File size:** {self.format_file_size(file_info['size'])}\n"
                        f"📏 **Maximum allowed:** {max_size_formatted}\n\n"
                        "Please try with a smaller file."
                    )
                    return
                
                # Generate file ID and URLs
                file_id = self.generate_file_id(replied_message)
                download_url = Config.get_download_url(file_id)
                stream_url = Config.get_stream_url(file_id)
                
                # Create response message
                file_type_emoji = {
                    'video': '🎬',
                    'audio': '🎵',
                    'document': '📄'
                }
                
                emoji = file_type_emoji.get(file_info['type'], '📁')
                
                response_text = (
                    f"{emoji} **File Links Generated Successfully!**\n\n"
                    f"📝 **File Name:** `{file_info['name']}`\n"
                    f"📏 **File Size:** {self.format_file_size(file_info['size'])}\n"
                    f"🗂️ **File Type:** {file_info['type'].title()}\n"
                    f"🔗 **MIME Type:** `{file_info['mime_type']}`\n\n"
                    f"**🔗 Your Links:**\n"
                    f"📥 **Download:** [Click Here]({download_url})\n"
                    f"📺 **Stream:** [Click Here]({stream_url})\n\n"
                    f"⚡ Links are ready to use immediately!\n"
                    f"🔒 Links are secure and will work as long as the original file exists."
                )
                
                # Create inline keyboard with action buttons
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📥 Download", url=download_url),
                        InlineKeyboardButton("📺 Stream", url=stream_url)
                    ],
                    [
                        InlineKeyboardButton("📋 Copy Download Link", callback_data=f"copy_download_{file_id}"),
                        InlineKeyboardButton("📋 Copy Stream Link", callback_data=f"copy_stream_{file_id}")
                    ],
                    [
                        InlineKeyboardButton("🔄 Generate New Links", callback_data=f"regenerate_{file_id}")
                    ]
                ])
                
                await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
                
                # Log successful link generation
                logger.info(f"Generated links for file: {file_info['name']} ({file_info['size']} bytes) for user {message.from_user.id}")
                
            except FloodWait as e:
                logger.warning(f"FloodWait: {e.value} seconds")
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error in fdl_command: {e}")
                await message.reply_text(
                    "❌ **An error occurred while processing your request.**\n\n"
                    "Please try again in a few moments. If the problem persists, "
                    "contact support with the error details."
                )
        
        @self.bot.on_callback_query()
        async def handle_callbacks(client: Client, callback_query):
            """Handle inline keyboard callbacks"""
            try:
                data = callback_query.data
                
                if data == "help":
                    help_text = (
                        "📖 **Quick Help**\n\n"
                        "1. Send or forward a file\n"
                        "2. Reply to it with `/fdl`\n"
                        "3. Get download links!\n\n"
                        "Supported: Videos, Audio, Documents"
                    )
                    await callback_query.answer(help_text, show_alert=True)
                
                elif data == "about":
                    about_text = (
                        "ℹ️ **About File-to-Link Bot**\n\n"
                        "🚀 High-performance Telegram file linking service\n"
                        "⚡ Built with Pyrogram + AIOHTTP\n"
                        "🔒 Secure and efficient file streaming\n"
                        "📱 Mobile-friendly interface\n\n"
                        "Version: 1.0.0"
                    )
                    await callback_query.answer(about_text, show_alert=True)
                
                elif data.startswith("copy_download_"):
                    file_id = data.replace("copy_download_", "")
                    download_url = Config.get_download_url(file_id)
                    await callback_query.answer(f"📋 Download link copied!\n{download_url}", show_alert=True)
                
                elif data.startswith("copy_stream_"):
                    file_id = data.replace("copy_stream_", "")
                    stream_url = Config.get_stream_url(file_id)
                    await callback_query.answer(f"📋 Stream link copied!\n{stream_url}", show_alert=True)
                
                elif data.startswith("regenerate_"):
                    await callback_query.answer("🔄 Links are still active! No need to regenerate.", show_alert=True)
                
            except Exception as e:
                logger.error(f"Error in callback handler: {e}")
                await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)
    
    async def start(self):
        """Start the bot and web server"""
        try:
            # Validate configuration
            if not Config.validate():
                logger.error("❌ Configuration validation failed. Please check your environment variables.")
                return
            
            # Setup handlers
            await self.setup_handlers()
            
            # Start the bot
            await self.bot.start()
            bot_info = await self.bot.get_me()
            logger.info(f"🤖 Bot started successfully: @{bot_info.username}")
            
            # Start web server
            self.web_runner = await start_web_server(self.bot)
            
            logger.info("✅ File-to-Link Bot is fully operational!")
            logger.info(f"🔗 Web server: {Config.BASE_URL}")
            logger.info("📱 Bot is ready to handle /fdl commands")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal")
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.web_runner:
                await self.web_runner.cleanup()
                logger.info("🧹 Web server cleaned up")
            
            if self.bot.is_connected:
                await self.bot.stop()
                logger.info("🧹 Bot stopped")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main entry point"""
    bot = FileLinkBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown completed")
