# Server Setup Guide - Encrypted Chat Application

## Prerequisites

- **Python 3.10+** 
- **Linux Debian Server** (or Ubuntu)
- **pip** and **venv** for Python package management
- **OpenSSL** for HTTPS certificates (optional but recommended)
- **Build tools** for some Python packages on newer distros: `build-essential`, `libffi-dev`, `libssl-dev`, `rustc`, `cargo`

## Step 1: Install Python and Dependencies

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and required system packages
sudo apt-get install -y python3 python3-pip python3-venv git curl wget build-essential libffi-dev libssl-dev rustc cargo

# Verify Python installation
python3 --version
pip3 --version
```

## Step 2: Clone or Setup Project

```bash
# Navigate to your project directory
cd /home/your_user/encrypted-chat-app

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r server/requirements.txt

# If your server uses Python 3.13, use this compatibility file instead
cd server
cp -f requirements.txt requirements.linux.txt
sed -i 's/uvicorn\[standard\]==0.24.0/uvicorn==0.24.0/' requirements.linux.txt
sed -i 's/curl-cffi==0.5.9/curl-cffi>=0.7.4/' requirements.linux.txt
sed -i 's/pillow==10.1.0/pillow>=11.0.0/' requirements.linux.txt
sed -i 's/pydantic==2.5.0/pydantic>=2.10.6,<3/' requirements.linux.txt
sed -i 's/pydantic-settings==2.1.0/pydantic-settings>=2.6.1,<3/' requirements.linux.txt
sed -i 's/^sqlalchemy==2.0.23$/sqlalchemy>=2.0.40,<2.1/' requirements.linux.txt
cd ..
pip install --only-binary=:all: -r server/requirements.linux.txt
```

## Step 3: Configure Environment Variables

Create a `.env` file in the server directory:

```bash
# .env file
DANBOORU_USER=your_danbooru_username
DANBOORU_API_KEY=your_danbooru_api_key
RULE34_USER_ID=your_rule34_user_id
RULE34_API_KEY=your_rule34_api_key
DATABASE_URL=sqlite:///./chat_app.db
SECRET_KEY=your_secret_key_here
```

Or set environment variables directly:

```bash
export DANBOORU_USER="your_username"
export DANBOORU_API_KEY="your_api_key"
export RULE34_USER_ID="your_user_id"
export RULE34_API_KEY="your_api_key"
```

## Step 4: Initialize Database

```bash
# Navigate to server directory
cd server

# Activate virtual environment if not already
source ../venv/bin/activate

# Run database initialization
python3 -c "from database import init_db; init_db()"
```

## Step 5: Start the Server

### Option A: Direct Python (Development)

```bash
# From the server directory with venv activated
python3 main.py
```

The server will start on `http://0.0.0.0:8000`

### Option B: Uvicorn with Watch (Development)

```bash
# Install uvicorn if not included
pip install uvicorn

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option C: Systemd Service (Production)

Create `/etc/systemd/system/encrypted-chat.service`:

```ini
[Unit]
Description=Encrypted Chat Application
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/encrypted-chat-app/server
ExecStart=/home/your_user/encrypted-chat-app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable encrypted-chat
sudo systemctl start encrypted-chat
sudo systemctl status encrypted-chat
```

If your app path is `/home/frostbyte/ChatAPP/encrypted-chat-app`, use this exact service file values:

- `User=frostbyte`
- `WorkingDirectory=/home/frostbyte/ChatAPP/encrypted-chat-app/server`
- `ExecStart=/home/frostbyte/ChatAPP/encrypted-chat-app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`

## Step 6: Setup HTTPS (Optional but Recommended)

### Using Let's Encrypt (Free SSL)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Certificate files will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

Update `main.py` to use SSL:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="/etc/letsencrypt/live/your-domain.com/privkey.pem",
        ssl_certfile="/etc/letsencrypt/live/your-domain.com/fullchain.pem"
    )
```

### Using Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Update main.py to use these files
```

## Step 7: Setup Remote Access (Choose One)

### Option A1: Cloudflare Tunnel (Recommended - No Port Forwarding)

```bash
# Download Cloudflare Tunnel
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create encrypted-chat

# Get tunnel credentials file
# It will be saved to ~/.cloudflared/{tunnel-id}.json

# Create config file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: encrypted-chat
credentials-file: /home/your_user/.cloudflared/{tunnel-id}.json

ingress:
  - hostname: chat.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Route the tunnel to your domain
cloudflared tunnel route dns encrypted-chat chat.your-domain.com

# Run the tunnel
cloudflared tunnel run encrypted-chat
```

Important dashboard note: for public websites/apps, add routes under `Published application routes`.
Do not use `Hostname routes` for this use case (that is private routing/WARP flow).

For two apps on the same server, use one healthy tunnel with multiple hostname routes:

- `chat.frostchat.uk` -> `http://localhost:8000` (encrypted chat)
- `8bitfrostbyte.win` -> `http://localhost:8096` (other app)

If cloudflared is already installed as a service, do not install a second one.
Just keep one `cloudflared` service running and manage both hostnames in the tunnel dashboard.

Create systemd service for tunnel:

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user
ExecStart=/usr/local/bin/cloudflared tunnel run encrypted-chat
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option A2: ngrok (Quick Testing)

```bash
# Download ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
unzip ngrok-v3-stable-linux-amd64.zip
sudo mv ngrok /usr/local/bin

# Sign up at https://ngrok.com and get auth token
ngrok config add-authtoken your_token

# Expose your server
ngrok http 8000

# Note the public URL (e.g., https://abc123.ngrok.io)
```

### Option A3: Tailscale VPN (Private Network)

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Get your Tailscale IP
tailscale ip -4

# Clients can connect via: http://your-tailscale-ip:8000
```

## Step 8: Verify Server is Running

```bash
# Check if server is listening
netstat -tuln | grep 8000

# Test health endpoint
curl http://localhost:8000/health

# If using tunnel, test the public URL
curl https://your-public-url/health
```

## Testing the Server

```bash
# Test user registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# List rooms
curl http://localhost:8000/api/rooms
```

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use: `sudo lsof -i :8000`
- Kill existing process: `sudo kill -9 <PID>`
- Check logs for errors

Common startup fixes:

- `status=203/EXEC`: your `ExecStart` path is wrong in `/etc/systemd/system/encrypted-chat.service`.
- `ImportError: cannot import name PBKDF2...`: in `server/encryption.py`, use `PBKDF2HMAC`.
- If manual run works but service fails, run `sudo systemctl daemon-reload` then restart service.

### Database errors
- Delete old database: `rm chat_app.db`
- Reinitialize: `python3 -c "from database import init_db; init_db()"`

### Connection issues from clients
- Verify server is listening: `netstat -tuln | grep 8000`
- Check firewall: `sudo ufw status`
- Allow port through firewall: `sudo ufw allow 8000`

### Slow performance
- Increase max connections in Uvicorn: `--workers 4`
- Use PostgreSQL instead of SQLite for production
- Enable caching

## Production Deployment Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS with valid certificate
- [ ] Set up remote access tunnel
- [ ] Configure systemd service for auto-start
- [ ] Set up SSL certificate auto-renewal with certbot
- [ ] Configure firewall rules
- [ ] Setup logging and monitoring
- [ ] Regular database backups
- [ ] Monitor server resources (CPU, memory, disk)
- [ ] Setup rate limiting on sensitive endpoints
- [ ] Enable CORS only for known client domains

## Security Hardening

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Limit Resource Usage

```bash
# Edit /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
```

### Backup Strategy

```bash
# Daily database backup
0 2 * * * /home/your_user/backup.sh

# backup.sh
#!/bin/bash
BACKUP_DIR="/home/your_user/backups"
mkdir -p $BACKUP_DIR
cp /home/your_user/encrypted-chat-app/server/chat_app.db \
   $BACKUP_DIR/chat_app_$(date +%Y%m%d_%H%M%S).db
# Keep only last 30 days
find $BACKUP_DIR -mtime +30 -delete
```

## Monitoring

### Check Server Status

```bash
# View service logs
sudo journalctl -u encrypted-chat -f

# View specific errors
sudo journalctl -u encrypted-chat -p err

# Monitor resource usage
htop

# Check disk space
df -h
```

Additional useful checks:

```bash
# Confirm app endpoint locally
curl http://localhost:8000/health

# Confirm cloudflared is connected
sudo systemctl status cloudflared --no-pager -l
sudo journalctl -u cloudflared -n 80 --no-pager
```

## Next Steps

1. Setup Windows clients using the Client Setup Guide
2. Configure remote access tunnel
3. Test with multiple clients
4. Monitor server logs and performance
5. Setup automated backups

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
