# Encrypted Chat Application - Complete Architecture

## System Overview
A secure, real-time chat application with end-to-end encryption, image sharing, and integrated image bot functionality.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        WINDOWS CLIENTS                          │
│              (GUI Chat App with Notification System)            │
└────────────────┬────────────────────────────────────────────────┘
                 │  WebSocket (encrypted TLS)
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                    CLOUD/VPS SERVER                             │
│              (Headless Debian Linux Running)                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI/Uvicorn Server (Python)                         │  │
│  │  - User Authentication & Session Management              │  │
│  │  - Room/Channel Management                               │  │
│  │  - WebSocket Connection Pooling                          │  │
│  │  - Message Encryption/Decryption                         │  │
│  │  - File Upload Handling (Images)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Integrated Image Bot Service                            │  │
│  │  - Rule34/Danbooru Tag Search                            │  │
│  │  - Image Streaming to Chat Rooms                         │  │
│  │  - Blacklist Management                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Database (SQLite/PostgreSQL)                            │  │
│  │  - User Credentials (hashed passwords)                   │  │
│  │  - Messages (encrypted at rest)                          │  │
│  │  - Room Metadata                                         │  │
│  │  - Message History                                       │  │
│  │  - User Sessions                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  File Storage                                            │  │
│  │  - Uploaded Images (encrypted)                           │  │
│  │  - Blacklist Configuration                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Server** | Python 3.10+ (FastAPI) | Web framework with async support |
| **Real-time** | WebSocket + python-socketio | Bi-directional messaging |
| **Database** | SQLite/PostgreSQL | Persistent data storage |
| **Encryption** | cryptography (Fernet) | Message & password encryption |
| **Auth** | JWT + bcrypt | Secure user authentication |
| **Image Handler** | PIL/Pillow | Image processing |
| **Client App** | PyQt6/PySimpleGUI | Windows GUI desktop app |
| **Remote Access** | ngrok/Cloudflare Tunnel | No port forwarding needed |

## Feature Implementation

### 1. User Authentication
- ✅ Username/Password registration
- ✅ Hashed password storage (bcrypt)
- ✅ No auto-login (session expires on app close)
- ✅ Session token validation on every request

### 2. Messaging System
- ✅ Real-time message sending via WebSocket
- ✅ Message encryption (Fernet - symmetric encryption)
- ✅ Message deletion with timestamp verification
- ✅ Message history retrieval
- ✅ User typing indicators

### 3. Rooms/Channels
- ✅ Create/join/leave rooms
- ✅ Room member list
- ✅ Default "General" room
- ✅ Private room option (invites only)

### 4. Media Features
- ✅ Image upload to chat
- ✅ Automatic image resizing
- ✅ Encrypted file storage
- ✅ Image preview in chat

### 5. Notifications
- ✅ Desktop notifications when messages arrive
- ✅ Notification sounds (configurable)
- ✅ Sound muting options
- ✅ Notification badges

### 6. System Messages
- ✅ User joined room notification
- ✅ User left room notification
- ✅ Management notifications

### 7. Integrated Image Bot
- ✅ Tag search from Rule34/Danbooru
- ✅ Image streaming to selected rooms
- ✅ Blacklist management
- ✅ Tag pool management

## Security Features

1. **End-to-End Encryption**
   - Messages encrypted with Fernet (symmetric)
   - Each room has its own encryption key
   - Keys managed server-side, transmitted securely

2. **Authentication Security**
   - Bcrypt password hashing with salt
   - JWT tokens for session management
   - Token expiration on logout
   - No persistent local credentials

3. **Transport Security**
   - TLS/SSL for HTTPS
   - WSS (WebSocket Secure) for real-time data
   - Certificate validation

4. **Data Protection**
   - Encrypted message storage
   - User data isolation per session
   - Secure file upload validation

## Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rooms Table
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_by INTEGER,
    is_private BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Room Members Table
CREATE TABLE room_members (
    id INTEGER PRIMARY KEY,
    room_id INTEGER,
    user_id INTEGER,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(room_id, user_id)
);

-- Messages Table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    room_id INTEGER,
    user_id INTEGER,
    content TEXT ENCRYPTED,
    message_type TEXT DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Files Table
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    message_id INTEGER,
    filename TEXT,
    file_path TEXT ENCRYPTED,
    file_size INTEGER,
    file_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

-- Sessions Table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    token TEXT UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/verify` - Verify token

### Messages
- `GET /api/rooms/{id}/messages` - Get message history
- `POST /api/messages` - Send message (via WebSocket)
- `DELETE /api/messages/{id}` - Delete message
- `GET /api/messages/{id}` - Get single message

### Rooms
- `GET /api/rooms` - List available rooms
- `POST /api/rooms` - Create room
- `GET /api/rooms/{id}` - Get room details
- `POST /api/rooms/{id}/join` - Join room
- `POST /api/rooms/{id}/leave` - Leave room
- `GET /api/rooms/{id}/members` - Get room members

### Files/Images
- `POST /api/upload` - Upload image file
- `GET /api/files/{id}` - Download/serve file
- `DELETE /api/files/{id}` - Delete file

### Bot Commands (via Chat)
- `/bot search <query>` - Search tags
- `/bot stream <tags>` - Start image stream
- `/bot stop` - Stop stream
- `/bot blacklist add <tags>` - Add blacklist
- `/bot blacklist remove <tags>` - Remove blacklist

## WebSocket Events

### Client → Server
- `connect` - Establish connection
- `message:send` - Send chat message
- `message:delete` - Delete message
- `room:join` - Join a room
- `room:leave` - Leave room
- `typing:start` - User typing
- `typing:stop` - Stopped typing

### Server → Client
- `message:new` - New message received
- `message:deleted` - Message deleted
- `user:joined` - User joined room
- `user:left` - User left room
- `typing:active` - User typing
- `notification` - System notification

## Remote Access (No Port Forwarding)

### Option 1: Cloudflare Tunnel
```bash
cloudflare tunnel create encrypted-chat
cloudflare tunnel route dns encrypted-chat your_domain.com
cloudflare tunnel run --url localhost:8000 encrypted-chat
```

### Option 2: ngrok
```bash
ngrok http 8000
# Get public URL like https://abc123.ngrok.io
```

### Option 3: Tailscale VPN
- Create Tailscale account
- Connect server and all client machines
- Access server via Tailscale IP (private, secure)

## Deployment Steps

1. **Server Setup (Debian)**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv
   # ... additional setup steps
   ```

2. **Database Initialization**
   - Create SQLite/PostgreSQL database
   - Run schema migrations
   - Create admin user

3. **Client Installation**
   - Distribute Windows GUI app
   - Configure server URL (localhost, IP, or domain)
   - First login creates user account

4. **Remote Access Setup**
   - Choose tunnel method (Cloudflare/ngrok/Tailscale)
   - Configure SSL certificates
   - Test external access

## File Structure
```
encrypted-chat/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt       # Python dependencies
│   ├── database.py           # Database models
│   ├── auth.py               # Authentication logic
│   ├── encryption.py         # Message encryption
│   ├── websocket_handler.py  # WebSocket events
│   ├── image_bot.py          # Integrated bot from botUpdated.py
│   └── models/
│       ├── user.py
│       ├── room.py
│       ├── message.py
│       └── file.py
├── frontend/
│   ├── main.py               # PyQt6 GUI entry point
│   ├── ui/
│   │   ├── login_window.py
│   │   ├── chat_window.py
│   │   ├── room_list.py
│   │   └── user_settings.py
│   ├── websocket_client.py   # WebSocket connection
│   └── notification_handler.py
├── config/
│   ├── server_config.py
│   ├── client_config.py
│   └── encryption_keys.py
└── docs/
    ├── setup_guide.md
    ├── user_guide.md
    └── troubleshooting.md
```

## Security Checklist

- [ ] All passwords hashed with bcrypt
- [ ] All messages encrypted at rest
- [ ] WebSocket connections use WSS (secure)
- [ ] HTTPS enforced
- [ ] SQL injection prevention (use ORM/parameterized queries)
- [ ] CSRF protection enabled
- [ ] Session timeout implemented
- [ ] File uploads validation
- [ ] Input sanitization
- [ ] Rate limiting on API endpoints

## Next Steps

1. Create FastAPI server with SQLite
2. Implement user authentication
3. Setup WebSocket real-time messaging
4. Add encryption layer
5. Create Windows GUI client
6. Integrate image bot functionality
7. Setup notification system
8. Configure remote access tunnel
9. Testing and deployment

---

**Estimated Timeline:**
- Server Core: 2-3 days
- Client App: 2-3 days
- Integration & Bot: 1-2 days
- Testing & Deployment: 1 day
- **Total: 6-9 days of development**
