# 🤖 Telegram File-to-Link Bot

A high-performance Telegram bot that generates direct download and streaming links for files shared on Telegram. Built with Python, Pyrogram, and AIOHTTP for maximum efficiency and scalability.

## ✨ Features

- 🚀 **High Performance**: Built with Pyrogram and AIOHTTP for optimal speed
- 📁 **Large File Support**: Handles files up to 4GB
- 🎬 **Smart Streaming**: Direct streaming without downloading to server disk
- 📱 **Mobile Friendly**: Responsive links that work on all devices
- 🔒 **Secure**: Environment-based configuration and secure file handling
- ⚡ **Fast Response**: Instant link generation with caching
- 🎯 **Range Requests**: Supports HTTP range requests for video streaming
- 📊 **Production Ready**: Comprehensive logging and error handling

## 🎯 Supported File Types

- 📹 **Videos**: MP4, MKV, AVI, MOV, and more
- 🎵 **Audio**: MP3, FLAC, WAV, AAC, and more  
- 📄 **Documents**: PDF, ZIP, APK, EXE, and more

## 🚀 Quick Start

### Prerequisites

1. **Telegram API Credentials**:
   - Visit [my.telegram.org/apps](https://my.telegram.org/apps)
   - Create a new application
   - Note down your `API_ID` and `API_HASH`

2. **Bot Token**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with `/newbot`
   - Save the bot token

### Local Development

1. **Clone and Setup**:
   ```bash
   git clone <your-repo-url>
   cd telegram-file-bot
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the Bot**:
   ```bash
   python bot_main.py
   ```

## 🌐 Deployment on Render

### Method 1: GitHub Integration (Recommended)

1. **Prepare Repository**:
   - Push your code to GitHub
   - Ensure all files are committed

2. **Create Render Service**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository containing your bot

3. **Configure Service**:
   ```
   Name: telegram-file-bot
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python bot_main.py
   ```

4. **Set Environment Variables**:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   BASE_URL=https://your-app-name.onrender.com
   SECRET_KEY=your-secret-key
   HOST=0.0.0.0
   PORT=10000
   ```

5. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Your bot will be live at `https://your-app-name.onrender.com`

### Method 2: Manual Deployment

1. **Create Web Service**:
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Choose "Deploy from Git repository"

2. **Repository Settings**:
   ```
   Repository URL: <your-git-repo-url>
   Branch: main
   Root Directory: (leave empty)
   ```

3. **Build Settings**:
   ```
   Environment: Python 3
   Python Version: 3.11.0
   Build Command: pip install -r requirements.txt
   Start Command: python bot_main.py
   ```

4. **Advanced Settings**:
   ```
   Health Check Path: /health
   Auto-Deploy: Yes
   ```

### Environment Variables Setup

In your Render service settings, add these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | `1234567` |
| `API_HASH` | Telegram API Hash | `abcdef1234567890...` |
| `BOT_TOKEN` | Bot token from BotFather | `1234567890:ABCdef...` |
| `BASE_URL` | Your Render app URL | `https://mybot.onrender.com` |
| `SECRET_KEY` | Random secret key | `my-secret-key-2024` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `10000` |

### Post-Deployment Steps

1. **Verify Deployment**:
   - Check Render logs for successful startup
   - Visit `https://your-app-name.onrender.com/health`
   - Should return: `{"status": "healthy", "service": "telegram-file-bot"}`

2. **Test Bot**:
   - Send `/start` to your bot on Telegram
   - Upload a test file
   - Reply with `/fdl`
   - Verify links work correctly

## 📱 How to Use

1. **Start the Bot**:
   - Send `/start` to your bot on Telegram
   - Read the welcome message

2. **Generate Links**:
   - Send any video, audio, or document file to the bot
   - Reply to that file message with `/fdl`
   - Get instant download and streaming links!

3. **Use the Links**:
   - Click "Download" for direct file download
   - Click "Stream" for in-browser streaming
   - Links work on all devices and browsers

## 🏗️ Project Structure

```
telegram-file-bot/
├── bot_main.py          # Main bot logic and command handlers
├── web_server.py        # AIOHTTP web server for file serving
├── config.py           # Configuration and environment management
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── render.yaml        # Render deployment configuration
└── README.md          # This file
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_ID` | Required | Telegram API ID |
| `API_HASH` | Required | Telegram API Hash |
| `BOT_TOKEN` | Required | Bot token from BotFather |
| `BASE_URL` | `http://localhost:8080` | Base URL for file links |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8080` | Server port number |
| `SECRET_KEY` | `your-secret-key-here` | Security secret key |
| `MAX_FILE_SIZE` | `4294967296` | Max file size (4GB) |
| `CHUNK_SIZE` | `1048576` | Streaming chunk size (1MB) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SESSION_NAME` | `file_bot_session` | Pyrogram session name |

### File Size Limits

- **Maximum file size**: 4GB (configurable)
- **Streaming chunk size**: 1MB (configurable)
- **Supported by Telegram**: Up to 2GB via Bot API, 4GB via MTProto

## 🛠️ Advanced Features

### HTTP Range Requests
The bot supports HTTP range requests, enabling:
- Video seeking in browsers
- Partial content delivery
- Bandwidth optimization
- Better mobile experience

### Caching System
- In-memory file metadata caching
- 5-minute cache expiration
- Reduces Telegram API calls
- Improves response times

### Error Handling
- Comprehensive error logging
- User-friendly error messages
- Automatic retry mechanisms
- Graceful degradation

## 🔍 Monitoring and Logs

### Health Check
- Endpoint: `GET /health`
- Returns: `{"status": "healthy", "service": "telegram-file-bot"}`

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages

### Render Logs
Access logs in your Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. Monitor real-time logs

## 🚨 Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check environment variables
   - Verify bot token is correct
   - Check Render service logs

2. **Links not working**:
   - Verify `BASE_URL` is set correctly
   - Check if web server is running
   - Ensure port configuration is correct

3. **File not found errors**:
   - Original message may be deleted
   - File may have expired on Telegram
   - Check file permissions

4. **Large file issues**:
   - Verify file size is under limit
   - Check available memory/bandwidth
   - Monitor streaming performance

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python bot_main.py
```

## 📊 Performance Optimization

### For High Traffic

1. **Increase Resources**:
   - Upgrade Render plan
   - Increase memory allocation
   - Use faster disk storage

2. **Optimize Configuration**:
   ```bash
   CHUNK_SIZE=2097152  # 2MB chunks
   MAX_FILE_SIZE=2147483648  # 2GB limit
   ```

3. **Monitor Usage**:
   - Check Render metrics
   - Monitor response times
   - Track error rates

## 🔒 Security Considerations

1. **Environment Variables**: Never commit sensitive data
2. **Secret Key**: Use a strong, unique secret key
3. **File Access**: Links are temporary and secure
4. **Rate Limiting**: Built-in Telegram rate limiting
5. **HTTPS**: Always use HTTPS in production

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- **Issues**: Create a GitHub issue
- **Questions**: Check existing issues first
- **Updates**: Watch the repository for updates

## 🎉 Acknowledgments

- [Pyrogram](https://github.com/pyrogram/pyrogram) - Modern Telegram MTProto API framework
- [AIOHTTP](https://github.com/aio-libs/aiohttp) - Asynchronous HTTP client/server framework
- [Render](https://render.com) - Cloud platform for hosting

---

**Made with ❤️ for the Telegram community**

*Happy file sharing! 🚀*
