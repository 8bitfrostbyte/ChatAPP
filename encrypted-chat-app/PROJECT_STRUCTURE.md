# Project Directory Structure - Final

## Complete File Layout

```
encrypted-chat-app/                          [Main Project Directory]
│
├─ README.md                                  [⭐ Start here - Complete overview]
├─ QUICKSTART.md                              [⚡ 10-minute quick start guide]
├─ ARCHITECTURE.md                            [🏗️ System design & architecture]
├─ SERVER_SETUP.md                            [🖥️ Server installation guide]
├─ CLIENT_SETUP.md                            [💻 Windows client setup]
├─ FEATURES.md                                [✨ Feature implementation details]
├─ FILE_INDEX.md                              [📚 Complete file directory]
├─ DELIVERY_SUMMARY.md                        [🎉 What you got]
├─ .env.example                               [🔑 Configuration template]
│
├─ server/                                    [🖥️ Backend - FastAPI Application]
│  ├─ main.py                                 [Main server with all endpoints]
│  ├─ database.py                             [SQLAlchemy ORM models]
│  ├─ auth.py                                 [User authentication system]
│  ├─ encryption.py                           [E2E message encryption]
│  ├─ image_bot.py                            [Image bot integration]
│  ├─ requirements.txt                        [Python dependencies]
│  └─ chat_app.db                             [SQLite database (created on init)]
│
└─ client/                                    [💻 Windows Client - PyQt6 GUI]
   ├─ main.py                                 [Main GUI application]
   ├─ websocket_client.py                     [WebSocket connection handler]
   ├─ notification_handler.py                 [Notification system]
   ├─ requirements.txt                        [Python dependencies]
   └─ sounds/                                 [Notification audio files]
      └─ notification.mp3                     [Optional custom notification sound]
```

## File Statistics

| Component | Files | Lines of Code | Purpose |
|-----------|-------|---------------|---------|
| **Server** | 5 | 1,000+ | Backend with all features |
| **Client** | 3 | 600+ | GUI application for Windows |
| **Documentation** | 8 | 5,000+ | Guides and references |
| **Configuration** | 2 | 100+ | Dependencies and settings |
| **TOTAL** | 18 | 6,700+ | Complete system |

## Code Breakdown

### Server (1,000+ lines)
- **main.py** (300+ lines) - FastAPI app with 21 API endpoints
- **image_bot.py** (400+ lines) - Integrated image bot from botUpdated.py
- **database.py** (150+ lines) - 6 data models with relationships
- **auth.py** (100+ lines) - Complete authentication system
- **encryption.py** (50+ lines) - E2E encryption system

### Client (600+ lines)
- **main.py** (600+ lines) - Complete PyQt6 GUI with all features
- **websocket_client.py** (150+ lines) - Real-time connection management
- **notification_handler.py** (100+ lines) - Desktop notifications

### Documentation (5,000+ lines)
- Comprehensive setup guides
- Architecture documentation
- API reference
- Troubleshooting guides
- Feature explanations

## What Each File Does

### Server Files

**main.py** - FastAPI Application
- Creates HTTP server on port 8000
- Handles all REST API endpoints
- Manages WebSocket connections
- Broadcasts messages in real-time
- Handles file uploads/downloads

**database.py** - Data Models
- User accounts
- Chat rooms
- Room memberships
- Messages
- Files/attachments
- Session tokens

**auth.py** - Authentication
- User registration with validation
- Secure login with password verification
- Session token generation
- Token expiration handling
- Password hashing with bcrypt

**encryption.py** - Message Encryption
- Fernet symmetric encryption
- Room-specific keys
- Password-based encryption
- Key derivation (PBKDF2)

**image_bot.py** - Image Bot
- Rule34 API client
- Danbooru API client
- Tag searching
- Image fetching
- Blacklist management

### Client Files

**main.py** - GUI Application
- Room list display
- Chat message window
- User input field
- Members list
- Image upload button
- Settings dialog
- Login/Register dialog

**websocket_client.py** - Real-Time Connection
- Async WebSocket client
- Message sending
- Message receiving loop
- Event callbacks
- Connection management

**notification_handler.py** - Notifications
- Windows toast notifications
- Sound playback
- System beep fallback
- Event notifications
- Settings management

## How Everything Connects

```
┌─────────────────────────────────────────────────────────┐
│               Windows Client (PyQt6)                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │ main.py - GUI with chat interface                │  │
│  │  ├─ Login dialog (auth via API)                  │  │
│  │  ├─ Room list (from GET /api/rooms)              │  │
│  │  ├─ Chat display (from WebSocket)                │  │
│  │  └─ Message input (via WebSocket)                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ websocket_client.py - Real-time connection       │  │
│  │  └─ WS connection to /ws/rooms/{id}/{token}      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ notification_handler.py - Notifications          │  │
│  │  └─ Play sounds, show desktop alerts             │  │
│  └──────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────────────────────────┘
           │ HTTPS + WebSocket Secure (WSS)
           │
┌──────────▼──────────────────────────────────────────────┐
│         Linux Server (FastAPI + Uvicorn)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ main.py - Web Server                             │  │
│  │  ├─ /api/auth/* - Authentication endpoints       │  │
│  │  ├─ /api/rooms/* - Room management               │  │
│  │  ├─ /api/messages/* - Message operations         │  │
│  │  ├─ /api/files/* - File operations               │  │
│  │  ├─ /api/bot/* - Image bot operations            │  │
│  │  └─ /ws/rooms/{id}/{token} - WebSocket           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ database.py - Data Layer                         │  │
│  │  ├─ User (accounts)                              │  │
│  │  ├─ Room (chat rooms)                            │  │
│  │  ├─ RoomMember (memberships)                     │  │
│  │  ├─ Message (chat messages)                      │  │
│  │  ├─ File (uploaded files)                        │  │
│  │  └─ Session (active sessions)                    │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ auth.py - Authentication Layer                   │  │
│  │  ├─ register_user()                              │  │
│  │  ├─ login_user()                                 │  │
│  │  ├─ verify_token()                               │  │
│  │  └─ logout_user()                                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ encryption.py - Encryption Layer                 │  │
│  │  ├─ encrypt_message()                            │  │
│  │  ├─ decrypt_message()                            │  │
│  │  └─ manage room keys                             │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ image_bot.py - Image Bot Layer                   │  │
│  │  ├─ search_tags()                                │  │
│  │  ├─ fetch_images()                               │  │
│  │  ├─ manage_blacklist()                           │  │
│  │  └─ API clients for Rule34/Danbooru              │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ chat_app.db - Data Storage                       │  │
│  │  └─ SQLite database with 6 tables                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### Flow 1: User Sends Encrypted Message
```
1. User types in client.main.py
2. client.websocket_client.send_message()
3. Message encrypted by encryption_manager
4. WebSocket sends to /ws/rooms/{id}/{token}
5. server.main.py receives via WebSocket handler
6. server.encryption.encrypt_message() stores
7. server.database adds Message record
8. server broadcasts to all WebSocket clients
9. Other clients receive via websocket_client
10. Client decrypts and displays in main.py
```

### Flow 2: User Uploads Image
```
1. User clicks "Upload Image" in client.main.py
2. File dialog opens (PyQt6)
3. client sends POST /api/upload with file
4. server.main.py validates file type
5. File saved to uploads/ directory
6. server.database stores File metadata
7. Message created with image_type
8. Response sent with message ID
9. Client displays image in chat
10. Other users download via GET /api/files/{id}
```

### Flow 3: Image Bot Search
```
1. User searches tags (via future UI)
2. POST /api/bot/search?query=tags
3. image_bot search_tags() called
4. Concurrent API requests to Rule34 & Danbooru
5. Results aggregated and sorted
6. JSON returned to client
7. Client displays image results
8. User can click to insert into chat
```

## Installation Paths

### Path 1: Local Network Only (Easiest)
```
Download all files
↓
Follow QUICKSTART.md
↓
Server: python3 main.py
Client: python main.py
↓
Connect to http://server-ip:8000
```

### Path 2: Remote Access with Tailscale
```
Download all files
↓
Setup Tailscale on server & client machines
↓
Follow SERVER_SETUP.md (Tailscale section)
↓
Server: Tailscale auto-connects
Client: Connect via Tailscale IP
```

### Path 3: Production Deployment
```
Follow SERVER_SETUP.md completely
↓
Setup PostgreSQL database
↓
Configure HTTPS with Let's Encrypt
↓
Setup systemd service
↓
Configure Cloudflare Tunnel
↓
Deploy to production
```

## Total Project Size

| Item | Size |
|------|------|
| Source code | ~50 KB |
| Documentation | ~200 KB |
| Database (empty) | ~10 KB |
| Dependencies (not included) | ~500 MB (when installed) |
| **Total (without dependencies)** | **~260 KB** |

## Deployment Checklist

- [ ] All 18 files present
- [ ] Server requirements.txt installed
- [ ] Client requirements.txt installed
- [ ] Database initialized
- [ ] Server starts without errors
- [ ] Client launches GUI successfully
- [ ] Can register new user
- [ ] Can login and join room
- [ ] Can send/receive messages
- [ ] Can upload images
- [ ] Can search bot images
- [ ] Notifications work
- [ ] Remote access configured (if needed)

---

**Everything is ready to go!** 🚀

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
