# Client Setup Guide - Windows Desktop Application

## Prerequisites

- **Windows 10 or 11**
- **Python 3.10+**
- **pip** for Python package management
- **Server URL** (from your server setup: local IP, domain, or tunnel URL)

## Step 1: Install Python

1. Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **IMPORTANT:** Check "Add Python to PATH" during installation
4. Click "Install Now"

Verify installation:

```cmd
python --version
pip --version
```

## Step 2: Setup Client Environment

```cmd
# Navigate to the encrypted-chat-app\client directory
cd C:\Users\YourUsername\Desktop\encrypted-chat-app\client

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# You should see (venv) at the start of your command line
```

## Step 3: Install Dependencies

```cmd
# Make sure you're in the client directory with venv activated
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# This will install:
# - PyQt6 (GUI framework)
# - WebSockets (real-time messaging)
# - Cryptography (encryption)
# - Requests (HTTP client)
# - Playsound (notification sounds)
```

If you see `Failed to build 'pillow' when getting requirements to build wheel`, run:

```cmd
pip install "pillow>=11.0.0"
pip install -r requirements.txt --prefer-binary
```

## Step 4: Configure Server URL

The application will prompt you to enter the server URL when you start it. You can use:

### Local Network (Same Network as Server)
```
http://your-server-ip:8000
```
Example: `http://192.168.1.100:8000`

### Remote (Over Internet)
```
https://your-tunnel-url
```
Examples:
- Cloudflare: `https://chat.your-domain.com`
- ngrok: `https://abc123.ngrok.io`
- Tailscale: `http://tailscale-ip:8000`

## Step 5: Run the Application

```cmd
# Make sure venv is activated
venv\Scripts\activate

# Run the application
python main.py
```

First time setup:
1. Enter server URL when prompted
2. Choose: **Register** to create new account or **Login** if account exists
3. Enter username and password
4. Click Register/Login

## Usage Guide

### Navigating Rooms

1. **Rooms List (Left Side):**
   - Shows all available chat rooms
   - Click a room to join and start chatting

2. **Create Room:**
   - Click "Create Room" button
   - Enter room name
   - Room is created and you're automatically joined

3. **Members List:**
   - Shows who's in the current room
   - Updates in real-time as people join/leave

### Sending Messages

1. Select a room from the list
2. Type your message in the input box at the bottom
3. Press Enter or click "Send" button
4. Message appears for all users in that room

### Uploading Images

1. Click "Upload Image" button
2. Select a .PNG, .JPG, .GIF, or .WEBP file
3. Image is uploaded and shared with room
4. All users see the image in chat history

### Settings

- Click "Settings" button
- Toggle notification sounds on/off
- Settings are applied immediately

### Logging Out

- Click "Logout" button
- You'll be logged out and can login with another account

## Features Explained

### Encryption
- All messages are encrypted before sending to server
- Server stores encrypted messages
- Messages are decrypted only when received
- Each room has its own encryption key

### Real-Time Updates
- Messages appear instantly via WebSocket
- User join/leave notifications
- Member list updates automatically
- Typing indicators (future enhancement)

### Notifications
- Desktop notifications when messages arrive
- Notification sounds (if enabled)
- Click notification to bring window to focus

### Message Deletion
- Right-click on message (future enhancement)
- Or use Settings menu
- Deleted messages are marked as removed for all users

## Troubleshooting

### "Connection Refused" Error

**Problem:** Can't connect to server
**Solutions:**
1. Verify server is running: Check your server's terminal
2. Check server URL is correct: Copy from server setup guide
3. Check firewall: Make sure port 8000 is open
4. Check VPN: If on corporate network, ensure you're authorized

### "Invalid Username or Password"

**Problem:** Login keeps failing
**Solutions:**
1. Verify credentials: Check spelling carefully
2. Register new account: If first time, click Register instead of Login
3. Password case-sensitive: Passwords are case-sensitive (Abc123 ≠ abc123)

### "Network Error" During Chat

**Problem:** Sudden disconnection while using app
**Solutions:**
1. Check internet connection: Verify you're still connected
2. Check server status: Server might be offline
3. Reconnect: Close and reopen the application
4. Check firewall logs: Firewall might be blocking WebSocket

### No Notification Sound

**Problem:** Notifications appear but no sound
**Solutions:**
1. Check Settings: Make sure sound is enabled
2. Check volume: System volume might be muted
3. Add custom sound: Place MP3 file in `sounds/notification.mp3`
4. Check permissions: Application needs audio device access

### Slow Performance or Lag

**Problem:** Messages appear delayed
**Solutions:**
1. Check network: Run speed test
2. Close other applications: Free up system resources
3. Check server: Server might be overloaded
4. Update Python: Ensure you have latest Python 3.10+

### Application Crashes on Startup

**Problem:** App closes immediately after starting
**Solutions:**
1. Check Python version: `python --version` (must be 3.10+)
2. Verify dependencies: `pip list` should show PyQt6, websockets, etc.
3. Reinstall dependencies:
   ```cmd
   pip uninstall -r requirements.txt -y
   python -m pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt --prefer-binary
   ```
4. Check for error logs: Look for error messages in console

### Pillow Wheel Build Error

**Problem:** `ERROR: Failed to build 'pillow' when getting requirements to build wheel`
**Solutions:**
1. Upgrade packaging tools:
   ```cmd
   python -m pip install --upgrade pip setuptools wheel
   ```
2. Install a newer compatible Pillow:
   ```cmd
   pip install "pillow>=11.0.0"
   ```
3. Reinstall requirements preferring binary wheels:
   ```cmd
   pip install -r requirements.txt --prefer-binary
   ```
4. If still failing, use Python 3.11 for client packaging/build tasks.

## Advanced Configuration

### Using Custom Server Certificate

If your server uses self-signed HTTPS:

1. Edit `main.py` and add to websocket connection:
   ```python
   import ssl
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = False
   ssl_context.verify_mode = ssl.CERT_NONE
   ```

2. Note: This is insecure, only use for testing!

### Connecting to Bot Features

From any chat room, you can search for images:

1. Use keyboard shortcut Ctrl+B (future feature)
2. Or type command: `!bot search <tags>`
3. Bot will search Rule34 and Danbooru sites
4. Results appear in chat as clickable links

### Proxy Configuration

If behind corporate proxy:

```cmd
# Set environment variables before running
set HTTP_PROXY=http://proxy.company.com:8080
set HTTPS_PROXY=https://proxy.company.com:8080
python main.py
```

## Security Best Practices

### Password Security
- Use strong passwords (12+ characters, mix of upper/lower/numbers/symbols)
- Don't share your password with others
- Change password if you suspect compromise

### Session Security
- Always logout when done using the app
- Don't leave app running on shared computers
- Close app if you won't use for extended period

### Content Privacy
- Understand room privacy settings
- Don't share sensitive information in public rooms
- Be aware that server administrators can see encrypted content

### Update Regularly
- Keep Python updated
- Keep application files updated
- Subscribe to security notices from server administrator

## Connection Scenarios

### Scenario 1: Local Network (Same Building)
```
Client: Windows PC
Server: Debian server in same building
Server URL: http://192.168.1.100:8000
Security: Local network, all traffic internal
```

### Scenario 2: Remote with Cloudflare Tunnel
```
Client: Windows PC (any location)
Server: Debian server (any location)
Server URL: https://chat.yourdomain.com
Security: Encrypted tunnel, valid SSL certificate
```

### Scenario 3: Remote with Tailscale VPN
```
Client: Windows PC (any location)
Server: Debian server (private network)
Server URL: http://100.x.x.x:8000
Security: VPN encrypted, private network
```

## Performance Tips

1. **Limit messages loaded:** First load shows last 50 messages
2. **Close unused rooms:** Each connection uses memory
3. **Clear message cache:** Periodically restart app
4. **Optimize server connection:** Use same network when possible
5. **Disable notifications:** If battery critical

## Launchable App Options

You can run the client like a normal launchable app without changing any server setup.

### Option 1: Desktop Shortcut (Fastest)

1. Right-click on Desktop
2. Create New → Shortcut
3. Location:
   ```
   cmd /k cd C:\Users\YourUsername\Desktop\encrypted-chat-app\client && venv\Scripts\python main.py
   ```
4. Name: "Encrypted Chat"
5. Click Finish
6. (Optional) Right-click → Properties → Change Icon

### Option 2: Build a Standalone .EXE (Best User Experience)

```cmd
cd C:\Users\YourUsername\Desktop\encrypted-chat-app\client
venv\Scripts\activate
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name EncryptedChat main.py
```

After build, run:
- `dist\EncryptedChat.exe`

Notes:
- No server-side changes required.
- Rebuild the `.exe` after client code updates.

## Uninstalling

To completely remove:

1. Delete the `encrypted-chat-app` folder
2. Delete the Desktop shortcut (if created)
3. That's it! No registry changes or system files modified

## Next Steps

1. Test with another user on different computer
2. Setup more rooms for different purposes
3. Configure image bot search tags
4. Explore advanced features
5. Provide feedback for improvements

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review server logs on server machine
3. Verify network connectivity between machines
4. Check Python version compatibility
5. Reinstall dependencies cleanly
