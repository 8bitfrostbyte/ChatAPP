# Quick Start Guide - 10 Minutes

This guide will get you running with encrypted chat in **10 minutes**.

## Prerequisites

- **Python 3.10+** installed on both server and client
- **Linux Debian server** and **Windows PC**
- Both machines connected to internet (or same local network)

## Server Setup (5 minutes)

### On Your Linux Server:

```bash
# 1. Clone/download the project
cd /home/your_user
git clone <your-repo>  # or copy files manually
cd encrypted-chat-app/server

# 2. Create Python environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python3 -c "from database import init_db; init_db()"

# 5. Run the server
python3 main.py
```

You should see:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal open!**

## Client Setup (5 minutes)

### On Your Windows PC:

```cmd
# 1. Open Command Prompt or PowerShell
# 2. Navigate to client folder
cd "C:\Users\YourName\Desktop\encrypted-chat-app\client"

# 3. Create Python environment
python -m venv venv
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py
```

## First Time Usage

When the app starts:

1. **Server URL Dialog:**
   - If server is on same network: Enter `http://SERVER_IP:8000`
   - Find server IP by running on server: `hostname -I`
   - Example: `http://192.168.1.100:8000`

2. **Login/Register Dialog:**
   - First time: Click "Register"
   - Username: Choose any name (testuser)
   - Password: Choose a password (test123456)
   - Click "Register"

3. **Chat Window:**
   - You're now in the "General" room
   - Type a message and press Enter
   - Click "Upload Image" to share images

## Multi-User Testing

To test with multiple users (2 Windows PCs):

1. **Start server:** Follow "Server Setup" above
2. **User 1 (PC1):**
   - Run client, register as "Alice"
   - Join "General" room
3. **User 2 (PC2):**
   - Run client, register as "Bob"  
   - Join "General" room
   - Both see each other's messages in real-time!

## Remote Access (Optional)

To access from outside your network, use **Tailscale** (easiest):

### On Server:
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Note the Tailscale IP (e.g., 100.x.x.x)
tailscale ip -4
```

### On Client (Windows):
```cmd
# Install Tailscale from https://tailscale.com/download/windows
# Sign in with same account as server
# Then use Server URL: http://100.x.x.x:8000
```

This creates encrypted private network without port forwarding!

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Connection refused" | Is server running? Check terminal where you started it |
| Can't find server IP | On server, run: `hostname -I` |
| Port 8000 in use | Stop other Python apps or use different port |
| Module not found errors | Did you activate venv? Check `(venv)` in prompt |
| Blank message display | Try refreshing by leaving/rejoining room |

## Using Image Bot Features

In any room, you can search and share images:

### Via API (Advanced):
```bash
# Search tags
curl -X POST "http://localhost:8000/api/bot/search?query=cat"

# Get images
curl -X POST "http://localhost:8000/api/bot/images?tags=cat"
```

### Via GUI (Future):
- Hotkey: Ctrl+B
- Command: `/bot search <tags>`

## Next Steps

1. ✅ Server running
2. ✅ Client connected
3. ✅ Multiple users chatting
4. **Now try:**
   - Create new rooms: Click "Create Room"
   - Upload images: Click "Upload Image"
   - Test notifications: Enable in Settings
   - Invite more users: Share server URL

## Production Deployment

When ready for real use:

1. **Enable HTTPS:**
   - Get free SSL certificate from Let's Encrypt
   - Update `main.py` with cert paths

2. **Remote Access:**
   - Choose Tailscale (easiest), Cloudflare Tunnel, or ngrok
   - See README.md for full instructions

3. **Autostart Server:**
   ```bash
   # Create systemd service
   sudo systemctl enable encrypted-chat
   sudo systemctl start encrypted-chat
   ```

4. **Backup Database:**
   ```bash
   # Daily backup script
   crontab -e
   # Add: 0 2 * * * cp /path/to/chat_app.db /path/to/backups/
   ```

## Security Checklist

- [ ] Use strong passwords (12+ characters)
- [ ] Always logout when done
- [ ] Never share your password
- [ ] Use HTTPS for public networks
- [ ] Keep Python updated
- [ ] Backup database regularly

## Getting Help

1. Check the full guides:
   - Server issues? See `SERVER_SETUP.md`
   - Client issues? See `CLIENT_SETUP.md`

2. Common solutions:
   - Restart the application
   - Restart the server
   - Check network connectivity
   - Check Python version: `python --version`

3. Debug mode:
   - Server: Look at terminal output
   - Client: Check command prompt for errors

---

**Everything working? Great!** 🎉

You now have a fully encrypted chat system!

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
