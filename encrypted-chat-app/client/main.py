"""
Main GUI application for encrypted chat client.
PyQt6-based user interface for Windows.
"""

import sys
import os
import copy
import asyncio
import json
import requests
import subprocess
import tempfile
import shlex
import base64
import html
import re
import time
import threading
import mimetypes
from typing import Optional, List, Dict
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QPushButton,
    QTextEdit, QTextBrowser, QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QFileDialog, QScrollArea, QInputDialog, QSplitter,
    QColorDialog, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QStandardPaths
from PyQt6.QtGui import QIcon, QPixmap, QFont, QFontDatabase
from PyQt6.QtGui import QDesktopServices

from websocket_client import WebSocketClient
from notification_handler import NotificationHandler

def _load_client_version(default: str = "1.0.0") -> str:
    """Load client version from packaged version.txt when available."""
    try:
        if getattr(sys, "frozen", False):
            base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        else:
            base_dir = Path(__file__).resolve().parent
        version_path = base_dir / "version.txt"
        if version_path.exists():
            value = version_path.read_text(encoding="utf-8").strip()
            if value:
                return value
    except Exception:
        pass
    return default


CLIENT_VERSION = _load_client_version("1.0.0")

# ---------------------------------------------------------------------------
# Theme system
# ---------------------------------------------------------------------------
_THEME_DEFAULTS: Dict = {
    "window_bg":      "#141a24",
    "panel_bg":       "#1d2533",
    "header_bg":      "#0f1520",
    "chat_bg":        "#1d2533",
    "input_bg":       "#1d2533",
    "border_color":   "#2f3d54",
    "text_color":     "#e8edf5",
    "button_bg":      "#244063",
    "button_border":  "#33547c",
    "button_text":    "#edf3ff",
    "timestamp_color": "#9aa8ba",
    "link_color":     "#7fb4ff",
    "font_family":    "",
    "font_size":      13,
    "font_weight":    600,
    "widget_radius":  8,
    "button_radius":  8,
    "border_width":   1,
    "timestamp_size": 11,
    "username_weight": 700,
    "message_spacing": 4,
    "system_italic":  True,
    "image_max_width": 420,
    "image_max_height": 320,
    "image_radius":   6,
    "splitter_handle_size": 8,
    "msg_own_name":   "#8df2d4",
    "msg_other_name": "#9bc3ff",
    "msg_own_text":   "#d8f1ec",
    "msg_other_text": "#dde8f8",
    "system_color":   "#9aa8ba",
}

_THEME_PRESETS: Dict = {
    "Dark (Default)": {
        "window_bg": "#141a24", "panel_bg": "#1d2533", "border_color": "#2f3d54",
        "text_color": "#e8edf5", "button_bg": "#244063", "button_border": "#33547c",
        "button_text": "#edf3ff", "msg_own_name": "#8df2d4", "msg_other_name": "#9bc3ff",
        "msg_own_text": "#d8f1ec", "msg_other_text": "#dde8f8", "system_color": "#9aa8ba",
        "font_family": "", "font_size": 13,
    },
    "PowerShell": {
        "window_bg": "#000000", "panel_bg": "#000000", "border_color": "#2b2b2b",
        "text_color": "#f0f0f0", "button_bg": "#111111", "button_border": "#3a3a3a",
        "button_text": "#f0f0f0", "msg_own_name": "#ffff00", "msg_other_name": "#00ffff",
        "msg_own_text": "#f0f0f0", "msg_other_text": "#f0f0f0", "system_color": "#b0b0b0",
        "font_family": "Consolas", "font_size": 13,
    },
    "Light": {
        "window_bg": "#f0f2f5", "panel_bg": "#ffffff", "border_color": "#c8d0de",
        "text_color": "#1a2030", "button_bg": "#dce8f8", "button_border": "#a8c0d8",
        "button_text": "#1a2a40", "msg_own_name": "#007a60", "msg_other_name": "#2060a8",
        "msg_own_text": "#1a3330", "msg_other_text": "#1a2a44", "system_color": "#667088",
        "font_family": "", "font_size": 13,
    },
    "Midnight Blue": {
        "window_bg": "#0a0e1a", "panel_bg": "#10162a", "border_color": "#1c2540",
        "text_color": "#c8d8f0", "button_bg": "#1a2848", "button_border": "#2a3f68",
        "button_text": "#d8e8ff", "msg_own_name": "#60e8b0", "msg_other_name": "#60b0ff",
        "msg_own_text": "#b8e8d8", "msg_other_text": "#c0d4f0", "system_color": "#7080a0",
        "font_family": "", "font_size": 13,
    },
    "Forest Green": {
        "window_bg": "#0d1a0d", "panel_bg": "#142014", "border_color": "#1e3c1e",
        "text_color": "#d0ead0", "button_bg": "#1a3c1a", "button_border": "#285228",
        "button_text": "#d8f4d8", "msg_own_name": "#80ff80", "msg_other_name": "#60c890",
        "msg_own_text": "#b8e8b8", "msg_other_text": "#c0dcc0", "system_color": "#709070",
        "font_family": "", "font_size": 13,
    },
    "Matrix CRT": {
        "window_bg": "#000000", "panel_bg": "#000000", "border_color": "#154215",
        "text_color": "#7dff7d", "button_bg": "#001700", "button_border": "#1d5c1d",
        "button_text": "#8dff8d", "msg_own_name": "#baff00", "msg_other_name": "#6cff6c",
        "msg_own_text": "#9eff9e", "msg_other_text": "#7dff7d", "system_color": "#4dcf4d",
        "font_family": "Lucida Console", "font_size": 13,
    },
    "Amber Terminal": {
        "window_bg": "#0a0700", "panel_bg": "#0a0700", "border_color": "#4a2c00",
        "text_color": "#ffb000", "button_bg": "#1a1200", "button_border": "#6f4200",
        "button_text": "#ffbf40", "msg_own_name": "#ffd86b", "msg_other_name": "#ff9e2f",
        "msg_own_text": "#ffc862", "msg_other_text": "#ffb94d", "system_color": "#c8871a",
        "font_family": "Consolas", "font_size": 13,
    },
    "Cyberpunk Neon": {
        "window_bg": "#0a0014", "panel_bg": "#140025", "border_color": "#3c1b66",
        "text_color": "#f6dcff", "button_bg": "#2f0a52", "button_border": "#6c2aa6",
        "button_text": "#ffe8ff", "msg_own_name": "#ff5ec4", "msg_other_name": "#3de6ff",
        "msg_own_text": "#ffd3f1", "msg_other_text": "#c6f7ff", "system_color": "#b69ad1",
        "font_family": "Segoe UI", "font_size": 13,
    },
    "Solarized Dark": {
        "window_bg": "#002b36", "panel_bg": "#073642", "border_color": "#1f5665",
        "text_color": "#93a1a1", "button_bg": "#0f4c5c", "button_border": "#2b6877",
        "button_text": "#dbe6e6", "msg_own_name": "#2aa198", "msg_other_name": "#268bd2",
        "msg_own_text": "#b5c2c2", "msg_other_text": "#c4d1d1", "system_color": "#839496",
        "font_family": "Cascadia Code", "font_size": 13,
    },
    "Gruvbox": {
        "window_bg": "#282828", "panel_bg": "#1d2021", "border_color": "#504945",
        "text_color": "#ebdbb2", "button_bg": "#3c3836", "button_border": "#665c54",
        "button_text": "#fbf1c7", "msg_own_name": "#b8bb26", "msg_other_name": "#83a598",
        "msg_own_text": "#ebdbb2", "msg_other_text": "#d5c4a1", "system_color": "#a89984",
        "font_family": "", "font_size": 13,
    },
    "Ice Cave": {
        "window_bg": "#dff6ff", "panel_bg": "#ffffff", "border_color": "#9ec7dd",
        "text_color": "#0f2b3a", "button_bg": "#b9e4f7", "button_border": "#86bfd8",
        "button_text": "#0f2d3f", "msg_own_name": "#005f8d", "msg_other_name": "#4c3bff",
        "msg_own_text": "#12384d", "msg_other_text": "#1a2d5c", "system_color": "#4f6f82",
        "font_family": "", "font_size": 13,
    },
    "High Contrast": {
        "window_bg": "#000000", "panel_bg": "#000000", "border_color": "#ffffff",
        "text_color": "#ffffff", "button_bg": "#000000", "button_border": "#ffffff",
        "button_text": "#ffffff", "msg_own_name": "#ffff00", "msg_other_name": "#00ffff",
        "msg_own_text": "#ffffff", "msg_other_text": "#ffffff", "system_color": "#ff00ff",
        "font_family": "Arial", "font_size": 14,
    },
    "Goblin Mode": {
        "window_bg": "#1c1500", "panel_bg": "#281d00", "border_color": "#4f3200",
        "text_color": "#d0ff00", "button_bg": "#3d2b00", "button_border": "#6c4700",
        "button_text": "#f2ff8a", "msg_own_name": "#ff6a00", "msg_other_name": "#9eff00",
        "msg_own_text": "#e8ff7a", "msg_other_text": "#ceff44", "system_color": "#c1a735",
        "font_family": "Comic Sans MS", "font_size": 13,
    },
    "Arcade Glitch": {
        "window_bg": "#080808", "panel_bg": "#111111", "border_color": "#3a3a3a",
        "text_color": "#f5f5f5", "button_bg": "#191919", "button_border": "#4c4c4c",
        "button_text": "#ffffff", "msg_own_name": "#ff0055", "msg_other_name": "#00e5ff",
        "msg_own_text": "#ffc7d8", "msg_other_text": "#c7f8ff", "system_color": "#b3b3b3",
        "font_family": "OCR A Extended", "font_size": 13,
    },
}


def _resolve_user_settings_path() -> Path:
    """Return a writable per-user settings path."""
    app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if app_data:
        settings_dir = Path(app_data)
    else:
        settings_dir = Path.home() / ".encrypted-chat"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "user_settings.json"


def _normalize_server_url(server_url: str, default: str = "http://localhost:8000") -> str:
    """Normalize a server URL for REST and WebSocket use."""
    value = str(server_url or "").strip() or default
    return value.rstrip("/")


def _load_saved_server_url(default: str = "http://localhost:8000") -> str:
    """Load last used server URL for startup prompt."""
    try:
        settings_path = _resolve_user_settings_path()
        if not settings_path.exists():
            return _normalize_server_url(default, default)
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        value = str(data.get("server_url", "")).strip()
        if value.lower().startswith(("http://", "https://")):
            return _normalize_server_url(value, default)
    except Exception:
        pass
    return _normalize_server_url(default, default)


def _save_server_url(server_url: str):
    """Persist last used server URL without overwriting other settings."""
    try:
        settings_path = _resolve_user_settings_path()
        payload = {}
        if settings_path.exists():
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        payload["server_url"] = _normalize_server_url(server_url)
        settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


class APIClient:
    """Client for interacting with the server REST API."""
    
    def __init__(self, server_url: str):
        self.server_url = _normalize_server_url(server_url)
        self.token = None
        self.user_id = None
        self.username = None
    
    def _get_headers(self):
        """Get authorization headers."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def register(self, username: str, password: str) -> tuple:
        """Register a new user."""
        try:
            response = requests.post(
                f"{self.server_url}/api/auth/register",
                json={"username": username, "password": password},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, response.json().get("detail", "Registration failed")
        except Exception as e:
            return False, str(e)
    
    def login(self, username: str, password: str) -> tuple:
        """Login a user."""
        try:
            response = requests.post(
                f"{self.server_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.user_id = data["user"]["id"]
                self.username = data["user"]["username"]
                return True, data
            else:
                return False, response.json().get("detail", "Login failed")
        except Exception as e:
            return False, str(e)
    
    def logout(self) -> bool:
        """Logout a user."""
        try:
            requests.post(
                f"{self.server_url}/api/auth/logout",
                headers=self._get_headers(),
                timeout=5
            )
            self.token = None
            self.user_id = None
            self.username = None
            return True
        except:
            return False
    
    def list_rooms(self) -> tuple:
        """Get list of available rooms."""
        try:
            response = requests.get(
                f"{self.server_url}/api/rooms",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, []
    
    def create_room(self, name: str, is_private: bool = False) -> tuple:
        """Create a new room."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms",
                params={"name": name, "is_private": is_private},
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Failed to create room")
        except Exception as e:
            return False, str(e)

    def delete_room(self, room_id: int) -> tuple:
        """Delete a room by ID."""
        try:
            response = requests.delete(
                f"{self.server_url}/api/rooms/{room_id}",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to delete room")
        except Exception as e:
            return False, str(e)

    def make_room_private(self, room_id: int) -> tuple:
        """Mark a room as private."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{room_id}/make-private",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to make room private")
        except Exception as e:
            return False, str(e)
    
    def join_room(self, room_id: int) -> tuple:
        """Join a room."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{room_id}/join",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Failed to join room")
        except Exception as e:
            return False, str(e)
    
    def leave_room(self, room_id: int) -> tuple:
        """Leave a room."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{room_id}/leave",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Failed to leave room")
        except Exception as e:
            return False, str(e)

    def invite_user(self, room_id: int, username: str) -> tuple:
        """Invite a user to a room (creator only)."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{room_id}/invite",
                params={"username": username},
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to invite user")
        except Exception as e:
            return False, str(e)

    def get_pending_invites(self) -> tuple:
        """Fetch pending room invites for the current user."""
        try:
            response = requests.get(
                f"{self.server_url}/api/invites/pending",
                headers=self._get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to fetch invites")
        except Exception as e:
            return False, str(e)

    def respond_to_invite(self, invite_id: int, action: str) -> tuple:
        """Accept or decline a room invite."""
        try:
            response = requests.post(
                f"{self.server_url}/api/invites/{invite_id}/respond",
                params={"action": action},
                headers=self._get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to respond to invite")
        except Exception as e:
            return False, str(e)
    
    def get_room_members(self, room_id: int) -> tuple:
        """Get members of a room."""
        try:
            response = requests.get(
                f"{self.server_url}/api/rooms/{room_id}/members",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, []
    
    def get_messages(self, room_id: int, limit: int = 500, offset: int = 0) -> tuple:
        """Get message history."""
        try:
            response = requests.get(
                f"{self.server_url}/api/rooms/{room_id}/messages",
                params={"limit": limit, "offset": offset},
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            return False, []
    
    def delete_message(self, message_id: int) -> tuple:
        """Delete a message."""
        try:
            response = requests.delete(
                f"{self.server_url}/api/messages/{message_id}",
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Failed to delete message")
        except Exception as e:
            return False, str(e)
    
    def clear_room_messages(self, room_id: int, count: int) -> tuple:
        """Clear recent messages in a room."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{room_id}/clear",
                params={"count": count},
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to clear messages")
        except Exception as e:
            return False, str(e)
    def upload_file(self, room_id: int, file_path: str) -> tuple:
        """Upload a file/image."""
        try:
            with open(file_path, "rb") as f:
                guessed_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                files = {"file": (Path(file_path).name, f, guessed_type)}
                response = requests.post(
                    f"{self.server_url}/api/upload",
                    params={"room_id": room_id},
                    files=files,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10
                )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Upload failed")
        except Exception as e:
            return False, str(e)
    
    def search_tags(self, query: str) -> tuple:
        """Search image tags."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/search",
                params={"query": query},
                timeout=35
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.json().get("detail", "Bot search request failed")
        except Exception as e:
            return False, str(e)

    def fetch_bot_images(self, tags: str, limit: int = 5) -> tuple:
        """Fetch images from the integrated bot."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/images",
                params={"tags": tags, "limit": limit},
                timeout=15
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Bot image request failed")
        except Exception as e:
            return False, str(e)

    def get_bot_blacklist(self) -> tuple:
        """Get current bot blacklist."""
        try:
            response = requests.get(f"{self.server_url}/api/bot/blacklist", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to fetch blacklist")
        except Exception as e:
            return False, str(e)

    def add_bot_blacklist(self, tags: str) -> tuple:
        """Add tags to bot blacklist."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/blacklist/add",
                params={"tags": tags},
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to add blacklist tags")
        except Exception as e:
            return False, str(e)

    def remove_bot_blacklist(self, tags: str) -> tuple:
        """Remove tags from bot blacklist."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/blacklist/remove",
                params={"tags": tags},
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to remove blacklist tags")
        except Exception as e:
            return False, str(e)

    def clear_bot_blacklist(self) -> tuple:
        """Clear all bot blacklist tags."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/blacklist/clear",
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to clear blacklist tags")
        except Exception as e:
            return False, str(e)

    def start_bot_stream(self, room_id: int, interval: float, tags: Optional[str] = None) -> tuple:
        """Start room bot image stream."""
        try:
            params = {"room_id": room_id, "interval": interval}
            if tags is not None and tags.strip():
                params["tags"] = tags
            response = requests.post(
                f"{self.server_url}/api/bot/stream/start",
                params=params,
                headers=self._get_headers(),
                timeout=20
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to start stream")
        except Exception as e:
            return False, str(e)

    def stop_bot_stream(self, room_id: int) -> tuple:
        """Stop room bot image stream."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/stream/stop",
                params={"room_id": room_id},
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to stop stream")
        except Exception as e:
            return False, str(e)

    def bot_stream_status(self, room_id: int) -> tuple:
        """Get room bot stream status."""
        try:
            response = requests.get(
                f"{self.server_url}/api/bot/stream/status",
                params={"room_id": room_id},
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to get stream status")
        except Exception as e:
            return False, str(e)

    def pause_bot_stream(self, room_id: int) -> tuple:
        """Pause room bot image stream."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/stream/pause",
                params={"room_id": room_id},
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to pause stream")
        except Exception as e:
            return False, str(e)

    def resume_bot_stream(self, room_id: int) -> tuple:
        """Resume room bot image stream."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/stream/resume",
                params={"room_id": room_id},
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to resume stream")
        except Exception as e:
            return False, str(e)

    def get_saved_tags(self) -> tuple:
        """Get saved bot tags."""
        try:
            response = requests.get(f"{self.server_url}/api/bot/tags", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to fetch saved tags")
        except Exception as e:
            return False, str(e)

    def add_saved_tags(self, tags: str) -> tuple:
        """Add tags to saved bot pool."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/tags/add",
                params={"tags": tags},
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to add tags")
        except Exception as e:
            return False, str(e)

    def remove_saved_tags(self, tags: str) -> tuple:
        """Remove tags from saved bot pool."""
        try:
            response = requests.post(
                f"{self.server_url}/api/bot/tags/remove",
                params={"tags": tags},
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to remove tags")
        except Exception as e:
            return False, str(e)

    def clear_saved_tags(self) -> tuple:
        """Clear saved bot tags."""
        try:
            response = requests.post(f"{self.server_url}/api/bot/tags/clear", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to clear tags")
        except Exception as e:
            return False, str(e)

    def check_for_update(self, current_version: str) -> tuple:
        """Ask server whether a newer client build is available."""
        try:
            response = requests.get(
                f"{self.server_url}/api/update/check",
                params={"current_version": current_version},
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Update check failed")
        except Exception as e:
            return False, str(e)

    def download_update_file(self, destination_path: str) -> tuple:
        """Download latest update EXE from server to destination path."""
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        last_error = "Update download failed"
        for attempt in range(1, 3):
            try:
                with requests.get(
                    f"{self.server_url}/api/update/download",
                    stream=True,
                    timeout=(10, 30),
                ) as response:
                    if response.status_code != 200:
                        try:
                            return False, response.json().get("detail", "Update download failed")
                        except Exception:
                            return False, f"Update download failed ({response.status_code})"

                    tmp_path = dest.with_suffix(dest.suffix + ".part")
                    started_at = time.monotonic()
                    with open(tmp_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if not chunk:
                                continue
                            f.write(chunk)

                            # Prevent endless hangs on bad/half-open connections.
                            if time.monotonic() - started_at > 15 * 60:
                                raise TimeoutError("Download timed out after 15 minutes")

                    tmp_path.replace(dest)
                    return True, {"path": str(dest)}
            except Exception as e:
                last_error = str(e)
                try:
                    part_path = dest.with_suffix(dest.suffix + ".part")
                    if part_path.exists():
                        part_path.unlink()
                except Exception:
                    pass
                if attempt < 2:
                    time.sleep(1.0)

        return False, last_error

    def download_file_from_url(self, file_url: str, destination_path: str) -> tuple:
        """Download a file URL to destination path."""
        try:
            url = str(file_url or "").strip()
            if not url:
                return False, "Missing file URL"
            if url.startswith("/"):
                url = f"{self.server_url.rstrip('/')}{url}"
            elif not url.lower().startswith(("http://", "https://")):
                url = f"{self.server_url.rstrip('/')}/{url.lstrip('/')}"

            response = requests.get(url, headers=self._get_headers(), stream=True, timeout=(10, 60))
            if response.status_code != 200:
                return False, f"Download failed ({response.status_code})"

            dest = Path(destination_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            return True, {"path": str(dest)}
        except Exception as e:
            return False, str(e)


class WebSocketThread(QThread):
    """Thread for managing WebSocket connection."""
    
    message_received = pyqtSignal(dict)
    user_joined = pyqtSignal(dict)
    user_left = pyqtSignal(dict)
    typing_received = pyqtSignal(dict)
    message_deleted = pyqtSignal(dict)
    connection_closed = pyqtSignal()
    
    def __init__(self, server_url: str, token: str, room_id: int):
        super().__init__()
        self.server_url = server_url
        self.token = token
        self.room_id = room_id
        self.client = None
        self.loop = None

    def _ensure_membership(self) -> bool:
        """Best-effort join attempt before websocket reconnect."""
        try:
            response = requests.post(
                f"{self.server_url}/api/rooms/{self.room_id}/join",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=8,
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _run_client(self):
        def _init_client():
            self.client = WebSocketClient(self.server_url, self.token, self.room_id)
            self.client.set_on_message(lambda data: self.message_received.emit(data))
            self.client.set_on_user_joined(lambda data: self.user_joined.emit(data))
            self.client.set_on_user_left(lambda data: self.user_left.emit(data))
            self.client.set_on_typing(lambda data: self.typing_received.emit(data))
            self.client.set_on_message_deleted(lambda data: self.message_deleted.emit(data))

        _init_client()
        try:
            await self.client.connect()
        except Exception as first_error:
            if "403" in str(first_error):
                # Membership might be stale on this client/session; re-join then retry once.
                joined = await asyncio.to_thread(self._ensure_membership)
                if joined:
                    _init_client()
                    await self.client.connect()
                else:
                    raise first_error
            else:
                raise

        if self.client.receive_task:
            try:
                await self.client.receive_task
            except asyncio.CancelledError:
                pass
    
    def run(self):
        """Run the WebSocket connection."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_client())
        
        except Exception as e:
            print(f"WebSocket thread error: {e}")
        
        finally:
            if self.loop:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    try:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
                self.loop.close()
            self.connection_closed.emit()
    
    def send_message(self, content: str):
        """Send a message."""
        if self.client and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message(content),
                self.loop
            )
    
    def stop(self):
        """Stop the WebSocket connection."""
        if self.client and self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self.client.disconnect(),
                self.loop
            )
            try:
                future.result(timeout=2)
            except Exception:
                pass


class WorkerThread(QThread):
    """Generic one-shot background worker. Runs fn(*args) and emits result."""
    result = pyqtSignal(object)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):
        try:
            self.result.emit(self._fn(*self._args))
        except Exception as e:
            self.result.emit(None)
            print(f"WorkerThread error: {e}")


class RoomRefreshThread(QThread):
    """Background thread for polling the room list without blocking the UI."""

    rooms_fetched = pyqtSignal(list)

    def __init__(self, api_client: 'APIClient'):
        super().__init__()
        self.api_client = api_client
        self._stop = False

    def run(self):
        while not self._stop:
            success, rooms = self.api_client.list_rooms()
            if success:
                self.rooms_fetched.emit(rooms)
            self.msleep(5000)

    def stop(self):
        self._stop = True
        self.quit()


class LoginDialog(QDialog):
    """Login/Register dialog."""
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.is_login = True
        
        self.setWindowTitle("Encrypted Chat - Login")
        self.setGeometry(100, 100, 400, 200)
        
        layout = QVBoxLayout()
        
        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)
        
        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        # Login/Register buttons
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        button_layout.addWidget(self.login_btn)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.clicked.connect(self.register)
        button_layout.addWidget(self.register_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def login(self):
        """Attempt login."""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        success, result = self.api_client.login(username, password)
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", str(result))
    
    def register(self):
        """Attempt registration."""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        success, result = self.api_client.register(username, password)
        if success:
            QMessageBox.information(self, "Success", "Account created! You can now login.")
            self.username_input.clear()
            self.password_input.clear()
        else:
            QMessageBox.critical(self, "Registration Failed", str(result))


class ChatBrowser(QTextBrowser):
    """QTextBrowser that serves images from an in-memory bytes store via loadResource,
    avoiding large base64 data URIs in the HTML document."""

    # Class-level bytes store: {"chatimg://<key>": bytes}
    _image_store: Dict[str, bytes] = {}

    def loadResource(self, resource_type, url):
        if resource_type == 2:  # QTextDocument.ResourceType.ImageResource
            data = ChatBrowser._image_store.get(url.toString())
            if data is not None:
                from PyQt6.QtGui import QImage
                img = QImage()
                img.loadFromData(data)
                return img
        return super().loadResource(resource_type, url)


class ChatWindow(QMainWindow):
        _busy = False
    # Persistent image cache for the session (URL -> chatimg://key)
    _global_image_cache = {}
    """Main chat window."""
    
    _busy = False
    """Main chat window."""
    
    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = _normalize_server_url(server_url)
        self.api_client = APIClient(self.server_url)
        self.current_room = None
        self.websocket_thread = None
        self.notification_handler = NotificationHandler(self)
        self.sidebar_collapsed = False
        self._image_cache = ChatWindow._global_image_cache
        self._chat_raw_messages = []
        self._last_presence_message = None
        self._last_presence_at = 0.0
        self._seen_live_message_keys = set()
        self._uploaded_image_urls_by_message_id: Dict[int, str] = {}
        self._room_list_snapshot = []
        self._rooms_data: Dict[int, dict] = {}  # room_id -> {is_private, created_by}
        self._room_select_epoch = 0
        self._seen_invite_ids = set()
        self._pending_update_info: Dict = {}
        self._last_update_notice_version = ""
        self.settings_path = self._resolve_settings_path()
        self._theme: Dict = copy.deepcopy(_THEME_DEFAULTS)
        self._load_user_settings()
        
        self.setWindowTitle("Encrypted Chat")
        self.setGeometry(100, 100, 1000, 600)
        
        self.apply_dark_theme()

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row
        header_widget = QWidget()
        header_widget.setObjectName("HeaderBar")
        header_widget.setMinimumHeight(0)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 2)
        self.user_label = QLabel("User: not logged in")
        self.user_label.setObjectName("HeaderUserLabel")
        self.server_label = QLabel(f"Server: {self.server_url}")
        self.server_label.setObjectName("HeaderServerLabel")
        header_layout.addWidget(self.user_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.server_label)
        header_widget.setLayout(header_layout)

        # Content layout with resizable splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Allow dragging chat pane to full width by collapsing sibling pane.
        self.main_splitter.setChildrenCollapsible(True)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setOpaqueResize(True)
        
        # Left sidebar - Rooms
        self.sidebar_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        sidebar_header_layout = QHBoxLayout()
        rooms_label = QLabel("Rooms")
        rooms_label.setObjectName("SectionLabel")
        self.toggle_sidebar_btn = QPushButton("Collapse")
        self.toggle_sidebar_btn.setObjectName("SidebarToggleBtn")
        self.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        sidebar_header_layout.addWidget(rooms_label)
        sidebar_header_layout.addStretch(1)
        sidebar_header_layout.addWidget(self.toggle_sidebar_btn)
        left_layout.addLayout(sidebar_header_layout)
        
        self.room_list = QListWidget()
        self.room_list.itemClicked.connect(self.on_room_selected)
        left_layout.addWidget(self.room_list)
        
        # Create room button
        create_room_btn = QPushButton("Create Room")
        create_room_btn.clicked.connect(self.create_room)
        left_layout.addWidget(create_room_btn)
        
        # Join room button
        join_room_btn = QPushButton("Join Another Room")
        join_room_btn.clicked.connect(self.join_room_dialog)
        left_layout.addWidget(join_room_btn)
        
        # Members list
        members_label = QLabel("In Room")
        members_label.setObjectName("SectionLabel")
        left_layout.addWidget(members_label)
        self.members_list = QListWidget()
        self.members_list.setMaximumWidth(260)
        left_layout.addWidget(self.members_list)

        self.sidebar_widget.setLayout(left_layout)
        self.sidebar_widget.setMinimumWidth(0)
        
        # Right side - Chat
        chat_widget = QWidget()
        chat_widget.setMinimumWidth(0)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Room name
        self.room_name_label = QLabel("Select a room")
        self.room_name_label.setObjectName("RoomTitleLabel")
        self.room_name_label.setMinimumHeight(0)
        
        # Messages + composer in a vertical splitter so the chat pane is draggable.
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        # Allow dragging message area to full height by collapsing composer pane.
        self.chat_splitter.setChildrenCollapsible(True)
        self.chat_splitter.setHandleWidth(8)
        self.chat_splitter.setOpaqueResize(True)

        self.message_display = ChatBrowser()
        self.message_display.setObjectName("ChatDisplay")
        self.message_display.setMinimumHeight(0)
        self.message_display.setReadOnly(True)
        self.message_display.setOpenExternalLinks(False)
        self.message_display.anchorClicked.connect(self.open_message_link)
        self.chat_splitter.addWidget(self.message_display)

        composer_widget = QWidget()
        composer_widget.setMinimumHeight(0)
        composer_layout = QVBoxLayout()
        composer_layout.setContentsMargins(0, 0, 0, 0)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("ChatInput")
        self.message_input.returnPressed.connect(self.send_message)
        composer_layout.addWidget(self.message_input)

        button_layout = QHBoxLayout()

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        button_layout.addWidget(send_btn)

        upload_btn = QPushButton("Upload File")
        upload_btn.clicked.connect(self.upload_file_dialog)
        button_layout.addWidget(upload_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(settings_btn)

        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        button_layout.addWidget(logout_btn)

        composer_layout.addLayout(button_layout)
        composer_widget.setLayout(composer_layout)
        self.chat_splitter.addWidget(composer_widget)
        self.chat_splitter.setCollapsible(0, True)
        self.chat_splitter.setCollapsible(1, True)
        self.chat_splitter.setStretchFactor(0, 1)
        self.chat_splitter.setStretchFactor(1, 0)
        self.chat_splitter.setSizes([520, 120])

        # Top-edge drag support for message area (drag handle above messages).
        self.chat_area_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat_area_splitter.setChildrenCollapsible(True)
        self.chat_area_splitter.setHandleWidth(8)
        self.chat_area_splitter.setOpaqueResize(True)
        self.chat_area_splitter.addWidget(self.room_name_label)
        self.chat_area_splitter.addWidget(self.chat_splitter)
        self.chat_area_splitter.setCollapsible(0, True)
        self.chat_area_splitter.setCollapsible(1, True)
        self.chat_area_splitter.setStretchFactor(0, 0)
        self.chat_area_splitter.setStretchFactor(1, 1)
        self.chat_area_splitter.setSizes([34, 606])

        right_layout.addWidget(self.chat_area_splitter)

        chat_widget.setLayout(right_layout)

        self.main_splitter.addWidget(self.sidebar_widget)
        self.main_splitter.addWidget(chat_widget)
        self.main_splitter.setCollapsible(0, True)
        self.main_splitter.setCollapsible(1, True)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([280, 720])

        # Global vertical splitter enables dragging from top edge too (collapse header).
        self.window_splitter = QSplitter(Qt.Orientation.Vertical)
        self.window_splitter.setChildrenCollapsible(True)
        self.window_splitter.setHandleWidth(8)
        self.window_splitter.setOpaqueResize(True)
        self.window_splitter.addWidget(header_widget)
        self.window_splitter.addWidget(self.main_splitter)
        self.window_splitter.setCollapsible(0, True)
        self.window_splitter.setCollapsible(1, True)
        self.window_splitter.setStretchFactor(0, 0)
        self.window_splitter.setStretchFactor(1, 1)
        self.window_splitter.setSizes([28, 572])

        main_layout.addWidget(self.window_splitter)
        central_widget.setLayout(main_layout)
        
        # Prevent WorkerThread instances from being garbage-collected mid-run
        self._workers = []

        # Refresh rooms in a background thread so the UI never blocks
        self.room_refresh_thread = RoomRefreshThread(self.api_client)
        self.room_refresh_thread.rooms_fetched.connect(self._update_room_list)
        self.room_refresh_thread.start()

        # Keep room member list fresh even if a live WS presence event is missed.
        self.members_refresh_timer = QTimer(self)
        self.members_refresh_timer.setInterval(3000)
        self.members_refresh_timer.timeout.connect(self.refresh_members)
        self.members_refresh_timer.start()
    
    def show_login(self) -> bool:
        """Show login dialog. Returns True only on successful login."""
        dialog = LoginDialog(self.api_client, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.user_label.setText(f"User: {self.api_client.username}")
            self.setWindowTitle(f"Encrypted Chat - {self.api_client.username}")
            self.refresh_rooms()
            self.auto_join_default_room()
            self.check_pending_private_invites()

            self.invites_check_timer = QTimer(self)
            self.invites_check_timer.setInterval(10000)
            self.invites_check_timer.timeout.connect(self.check_pending_private_invites)
            self.invites_check_timer.start()

            self.check_for_updates(manual=False)

            self.update_check_timer = QTimer(self)
            self.update_check_timer.setInterval(15 * 60 * 1000)
            self.update_check_timer.timeout.connect(lambda: self.check_for_updates(manual=False))
            self.update_check_timer.start()
            return True
        return False

    def check_pending_private_invites(self):
        """Poll pending invites and prompt user to accept/decline."""
        def _apply(result):
            success, payload = result if result else (False, "Failed to fetch invites")
            if not success or not isinstance(payload, list):
                return

            for invite in payload:
                invite_id = int(invite.get("invite_id", 0) or 0)
                if invite_id <= 0 or invite_id in self._seen_invite_ids:
                    continue
                self._seen_invite_ids.add(invite_id)

                room_name = str(invite.get("room_name", "Unknown Room"))
                inviter_name = str(invite.get("inviter_username", "Unknown"))
                prompt = (
                    f"You have been invited to private room '{room_name}' by {inviter_name}.\n\n"
                    "Do you want to accept this invite?"
                )
                choice = QMessageBox.question(
                    self,
                    "Private Room Invite",
                    prompt,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )

                action = "accept" if choice == QMessageBox.StandardButton.Yes else "decline"

                def _apply_response(res, selected_action=action):
                    ok, data = res if res else (False, "Request failed")
                    if ok:
                        self.append_system_message(data.get("message", f"Invite {selected_action}ed"))
                        self.refresh_rooms()
                    else:
                        self.append_system_message(f"Invite response failed: {data}")

                self._run_in_bg(self.api_client.respond_to_invite, _apply_response, invite_id, action)

        self._run_in_bg(self.api_client.get_pending_invites, _apply)

    def check_for_updates(self, manual: bool = False, done_callback=None):
        """Check server-managed GitHub update status and announce in-app when available."""
        if ChatWindow._busy:
            self.append_system_message("Please wait: another operation is in progress.")
            if done_callback:
                done_callback(False, "Busy")
            return
        self.set_busy(True, "Checking for updates...")
        def _fetch(version_text):
            return self.api_client.check_for_update(version_text)

        def _apply(result):
            self.set_busy(False)
            success, payload = result if result else (False, "Update check failed")
            if success and isinstance(payload, dict):
                self._pending_update_info = payload
                if payload.get("configured") is False:
                    if manual:
                        self.append_system_message("Updates are not configured on this server yet.")
                    if done_callback:
                        done_callback(True, payload)
                    return
                latest = str(payload.get("latest_version", "")).strip()
                if payload.get("update_available") and latest and latest != self._last_update_notice_version:
                    self._last_update_notice_version = latest
                    self.append_system_message(
                        f"Update available: v{latest} (current v{CLIENT_VERSION}). Open Settings > Updates to install."
                    )
                elif manual and not payload.get("update_available"):
                    self.append_system_message(f"No update available. Current version: v{CLIENT_VERSION}.")
            else:
                if manual:
                    self.append_system_message(f"Update check failed: {payload}")
            if done_callback:
                done_callback(success, payload)

        self._run_in_bg(_fetch, _apply, CLIENT_VERSION)

    def install_update_from_server(self, done_callback=None):
        """Download latest update via server; replace EXE on restart when packaged."""
        if ChatWindow._busy:
            self.append_system_message("Please wait: another operation is in progress.")
            if done_callback:
                done_callback(False, "Busy")
            return
        self.set_busy(True, "Downloading update...")
        latest = str(self._pending_update_info.get("latest_version", "")).strip() or "latest"

        if getattr(sys, "frozen", False):
            current_exe = Path(sys.executable)
            new_exe = current_exe.with_name(f"{current_exe.stem}.new.exe")

            def _fetch(target_path):
                return self.api_client.download_update_file(str(target_path))

            def _apply(result):
                self.set_busy(False)
                progress_state["done"] = True
                success, payload = result if result else (False, "Update download failed")
                if not success:
                    self.append_system_message(f"Update download failed: {payload}")
                    if done_callback:
                        done_callback(False, payload)
                    return
                updater_bat = Path(tempfile.gettempdir()) / f"encrypted_chat_update_{os.getpid()}.bat"
                script = (
                    "@echo off\n"
                    "setlocal\n"
                    f"set \"PID={os.getpid()}\"\n"
                    f"set \"SRC={str(new_exe)}\"\n"
                    f"set \"DST={str(current_exe)}\"\n"
                    ":waitproc\n"
                    "tasklist /FI \"PID eq %PID%\" | find \"%PID%\" >nul\n"
                    "if not errorlevel 1 (\n"
                    "  timeout /t 1 /nobreak >nul\n"
                    "  goto waitproc\n"
                    ")\n"
                    ":copyretry\n"
                    "copy /Y \"%SRC%\" \"%DST%\" >nul\n"
                    "if errorlevel 1 (\n"
                    "  timeout /t 1 /nobreak >nul\n"
                    "  goto copyretry\n"
                    ")\n"
                    "start \"\" \"%DST%\"\n"
                    "del /f /q \"%SRC%\" >nul 2>&1\n"
                    "del /f /q \"%~f0\" >nul 2>&1\n"
                )

                try:
                    updater_bat.write_text(script, encoding="utf-8")
                    self.append_system_message(f"Update v{latest} downloaded. Restarting to apply update...")
                    subprocess.Popen(["cmd", "/c", str(updater_bat)], creationflags=0x08000000)
                    # Use a hard-exit fallback so the updater script is never blocked waiting on this process.
                    QTimer.singleShot(300, self.close)
                    QTimer.singleShot(450, lambda: QApplication.instance().quit())
                    QTimer.singleShot(4000, lambda: os._exit(0))
                    if done_callback:
                        done_callback(True, payload)
                except Exception as e:
                    self.append_system_message(f"Failed to prepare updater: {e}")
                    if done_callback:
                        done_callback(False, str(e))

            progress_state = {"done": False}

            def _heartbeat():
                if progress_state["done"]:
                    return
                self.append_system_message("Update download still in progress. Please wait...")
                QTimer.singleShot(60000, _heartbeat)

            self.append_system_message(
                f"Downloading update v{latest}. This can take a few minutes the first time."
            )
            QTimer.singleShot(60000, _heartbeat)
            self._run_in_bg(_fetch, _apply, new_exe)
            return

        # Source-run fallback: just download to a local folder and notify user.
        download_dir = self.settings_path.parent / "downloads"
        output_file = download_dir / f"EncryptedChat-v{latest}.exe"

        def _fetch_source(target_path):
            return self.api_client.download_update_file(str(target_path))

        def _apply_source(result):
            self.set_busy(False)
            success, payload = result if result else (False, "Update download failed")
            if not success:
                self.append_system_message(f"Update download failed: {payload}")
                if done_callback:
                    done_callback(False, payload)
                return
            self.append_system_message(f"Update v{latest} downloaded to {output_file}. Please install manually.")
            if done_callback:
                done_callback(True, payload)

        self._run_in_bg(_fetch_source, _apply_source, output_file)

    @staticmethod
    def _is_hex_color(value: str) -> bool:
        return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", str(value or "").strip()))

    def _sanitize_theme(self, raw_theme: Optional[dict]) -> Dict:
        """Normalize untrusted theme data into a safe, complete theme dict."""
        theme = copy.deepcopy(_THEME_DEFAULTS)
        if not isinstance(raw_theme, dict):
            return theme

        color_keys = {
            "window_bg", "panel_bg", "header_bg", "chat_bg", "input_bg", "border_color",
            "text_color", "button_bg", "button_border", "button_text", "timestamp_color",
            "link_color", "msg_own_name", "msg_other_name", "msg_own_text", "msg_other_text",
            "system_color",
        }
        int_ranges = {
            "font_size": (8, 36),
            "font_weight": (100, 900),
            "widget_radius": (0, 24),
            "button_radius": (0, 24),
            "border_width": (1, 4),
            "timestamp_size": (8, 22),
            "username_weight": (100, 900),
            "message_spacing": (0, 20),
            "image_max_width": (120, 1600),
            "image_max_height": (120, 1200),
            "image_radius": (0, 24),
            "splitter_handle_size": (4, 24),
        }
        available_fonts = set(QFontDatabase.families())

        for key, value in raw_theme.items():
            if key not in theme:
                continue
            if key in color_keys:
                if self._is_hex_color(value):
                    theme[key] = str(value).strip()
                continue
            if key == "font_family":
                font_name = str(value or "").strip()
                theme[key] = font_name if font_name in available_fonts else ""
                continue
            if key == "system_italic":
                theme[key] = bool(value)
                continue
            if key in int_ranges:
                low, high = int_ranges[key]
                try:
                    iv = int(value)
                except Exception:
                    continue
                theme[key] = max(low, min(high, iv))

        return theme

    def _build_stylesheet(self) -> str:
        """Build a QSS stylesheet string from the current theme dict."""
        t = self._theme
        ff = t.get("font_family", "")
        fs = int(t.get("font_size", 13))
        fw = max(100, min(900, int(t.get("font_weight", 600))))
        wr = max(0, int(t.get("widget_radius", 8)))
        br = max(0, int(t.get("button_radius", 8)))
        bw = max(1, int(t.get("border_width", 1)))
        hs = max(4, int(t.get("splitter_handle_size", 8)))
        font_widget = f"font-family: '{ff}';" if ff else ""
        font_text   = (f"font-family: '{ff}';" if ff else "") + f" font-size: {fs}px;"
        hover_btn   = t.get("button_border", "#33547c")
        pressed_btn = t.get("window_bg", "#141a24")
        header_bg = t.get("header_bg", t.get("window_bg", "#141a24"))
        chat_bg = t.get("chat_bg", t.get("panel_bg", "#1d2533"))
        input_bg = t.get("input_bg", t.get("panel_bg", "#1d2533"))
        return f"""
            QMainWindow, QWidget {{
                background-color: {t['window_bg']};
                color: {t['text_color']};
                {font_widget}
            }}
            QWidget#HeaderBar {{
                background-color: {header_bg};
                border-bottom: {bw}px solid {t['border_color']};
            }}
            QLabel#HeaderUserLabel, QLabel#HeaderServerLabel {{
                color: {t['system_color']};
                font-size: 11px;
            }}
            QLabel#SectionLabel {{
                color: {t['text_color']};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#RoomTitleLabel {{
                color: {t['text_color']};
                font-size: 16px;
                font-weight: 700;
                padding: 4px 2px;
            }}
            QListWidget, QTextEdit, QTextBrowser, QLineEdit, QComboBox, QScrollArea {{
                background-color: {t['panel_bg']};
                border: {bw}px solid {t['border_color']};
                border-radius: {wr}px;
                padding: 6px;
                color: {t['text_color']};
                selection-background-color: {t['button_bg']};
                {font_text}
            }}
            QTextBrowser#ChatDisplay {{
                background-color: {chat_bg};
            }}
            QLineEdit#ChatInput {{
                background-color: {input_bg};
            }}
            QTabWidget::pane {{
                background-color: {t['panel_bg']};
                border: {bw}px solid {t['border_color']};
            }}
            QPushButton {{
                background-color: {t['button_bg']};
                border: {bw}px solid {t['button_border']};
                border-radius: {br}px;
                padding: 7px 10px;
                color: {t['button_text']};
                font-weight: {fw};
            }}
            QPushButton:hover {{
                background-color: {hover_btn};
            }}
            QPushButton:pressed {{
                background-color: {pressed_btn};
            }}
            QPushButton#SidebarToggleBtn {{
                min-width: 88px;
            }}
            QSplitter::handle {{
                background-color: {t['border_color']};
                width: {hs}px;
                height: {hs}px;
            }}
            QSplitter::handle:hover {{
                background-color: {t['button_bg']};
            }}
            QScrollBar:vertical {{
                background: {t['window_bg']};
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['button_bg']};
                border-radius: 5px;
            }}
        """

    def _apply_theme(self):
        """Rebuild and apply the QSS stylesheet from current theme settings."""
        self._theme = self._sanitize_theme(self._theme)
        self.setStyleSheet(self._build_stylesheet())
        handle_width = int(self._theme.get("splitter_handle_size", 8))
        for attr in ("main_splitter", "chat_splitter", "chat_area_splitter", "window_splitter"):
            splitter = getattr(self, attr, None)
            if splitter is not None:
                splitter.setHandleWidth(handle_width)

    def apply_dark_theme(self):
        """Apply initial theme (uses persisted or default settings)."""
        self._apply_theme()

    def toggle_sidebar(self):
        """Collapse/expand the left sidebar."""
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.sidebar_widget.setVisible(not self.sidebar_collapsed)
        self.toggle_sidebar_btn.setText("Expand" if self.sidebar_collapsed else "Collapse")

    def _extract_image_urls(self, content: str) -> List[str]:
        if not content:
            return []

        urls = re.findall(
            r'(?:https?://[^\s<>\"]+|/api/files/\d+(?:\?[^\s]*)?)',
            content,
            re.IGNORECASE,
        )

        normalized = []
        for url in urls:
            # Trim punctuation that often trails links in chat text.
            url = url.rstrip('.,);\"]')
            lowered = url.lower()
            is_image_ext = bool(re.search(r"\.(jpg|jpeg|png|gif|webp|bmp)(\?.*)?$", lowered))
            # /api/files links are images only when the message text says [Image].
            is_room_image = ("/api/files/" in lowered and "[image]" in content.lower())
            if not (is_image_ext or is_room_image):
                continue

            if url.startswith("/"):
                normalized.append(f"{self.server_url.rstrip('/')}{url}")
            else:
                normalized.append(url)

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(normalized))

    def _remember_uploaded_image_url(self, payload: dict):
        """Cache upload response so image rendering can recover if live events omit file metadata."""
        if not isinstance(payload, dict):
            return

        message_id = payload.get("message_id")
        file_url = str(payload.get("file_url") or "").strip()
        file_id = payload.get("file_id")

        if not file_url and file_id is not None:
            file_url = f"{self.server_url}/api/files/{file_id}"

        if file_url.startswith("/"):
            file_url = f"{self.server_url.rstrip('/')}{file_url}"
        elif file_url and not file_url.lower().startswith(("http://", "https://")):
            file_url = f"{self.server_url.rstrip('/')}/{file_url.lstrip('/')}"

        if message_id not in (None, "") and file_url:
            try:
                self._uploaded_image_urls_by_message_id[int(message_id)] = file_url
            except Exception:
                pass

    def _extract_attachment_from_message(self, message: dict) -> Optional[Dict]:
        """Extract attachment metadata from API payloads for file download commands."""
        if not isinstance(message, dict):
            return None

        file_id = message.get("file_id")
        file_url = str(message.get("file_url") or "").strip()
        filename = str(message.get("filename") or "").strip()
        msg_type = str(message.get("message_type", "text")).lower()

        if not file_url and file_id is not None:
            file_url = f"{self.server_url}/api/files/{file_id}"
        if file_url.startswith("/"):
            file_url = f"{self.server_url.rstrip('/')}{file_url}"
        elif file_url and not file_url.lower().startswith(("http://", "https://")):
            file_url = f"{self.server_url.rstrip('/')}/{file_url.lstrip('/')}"

        if not file_url:
            return None

        if not filename:
            if file_id is not None:
                filename = f"file_{file_id}"
            else:
                parsed_name = Path(urlparse(file_url).path).name
                filename = parsed_name or "downloaded_file"

        return {
            "file_id": file_id,
            "file_url": file_url,
            "filename": filename,
            "file_type": str(message.get("file_type") or ""),
            "file_size": message.get("file_size"),
            "message_type": msg_type,
        }

    def _find_attachment_by_filename(self, filename: str) -> Optional[Dict]:
        """Find the most recent attachment in current chat view by filename."""
        needle = str(filename or "").strip().lower()
        if not needle:
            return None

        # 1) Exact filename match first.
        for msg in reversed(self._chat_raw_messages):
            attachment = msg.get("attachment") if isinstance(msg, dict) else None
            if not isinstance(attachment, dict):
                continue
            candidate = str(attachment.get("filename") or "").strip().lower()
            if candidate == needle:
                return attachment

        # 2) If no extension provided, match against filename stem.
        needle_stem = Path(needle).stem if "." in needle else needle
        for msg in reversed(self._chat_raw_messages):
            attachment = msg.get("attachment") if isinstance(msg, dict) else None
            if not isinstance(attachment, dict):
                continue
            candidate = str(attachment.get("filename") or "").strip().lower()
            candidate_stem = Path(candidate).stem
            if candidate_stem == needle_stem:
                return attachment

        # 3) Prefix/contains fallback so commands like !download Diablo files work.
        for msg in reversed(self._chat_raw_messages):
            attachment = msg.get("attachment") if isinstance(msg, dict) else None
            if not isinstance(attachment, dict):
                continue
            candidate = str(attachment.get("filename") or "").strip().lower()
            candidate_stem = Path(candidate).stem
            if candidate.startswith(needle) or candidate_stem.startswith(needle_stem):
                return attachment
            if needle in candidate or needle_stem in candidate_stem:
                return attachment
        return None

    def _display_content_from_message(self, message: dict) -> str:
        """Normalize API payload into displayable chat content."""
        content = str(message.get("content", ""))
        msg_type = str(message.get("message_type", "text"))

        if msg_type == "file":
            attachment = self._extract_attachment_from_message(message)
            if attachment:
                file_type = str(attachment.get("file_type") or "").lower()
                filename = str(attachment.get("filename") or "")
                ext = Path(filename).suffix.lower() or ".jpg"
                is_image_file = (
                    file_type.startswith("image/")
                    or ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                )
                if is_image_file:
                    return f"[Image] {attachment.get('file_url')}"
                return f"[File] {attachment.get('filename')}\n{attachment.get('file_url')}"
            return content

        if msg_type != "image":
            return content

        file_url = str(message.get("file_url") or "").strip()
        file_id = message.get("file_id")
        message_id = message.get("id")

        if not file_url and message_id not in (None, ""):
            try:
                file_url = self._uploaded_image_urls_by_message_id.get(int(message_id), "")
            except Exception:
                file_url = ""

        if not file_url:
            rel_match = re.search(r'(/api/files/\d+(?:\?[^\s]*)?)', content, re.IGNORECASE)
            if rel_match:
                file_url = f"{self.server_url.rstrip('/')}{rel_match.group(1)}"

        if file_url and file_url.startswith("/"):
            file_url = f"{self.server_url}{file_url}"
        elif file_url and not file_url.lower().startswith(("http://", "https://")):
            file_url = f"{self.server_url.rstrip('/')}/{file_url.lstrip('/')}"

        if not file_url and file_id is not None:
            file_url = f"{self.server_url}/api/files/{file_id}"

        if file_url:
            return f"[Image] {file_url}"
        return content

    def _save_images_from_chat(self, folder_path: Optional[str] = None) -> tuple:
        """Save all image URLs from currently loaded chat messages to a local folder."""
        if not folder_path:
            folder_path = QFileDialog.getExistingDirectory(self, "Select folder to save images")
            if not folder_path:
                return False, "Canceled"

        target_dir = Path(folder_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        image_urls = []
        for msg in self._chat_raw_messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("msg_type") == "system":
                continue
            content = str(msg.get("content", ""))
            image_urls.extend(self._extract_image_urls(content))

        # Preserve order while removing duplicates.
        unique_urls = list(dict.fromkeys(image_urls))
        if not unique_urls:
            return False, "No image URLs found in current chat view"

        saved_count = 0
        failed_count = 0

        for index, url in enumerate(unique_urls, start=1):
            try:
                parsed = urlparse(url)
                basename = Path(parsed.path).name or f"image_{index}.jpg"
                name = Path(basename).stem or f"image_{index}"
                ext = Path(basename).suffix.lower() or ".jpg"
                if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                    ext = ".jpg"

                file_path = target_dir / f"{index:03d}_{name}{ext}"
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                file_path.write_bytes(response.content)
                saved_count += 1
            except Exception:
                failed_count += 1

        if saved_count == 0:
            return False, "Failed to download images"

        return True, {
            "saved": saved_count,
            "failed": failed_count,
            "folder": str(target_dir),
        }

    def _cache_image_url(self, url: str) -> Optional[str]:
        """Fetch one image, store raw bytes in ChatBrowser resource store, return proxy URI."""
        if url in self._image_cache:
            return self._image_cache[url]

        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()

            import hashlib
            key = "chatimg://" + hashlib.md5(url.encode()).hexdigest()
            ChatBrowser._image_store[key] = response.content
            self._image_cache[url] = key
            return key
        except Exception:
            return None

    def _build_message_body_html(self, content: str, embedded_sources: Optional[Dict[str, str]] = None) -> str:
        """Build message body with text first and images under it, matching Discord-like layout."""
        embedded_sources = embedded_sources or {}
        image_urls = self._extract_image_urls(content)

        text_html = html.escape(content)
        for url in image_urls:
            text_html = text_html.replace(html.escape(url), "")

        text_html = re.sub(r'\n{3,}', '\n\n', text_html).strip()
        text_html = text_html.replace("\n", "<br>")

        # Preserve clickable non-image links inside text.
        link_color = self._theme.get("link_color", "#7fb4ff")
        text_html = re.sub(
            r'(https?://[^\s<]+)',
            f'<a href="\\1" style="color:{link_color};text-decoration:none;word-break:break-all;">\\1</a>',
            text_html,
            flags=re.IGNORECASE,
        )

        images_html = []
        image_w = int(self._theme.get("image_max_width", 420))
        image_h = int(self._theme.get("image_max_height", 320))
        image_r = int(self._theme.get("image_radius", 6))
        for url in image_urls:
            src = embedded_sources.get(url)
            if src:
                images_html.append(
                    f'<img src="{src}" style="max-width:{image_w}px;max-height:{image_h}px;'
                    f'border-radius:{image_r}px;display:block;margin:8px 0;">'
                )
            else:
                images_html.append(
                    f'<a href="{url}" style="color:{link_color};text-decoration:none;word-break:break-all;">{html.escape(url)}</a>'
                )

        if text_html and images_html:
            return f"{text_html}<br>{''.join(images_html)}"
        if images_html:
            return "".join(images_html)
        return text_html

    def _is_presence_system_message(self, content: str, msg_type: str) -> bool:
        """Return True for system presence lines like '<user> is online/offline'."""
        if msg_type != "system":
            return False
        return bool(re.match(r"^.+\s+is\s+(online|offline)$", (content or "").strip(), flags=re.IGNORECASE))

    def _is_duplicate_presence_message(self, content: str, msg_type: str) -> bool:
        """Suppress repeated identical presence lines emitted multiple times in quick succession."""
        if not self._is_presence_system_message(content, msg_type):
            return False

        now = time.time()
        normalized = (content or "").strip().lower()
        is_dup = (
            self._last_presence_message == normalized
            and (now - self._last_presence_at) < 3.0
        )

        self._last_presence_message = normalized
        self._last_presence_at = now
        return is_dup

    def _dedupe_presence_history(self, messages: List[dict]) -> List[dict]:
        """Collapse consecutive duplicate presence system lines in historical message loads."""
        filtered = []
        last_presence_key = None

        for msg in messages:
            msg_type = str(msg.get("message_type", "text"))
            content = str(msg.get("content", "")).strip()

            if self._is_presence_system_message(content, msg_type):
                key = content.lower()
                if key == last_presence_key:
                    continue
                last_presence_key = key
            else:
                last_presence_key = None

            filtered.append(msg)

        return filtered

    def format_message_html(self, username: str, body_html: str, msg_type: str = "text") -> str:
        """Render a styled chat line with timestamp and role-specific colors."""
        timestamp = datetime.now().strftime("%H:%M")
        t = self._theme
        ff = t.get("font_family", "")
        fs = int(t.get("font_size", 13))
        ts = int(t.get("timestamp_size", 11))
        uw = int(t.get("username_weight", 700))
        spacing = int(t.get("message_spacing", 4))
        sys_italic = "italic" if bool(t.get("system_italic", True)) else "normal"
        font_style = (f"font-family:'{ff}';" if ff else "") + f"font-size:{fs}px;"

        if msg_type == "system":
            # Make online/offline presence lines easier to scan.
            plain_body = html.unescape(re.sub(r"<br\s*/?>", "\n", body_html, flags=re.IGNORECASE)).strip()
            presence_match = re.match(r"^(.+?)\s+is\s+(online|offline)$", plain_body, flags=re.IGNORECASE)
            if presence_match:
                presence_user = html.escape(presence_match.group(1).strip())
                presence_state = presence_match.group(2).lower()
                status_color = "#38d16a" if presence_state == "online" else "#ff4d4d"
                return (
                    f'<div style="margin:2px 0;color:{t["system_color"]};font-style:{sys_italic};{font_style}">'
                    f'[{timestamp}] [SYSTEM] '
                    f'<span style="color:#ffffff;">{presence_user}</span> '
                    f'<span style="color:{status_color};">is {presence_state}</span>'
                    f'</div>'
                )

            return (
                f'<div style="margin:2px 0;color:{t["system_color"]};font-style:{sys_italic};{font_style}">'
                f'[{timestamp}] [SYSTEM] {body_html}</div>'
            )

        is_self = username == self.api_client.username
        align = "right" if is_self else "left"
        name_color = t["msg_own_name"] if is_self else t["msg_other_name"]
        text_color = t["msg_own_text"] if is_self else t["msg_other_text"]
        timestamp_color = t.get("timestamp_color", t["system_color"])

        return (
            f'<div style="text-align:{align};margin:{spacing}px 0;">'
            f'<span style="color:{timestamp_color};font-size:{ts}px;">[{timestamp}] </span>'
            f'<span style="color:{name_color};font-weight:{uw};">{username}</span><br>'
            f'<span style="color:{text_color};{font_style}">{body_html}</span>'
            f'</div>'
        )

    def append_chat_message(self, username: str, content: str, msg_type: str = "text", attachment: Optional[Dict] = None):
        """Append one formatted message to the chat display."""
        print(f"[DEBUG] Appending message: username={username!r}, content={content!r}, msg_type={msg_type!r}, attachment={attachment!r}")
        if self._is_duplicate_presence_message(content, msg_type):
            return

        self._chat_raw_messages.append({
            "username": username,
            "content": content,
            "msg_type": msg_type,
            "attachment": attachment,
        })

        # Collect image URLs from both message content and attachment
        image_urls = set(self._extract_image_urls(content))
        if attachment and attachment.get("file_url"):
            file_url = attachment["file_url"]
            file_type = (attachment.get("file_type") or "").lower()
            # Only treat as image if file_type is image/* or file extension is image-like
            if file_type.startswith("image/") or any(file_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]):
                image_urls.add(file_url)

        if msg_type != "system" and image_urls:
            # Show placeholder immediately (preserves message order), then rebuild once image is cached.
            body_html = self._build_message_body_html(content, {})
            self.message_display.append(self.format_message_html(username, body_html, msg_type))

            def _fetch_embeds(message_content, urls):
                sources = {}
                for image_url in urls:
                    uri = self._cache_image_url(image_url)
                    if uri:
                        sources[image_url] = uri
                return bool(sources)

            def _apply(any_loaded):
                if any_loaded:
                    self._schedule_chat_rebuild()

            self._run_in_bg(_fetch_embeds, _apply, content, list(image_urls))
            return

        body_html = self._build_message_body_html(content, {})
        self.message_display.append(self.format_message_html(username, body_html, msg_type))

    def _schedule_chat_rebuild(self):
        """Debounced full-document rebuild — coalesces multiple concurrent image downloads."""
        print(f"[DEBUG] _schedule_chat_rebuild called")
        if not hasattr(self, "_rebuild_timer"):
            self._rebuild_timer = QTimer(self)
            self._rebuild_timer.setSingleShot(True)
            self._rebuild_timer.timeout.connect(self._rebuild_chat_display)
        self._rebuild_timer.start(150)

    def _rebuild_chat_display(self):
        """Rebuild the chat display from _chat_raw_messages using any cached images."""
        print(f"[DEBUG] _rebuild_chat_display called. Message count: {len(self._chat_raw_messages)}")
        scrollbar = self.message_display.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 20
        self.message_display.clear()

        # Pass 1: Collect all image URLs that are not yet cached
        uncached_urls = set()
        for msg in self._chat_raw_messages:
            t = msg.get("msg_type") or msg.get("message_type", "text")
            if t == "system":
                continue
            c = msg.get("content", "")
            urls = self._extract_image_urls(c)
            for url in urls:
                if url not in self._image_cache:
                    uncached_urls.add(url)

        # Fetch/cache any missing images synchronously (history only, not for live messages)
        if uncached_urls:
            print(f"[DEBUG] Caching {len(uncached_urls)} uncached image URLs for history: {uncached_urls}")
            for url in uncached_urls:
                self._cache_image_url(url)

        # Pass 2: Render all messages
        for msg in list(self._chat_raw_messages):
            u = msg.get("username", "Unknown")
            c = msg.get("content", "")
            t = msg.get("msg_type") or msg.get("message_type", "text")
            urls = self._extract_image_urls(c) if t != "system" else []
            sources = {url: self._image_cache[url] for url in urls if url in self._image_cache}
            body_html = self._build_message_body_html(c, sources)
            if urls:
                print(f"[DEBUG] Image message for {u}: urls={urls}, sources={list(sources.keys())}, body_html={body_html}")
            html_line = self.format_message_html(u, body_html, t)
            print(f"[DEBUG] Appending to chat display: {html_line}")
            self.message_display.append(html_line)
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def open_message_link(self, url: QUrl):
        """Open links clicked inside the chat display in the default browser."""
        QDesktopServices.openUrl(url)

    def auto_join_default_room(self):
        """Automatically join the default chat room after login."""
        if self.current_room is not None:
            return

        preferred_item = None
        first_item = self.room_list.item(0) if self.room_list.count() > 0 else None

        for index in range(self.room_list.count()):
            item = self.room_list.item(index)
            if item and item.text().strip().lower() == "room one":
                preferred_item = item
                break

        target_item = preferred_item or first_item
        if target_item:
            self.room_list.setCurrentItem(target_item)
            self.on_room_selected(target_item)
    
    def _run_in_bg(self, fn, callback, *args):
        """Run fn(*args) in a background thread, call callback(result) on the main thread."""
        print("IN _run_in_bg, fn:", fn.__name__, "args:", args)
        worker = WorkerThread(fn, *args)
        worker.result.connect(callback)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def refresh_rooms(self):
        """Refresh list of available rooms (immediate, called after user actions)."""
        def _apply(result):
            if result and result[0]:
                self._update_room_list(result[1])
        self._run_in_bg(self.api_client.list_rooms, _apply)

    def _message_event_key(self, data: dict):
        """Build a stable key for deduplicating repeated live events."""
        message_id = data.get("id")
        if message_id not in (None, -1):
            return ("id", int(message_id))
        return (
            data.get("message_type", "text"),
            data.get("username", "Unknown"),
            data.get("content", ""),
            data.get("created_at", ""),
        )

    def _update_room_list(self, rooms: list):
        """Update the room list widget (safe to call from any thread via signal)."""
        snapshot = [
            (
                room.get("id"),
                room.get("name"),
                bool(room.get("is_private", False)),
                room.get("created_by"),
            )
            for room in rooms
        ]
        if snapshot == self._room_list_snapshot:
            return

        self._room_list_snapshot = snapshot
        selected_room_id = self.current_room
        self.room_list.clear()
        self._rooms_data.clear()
        selected_item = None
        for room in rooms:
            is_private = bool(room.get("is_private", False))
            created_by = room.get("created_by")
            prefix = "🔒 " if is_private else ""
            item = QListWidgetItem(f"{prefix}{room['name']}")
            item.setData(Qt.ItemDataRole.UserRole, room["id"])
            self.room_list.addItem(item)
            if room["id"] == selected_room_id:
                selected_item = item
            self._rooms_data[room["id"]] = {
                "is_private": is_private,
                "created_by": created_by,
                "name": room["name"],
           
    def on_room_selected(self, item):
        """Handle room selection — all network calls run in background."""
        room_id = item.data(Qt.ItemDataRole.UserRole)
        room_name = item.text()

        self.current_room = room_id
        self._room_select_epoch += 1
        epoch = self._room_select_epoch
        self.room_name_label.setText(f"Room: {room_name}")
        self.message_display.clear()
        self._chat_raw_messages.clear()
        self._seen_live_message_keys.clear()
        self.members_list.clear()

        # Stop previous WebSocket immediately (no blocking wait)
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread.wait(1500)
            self.websocket_thread = None

        def _fetch(rid):
            print("IN on_room_selected _fetch, rid:", rid)
            ok_join, _ = self.api_client.join_room(rid)
            if not ok_join:
                print("join_room failed")
                return None
            ok_msgs, messages = self.api_client.get_messages(rid, limit=500)
            ok_mbrs, members = self.api_client.get_room_members(rid)
            print("Fetched messages:", messages)
            print("Fetched members:", members)
            return {
                "messages": messages if ok_msgs else [],
                "members": members if ok_mbrs else [],
            }

        def _apply(result):
            print("IN on_room_selected _apply, result:", result)  # DEBUG: Print result
            if self._room_select_epoch != epoch:
                return  # stale callback — a newer room was selected, discard
            if result is None:
                QMessageBox.warning(self, "Error", "Failed to join room")
                return
            self.message_display.clear()
            self._chat_raw_messages.clear()
            self._seen_live_message_keys.clear()
            deduped_messages = self._dedupe_presence_history(result["messages"])
            for msg in deduped_messages:
                self._seen_live_message_keys.add(self._message_event_key(msg))
                username = msg.get("username", "Unknown")
                msg_type = msg.get("message_type", "text")
                content = self._display_content_from_message(msg)
                attachment = self._extract_attachment_from_message(msg)
                self.append_chat_message(username, content, msg_type, attachment)
            self._schedule_chat_rebuild()  # Ensure UI is rebuilt after loading messages
            self._update_members(result["members"])
            self.connect_websocket()

        print("IN on_room_selected, calling _run_in_bg with room_id:", room_id)
        self._run_in_bg(_fetch, _apply, room_id)

    def load_messages(self):
        """Reload message history for current room in background."""
        if not self.current_room:
            return
        def _fetch(rid):
            ok, msgs = self.api_client.get_messages(rid, limit=500)
            return msgs if ok else []
        def _apply(messages):
            print("Loaded messages:", messages)  # DEBUG: Print loaded messages
            self.message_display.clear()
            self._chat_raw_messages.clear()
            self._seen_live_message_keys.clear()
            # Reset deduplication state so deleted presence messages do not reappear
            self._last_presence_message = None
            self._last_presence_at = 0
            deduped_messages = self._dedupe_presence_history(messages)
            html_lines = []
            for msg in deduped_messages:
                self._seen_live_message_keys.add(self._message_event_key(msg))
                username = msg.get("username", "Unknown")
                msg_type = msg.get("message_type", "text")
                content = self._display_content_from_message(msg)
                attachment = self._extract_attachment_from_message(msg)
                # Build HTML for each message (same as append_chat_message, but do not append)
                image_urls = set(self._extract_image_urls(content))
                if attachment and attachment.get("file_url"):
                    file_url = attachment["file_url"]
                    file_type = (attachment.get("file_type") or "").lower()
                    if file_type.startswith("image/") or any(file_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]):
                        image_urls.add(file_url)
                sources = {url: self._image_cache[url] for url in image_urls if url in self._image_cache}
                body_html = self._build_message_body_html(content, sources)
                html_line = self.format_message_html(username, body_html, msg_type)
                html_lines.append(html_line)
            # Set all messages at once for performance
            self.message_display.setHtml("\n".join(html_lines))
            self._schedule_chat_rebuild()  # Ensure UI is rebuilt after loading messages
        self._run_in_bg(_fetch, _apply, self.current_room)
    
    def send_message(self):
        """Send a message."""
        if not self.current_room:
            QMessageBox.warning(self, "Error", "Please select a room first")
            return
        
        content = self.message_input.text().strip()
        if not content:
            return

        first_token = content.split(maxsplit=1)[0].lower()

        if first_token == "!commands":
            self.show_room_commands()
            self.message_input.clear()
            return

        if first_token == "!clear":
            parts = content.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip().isdigit():
                self.append_system_message("Usage: !clear <count>")
                self.message_input.clear()
                return

            count = int(parts[1].strip())
            if count <= 0:
                self.append_system_message("Usage: !clear <count> (count must be > 0)")
                self.message_input.clear()
                return

            success, result = self.api_client.clear_room_messages(self.current_room, count)
            if not success:
                self.append_system_message(f"Clear failed: {result}")
                self.message_input.clear()
                return

            self.append_system_message(result.get("message", "Messages cleared"))
            self.load_messages()
            self.message_input.clear()
            return

        if first_token == "!saveimages":
            parts = content.split(maxsplit=1)
            folder_arg = parts[1].strip() if len(parts) > 1 else None
            success, result = self._save_images_from_chat(folder_arg)
            if not success:
                self.append_system_message(f"Save images: {result}")
            else:
                self.append_system_message(
                    f"Saved {result['saved']} image(s)"
                    f"{f' ({result['failed']} failed)' if result['failed'] else ''}"
                    f" to {result['folder']}"
                )
            self.message_input.clear()
            return

        if first_token == "!download":
            try:
                parts = shlex.split(content)
            except ValueError:
                self.append_system_message("Usage: !download <filename> <folder_path>")
                self.message_input.clear()
                return

            if len(parts) < 3:
                self.append_system_message("Usage: !download <filename> <folder_path> (quote filename if it has spaces)")
                self.message_input.clear()
                return

            filename = parts[1].strip()
            folder_path = " ".join(parts[2:]).strip()
            if not filename or not folder_path:
                self.append_system_message("Usage: !download <filename> <folder_path> (quote filename if it has spaces)")
                self.message_input.clear()
                return

            self.download_attachment_by_name(filename, folder_path)
            self.message_input.clear()
            return

        if content.startswith("!botcommand") or content.startswith("!botcommands"):
            self.show_bot_commands()
            self.message_input.clear()
            return

        if content.startswith("!room") or content.startswith("!createroom") or content.startswith("!removeroom") or content.startswith("!rooms") or content.startswith("!makeprivate") or content.startswith("!invite") or content.startswith("!leaveroom"):
            self.handle_room_command(content)
            self.message_input.clear()
            return

        if content.startswith("!bot") or content.startswith("!"):
            self.handle_bot_command(content)
            self.message_input.clear()
            return
        
        if self.websocket_thread and self.websocket_thread.client:
            self.websocket_thread.send_message(content)
            self.message_input.clear()
        else:
            QMessageBox.warning(self, "Error", "Not connected to chat server")

    def append_system_message(self, text: str):
        """Append a local system message to the chat window."""
        self.append_chat_message("SYSTEM", text, "system")

    def show_room_commands(self):
        """Display all room commands."""
        commands = [
            "Room Commands:",
            "!rooms - List all available rooms",
            "!createroom <name> [private] - Create a new room",
            "!removeroom <name|id> - Delete a room (creator-only)",
            "!makeprivate - Make current room private (creator-only)",
            "!invite <username> <room_name|id> - Invite user to room (creator-only)",
            "!leaveroom [room_name|id] - Leave a room (current room if omitted)",
            "Invite flow: invited users accept/decline through in-app popup",
            "!clear <count> - Clear recent non-system messages in this room",
            "!saveimages [folder_path] - Save all image URLs currently visible in chat to a folder",
            "!download <filename> <folder_path> - Download an uploaded file from current chat",
            "!room clear <count> - Alias for clearing recent room messages",
            "!botcommands - Show bot command list",
            "/room list - List available rooms",
            "/room create <name> [private] - Create a new room",
            "/room delete <name|id> - Delete a room",
            "/room makeprivate - Make current room private"
        ]
        self.append_system_message(" | ".join(commands))

    def show_bot_commands(self):
        """Display all bot commands."""
        commands = [
            "Bot Commands:",
            "!start <seconds> [tags] - Start image streaming",
            "!pause - Pause the stream",
            "!resume - Resume the stream",
            "!stop - Stop the stream",
            "!status - Show stream status",
            "!addtags <tag1,tag2> - Add tags to saved pool",
            "!removetags <tag1,tag2|count> - Remove named tags or first N tags from taglist",
            "!taglist - Show saved tags",
            "!cleartags - Clear all saved tags",
            "!botcommands - Show this bot command list",
            "!bot search <tags> - Search for images",
            "!searchtags <query> - Detailed tag search (botUpdated-style)",
            "!bot image <tags> - Fetch single image",
            "!bot blacklist show|add|remove|clear - Manage blacklist"
        ]
        self.append_system_message(" | ".join(commands))

    def handle_bot_command(self, raw_command: str):
        """Handle !bot and Discord-like ! commands typed in chat input."""
        cmd = raw_command.strip()

        # Local-only utility command: never send to server/room.
        if cmd.lower().startswith("!bot saveimages"):
            parts = cmd.split(maxsplit=2)
            folder_arg = parts[2].strip() if len(parts) > 2 else None
            success, result = self._save_images_from_chat(folder_arg)
            if not success:
                self.append_system_message(f"Save images: {result}")
            else:
                failed_suffix = f" ({result['failed']} failed)" if result.get("failed") else ""
                self.append_system_message(
                    f"Saved {result['saved']} image(s){failed_suffix} to {result['folder']}"
                )
            return

        if cmd.startswith("!") and not cmd.lower().startswith("!bot"):
            bang_parts = cmd[1:].split(maxsplit=2)
            if not bang_parts:
                self.append_system_message("Unknown bot command. Use !help")
                return

            bang_action = bang_parts[0].lower()
            bang_rest = ""
            if len(bang_parts) >= 2:
                bang_rest = bang_parts[1] if len(bang_parts) == 2 else f"{bang_parts[1]} {bang_parts[2]}"

            if bang_action == "help":
                self.append_system_message(
                    "Discord-style commands: !start <seconds> [tags] | !pause | !resume | !stop | !status | !commands | "
                    "!addtags <tag1,tag2> | !removetags <tag1,tag2|count> | !taglist | !cleartags | "
                    "!blacklist [list|add <tags>|remove <tags>|clear] | !saveimages [folder_path]"
                )
                return

            if bang_action == "taglist":
                taglist_arg = bang_rest.strip()
                if not taglist_arg or taglist_arg.lower() == "list":
                    self.handle_bot_command("!bot tags list")
                    return

                tag_parts = taglist_arg.split(maxsplit=1)
                tag_action = tag_parts[0].lower()
                tag_payload = tag_parts[1].strip() if len(tag_parts) > 1 else ""

                if tag_action == "clear":
                    self.handle_bot_command("!bot tags clear")
                    return

                if tag_action in {"add", "addtags", "remove", "removetags"}:
                    if not tag_payload:
                        self.append_system_message("Usage: !taglist add|addtags <tags> | !taglist remove|removetags <tags>|<count> | !taglist clear")
                        return
                    normalized_action = "add" if tag_action in {"add", "addtags"} else "remove"
                    self.handle_bot_command(f"!bot tags {normalized_action} {tag_payload}")
                    return

                self.append_system_message("Usage: !taglist [list|add|addtags <tags>|remove|removetags <tags>|<count>|clear]")
                return

            shorthand_map = {
                "start":      lambda: self.handle_bot_command(f"!bot start {bang_rest}".strip()),
                "stop":       lambda: self.handle_bot_command("!bot stop"),
                "pause":      lambda: self.handle_bot_command("!bot pause"),
                "resume":     lambda: self.handle_bot_command("!bot resume"),
                "status":     lambda: self.handle_bot_command("!bot status"),
                "commands":   lambda: self.handle_bot_command("!bot commands"),
                "botcommand": lambda: self.handle_bot_command("!bot commands"),
                "botcommands": lambda: self.handle_bot_command("!bot commands"),
                "addtags":    lambda: self.handle_bot_command(f"!bot tags add {bang_rest}".strip()),
                "removetags": lambda: self.handle_bot_command(f"!bot tags remove {bang_rest}".strip()),
                "taglist":    lambda: self.handle_bot_command("!bot tags list"),
                "cleartags":  lambda: self.handle_bot_command("!bot tags clear"),
                "saveimages": lambda: self.handle_bot_command(f"!bot saveimages {bang_rest}".strip()),
                "search":     lambda: self.handle_bot_command(f"!bot search {bang_rest}".strip()),
                "searchtags": lambda: self.handle_bot_command(f"!bot searchtags {bang_rest}".strip()),
                "image":      lambda: self.handle_bot_command(f"!bot image {bang_rest}".strip()),
                "blacklist":  lambda: self.handle_bot_command(f"!bot blacklist {bang_rest}".strip()),
                "tags":       lambda: self.handle_bot_command(f"!bot tags {bang_rest}".strip()),
            }

            if bang_action in shorthand_map:
                shorthand_map[bang_action]()
                return

            self.append_system_message(
                "Unknown command. Available: !start !stop !pause !resume !status "
                "!search !searchtags !image !addtags !removetags !taglist !cleartags !blacklist !saveimages !botcommands"
            )
            return

        parts = cmd.split(maxsplit=2)
        if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() in {"help", "commands"}):
            self.append_system_message(
                "Bot commands: !bot start <seconds> [tags] | !bot pause | !bot resume | !bot stop | !bot status | !bot commands | "
                "!bot search <query> | !bot searchtags <query> | !bot image <tags> | "
                "!bot tags list|add <tags>|remove <tags>|clear | "
                "!bot blacklist show | !bot blacklist add <tag1,tag2> | !bot blacklist remove <tag1,tag2> | !bot blacklist clear"
            )
            return

        if len(parts) < 2:
            self.append_system_message("Invalid bot command. Use !bot help")
            return

        action = parts[1].lower()
        arg = parts[2].strip() if len(parts) > 2 else ""

        def _run_bot_request(api_fn, on_success, error_prefix: str, *api_args):
            def _apply(result):
                success, payload = result if result else (False, "Request failed")
                if not success:
                    self.append_system_message(f"{error_prefix}: {payload}")
                    return
                on_success(payload)

            self._run_in_bg(api_fn, _apply, *api_args)

        if action == "start":
            if not self.current_room:
                self.append_system_message("Join a room first before starting bot stream.")
                return

            if not arg:
                self.append_system_message("Usage: !bot start <seconds> [tags]")
                return

            start_parts = arg.split(maxsplit=1)

            try:
                interval = float(start_parts[0])
            except ValueError:
                self.append_system_message("Interval must be a number. Example: !bot start 10 cat_girl")
                return

            tags = start_parts[1].strip() if len(start_parts) > 1 else None

            def _start_success(result):
                mode = result.get("mode", "?")
                pool = result.get("tag_pool", [])
                self.append_system_message(
                    f"Bot stream started: every {interval:g}s | mode: {mode} | tags: {', '.join(pool) if pool else 'rating:explicit'}"
                )

            _run_bot_request(
                self.api_client.start_bot_stream,
                _start_success,
                "Failed to start stream",
                self.current_room,
                interval,
                tags,
            )
            return

        if action == "stop":
            if not self.current_room:
                self.append_system_message("Join a room first before stopping bot stream.")
                return
            _run_bot_request(
                self.api_client.stop_bot_stream,
                lambda _result: self.append_system_message("Bot stream stopped."),
                "Failed to stop stream",
                self.current_room,
            )
            return

        if action == "pause":
            if not self.current_room:
                self.append_system_message("Join a room first before pausing bot stream.")
                return
            _run_bot_request(
                self.api_client.pause_bot_stream,
                lambda _result: self.append_system_message("Bot stream paused."),
                "Failed to pause stream",
                self.current_room,
            )
            return

        if action == "resume":
            if not self.current_room:
                self.append_system_message("Join a room first before resuming bot stream.")
                return
            _run_bot_request(
                self.api_client.resume_bot_stream,
                lambda _result: self.append_system_message("Bot stream resumed."),
                "Failed to resume stream",
                self.current_room,
            )
            return

        if action == "status":
            if not self.current_room:
                self.append_system_message("Join a room first before checking bot stream status.")
                return

            def _status_success(result):
                if result.get("running"):
                    cfg = result.get("config") or {}
                    self.append_system_message(
                        f"Bot stream running: every {cfg.get('interval', '?')}s | mode: {cfg.get('mode', '?')} | "
                        f"tags: {', '.join(cfg.get('tag_pool', [])) if cfg.get('tag_pool') else 'rating:explicit'}"
                    )
                elif result.get("paused"):
                    cfg = result.get("config") or {}
                    self.append_system_message(
                        f"Bot stream paused: every {cfg.get('interval', '?')}s | mode: {cfg.get('mode', '?')} | "
                        f"tags: {', '.join(cfg.get('tag_pool', [])) if cfg.get('tag_pool') else 'rating:explicit'}"
                    )
                else:
                    self.append_system_message("Bot stream is not running in this room.")

            _run_bot_request(
                self.api_client.bot_stream_status,
                _status_success,
                "Failed to get stream status",
                self.current_room,
            )
            return

        if action == "tags":
            tags_parts = arg.split(maxsplit=1) if arg else []
            tags_action = tags_parts[0].lower() if tags_parts else ""
            tags_arg = tags_parts[1].strip() if len(tags_parts) > 1 else ""

            if tags_action == "list":
                def _list_tags_success(result):
                    saved = result.get("saved_tags", [])
                    self.append_system_message(
                        f"Saved tags ({len(saved)}): {', '.join(saved) if saved else 'empty'}"
                    )

                _run_bot_request(
                    self.api_client.get_saved_tags,
                    _list_tags_success,
                    "Failed to fetch saved tags",
                )
                return

            if tags_action == "add" and tags_arg:
                _run_bot_request(
                    self.api_client.add_saved_tags,
                    lambda result: self.append_system_message(
                        f"Added tags: {result.get('added', 0)} | Saved total: {len(result.get('saved_tags', []))}"
                    ),
                    "Failed to add tags",
                    tags_arg,
                )
                return

            if tags_action == "remove" and tags_arg:
                _run_bot_request(
                    self.api_client.remove_saved_tags,
                    lambda result: self.append_system_message(
                        f"Removed tags: {result.get('removed', 0)} | Saved total: {len(result.get('saved_tags', []))}"
                    ),
                    "Failed to remove tags",
                    tags_arg,
                )
                return

            if tags_action == "clear":
                _run_bot_request(
                    self.api_client.clear_saved_tags,
                    lambda result: self.append_system_message(
                        f"Cleared saved tags. Removed: {result.get('removed', 0)}"
                    ),
                    "Failed to clear tags",
                )
                return

            self.append_system_message("Usage: !bot tags list|add <tags>|remove <tags>|clear")
            return

        if not arg and action in {"search", "searchtags", "image"}:
            self.append_system_message("Invalid bot command. Use !bot help")
            return

        if action in {"search", "searchtags"}:

            def _search_success(result):
                combined = result.get("combined", [])
                if not combined:
                    self.append_system_message(f"No tags found for '{result.get('query', arg)}'.")
                    return

                query_tag = result.get("query", arg.strip().lower().replace(" ", "_"))

                combined_sorted = sorted(
                    combined,
                    key=lambda item: (-int(item.get("count", 0) or 0), str(item.get("name", "")))
                )
                exact_match = next((item for item in combined_sorted if item.get("name") == query_tag), None)
                remaining = [item for item in combined_sorted if item.get("name") != query_tag]
                exact_count = int(exact_match.get("count", 0) or 0) if exact_match else 0
                exact_entry = {
                    "name": query_tag,
                    "count": exact_count,
                    "rule34_count": int((result.get("rule34") or {}).get(query_tag, 0) or 0),
                    "danbooru_count": int((result.get("danbooru") or {}).get(query_tag, 0) or 0),
                }
                ordered = [exact_entry] + remaining
                total_combined = sum(int(item.get("count", 0) or 0) for item in combined_sorted)

                self.append_system_message(
                    f"Tag Search: {query_tag} | Combined Image Count (R34+Danbooru): {total_combined} | "
                    f"Exact Tag Images: {exact_count} | Rule34: {len(result.get('rule34', {}))} | "
                    f"Danbooru: {len(result.get('danbooru', {}))} | Listed Tags: {len(combined_sorted)}"
                )

                entries = [f"{item.get('name')}({int(item.get('count', 0) or 0)})" for item in ordered]
                chunk = ""
                for entry in entries:
                    candidate = f"{chunk}, {entry}" if chunk else entry
                    if len(candidate) > 1400:
                        self.append_system_message(chunk)
                        chunk = entry
                    else:
                        chunk = candidate
                if chunk:
                    self.append_system_message(chunk)

            _run_bot_request(self.api_client.search_tags, _search_success, "Bot search failed", arg)
            return

        if action == "image":

            def _image_success(result):
                images = result.get("images", [])
                if not images:
                    self.append_system_message(f"No images found for tags '{arg}'.")
                    return

                image_url = images[0].get("url")
                image_tags = images[0].get("tags", "")
                if not image_url:
                    self.append_system_message("Bot returned an image without URL.")
                    return

                pretty_tags = image_tags if image_tags else "(no tags)"
                payload = f"Tags: {pretty_tags}\n{image_url}"

                if self.websocket_thread and self.websocket_thread.client:
                    self.websocket_thread.send_message(payload)
                    self.append_system_message("Bot image sent to room.")
                else:
                    self.append_system_message(payload)

            _run_bot_request(self.api_client.fetch_bot_images, _image_success, "Bot image fetch failed", arg, 1)
            return

        if action == "blacklist":
            bl_parts = arg.split(maxsplit=1)
            bl_action = bl_parts[0].lower() if bl_parts else "list"
            bl_tags = bl_parts[1].strip() if len(bl_parts) > 1 else ""

            if bl_action in {"show", "list"}:
                _run_bot_request(
                    self.api_client.get_bot_blacklist,
                    lambda result: self.append_system_message(
                        f"Bot blacklist ({len(result.get('blacklist', []))}): {', '.join(result.get('blacklist', [])) if result.get('blacklist', []) else 'empty'}"
                    ),
                    "Failed to fetch blacklist",
                )
                return

            if bl_action == "add" and bl_tags:
                _run_bot_request(
                    self.api_client.add_bot_blacklist,
                    lambda result: self.append_system_message(
                        f"Added blacklist tags. Total: {len(result.get('blacklist', []))}"
                    ),
                    "Failed to add blacklist tags",
                    bl_tags,
                )
                return

            if bl_action == "remove" and bl_tags:
                _run_bot_request(
                    self.api_client.remove_bot_blacklist,
                    lambda result: self.append_system_message(
                        f"Removed blacklist tags. Total: {len(result.get('blacklist', []))}"
                    ),
                    "Failed to remove blacklist tags",
                    bl_tags,
                )
                return

            if bl_action == "clear":
                _run_bot_request(
                    self.api_client.clear_bot_blacklist,
                    lambda result: self.append_system_message(
                        f"Cleared blacklist tags. Removed: {result.get('removed', 0)}"
                    ),
                    "Failed to clear blacklist tags",
                )
                return

            self.append_system_message("Usage: !bot blacklist show|add <tags>|remove <tags>|clear")
            return

        self.append_system_message("Unknown bot command. Use !bot help")

    def handle_room_command(self, raw_command: str):
        """Handle room creation/deletion commands from chat input."""
        cmd = raw_command.strip()

        if cmd.startswith("!leaveroom"):
            rest = cmd[len("!leaveroom"):].strip()

            target_room_id = None
            if not rest:
                target_room_id = self.current_room
            elif rest.isdigit():
                target_room_id = int(rest)
            else:
                normalized = rest.lower()
                for rid, info in self._rooms_data.items():
                    if str(info.get("name", "")).strip().lower() == normalized:
                        target_room_id = int(rid)
                        break

            if not target_room_id:
                self.append_system_message("Usage: !leaveroom [room_name_or_id]")
                return

            def _apply_leave(result):
                success, payload = result if result else (False, "Request failed")
                if not success:
                    self.append_system_message(f"Leave room failed: {payload}")
                    return

                self.append_system_message(payload.get("message", "Left room successfully"))

                if self.current_room == target_room_id:
                    if self.websocket_thread:
                        self.websocket_thread.stop()
                        self.websocket_thread.wait(1500)
                        self.websocket_thread = None
                    self.current_room = None
                    self.room_name_label.setText("Select a room")
                    self.message_display.clear()
                    self.members_list.clear()
                    self._chat_raw_messages.clear()
                    self._seen_live_message_keys.clear()

                self.refresh_rooms()

            self._run_in_bg(self.api_client.leave_room, _apply_leave, target_room_id)
            return

        if cmd.startswith("!makeprivate"):
            if not self.current_room:
                self.append_system_message("Join a room first, then run !makeprivate")
                return

            room_id = self.current_room

            def _apply_make_private(result):
                success, payload = result if result else (False, "Request failed")
                if not success:
                    self.append_system_message(f"Make private failed: {payload}")
                    return

                self.append_system_message(payload.get("message", "Room is now private"))
                self.refresh_rooms()

            self._run_in_bg(self.api_client.make_room_private, _apply_make_private, room_id)
            return

        if cmd.startswith("!invite"):
            rest = cmd[len("!invite"):].strip()
            if not rest:
                self.append_system_message("Usage: !invite <username> <room_name_or_id>")
                return

            try:
                args = shlex.split(rest)
            except ValueError:
                self.append_system_message("Invite failed: invalid quoting in command.")
                return

            if not args:
                self.append_system_message("Usage: !invite <username> <room_name_or_id>")
                return

            username = args[0].strip()
            room_selector = " ".join(args[1:]).strip() if len(args) > 1 else ""

            if not username:
                self.append_system_message("Usage: !invite <username> <room_name_or_id>")
                return

            # Backward compatibility: !invite <username> uses current room.
            if not room_selector:
                if not self.current_room:
                    self.append_system_message("Join a room first, then run !invite <username> <room_name_or_id>")
                    return
                room_id = self.current_room
            else:
                room_id = None
                if room_selector.isdigit():
                    room_id = int(room_selector)
                else:
                    normalized_room = room_selector.lower()
                    for rid, info in self._rooms_data.items():
                        room_name = str(info.get("name", "")).strip().lower()
                        if room_name == normalized_room:
                            room_id = int(rid)
                            break
                if room_id is None:
                    self.append_system_message(f"Invite failed: room not found '{room_selector}'. Use !rooms to list room names/ids.")
                    return

            def _apply_invite(result):
                success, payload = result if result else (False, "Request failed")
                if not success:
                    self.append_system_message(f"Invite failed: {payload}")
                    return
                self.append_system_message(payload.get("message", f"Invited {username}"))

            self._run_in_bg(self.api_client.invite_user, _apply_invite, room_id, username)
            return

        if cmd.startswith("!rooms"):
            def _apply_rooms(result):
                success, rooms = result if result else (False, [])
                if not success:
                    self.append_system_message("Failed to fetch room list.")
                    return

                if not rooms:
                    self.append_system_message("No rooms available.")
                    return

                lines = []
                for room in rooms:
                    visibility = "private" if room.get("is_private") else "public"
                    lines.append(f"{room.get('id')}: {room.get('name')} ({visibility})")

                self.append_system_message("Rooms: " + " | ".join(lines))

            self._run_in_bg(self.api_client.list_rooms, _apply_rooms)
            return

        if cmd.startswith("!createroom"):
            rest = cmd[len("!createroom"):].strip()
            if not rest:
                self.append_system_message("Usage: !createroom <room name> [private]")
                return

            is_private = False
            if rest.lower().endswith(" private"):
                is_private = True
                rest = rest[:-8].strip()

            if not rest:
                self.append_system_message("Usage: !createroom <room name> [private]")
                return

            room_name = rest

            def _apply_create_room(result):
                success, payload = result if result else (False, "Request failed")
                if success:
                    QMessageBox.information(self, "Success", "Room created")
                    self.refresh_rooms()
                else:
                    QMessageBox.critical(self, "Error", str(payload))

            self._run_in_bg(self.api_client.create_room, _apply_create_room, room_name, is_private)
            return

        if cmd.startswith("!removeroom"):
            rest = cmd[len("!removeroom"):].strip()
            if not rest:
                self.append_system_message("Usage: !removeroom <room name or room id>")
                return

            target_room_id = None

            def _fetch_delete_room(target):
                target_room_id = None
                if target.isdigit():
                    target_room_id = int(target)
                else:
                    ok, rooms = self.api_client.list_rooms()
                    if ok:
                        for room in rooms:
                            if room.get("name", "").strip().lower() == target.lower():
                                target_room_id = room.get("id")
                                break

                if not target_room_id:
                    return False, {"error": f"Room not found: {target}"}

                success, payload = self.api_client.delete_room(target_room_id)
                return success, {
                    "room_id": target_room_id,
                    "payload": payload,
                }

            def _apply_delete_room(result):
                success, payload = result if result else (False, {"error": "Request failed"})
                if not success:
                    error_text = payload.get("error") if isinstance(payload, dict) else payload
                    self.append_system_message(f"Remove room failed: {error_text}")
                    return

                target_room_id = payload.get("room_id")
                self.append_system_message(f"Room removed (id={target_room_id}).")

                if self.current_room == target_room_id:
                    self.current_room = None
                    self.room_name_label.setText("Select a room")
                    self.message_display.clear()
                    self.members_list.clear()
                    if self.websocket_thread:
                        self.websocket_thread.stop()
                        self.websocket_thread.wait(1500)
                        self.websocket_thread = None

                self.refresh_rooms()

            self._run_in_bg(_fetch_delete_room, _apply_delete_room, rest)
            return

        if cmd.startswith("!room"):
            parts = cmd.split(maxsplit=3)
            if len(parts) < 2:
                self.append_system_message("Room commands: !room list | !room create <name> [private] | !room delete <name|id> | !room makeprivate | !room clear <count>")
                return

            action = parts[1].lower()
            if action == "list":
                self.handle_room_command("!rooms")
                return

            if action == "create":
                if len(parts) < 3:
                    self.append_system_message("Usage: !room create <name> [private]")
                    return
                room_part = " ".join(parts[2:]).strip()
                self.handle_room_command(f"!createroom {room_part}")
                return

            if action == "makeprivate":
                self.handle_room_command("!makeprivate")
                return

            if action == "clear":
                if len(parts) < 3:
                    self.append_system_message("Usage: !room clear <count>")
                    return
                self.send_room_clear(parts[2].strip())
                return

            if action in {"delete", "remove"}:
                if len(parts) < 3:
                    self.append_system_message("Usage: !room delete <name|id>")
                    return
                room_part = " ".join(parts[2:]).strip()
                self.handle_room_command(f"!removeroom {room_part}")
                return

            self.append_system_message("Room commands: !room list | !room create <name> [private] | !room delete <name|id> | !room makeprivate | !room clear <count>")
            return

        self.append_system_message("Unknown room command. Use !createroom or !removeroom")

    def send_room_clear(self, count_text: str):
        """Execute room clear command from shared parser path."""
        if not count_text.isdigit():
            self.append_system_message("Usage: !clear <count>")
            return
        count = int(count_text)
        if count <= 0:
            self.append_system_message("Usage: !clear <count> (count must be > 0)")
            return
        success, result = self.api_client.clear_room_messages(self.current_room, count)
        if not success:
            self.append_system_message(f"Clear failed: {result}")
            return
        self.append_system_message(result.get("message", "Messages cleared"))
        self.load_messages()

    def download_attachment_by_name(self, filename: str, folder_path: str):
        """Download the most recent attachment in chat matching filename."""
        attachment = self._find_attachment_by_filename(filename)
        if not attachment:
            self.append_system_message(f"Download failed: file not found in current chat view: {filename}")
            return

        target_dir = Path(folder_path)
        target_file = target_dir / attachment.get("filename", filename)

        def _apply_download(result):
            success, payload = result if result else (False, "Download failed")
            if not success:
                self.append_system_message(f"Download failed: {payload}")
                return
            self.append_system_message(f"Downloaded file: {target_file}")

        self._run_in_bg(
            self.api_client.download_file_from_url,
            _apply_download,
            attachment.get("file_url", ""),
            str(target_file),
        )
    
    def upload_file_dialog(self):
        """Upload any file type to the current room."""
        if not self.current_room:
            QMessageBox.warning(self, "Error", "Please select a room first")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Files (*)"
        )
        if file_path:
            room_id = self.current_room

            def _fetch_upload(rid, path):
                return self.api_client.upload_file(rid, path)


            def _apply_upload(result):
                success, payload = result if result else (False, "Upload failed")
                if success:
                    self._remember_uploaded_image_url(payload)
                    uploaded_name = str(payload.get("filename") or Path(file_path).name)
                    # Immediately append the uploaded message to the chat
                    msg_type = payload.get("message_type", "file")
                    username = self.api_client.username or "You"
                    content = payload.get("content") or ("[Image]" if msg_type == "image" else f"[File] {uploaded_name}")
                    attachment = {
                        "file_id": payload.get("file_id"),
                        "file_url": payload.get("file_url"),
                        "filename": uploaded_name,
                        "file_type": payload.get("file_type"),
                        "file_size": payload.get("file_size"),
                        "message_type": msg_type,
                    }
                    self.append_chat_message(username, content, msg_type, attachment)
                    QMessageBox.information(self, "Success", f"File uploaded: {uploaded_name}")
                    if room_id == self.current_room:
                        self.load_messages()
                else:
                    QMessageBox.critical(self, "Error", f"Upload failed: {payload}")

            self._run_in_bg(_fetch_upload, _apply_upload, room_id, file_path)
    
    def connect_websocket(self):
        """Connect to WebSocket for real-time messaging."""
        if not self.current_room:
            return
        
        # Stop any existing connection before creating a new one
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread.wait(1500)
            self.websocket_thread = None

        self.websocket_thread = WebSocketThread(
            self.server_url,
            self.api_client.token,
            self.current_room
        )
        
        self.websocket_thread.message_received.connect(self.on_message_received)
        self.websocket_thread.user_joined.connect(self.on_user_joined)
        self.websocket_thread.user_left.connect(self.on_user_left)
        self.websocket_thread.typing_received.connect(self.on_typing)
        self.websocket_thread.message_deleted.connect(self.on_message_deleted)
        self.websocket_thread.start()
    
    def on_message_received(self, data: dict):
        """Handle received message."""
        event_room_id = data.get("room_id")
        if event_room_id is not None and event_room_id != self.current_room:
            return

        message_key = self._message_event_key(data)
        if message_key in self._seen_live_message_keys:
            return
        self._seen_live_message_keys.add(message_key)

        username = data.get("username", "Unknown")
        msg_type = data.get("message_type", "text")
        content = self._display_content_from_message(data)
        attachment = self._extract_attachment_from_message(data)

        self.append_chat_message(username, content, msg_type, attachment)
        
        # Only notify (sound) for messages from other users
        if username != self.api_client.username:
            self.notification_handler.notify_message_received(username, content[:50])
    
    def on_user_joined(self, data: dict):
        """Handle user joined and refresh member list."""
        username = data.get("username", "Unknown")
        self.append_chat_message("SYSTEM", f"{username} has joined the room", "system")
        self.append_chat_message("SYSTEM", f"{username} is online", "system")
        if username != self.api_client.username:
            self.notification_handler.notify_user_joined(username)
        self.refresh_members()
    
    def on_user_left(self, data: dict):
        """Handle user left."""
        username = data.get("username", "Unknown")
        self.append_chat_message("SYSTEM", f"{username} has left the room", "system")
        self.append_chat_message("SYSTEM", f"{username} is offline", "system")
        self.notification_handler.notify_user_left(username)
        self.refresh_members()
    
    def on_typing(self, data: dict):
        """Handle typing indicator."""
        pass  # Could show "User is typing..."

    def on_message_deleted(self, data: dict):
        """Handle message deletion broadcast by reloading room history."""
        self.load_messages()
    
    def _update_members(self, members: list):
        """Update the members list widget (must be called on main thread)."""
        self.members_list.clear()
        for member in members:
            self.members_list.addItem(QListWidgetItem(member["username"]))

    def refresh_members(self):
        """Refresh room members list in background."""
        if not self.current_room:
            return
        def _fetch(rid):
            ok, mbrs = self.api_client.get_room_members(rid)
            return mbrs if ok else []
        self._run_in_bg(_fetch, self._update_members, self.current_room)
    
    def create_room(self):
        """Create a new room."""
        room_name, ok = QInputDialog.getText(self, "Create Room", "Room name:")
        if ok and room_name:
            def _apply_create(result):
                success, payload = result if result else (False, "Request failed")
                if success:
                    QMessageBox.information(self, "Success", "Room created")
                    self.refresh_rooms()
                else:
                    QMessageBox.critical(self, "Error", str(payload))

            self._run_in_bg(self.api_client.create_room, _apply_create, room_name)
    
    def join_room_dialog(self):
        """Show dialog to join another room."""
        # Could be enhanced with a more sophisticated dialog
        pass
    
    def show_settings(self):
        """Show settings dialog with Notifications and Appearance tabs."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(520)
        outer = QVBoxLayout()

        tabs = QTabWidget()

        # ── Tab 1: Notifications ──────────────────────────────────────────────
        notif_widget = QWidget()
        notif_layout = QVBoxLayout()
        notif_layout.addWidget(QLabel("Notifications:"))

        sound_checkbox = QPushButton("Toggle Sound")
        sound_checkbox.clicked.connect(self._toggle_notification_sound)
        notif_layout.addWidget(sound_checkbox)

        custom_sound_btn = QPushButton("Set Custom Message Sound")
        custom_sound_btn.clicked.connect(self._pick_custom_sound)
        notif_layout.addWidget(custom_sound_btn)

        clear_custom_sound_btn = QPushButton("Clear Custom Sound")
        clear_custom_sound_btn.clicked.connect(self._clear_custom_sound)
        notif_layout.addWidget(clear_custom_sound_btn)

        test_sound_btn = QPushButton("Test Notification Sound")
        test_sound_btn.clicked.connect(self.notification_handler.play_sound)
        notif_layout.addWidget(test_sound_btn)
        notif_layout.addStretch()
        notif_widget.setLayout(notif_layout)
        tabs.addTab(notif_widget, "Notifications")

        # ── Tab 2: Updates ──────────────────────────────────────────────────
        updates_widget = QWidget()
        updates_layout = QVBoxLayout()
        updates_layout.addWidget(QLabel(f"Current client version: v{CLIENT_VERSION}"))

        update_status_label = QLabel("Checking status: not checked yet")
        update_status_label.setWordWrap(True)
        updates_layout.addWidget(update_status_label)

        check_updates_btn = QPushButton("Check for Updates")
        install_update_btn = QPushButton("Download && Install Update")
        updates_layout.addWidget(check_updates_btn)
        updates_layout.addWidget(install_update_btn)
        updates_layout.addStretch()

        def _render_update_status(success=None, payload=None):
            info = payload if isinstance(payload, dict) else self._pending_update_info
            if success is False and payload is not None and not isinstance(payload, dict):
                update_status_label.setText(f"Update check failed: {payload}")
                return
            if not isinstance(info, dict) or not info:
                update_status_label.setText("Checking status: not checked yet")
                return

            if info.get("configured") is False:
                update_status_label.setText("Updates are not configured on this server.")
                return

            latest = str(info.get("latest_version", "unknown"))
            if info.get("update_available"):
                update_status_label.setText(
                    f"New version available: v{latest}. Press 'Download && Install Update' to apply it."
                )
            else:
                update_status_label.setText(f"You are up to date (v{CLIENT_VERSION}).")

        def _on_check_click():
            update_status_label.setText("Checking for updates...")
            self.check_for_updates(manual=True, done_callback=_render_update_status)

        def _on_install_click():
            if not self._pending_update_info.get("update_available"):
                self.append_system_message("No update available to install.")
                _render_update_status(True, self._pending_update_info)
                return
            update_status_label.setText("Downloading update from server...")
            self.install_update_from_server(done_callback=lambda s, p: _render_update_status(s, self._pending_update_info))

        check_updates_btn.clicked.connect(_on_check_click)
        install_update_btn.clicked.connect(_on_install_click)
        _render_update_status()

        updates_widget.setLayout(updates_layout)
        tabs.addTab(updates_widget, "Updates")

        # ── Tab 3: Appearance (Basic) ───────────────────────────────────────
        basic_widget = QWidget()
        basic_layout = QVBoxLayout()

        basic_preset_row = QHBoxLayout()
        basic_preset_row.addWidget(QLabel("Quick preset:"))
        basic_preset_combo = QComboBox()
        basic_preset_combo.addItems(["Custom"] + list(_THEME_PRESETS.keys()))
        basic_preset_row.addWidget(basic_preset_combo)
        basic_apply_preset_btn = QPushButton("Apply")
        basic_preset_row.addWidget(basic_apply_preset_btn)
        basic_layout.addLayout(basic_preset_row)

        basic_font_row = QHBoxLayout()
        basic_font_row.addWidget(QLabel("Font:"))
        basic_font_combo = QComboBox()
        basic_available_fonts = sorted(QFontDatabase.families())
        basic_font_combo.addItems(["(default)"] + basic_available_fonts)
        current_basic_ff = self._theme.get("font_family", "")
        basic_font_combo.setCurrentText(current_basic_ff if current_basic_ff else "(default)")
        basic_font_row.addWidget(basic_font_combo)
        basic_layout.addLayout(basic_font_row)

        basic_size_row = QHBoxLayout()
        basic_size_row.addWidget(QLabel("Font size:"))
        basic_size_spin = QSpinBox()
        basic_size_spin.setRange(8, 36)
        basic_size_spin.setValue(int(self._theme.get("font_size", 13)))
        basic_size_row.addWidget(basic_size_spin)
        basic_layout.addLayout(basic_size_row)

        basic_color_buttons: Dict[str, tuple] = {}

        def _sync_basic_controls_from_theme():
            ff_basic = self._theme.get("font_family", "")
            if ff_basic and basic_font_combo.findText(ff_basic) == -1:
                basic_font_combo.addItem(ff_basic)
            basic_font_combo.setCurrentText(ff_basic if ff_basic else "(default)")
            basic_size_spin.setValue(int(self._theme.get("font_size", 13)))

            for k, (sw, cl) in basic_color_buttons.items():
                val = self._theme.get(k, "#ffffff")
                sw.setStyleSheet(
                    f"background-color:{val};border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                )
                cl.setText(val)

        def _make_basic_color_row(theme_key: str, label: str):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            swatch = QPushButton()
            swatch.setFixedSize(24, 24)
            color_label = QLabel(self._theme.get(theme_key, "#ffffff"))

            def _refresh_swatch():
                val = self._theme.get(theme_key, "#ffffff")
                swatch.setStyleSheet(
                    f"background-color:{val};border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                )
                color_label.setText(val)

            def _pick():
                from PyQt6.QtGui import QColor
                chosen = QColorDialog.getColor(QColor(self._theme.get(theme_key, "#ffffff")), dialog, f"Pick {label}")
                if chosen.isValid():
                    self._theme[theme_key] = chosen.name()
                    _refresh_swatch()
                    self._apply_theme()

            swatch.clicked.connect(_pick)
            _refresh_swatch()
            row.addWidget(swatch)
            row.addWidget(color_label)
            row.addStretch()
            basic_layout.addLayout(row)
            basic_color_buttons[theme_key] = (swatch, color_label)

        _make_basic_color_row("window_bg", "Window background:")
        _make_basic_color_row("header_bg", "Header background:")
        _make_basic_color_row("panel_bg", "Panel background:")
        _make_basic_color_row("chat_bg", "Chat background:")
        _make_basic_color_row("input_bg", "Input background:")
        _make_basic_color_row("text_color", "Text colour:")
        _make_basic_color_row("button_bg", "Button background:")

        def _theme_from_preset_name(name: str) -> Dict:
            preset_data = _THEME_PRESETS.get(name, {})
            merged = {**_THEME_DEFAULTS, **preset_data}

            # Fill omitted visual keys so preset changes propagate everywhere.
            if "header_bg" not in preset_data:
                merged["header_bg"] = merged.get("window_bg", _THEME_DEFAULTS["window_bg"])
            if "chat_bg" not in preset_data:
                merged["chat_bg"] = merged.get("panel_bg", _THEME_DEFAULTS["panel_bg"])
            if "input_bg" not in preset_data:
                merged["input_bg"] = merged.get("panel_bg", _THEME_DEFAULTS["panel_bg"])
            if "button_text" not in preset_data:
                merged["button_text"] = merged.get("text_color", _THEME_DEFAULTS["text_color"])
            if "timestamp_color" not in preset_data:
                merged["timestamp_color"] = merged.get("system_color", _THEME_DEFAULTS["system_color"])
            if "link_color" not in preset_data:
                merged["link_color"] = merged.get("msg_other_name", _THEME_DEFAULTS["link_color"])
            if "msg_own_text" not in preset_data:
                merged["msg_own_text"] = merged.get("text_color", _THEME_DEFAULTS["msg_own_text"])
            if "msg_other_text" not in preset_data:
                merged["msg_other_text"] = merged.get("text_color", _THEME_DEFAULTS["msg_other_text"])
            if "system_color" not in preset_data:
                merged["system_color"] = merged.get("text_color", _THEME_DEFAULTS["system_color"])

            return self._sanitize_theme(merged)

        basic_btn_row = QHBoxLayout()
        basic_apply_save_btn = QPushButton("Apply && Save")
        basic_reset_btn = QPushButton("Reset")
        basic_btn_row.addWidget(basic_apply_save_btn)
        basic_btn_row.addWidget(basic_reset_btn)
        basic_layout.addLayout(basic_btn_row)
        basic_layout.addStretch()

        def _apply_basic_preset():
            name = basic_preset_combo.currentText()
            if name == "Custom":
                return
            self._theme = _theme_from_preset_name(name)
            _sync_basic_controls_from_theme()
            self._apply_theme()

        def _apply_basic_and_save():
            ff = basic_font_combo.currentText()
            if ff != "(default)" and ff not in set(basic_available_fonts):
                ff = "(default)"
                basic_font_combo.setCurrentText("(default)")
            self._theme["font_family"] = "" if ff == "(default)" else ff
            self._theme["font_size"] = basic_size_spin.value()
            self._theme = self._sanitize_theme(self._theme)
            self._apply_theme()
            self._save_user_settings()
            self.load_messages()

        def _reset_basic():
            self._theme = copy.deepcopy(_THEME_DEFAULTS)
            _sync_basic_controls_from_theme()
            self._apply_theme()

        basic_apply_preset_btn.clicked.connect(_apply_basic_preset)
        basic_apply_save_btn.clicked.connect(_apply_basic_and_save)
        basic_reset_btn.clicked.connect(_reset_basic)

        basic_widget.setLayout(basic_layout)
        tabs.addTab(basic_widget, "Appearance")

        # ── Tab 4: Appearance (Advanced) ─────────────────────────────────────
        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_inner = QWidget()
        app_layout = QVBoxLayout()
        app_layout.setSpacing(6)

        # Preset row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Theme preset:"))
        preset_combo = QComboBox()
        preset_combo.addItems(["Custom"] + list(_THEME_PRESETS.keys()))
        preset_row.addWidget(preset_combo)
        apply_preset_btn = QPushButton("Apply Preset")
        preset_row.addWidget(apply_preset_btn)
        app_layout.addLayout(preset_row)

        # Color pickers
        color_settings = [
            ("window_bg",      "Window background"),
            ("panel_bg",       "Panel / widget background"),
            ("header_bg",      "Header background"),
            ("chat_bg",        "Chat area background"),
            ("input_bg",       "Input background"),
            ("border_color",   "Border / separator"),
            ("text_color",     "Main text"),
            ("button_bg",      "Button background"),
            ("button_border",  "Button border"),
            ("button_text",    "Button text"),
            ("timestamp_color", "Timestamp colour"),
            ("link_color",     "Link colour"),
            ("msg_own_name",   "Your username colour"),
            ("msg_other_name", "Other username colour"),
            ("msg_own_text",   "Your message text"),
            ("msg_other_text", "Other message text"),
            ("system_color",   "System message colour"),
        ]

        color_buttons: Dict[str, tuple] = {}

        for key, label in color_settings:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setMinimumWidth(200)
            row.addWidget(lbl)

            swatch = QPushButton()
            swatch.setFixedSize(24, 24)
            current_color = self._theme.get(key, "#ffffff")
            swatch.setStyleSheet(
                f"background-color:{current_color};"
                f"border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
            )
            color_label = QLabel(current_color)
            color_label.setMinimumWidth(76)

            def _make_clicker(k, sw, cl):
                def _click():
                    from PyQt6.QtGui import QColor
                    c = QColorDialog.getColor(QColor(self._theme.get(k, "#ffffff")), dialog, "Pick colour")
                    if c.isValid():
                        hex_val = c.name()
                        self._theme[k] = hex_val
                        sw.setStyleSheet(
                            f"background-color:{hex_val};"
                            f"border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                        )
                        cl.setText(hex_val)
                        self._apply_theme()
                return _click

            swatch.clicked.connect(_make_clicker(key, swatch, color_label))
            row.addWidget(swatch)
            row.addWidget(color_label)
            row.addStretch()
            app_layout.addLayout(row)
            color_buttons[key] = (swatch, color_label)

        # Font family
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font family:"))
        font_combo = QComboBox()
        available_fonts = set(QFontDatabase.families())
        preferred_fonts = [
            "Consolas", "Cascadia Code", "Courier New", "Lucida Console", "OCR A Extended",
            "Segoe UI", "Arial", "Verdana", "Calibri", "Tahoma", "Trebuchet MS",
            "Georgia", "Times New Roman", "Palatino Linotype", "Lucida Handwriting",
            "Comic Sans MS", "Papyrus", "Impact", "Jokerman", "Chiller", "Stencil",
            "Webdings", "Wingdings"
        ]
        ordered_fonts = [font for font in preferred_fonts if font in available_fonts]
        ordered_fonts.extend(sorted(font for font in available_fonts if font not in set(ordered_fonts)))
        font_combo.addItems(["(default)"] + ordered_fonts)
        current_ff = self._theme.get("font_family", "")
        if current_ff and current_ff not in ordered_fonts:
            font_combo.addItem(current_ff)
        font_combo.setCurrentText(current_ff if current_ff else "(default)")
        font_row.addWidget(font_combo)
        font_row.addStretch()
        app_layout.addLayout(font_row)

        # Font size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Font size (px):"))
        size_spin = QSpinBox()
        size_spin.setRange(8, 28)
        size_spin.setValue(int(self._theme.get("font_size", 13)))
        size_row.addWidget(size_spin)
        size_row.addStretch()
        app_layout.addLayout(size_row)

        # Extra style controls
        weight_row = QHBoxLayout()
        weight_row.addWidget(QLabel("Font weight:"))
        weight_spin = QSpinBox()
        weight_spin.setRange(100, 900)
        weight_spin.setSingleStep(100)
        weight_spin.setValue(int(self._theme.get("font_weight", 600)))
        weight_row.addWidget(weight_spin)
        weight_row.addStretch()
        app_layout.addLayout(weight_row)

        radius_row = QHBoxLayout()
        radius_row.addWidget(QLabel("Widget corner radius:"))
        widget_radius_spin = QSpinBox()
        widget_radius_spin.setRange(0, 24)
        widget_radius_spin.setValue(int(self._theme.get("widget_radius", 8)))
        radius_row.addWidget(widget_radius_spin)
        radius_row.addStretch()
        app_layout.addLayout(radius_row)

        button_radius_row = QHBoxLayout()
        button_radius_row.addWidget(QLabel("Button corner radius:"))
        button_radius_spin = QSpinBox()
        button_radius_spin.setRange(0, 24)
        button_radius_spin.setValue(int(self._theme.get("button_radius", 8)))
        button_radius_row.addWidget(button_radius_spin)
        button_radius_row.addStretch()
        app_layout.addLayout(button_radius_row)

        border_row = QHBoxLayout()
        border_row.addWidget(QLabel("Border width:"))
        border_width_spin = QSpinBox()
        border_width_spin.setRange(1, 4)
        border_width_spin.setValue(int(self._theme.get("border_width", 1)))
        border_row.addWidget(border_width_spin)
        border_row.addStretch()
        app_layout.addLayout(border_row)

        timestamp_row = QHBoxLayout()
        timestamp_row.addWidget(QLabel("Timestamp size (px):"))
        timestamp_spin = QSpinBox()
        timestamp_spin.setRange(8, 22)
        timestamp_spin.setValue(int(self._theme.get("timestamp_size", 11)))
        timestamp_row.addWidget(timestamp_spin)
        timestamp_row.addStretch()
        app_layout.addLayout(timestamp_row)

        name_weight_row = QHBoxLayout()
        name_weight_row.addWidget(QLabel("Username weight:"))
        name_weight_spin = QSpinBox()
        name_weight_spin.setRange(100, 900)
        name_weight_spin.setSingleStep(100)
        name_weight_spin.setValue(int(self._theme.get("username_weight", 700)))
        name_weight_row.addWidget(name_weight_spin)
        name_weight_row.addStretch()
        app_layout.addLayout(name_weight_row)

        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("Message spacing:"))
        message_spacing_spin = QSpinBox()
        message_spacing_spin.setRange(0, 20)
        message_spacing_spin.setValue(int(self._theme.get("message_spacing", 4)))
        spacing_row.addWidget(message_spacing_spin)
        spacing_row.addStretch()
        app_layout.addLayout(spacing_row)

        italic_row = QHBoxLayout()
        system_italic_chk = QCheckBox("Italic system messages")
        system_italic_chk.setChecked(bool(self._theme.get("system_italic", True)))
        italic_row.addWidget(system_italic_chk)
        italic_row.addStretch()
        app_layout.addLayout(italic_row)

        imgw_row = QHBoxLayout()
        imgw_row.addWidget(QLabel("Image max width (px):"))
        image_width_spin = QSpinBox()
        image_width_spin.setRange(120, 1600)
        image_width_spin.setValue(int(self._theme.get("image_max_width", 420)))
        imgw_row.addWidget(image_width_spin)
        imgw_row.addStretch()
        app_layout.addLayout(imgw_row)

        imgh_row = QHBoxLayout()
        imgh_row.addWidget(QLabel("Image max height (px):"))
        image_height_spin = QSpinBox()
        image_height_spin.setRange(120, 1200)
        image_height_spin.setValue(int(self._theme.get("image_max_height", 320)))
        imgh_row.addWidget(image_height_spin)
        imgh_row.addStretch()
        app_layout.addLayout(imgh_row)

        imgr_row = QHBoxLayout()
        imgr_row.addWidget(QLabel("Image corner radius:"))
        image_radius_spin = QSpinBox()
        image_radius_spin.setRange(0, 24)
        image_radius_spin.setValue(int(self._theme.get("image_radius", 6)))
        imgr_row.addWidget(image_radius_spin)
        imgr_row.addStretch()
        app_layout.addLayout(imgr_row)

        split_row = QHBoxLayout()
        split_row.addWidget(QLabel("Splitter handle size:"))
        splitter_size_spin = QSpinBox()
        splitter_size_spin.setRange(4, 24)
        splitter_size_spin.setValue(int(self._theme.get("splitter_handle_size", 8)))
        split_row.addWidget(splitter_size_spin)
        split_row.addStretch()
        app_layout.addLayout(split_row)

        # Apply / Reset buttons
        btn_row = QHBoxLayout()
        apply_theme_btn = QPushButton("Apply && Save")
        reset_theme_btn = QPushButton("Reset to Default")
        export_theme_btn = QPushButton("Export Theme")
        import_theme_btn = QPushButton("Import Theme")
        edit_json_btn = QPushButton("Advanced JSON")
        btn_row.addWidget(apply_theme_btn)
        btn_row.addWidget(reset_theme_btn)
        btn_row.addWidget(export_theme_btn)
        btn_row.addWidget(import_theme_btn)
        btn_row.addWidget(edit_json_btn)
        app_layout.addLayout(btn_row)
        app_layout.addStretch()

        app_inner.setLayout(app_layout)
        app_scroll.setWidget(app_inner)
        tabs.addTab(app_scroll, "Appearance (Advanced)")

        def _sync_controls_from_theme():
            _sync_basic_controls_from_theme()
            ff2 = self._theme.get("font_family", "")
            font_combo.setCurrentText(ff2 if ff2 else "(default)")
            size_spin.setValue(int(self._theme.get("font_size", 13)))
            weight_spin.setValue(int(self._theme.get("font_weight", 600)))
            widget_radius_spin.setValue(int(self._theme.get("widget_radius", 8)))
            button_radius_spin.setValue(int(self._theme.get("button_radius", 8)))
            border_width_spin.setValue(int(self._theme.get("border_width", 1)))
            timestamp_spin.setValue(int(self._theme.get("timestamp_size", 11)))
            name_weight_spin.setValue(int(self._theme.get("username_weight", 700)))
            message_spacing_spin.setValue(int(self._theme.get("message_spacing", 4)))
            system_italic_chk.setChecked(bool(self._theme.get("system_italic", True)))
            image_width_spin.setValue(int(self._theme.get("image_max_width", 420)))
            image_height_spin.setValue(int(self._theme.get("image_max_height", 320)))
            image_radius_spin.setValue(int(self._theme.get("image_radius", 6)))
            splitter_size_spin.setValue(int(self._theme.get("splitter_handle_size", 8)))

            for key, (sw, cl) in color_buttons.items():
                cv = self._theme.get(key, "#ffffff")
                sw.setStyleSheet(
                    f"background-color:{cv};"
                    f"border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                )
                cl.setText(cv)

        # ── Wire preset selector ──────────────────────────────────────────────
        def _apply_preset():
            name = preset_combo.currentText()
            if name == "Custom":
                return
            self._theme = _theme_from_preset_name(name)
            _sync_controls_from_theme()
            self._apply_theme()

        apply_preset_btn.clicked.connect(_apply_preset)

        # ── Wire apply & save ─────────────────────────────────────────────────
        def _apply_and_save():
            ff3 = font_combo.currentText()
            if ff3 != "(default)" and ff3 not in available_fonts:
                QMessageBox.warning(dialog, "Font not available", f"The font '{ff3}' is not installed. Using default font.")
                ff3 = "(default)"
                font_combo.setCurrentText("(default)")
            self._theme["font_family"] = "" if ff3 == "(default)" else ff3
            self._theme["font_size"] = size_spin.value()
            self._theme["font_weight"] = weight_spin.value()
            self._theme["widget_radius"] = widget_radius_spin.value()
            self._theme["button_radius"] = button_radius_spin.value()
            self._theme["border_width"] = border_width_spin.value()
            self._theme["timestamp_size"] = timestamp_spin.value()
            self._theme["username_weight"] = name_weight_spin.value()
            self._theme["message_spacing"] = message_spacing_spin.value()
            self._theme["system_italic"] = system_italic_chk.isChecked()
            self._theme["image_max_width"] = image_width_spin.value()
            self._theme["image_max_height"] = image_height_spin.value()
            self._theme["image_radius"] = image_radius_spin.value()
            self._theme["splitter_handle_size"] = splitter_size_spin.value()
            self._theme = self._sanitize_theme(self._theme)
            self._apply_theme()
            self._save_user_settings()
            self.load_messages()

        apply_theme_btn.clicked.connect(_apply_and_save)

        # ── Wire reset ────────────────────────────────────────────────────────
        def _reset_defaults():
            self._theme = copy.deepcopy(_THEME_DEFAULTS)
            _sync_controls_from_theme()
            self._apply_theme()

        reset_theme_btn.clicked.connect(_reset_defaults)

        def _export_theme():
            path, _ = QFileDialog.getSaveFileName(dialog, "Export Theme", "theme.json", "JSON Files (*.json)")
            if not path:
                return
            try:
                Path(path).write_text(json.dumps(self._sanitize_theme(self._theme), indent=2), encoding="utf-8")
                self.append_system_message(f"Theme exported: {path}")
            except Exception as e:
                QMessageBox.critical(dialog, "Export failed", str(e))

        def _import_theme():
            path, _ = QFileDialog.getOpenFileName(dialog, "Import Theme", "", "JSON Files (*.json)")
            if not path:
                return
            try:
                incoming = json.loads(Path(path).read_text(encoding="utf-8"))
                self._theme = self._sanitize_theme(incoming)
                _sync_controls_from_theme()
                self._apply_theme()
            except Exception as e:
                QMessageBox.critical(dialog, "Import failed", str(e))

        def _edit_theme_json():
            editor = QDialog(dialog)
            editor.setWindowTitle("Advanced Theme JSON")
            editor.setMinimumSize(640, 500)
            editor_layout = QVBoxLayout()
            text = QTextEdit()
            text.setPlainText(json.dumps(self._sanitize_theme(self._theme), indent=2))
            editor_layout.addWidget(text)
            btns = QHBoxLayout()
            apply_btn = QPushButton("Apply JSON")
            close_btn2 = QPushButton("Close")
            btns.addWidget(apply_btn)
            btns.addWidget(close_btn2)
            editor_layout.addLayout(btns)
            editor.setLayout(editor_layout)

            def _apply_json_text():
                try:
                    incoming = json.loads(text.toPlainText())
                    self._theme = self._sanitize_theme(incoming)
                    _sync_controls_from_theme()
                    self._apply_theme()
                except Exception as e:
                    QMessageBox.critical(editor, "Invalid JSON", str(e))

            apply_btn.clicked.connect(_apply_json_text)
            close_btn2.clicked.connect(editor.accept)
            editor.exec()

        export_theme_btn.clicked.connect(_export_theme)
        import_theme_btn.clicked.connect(_import_theme)
        edit_json_btn.clicked.connect(_edit_theme_json)

        _sync_controls_from_theme()

        outer.addWidget(tabs)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        outer.addWidget(close_btn)
        dialog.setLayout(outer)
        dialog.exec()
        # Persist any already-applied theme/sound changes when settings closes.
        self._save_user_settings()

    def _resolve_settings_path(self) -> Path:
        """Return a writable per-user settings path (works for source runs and packaged EXE)."""
        return _resolve_user_settings_path()

    def _load_user_settings(self):
        """Load persisted client-side settings."""
        try:
            if not self.settings_path.exists():
                return
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            sound_enabled = bool(data.get("sound_enabled", True))
            custom_sound = data.get("custom_sound_path")
            if custom_sound and not Path(custom_sound).exists():
                custom_sound = None

            self.notification_handler.set_sound_enabled(sound_enabled)
            self.notification_handler.set_custom_sound(custom_sound)

            saved_theme = data.get("theme")
            self._theme = self._sanitize_theme(saved_theme)
        except Exception:
            pass

    def _save_user_settings(self):
        """Persist client-side settings."""
        try:
            payload = {
                "sound_enabled": self.notification_handler.sound_enabled,
                "custom_sound_path": self.notification_handler.custom_sound_path,
                "theme": self._sanitize_theme(self._theme),
                "server_url": self.server_url,
            }
            self.settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _pick_custom_sound(self):
        """Choose a custom sound file for incoming messages from other users."""
        sound_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Notification Sound",
            "",
            "Audio Files (*.wav *.mp3);;All Files (*)",
        )
        if not sound_path:
            return

        self.notification_handler.set_custom_sound(sound_path)
        self._save_user_settings()
        self.append_system_message(f"Custom notification sound set: {sound_path}")

    def _toggle_notification_sound(self):
        """Toggle message notification sound for messages from other users."""
        new_state = not self.notification_handler.sound_enabled
        self.notification_handler.set_sound_enabled(new_state)
        self._save_user_settings()
        self.append_system_message(
            f"Notification sound {'enabled' if new_state else 'disabled'}."
        )

    def _clear_custom_sound(self):
        """Reset custom sound and fall back to default/system sound."""
        self.notification_handler.set_custom_sound(None)
        self._save_user_settings()
        self.append_system_message("Custom notification sound cleared.")
    
    def logout(self):
        """Logout user."""
        self.api_client.logout()
        self.close()
    
    def closeEvent(self, event):
        """Handle window close."""
        self._save_user_settings()
        if hasattr(self, "members_refresh_timer") and self.members_refresh_timer is not None:
            self.members_refresh_timer.stop()
        if hasattr(self, "invites_check_timer") and self.invites_check_timer is not None:
            self.invites_check_timer.stop()
        if hasattr(self, "update_check_timer") and self.update_check_timer is not None:
            self.update_check_timer.stop()
        if self.current_room:
            # Best effort to announce offline state when app closes.
            room_id = self.current_room
            threading.Thread(target=lambda: self.api_client.leave_room(room_id), daemon=True).start()
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread.wait(1500)
        self.room_refresh_thread.stop()
        self.room_refresh_thread.wait(1500)
        super().closeEvent(event)


class ChatApp(QApplication):
    """Main application class."""
    
    def __init__(self, argv, server_url: str = "http://localhost:8000"):
        super().__init__(argv)
        
        self.window = ChatWindow(server_url)
        if not self.window.show_login():
            sys.exit(0)
        self.window.show()


def main():
    """Main entry point."""
    # Prompt for server URL
    from PyQt6.QtWidgets import QInputDialog
    
    app_instance = QApplication(sys.argv)
    
    default_server_url = _load_saved_server_url("http://localhost:8000")

    # Get server URL from user (or use saved/default)
    server_url, ok = QInputDialog.getText(
        None,
        "Server Configuration",
        "Server URL:",
        text=default_server_url
    )
    
    if not ok:
        sys.exit(1)

    entered_server_url = str(server_url or "").strip() or default_server_url
    server_url = _normalize_server_url(entered_server_url, default_server_url)
    _save_server_url(server_url)

    if entered_server_url != server_url:
        QMessageBox.information(
            None,
            "Server URL Updated",
            f"Using normalized server URL:\n{server_url}"
        )
    
    app = ChatApp(sys.argv, server_url)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
