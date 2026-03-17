# Encrypted Chat Application - Complete Guide

A secure, real-time encrypted chat application with integrated image searching and streaming capabilities. Designed for secure communication without port forwarding, with support for Windows clients and Debian servers.

## Features

✅ **End-to-End Encryption**
- Messages encrypted with Fernet (symmetric encryption)
- Each room has its own encryption key
- Encrypted storage on server

✅ **Real-Time Messaging**
- WebSocket-based real-time communication
- Instant message delivery
- Typing indicators
- User join/leave notifications

✅ **User Authentication**
- Secure username/password registration
- No auto-login (session expires on logout)
- Bcrypt password hashing
- Session-based authentication

✅ **Room Management**
- Create public and private rooms
- Join/leave rooms dynamically
- Real-time member list
- Welcome/goodbye messages

✅ **Media Support**
- Image upload and sharing
- Encrypted file storage
- Image preview in chat
- Support for PNG, JPG, GIF, WebP

✅ **Integrated Image Bot**
- Search Rule34 and Danbooru sites
- Tag auto-completion
- Blacklist management
- Image streaming to chat rooms

✅ **Notifications**
- Desktop notifications for messages
- Configurable notification sounds
- Typing indicators
- System messages for user events

✅ **Remote Access**
- No port forwarding required
- Multiple access methods:
  - Cloudflare Tunnel (3rd party URL)
  - ngrok quick tunneling
  - Tailscale VPN (private network)
  - Direct local network

## System Architecture

```
┌─────────────────────────────────┐
│   Windows Chat Clients          │
│  (PyQt6 GUI Application)        │
└────────────┬────────────────────┘
             │ WebSocket (TCP/SSL)
             │ REST API (HTTPS)
             │
┌────────────▼────────────────────┐
│   Debian Linux Server           │
│  (FastAPI + Uvicorn)           │
├─────────────────────────────────┤
│ • User Authentication           │
│ • Message Encryption/Storage    │
│ • Room Management               │
│ • WebSocket Real-time Server    │
│ • Integrated Image Bot          │
│ • SQLite/PostgreSQL Database    │
└─────────────────────────────────┘
             │
             ├─ Local Network (same building)
             ├─ Cloudflare Tunnel (no port forward)
             ├─ ngrok (testing/demo)
             └─ Tailscale VPN (private secure)
```

## Quick Start

### TL;DR - 5 Minutes

**Server:**
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
# Server running on localhost:8000
```

**Client (Windows):**
```cmd
cd client
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Enter: http://localhost:8000
# Register/Login
# Start chatting!
```

## Detailed Setup

### Server Setup (Debian Linux)

See [SERVER_SETUP.md](SERVER_SETUP.md) for complete instructions:

1. Install Python 3.10+
2. Setup virtual environment
3. Install dependencies
4. Initialize database
5. Configure API keys (optional - for image bot)
6. Start server with Uvicorn
7. Setup remote access tunnel
8. Enable HTTPS

**Quick Reference:**
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r server/requirements.txt

# 3. Initialize database
cd server
python3 -c "from database import init_db; init_db()"

# 4. Start server
python3 main.py
```

### Client Setup (Windows)

See [CLIENT_SETUP.md](CLIENT_SETUP.md) for complete instructions:

1. Install Python 3.10+
2. Setup virtual environment
3. Install dependencies
4. Configure server URL
5. Register/Login
6. Start chatting!

**Quick Reference:**
```cmd
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r client/requirements.txt

# 3. Run the application
python main.py
```

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/auth/verify` | Verify token |

### Room Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rooms` | List all rooms |
| POST | `/api/rooms` | Create new room |
| GET | `/api/rooms/{id}` | Get room details |
| POST | `/api/rooms/{id}/join` | Join room |
| POST | `/api/rooms/{id}/leave` | Leave room |
| GET | `/api/rooms/{id}/members` | Get room members |

### Message Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rooms/{id}/messages` | Get message history |
| DELETE | `/api/messages/{id}` | Delete message |

### File Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload image file |
| GET | `/api/files/{id}` | Download file |

### Bot Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bot/search` | Search image tags |
| POST | `/api/bot/images` | Get images for tags |
| GET | `/api/bot/blacklist` | Get blacklist |
| POST | `/api/bot/blacklist/add` | Add blacklist tags |
| POST | `/api/bot/blacklist/remove` | Remove blacklist tags |

### WebSocket

```
ws://server:8000/ws/rooms/{room_id}/{token}
```

**Events:**
- `message` - Send message
- `typing` - Send typing indicator
- Receive: `message_new`, `user_joined`, `user_left`, `typing`

## Configuration

### Server Environment Variables

```bash
# Image Bot Credentials (Optional)
DANBOORU_USER=your_username
DANBOORU_API_KEY=your_api_key
RULE34_USER_ID=your_user_id
RULE34_API_KEY=your_api_key

# Database
DATABASE_URL=sqlite:///./chat_app.db

# Security
SECRET_KEY=your_secret_key
```

### Client Configuration

Server URL is entered when application starts:
- Local: `http://192.168.1.100:8000`
- Remote: `https://chat.your-domain.com`
- Tailscale: `http://100.x.x.x:8000`

## Remote Access Options

### Option 1: Cloudflare Tunnel (Recommended)

No port forwarding needed. Requires Cloudflare account.

```bash
# Install
wget https://github.com/cloudflare/cloudflared/releases/download/2023.10.0/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Setup
cloudflared tunnel login
cloudflared tunnel create encrypted-chat
cloudflared tunnel route dns encrypted-chat chat.your-domain.com
cloudflared tunnel run encrypted-chat
```

Client connects to: `https://chat.your-domain.com`

### Option 2: Tailscale VPN (Most Secure)

Private VPN network. All traffic encrypted. No port forwarding.

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Client uses: http://your-tailscale-ip:8000
```

### Option 3: ngrok (Quick Testing)

```bash
# Install and authenticate
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
unzip ngrok-v3-stable-linux-amd64.zip
sudo mv ngrok /usr/local/bin
ngrok config add-authtoken YOUR_TOKEN

# Expose server
ngrok http 8000
```

Client connects to: `https://abc123.ngrok.io`

## Security Considerations

### Encryption
- ✅ Messages encrypted end-to-end with Fernet
- ✅ Passwords hashed with bcrypt
- ✅ HTTPS/WSS for transport security
- ✅ Encrypted file storage

### Authentication
- ✅ No plaintext passwords stored
- ✅ Session tokens with expiration
- ✅ No auto-login (session logout on app close)
- ✅ Token validation on every request

### Best Practices
- ✅ Use strong passwords (12+ characters)
- ✅ Always logout when done
- ✅ Keep software updated
- ✅ Use HTTPS in production
- ✅ Regular database backups
- ✅ Monitor server logs

### Limitations
- Server administrator can see encrypted content at rest
- Use additional E2E encryption if maximum privacy needed
- Trust your server operator with your data

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is in use
netstat -tuln | grep 8000

# Kill existing process
sudo kill -9 <PID>

# Check error in logs
tail -f app.log
```

### Client Can't Connect

```cmd
# Verify server is running
ping your-server-ip

# Test HTTP connection
curl http://your-server-ip:8000/health

# Check firewall
ipconfig /all
```

### Database Issues

```bash
# Reset database
rm chat_app.db
python3 -c "from database import init_db; init_db()"
```

### WebSocket Connection Fails

1. Check server is running: `curl http://server:8000/health`
2. Verify port 8000 is open in firewall
3. Check proxy settings on client
4. Use HTTPS URL if HTTP fails

See [SERVER_SETUP.md](SERVER_SETUP.md) and [CLIENT_SETUP.md](CLIENT_SETUP.md) for detailed troubleshooting.

## Development

### Project Structure

```
encrypted-chat-app/
├── server/
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLAlchemy models
│   ├── auth.py              # Authentication logic
│   ├── encryption.py        # Message encryption
│   ├── image_bot.py         # Image bot integration
│   ├── requirements.txt      # Python dependencies
│   └── chat_app.db         # SQLite database
├── client/
│   ├── main.py              # PyQt6 GUI application
│   ├── websocket_client.py  # WebSocket connection
│   ├── notification_handler.py  # Notifications
│   ├── requirements.txt      # Python dependencies
│   └── sounds/              # Notification sounds
├── ARCHITECTURE.md          # System design
├── SERVER_SETUP.md          # Server installation
├── CLIENT_SETUP.md          # Client installation
└── README.md                # This file
```

### Running in Development Mode

**Server:**
```bash
cd server
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Client:**
```cmd
cd client
venv\Scripts\activate
python main.py
```

### Database Schema

See [ARCHITECTURE.md](ARCHITECTURE.md#database-schema) for complete schema.

Key tables:
- `users` - User accounts
- `rooms` - Chat rooms
- `room_members` - Room memberships
- `messages` - Chat messages
- `files` - Uploaded files
- `sessions` - User sessions

## Performance Optimization

### Server
- Use PostgreSQL instead of SQLite for production
- Enable connection pooling
- Setup caching for frequently accessed data
- Use multiple workers: `--workers 4`

### Client
- Lazy load message history
- Limit active connections to 1 room
- Close app when not in use
- Clear message cache periodically

### Network
- Use Tailscale for lowest latency private network
- Use Cloudflare Tunnel for reliable remote access
- Cache room list and member data locally

## Monitoring

### Server Health

```bash
# View logs
sudo journalctl -u encrypted-chat -f

# Check resource usage
htop

# View active connections
netstat -an | grep :8000

# Database size
du -h chat_app.db
```

### Client Diagnostics

- Check network connectivity
- Verify server URL is correct
- Monitor local disk space for uploads
- Check notification permissions

## Future Enhancements

- [ ] Group profiles and avatars
- [ ] Message reactions (emoji)
- [ ] Typing indicators UI
- [ ] Read receipts
- [ ] Message search
- [ ] Channel topics/descriptions
- [ ] User status (online/offline)
- [ ] Private direct messages
- [ ] Call/video support
- [ ] Mobile app (iOS/Android)

## License

MIT License - Free to use and modify

## Support

For issues, please:
1. Check the troubleshooting sections in setup guides
2. Review server logs: `sudo journalctl -u encrypted-chat`
3. View client console output for error messages
4. Verify network connectivity between client and server
5. Check firewall and port forwarding rules

## Contributing

Contributions welcome! Areas for enhancement:
- UI improvements
- Additional image sources
- Performance optimization
- Mobile client
- Video calling support

---

**Created:** 2024
**Status:** Production Ready
**Support:** Community Driven

## March 2026 Updates

### New requirements and behavior

- Default room is now Room One.
- Users are automatically added to Room One at login.
- Client auto-joins Room One after successful login.
- Presence messages are now "user is online" on join and "user is offline" on leave/app close.
- Private rooms are hidden from non-members and are invite-only.
- Side panel shows users currently in the selected room and removes users after they leave.

### New command instructions

- Bot commands:
  - !start <seconds> [tags]
  - !pause, !resume, !stop, !status, !commands
  - !addtags <tag1,tag2>, !removetags <tag1,tag2>, !taglist, !cleartags
- Room commands:
  - !rooms
  - !createroom <name> [private]
  - !removeroom <name|id>
  - !makeprivate

### Private room rules

- Non-members cannot list, view, join, or read private rooms.
- Only room creator can delete a room.
- Room One cannot be deleted.

### Setup instruction

- Restart both server and client after updating so all new endpoints and commands are active.
