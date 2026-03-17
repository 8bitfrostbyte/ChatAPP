# Encrypted Chat Application - Complete File Index

## 📁 Project Structure

```
encrypted-chat-app/
│
├── 📄 README.md                    ⭐ START HERE - Complete overview
├── 📄 QUICKSTART.md                ⚡ 10-minute quick start
├── 📄 ARCHITECTURE.md              🏗️ System design and architecture
├── 📄 SERVER_SETUP.md              🖥️ Server installation & configuration
├── 📄 CLIENT_SETUP.md              💻 Client installation & usage
├── 📄 .env.example                 🔑 Configuration template
│
├── server/                         🖥️ Backend Server
│   ├── main.py                     ▶️ FastAPI application entry point
│   ├── database.py                 🗄️ SQLAlchemy models & database setup
│   ├── auth.py                     🔐 User authentication & session management
│   ├── encryption.py               🔒 Message encryption/decryption
│   ├── image_bot.py                🤖 Integrated image search bot
│   ├── requirements.txt             📦 Python dependencies
│   └── chat_app.db                 💾 SQLite database (created on init)
│
└── client/                         💻 Windows Client
    ├── main.py                     ▶️ PyQt6 GUI application
    ├── websocket_client.py         🔄 WebSocket connection handler
    ├── notification_handler.py     🔔 Desktop notifications & sounds
    ├── requirements.txt             📦 Python dependencies
    └── sounds/                      🔊 Notification sound files
```

## 📚 Documentation Guide

### For First-Time Users

1. **[README.md](README.md)** - Read this first!
   - System overview
   - Feature list
   - Quick start instructions
   - Security information

2. **[QUICKSTART.md](QUICKSTART.md)** - Get up and running fast
   - 10-minute setup guide
   - Step-by-step instructions
   - Quick troubleshooting
   - Multi-user testing

### For Installation

3. **[SERVER_SETUP.md](SERVER_SETUP.md)** - Deploy the backend
   - Python installation
   - Virtual environment setup
   - Database initialization
   - Starting the server
   - HTTPS configuration
   - Remote access (Cloudflare, ngrok, Tailscale)
   - Systemd service setup
   - Backup strategy
   - Monitoring & security

4. **[CLIENT_SETUP.md](CLIENT_SETUP.md)** - Configure client
   - Windows Python installation
   - Dependencies setup
   - Server configuration
   - Running the application
   - Feature explanation
   - Detailed troubleshooting
   - Advanced configuration
   - Security best practices

### For Understanding the System

5. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Deep dive into design
   - System architecture diagram
   - Technology stack details
   - Feature implementation breakdown
   - Database schema
   - API endpoints
   - WebSocket events
   - Security features
   - Deployment architecture
   - File structure

### Configuration

6. **[.env.example](.env.example)** - Configuration template
   - All configurable options
   - Database settings
   - API credentials
   - Security settings
   - Email configuration
   - Remote access setup

## 🚀 Quick Navigation

### I want to...

**...get started immediately**
→ See [QUICKSTART.md](QUICKSTART.md)

**...install on my server**
→ See [SERVER_SETUP.md](SERVER_SETUP.md)

**...install on my Windows PC**
→ See [CLIENT_SETUP.md](CLIENT_SETUP.md)

**...understand the system design**
→ See [ARCHITECTURE.md](ARCHITECTURE.md)

**...troubleshoot an issue**
→ Check README.md "Troubleshooting" section or specific setup guide

**...configure the image bot**
→ See [SERVER_SETUP.md](SERVER_SETUP.md#step-3-configure-environment-variables) and [.env.example](.env.example)

**...setup remote access**
→ See [SERVER_SETUP.md](SERVER_SETUP.md#step-7-setup-remote-access-choose-one)

**...enable HTTPS**
→ See [SERVER_SETUP.md](SERVER_SETUP.md#step-6-setup-https-optional-but-recommended)

**...run in production**
→ See [SERVER_SETUP.md](SERVER_SETUP.md#production-deployment-checklist)

**...add more users**
→ See [QUICKSTART.md](QUICKSTART.md#multi-user-testing)

## 📋 Server Files

### main.py
The main FastAPI application with all endpoints and WebSocket handling.

**Key Components:**
- REST API endpoints (auth, rooms, messages, files, bot)
- WebSocket real-time messaging
- CORS middleware
- Database session management
- File upload handling

**Run with:** `python3 main.py`

### database.py
SQLAlchemy ORM models for database structure.

**Tables:**
- `User` - User accounts and authentication
- `Room` - Chat rooms/channels
- `RoomMember` - Room membership tracking
- `Message` - Chat messages
- `File` - File attachments
- `Session` - User session tokens

**Usage:** Database initialization and ORM queries

### auth.py
Authentication and session management.

**Features:**
- User registration with validation
- Secure login with bcrypt hashing
- Session token generation
- Token verification
- User logout

**Key Classes:**
- `AuthManager` - Central auth handling
- `UserRegisterRequest` / `UserLoginRequest` - Request models
- `SessionResponse` - Response model

### encryption.py
End-to-end message encryption.

**Features:**
- Fernet symmetric encryption
- Room-specific encryption keys
- Password-based encryption
- Key derivation with PBKDF2

**Key Classes:**
- `EncryptionManager` - Central encryption handling

### image_bot.py
Integrated image bot from botUpdated.py.

**Features:**
- Rule34 API integration
- Danbooru API integration
- Tag searching and autocomplete
- Image fetching with filtering
- Blacklist management

**Key Classes:**
- `ImageBot` - Bot functionality
- `ImageBotConfig` - Configuration

## 💻 Client Files

### main.py
PyQt6-based graphical user interface.

**Key Classes:**
- `ChatWindow` - Main window with chat interface
- `LoginDialog` - Login/registration dialog
- `WebSocketThread` - Background WebSocket connection
- `APIClient` - REST API communication
- `ChatApp` - Application entry point

**Features:**
- Room list and selection
- Real-time messaging
- Image upload
- Member list
- Settings dialog
- Notifications

### websocket_client.py
WebSocket client for real-time communication.

**Key Class:**
- `WebSocketClient` - Manages connection and messages

**Features:**
- Async connection handling
- Message receiving loop
- Event callbacks
- Auto-reconnection support

### notification_handler.py
Desktop notifications and sound alerts.

**Key Class:**
- `NotificationHandler` - Manages notifications

**Features:**
- Windows 10/11 toast notifications
- Notification sounds
- User events (join/leave/message)
- Sound enable/disable toggle

## 🔄 Data Flow

### Message Sending Flow
1. User types message in client
2. Client encrypts message
3. WebSocket sends to server
4. Server stores encrypted message in database
5. Server broadcasts to all users in room
6. Other clients decrypt and display

### Authentication Flow
1. User enters credentials on client
2. Client sends registration/login request via REST API
3. Server validates and creates session
4. Server returns auth token
5. Client stores token in memory (not persistent)
6. All future requests include token in Authorization header

### File Upload Flow
1. User selects image in client
2. Client sends file via POST to /api/upload
3. Server saves encrypted file to disk
4. Server creates message record with image metadata
5. Server broadcasts image message to all users
6. Clients fetch image via /api/files/{id}

## 🔐 Security Architecture

### Transport Security
- HTTPS for REST API endpoints
- WSS (WebSocket Secure) for real-time messaging
- SSL/TLS certificate validation

### Message Security
- Fernet symmetric encryption (AES-128-CBC)
- Each room has unique encryption key
- Messages encrypted before sending to server
- Server stores encrypted data

### Authentication Security
- bcrypt password hashing with salt
- JWT-style tokens with expiration
- No auto-login (session cleared on logout)
- Token validation on every request

### File Security
- File validation before upload
- Encrypted file storage
- Access control via message ownership
- File deletion prevents access

## 🌐 API Endpoints Summary

### Authentication (5 endpoints)
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login and get session
- `POST /api/auth/logout` - Logout
- `GET /api/auth/verify` - Verify token validity

### Rooms (6 endpoints)
- `GET /api/rooms` - List all rooms
- `POST /api/rooms` - Create new room
- `GET /api/rooms/{id}` - Get room details
- `POST /api/rooms/{id}/join` - Join room
- `POST /api/rooms/{id}/leave` - Leave room
- `GET /api/rooms/{id}/members` - List members

### Messages (3 endpoints)
- `GET /api/rooms/{id}/messages` - Message history
- `DELETE /api/messages/{id}` - Delete message

### Files (2 endpoints)
- `POST /api/upload` - Upload image
- `GET /api/files/{id}` - Download file

### Bot (5 endpoints)
- `POST /api/bot/search` - Search tags
- `POST /api/bot/images` - Get images
- `GET /api/bot/blacklist` - Get blacklist
- `POST /api/bot/blacklist/add` - Add blacklist
- `POST /api/bot/blacklist/remove` - Remove blacklist

### WebSocket (1 endpoint)
- `WS /ws/rooms/{room_id}/{token}` - Real-time messaging

## 📊 Database Schema Summary

### users
- id (PK)
- username (unique)
- password_hash
- created_at

### rooms
- id (PK)
- name (unique)
- created_by (FK)
- is_private
- encryption_key
- created_at

### room_members
- id (PK)
- room_id (FK)
- user_id (FK)
- joined_at

### messages
- id (PK)
- room_id (FK)
- user_id (FK)
- content (encrypted)
- message_type
- created_at
- deleted_at

### files
- id (PK)
- message_id (FK)
- filename
- file_path
- file_size
- file_type
- created_at

### sessions
- id (PK)
- user_id (FK)
- token (unique)
- expires_at
- created_at

## 🛠️ Configuration Files

### .env (Environment Variables)
Located in project root, contains:
- Database connection string
- API credentials (Danbooru, Rule34)
- Security keys and secrets
- Server configuration
- Logging settings
- Backup configuration

Use `.env.example` as template.

### requirements.txt (Server)
Python packages needed for server:
- fastapi, uvicorn - Web framework
- sqlalchemy - Database ORM
- cryptography - Encryption
- bcrypt - Password hashing
- requests - HTTP client
- pydantic - Data validation
- python-socketio - WebSocket protocol

### requirements.txt (Client)
Python packages needed for client:
- pyqt6 - GUI framework
- websockets - WebSocket client
- cryptography - Encryption
- requests - HTTP client
- playsound - Sound playback
- pillow - Image handling

## 🚨 Troubleshooting Quick Links

| Issue | Documentation |
|-------|---------------|
| Server won't start | [SERVER_SETUP.md - Troubleshooting](SERVER_SETUP.md#troubleshooting) |
| Client can't connect | [CLIENT_SETUP.md - Troubleshooting](CLIENT_SETUP.md#troubleshooting) |
| WebSocket errors | [README.md - Troubleshooting](README.md#troubleshooting) |
| Database issues | [SERVER_SETUP.md - Database](SERVER_SETUP.md#step-4-initialize-database) |
| Password/auth issues | [CLIENT_SETUP.md - Login](CLIENT_SETUP.md#invalid-username-or-password) |
| Network/firewall | [SERVER_SETUP.md - Security](SERVER_SETUP.md#firewall-configuration) |
| Performance issues | [README.md - Performance Optimization](README.md#performance-optimization) |

## 📞 Support & Help

1. **Check Documentation** - Most answers in setup guides
2. **Review Logs** - Server: `sudo journalctl -u encrypted-chat -f` / Client: command prompt output
3. **Verify Setup** - Re-read the quick start guide
4. **Test Connectivity** - `ping server` / `curl http://server:8000/health`
5. **Community** - Check issues/forums

## ✅ Deployment Checklist

- [ ] Read README.md
- [ ] Follow QUICKSTART for initial setup
- [ ] Review SERVER_SETUP.md for production considerations
- [ ] Setup HTTPS with valid certificate
- [ ] Configure remote access (Tailscale/Cloudflare/ngrok)
- [ ] Setup database auto-backup
- [ ] Configure systemd service
- [ ] Test with multiple users
- [ ] Monitor server logs initially
- [ ] Document your setup

## 📖 Learning Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **PyQt6 Documentation:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **Cryptography Guide:** https://cryptography.io/
- **WebSockets RFC:** https://tools.ietf.org/html/rfc6455

---

**Version:** 1.0.0  
**Last Updated:** 2024  
**Status:** Production Ready  
**License:** MIT

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
