"""
Main GUI application for encrypted chat client.
PyQt6-based user interface for Windows.
"""

import sys
import copy
import asyncio
import json
import requests
import base64
import html
import re
import time
from typing import Optional, List, Dict
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QPushButton,
    QTextEdit, QTextBrowser, QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QFileDialog, QScrollArea, QInputDialog, QSplitter,
    QColorDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QFont
from PyQt6.QtGui import QDesktopServices

from websocket_client import WebSocketClient
from notification_handler import NotificationHandler

# ---------------------------------------------------------------------------
# Theme system
# ---------------------------------------------------------------------------
_THEME_DEFAULTS: Dict = {
    "window_bg":      "#141a24",
    "panel_bg":       "#1d2533",
    "border_color":   "#2f3d54",
    "text_color":     "#e8edf5",
    "button_bg":      "#244063",
    "button_border":  "#33547c",
    "button_text":    "#edf3ff",
    "font_family":    "",
    "font_size":      13,
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
        "window_bg": "#012456", "panel_bg": "#001232", "border_color": "#1a3f6f",
        "text_color": "#eeedf0", "button_bg": "#003080", "button_border": "#1a5096",
        "button_text": "#ffffff", "msg_own_name": "#ffff00", "msg_other_name": "#00dfff",
        "msg_own_text": "#eeedf0", "msg_other_text": "#eeedf0", "system_color": "#aaaaaa",
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
}


class APIClient:
    """Client for interacting with the server REST API."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
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
    
    def get_messages(self, room_id: int, limit: int = 50, offset: int = 0) -> tuple:
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
                files = {"file": f}
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
    
    def run(self):
        """Run the WebSocket connection."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.client = WebSocketClient(self.server_url, self.token, self.room_id)
            self.client.set_on_message(lambda data: self.message_received.emit(data))
            self.client.set_on_user_joined(lambda data: self.user_joined.emit(data))
            self.client.set_on_user_left(lambda data: self.user_left.emit(data))
            self.client.set_on_typing(lambda data: self.typing_received.emit(data))
            self.client.set_on_message_deleted(lambda data: self.message_deleted.emit(data))
            
            self.loop.run_until_complete(self.client.connect())
            self.loop.run_forever()
        
        except Exception as e:
            print(f"WebSocket thread error: {e}")
        
        finally:
            if self.loop:
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
            asyncio.run_coroutine_threadsafe(
                self.client.disconnect(),
                self.loop
            )


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


class ChatWindow(QMainWindow):
    """Main chat window."""
    
    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = server_url
        self.api_client = APIClient(server_url)
        self.current_room = None
        self.websocket_thread = None
        self.notification_handler = NotificationHandler(self)
        self.sidebar_collapsed = False
        self._image_cache = {}
        self._chat_raw_messages = []
        self._last_presence_message = None
        self._last_presence_at = 0.0
        self._rooms_data: Dict[int, dict] = {}  # room_id -> {is_private, created_by}
        self.settings_path = Path(__file__).parent / "user_settings.json"
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
        self.main_splitter.setCollapsible(0, True)
        self.main_splitter.setCollapsible(1, True)
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
        self.chat_splitter.setCollapsible(0, True)
        self.chat_splitter.setCollapsible(1, True)
        self.chat_splitter.setHandleWidth(8)
        self.chat_splitter.setOpaqueResize(True)

        self.message_display = QTextBrowser()
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
        self.message_input.returnPressed.connect(self.send_message)
        composer_layout.addWidget(self.message_input)

        button_layout = QHBoxLayout()

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        button_layout.addWidget(send_btn)

        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(self.upload_image)
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
        self.chat_splitter.setStretchFactor(0, 1)
        self.chat_splitter.setStretchFactor(1, 0)
        self.chat_splitter.setSizes([520, 120])

        # Top-edge drag support for message area (drag handle above messages).
        self.chat_area_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat_area_splitter.setChildrenCollapsible(True)
        self.chat_area_splitter.setCollapsible(0, True)
        self.chat_area_splitter.setCollapsible(1, True)
        self.chat_area_splitter.setHandleWidth(8)
        self.chat_area_splitter.setOpaqueResize(True)
        self.chat_area_splitter.addWidget(self.room_name_label)
        self.chat_area_splitter.addWidget(self.chat_splitter)
        self.chat_area_splitter.setStretchFactor(0, 0)
        self.chat_area_splitter.setStretchFactor(1, 1)
        self.chat_area_splitter.setSizes([34, 606])

        right_layout.addWidget(self.chat_area_splitter)

        chat_widget.setLayout(right_layout)

        self.main_splitter.addWidget(self.sidebar_widget)
        self.main_splitter.addWidget(chat_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([280, 720])

        # Global vertical splitter enables dragging from top edge too (collapse header).
        self.window_splitter = QSplitter(Qt.Orientation.Vertical)
        self.window_splitter.setChildrenCollapsible(True)
        self.window_splitter.setCollapsible(0, True)
        self.window_splitter.setCollapsible(1, True)
        self.window_splitter.setHandleWidth(8)
        self.window_splitter.setOpaqueResize(True)
        self.window_splitter.addWidget(header_widget)
        self.window_splitter.addWidget(self.main_splitter)
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
    
    def show_login(self) -> bool:
        """Show login dialog. Returns True only on successful login."""
        dialog = LoginDialog(self.api_client, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.user_label.setText(f"User: {self.api_client.username}")
            self.setWindowTitle(f"Encrypted Chat - {self.api_client.username}")
            self.refresh_rooms()
            self.auto_join_default_room()
            return True
        return False

    def _build_stylesheet(self) -> str:
        """Build a QSS stylesheet string from the current theme dict."""
        t = self._theme
        ff = t.get("font_family", "")
        fs = int(t.get("font_size", 13))
        font_widget = f"font-family: '{ff}';" if ff else ""
        font_text   = (f"font-family: '{ff}';" if ff else "") + f" font-size: {fs}px;"
        hover_btn   = t.get("button_border", "#33547c")
        pressed_btn = t.get("window_bg", "#141a24")
        return f"""
            QMainWindow, QWidget {{
                background-color: {t['window_bg']};
                color: {t['text_color']};
                {font_widget}
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
            QListWidget, QTextEdit, QLineEdit {{
                background-color: {t['panel_bg']};
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                padding: 6px;
                color: {t['text_color']};
                selection-background-color: {t['button_bg']};
                {font_text}
            }}
            QPushButton {{
                background-color: {t['button_bg']};
                border: 1px solid {t['button_border']};
                border-radius: 8px;
                padding: 7px 10px;
                color: {t['button_text']};
                font-weight: 600;
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
                width: 8px;
                height: 8px;
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
        self.setStyleSheet(self._build_stylesheet())

    def apply_dark_theme(self):
        """Apply initial theme (uses persisted or default settings)."""
        self._apply_theme()

    def toggle_sidebar(self):
        """Collapse/expand the left sidebar."""
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.sidebar_widget.setVisible(not self.sidebar_collapsed)
        self.toggle_sidebar_btn.setText("Expand" if self.sidebar_collapsed else "Collapse")

    def _extract_image_urls(self, content: str) -> List[str]:
        return re.findall(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s]*)?', content, re.IGNORECASE)

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
        """Fetch one image and return in-memory data URI for embedding (no disk writes)."""
        if url in self._image_cache:
            return self._image_cache[url]

        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()

            content_type = (response.headers.get("content-type") or "").lower()
            mime_type = "image/jpeg"
            if "png" in content_type:
                mime_type = "image/png"
            elif "gif" in content_type:
                mime_type = "image/gif"
            elif "webp" in content_type:
                mime_type = "image/webp"
            elif "jpeg" in content_type or "jpg" in content_type:
                mime_type = "image/jpeg"

            encoded = base64.b64encode(response.content).decode("ascii")
            data_uri = f"data:{mime_type};base64,{encoded}"
            self._image_cache[url] = data_uri
            return data_uri
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
        text_html = re.sub(
            r'(https?://[^\s<]+)',
            r'<a href="\1" style="color:#7fb4ff;text-decoration:none;word-break:break-all;">\1</a>',
            text_html,
            flags=re.IGNORECASE,
        )

        images_html = []
        for url in image_urls:
            src = embedded_sources.get(url)
            if src:
                images_html.append(
                    f'<img src="{src}" style="max-width:420px;max-height:320px;'
                    f'border-radius:6px;display:block;margin:8px 0;">'
                )
            else:
                images_html.append(
                    f'<a href="{url}" style="color:#7fb4ff;text-decoration:none;word-break:break-all;">{html.escape(url)}</a>'
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
        font_style = (f"font-family:'{ff}';" if ff else "") + f"font-size:{fs}px;"

        if msg_type == "system":
            return (
                f'<div style="margin:2px 0;color:{t["system_color"]};font-style:italic;{font_style}">'
                f'[{timestamp}] [SYSTEM] {body_html}</div>'
            )

        is_self = username == self.api_client.username
        align = "right" if is_self else "left"
        name_color = t["msg_own_name"] if is_self else t["msg_other_name"]
        text_color = t["msg_own_text"] if is_self else t["msg_other_text"]

        return (
            f'<div style="text-align:{align};margin:4px 0;">'
            f'<span style="color:{t["system_color"]};font-size:11px;">[{timestamp}] </span>'
            f'<span style="color:{name_color};font-weight:700;">{username}</span><br>'
            f'<span style="color:{text_color};{font_style}">{body_html}</span>'
            f'</div>'
        )

    def append_chat_message(self, username: str, content: str, msg_type: str = "text"):
        """Append one formatted message to the chat display."""
        if self._is_duplicate_presence_message(content, msg_type):
            return

        self._chat_raw_messages.append({
            "username": username,
            "content": content,
            "msg_type": msg_type,
        })

        image_urls = self._extract_image_urls(content)

        if msg_type != "system" and image_urls:
            # Download images in background and append exactly one rendered message.
            def _fetch_embeds(message_content, urls):
                sources = {}
                for image_url in urls:
                    uri = self._cache_image_url(image_url)
                    if uri:
                        sources[image_url] = uri
                return self._build_message_body_html(message_content, sources)

            def _apply(body_html):
                if not body_html:
                    body_html = self._build_message_body_html(content, {})
                self.message_display.append(self.format_message_html(username, body_html, msg_type))

            self._run_in_bg(_fetch_embeds, _apply, content, image_urls)
            return

        body_html = self._build_message_body_html(content, {})
        self.message_display.append(self.format_message_html(username, body_html, msg_type))

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

    def _update_room_list(self, rooms: list):
        """Update the room list widget (safe to call from any thread via signal)."""
        self.room_list.clear()
        self._rooms_data.clear()
        for room in rooms:
            is_private = bool(room.get("is_private", False))
            created_by = room.get("created_by")
            prefix = "🔒 " if is_private else ""
            item = QListWidgetItem(f"{prefix}{room['name']}")
            item.setData(Qt.ItemDataRole.UserRole, room["id"])
            self.room_list.addItem(item)
            self._rooms_data[room["id"]] = {
                "is_private": is_private,
                "created_by": created_by,
                "name": room["name"],
            }
    
    def on_room_selected(self, item):
        """Handle room selection — all network calls run in background."""
        room_id = item.data(Qt.ItemDataRole.UserRole)
        room_name = item.text()

        self.current_room = room_id
        self.room_name_label.setText(f"Room: {room_name}")
        self.message_display.clear()
        self._chat_raw_messages.clear()
        self.members_list.clear()

        # Stop previous WebSocket immediately (no blocking wait)
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread = None

        def _fetch(rid):
            ok_join, _ = self.api_client.join_room(rid)
            if not ok_join:
                return None
            ok_msgs, messages = self.api_client.get_messages(rid, limit=50)
            ok_mbrs, members = self.api_client.get_room_members(rid)
            return {
                "messages": messages if ok_msgs else [],
                "members": members if ok_mbrs else [],
            }

        def _apply(result):
            if result is None:
                QMessageBox.warning(self, "Error", "Failed to join room")
                return
            self.message_display.clear()
            self._chat_raw_messages.clear()
            deduped_messages = self._dedupe_presence_history(result["messages"])
            for msg in deduped_messages:
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")
                msg_type = msg.get("message_type", "text")
                self.append_chat_message(username, content, msg_type)
            self._update_members(result["members"])
            self.connect_websocket()

        self._run_in_bg(_fetch, _apply, room_id)

    def load_messages(self):
        """Reload message history for current room in background."""
        if not self.current_room:
            return
        def _fetch(rid):
            ok, msgs = self.api_client.get_messages(rid, limit=50)
            return msgs if ok else []
        def _apply(messages):
            self.message_display.clear()
            self._chat_raw_messages.clear()
            deduped_messages = self._dedupe_presence_history(messages)
            for msg in deduped_messages:
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")
                msg_type = msg.get("message_type", "text")
                self.append_chat_message(username, content, msg_type)
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

        if content.startswith("!botcommand") or content.startswith("!botcommands"):
            self.show_bot_commands()
            self.message_input.clear()
            return

        if content.startswith("!room") or content.startswith("!createroom") or content.startswith("!removeroom") or content.startswith("!rooms") or content.startswith("!makeprivate") or content.startswith("!invite"):
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
            "!invite <username> - Invite a user to current room (creator-only)",
            "!clear <count> - Clear recent non-system messages in this room",
            "!saveimages [folder_path] - Save all image URLs currently visible in chat to a folder",
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
            "!removetags <tag1,tag2> - Remove tags from saved pool",
            "!taglist - Show saved tags",
            "!cleartags - Clear all saved tags",
            "!botcommands - Show this bot command list",
            "!bot search <tags> - Search for images",
            "!searchtags <query> - Detailed tag search (botUpdated-style)",
            "!bot image <tags> - Fetch single image",
            "!bot blacklist show|add|remove - Manage blacklist"
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
                    "!addtags <tag1,tag2> | !removetags <tag1,tag2> | !taglist | !cleartags | !saveimages [folder_path]"
                )
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
                "!bot blacklist show | !bot blacklist add <tag1,tag2> | !bot blacklist remove <tag1,tag2>"
            )
            return

        if len(parts) < 2:
            self.append_system_message("Invalid bot command. Use !bot help")
            return

        action = parts[1].lower()
        arg = parts[2].strip() if len(parts) > 2 else ""

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
            success, result = self.api_client.start_bot_stream(self.current_room, interval, tags)
            if not success:
                self.append_system_message(f"Failed to start stream: {result}")
                return

            mode = result.get("mode", "?")
            pool = result.get("tag_pool", [])
            self.append_system_message(
                f"Bot stream started: every {interval:g}s | mode: {mode} | tags: {', '.join(pool) if pool else 'rating:explicit'}"
            )
            return

        if action == "stop":
            if not self.current_room:
                self.append_system_message("Join a room first before stopping bot stream.")
                return
            success, result = self.api_client.stop_bot_stream(self.current_room)
            if not success:
                self.append_system_message(f"Failed to stop stream: {result}")
                return
            self.append_system_message("Bot stream stopped.")
            return

        if action == "pause":
            if not self.current_room:
                self.append_system_message("Join a room first before pausing bot stream.")
                return
            success, result = self.api_client.pause_bot_stream(self.current_room)
            if not success:
                self.append_system_message(f"Failed to pause stream: {result}")
                return
            self.append_system_message("Bot stream paused.")
            return

        if action == "resume":
            if not self.current_room:
                self.append_system_message("Join a room first before resuming bot stream.")
                return
            success, result = self.api_client.resume_bot_stream(self.current_room)
            if not success:
                self.append_system_message(f"Failed to resume stream: {result}")
                return
            self.append_system_message("Bot stream resumed.")
            return

        if action == "status":
            if not self.current_room:
                self.append_system_message("Join a room first before checking bot stream status.")
                return
            success, result = self.api_client.bot_stream_status(self.current_room)
            if not success:
                self.append_system_message(f"Failed to get stream status: {result}")
                return

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
            return

        if action == "tags":
            tags_parts = arg.split(maxsplit=1) if arg else []
            tags_action = tags_parts[0].lower() if tags_parts else ""
            tags_arg = tags_parts[1].strip() if len(tags_parts) > 1 else ""

            if tags_action == "list":
                success, result = self.api_client.get_saved_tags()
                if not success:
                    self.append_system_message(f"Failed to fetch saved tags: {result}")
                    return
                saved = result.get("saved_tags", [])
                self.append_system_message(
                    f"Saved tags ({len(saved)}): {', '.join(saved) if saved else 'empty'}"
                )
                return

            if tags_action == "add" and tags_arg:
                success, result = self.api_client.add_saved_tags(tags_arg)
                if not success:
                    self.append_system_message(f"Failed to add tags: {result}")
                    return
                self.append_system_message(
                    f"Added tags: {result.get('added', 0)} | Saved total: {len(result.get('saved_tags', []))}"
                )
                return

            if tags_action == "remove" and tags_arg:
                success, result = self.api_client.remove_saved_tags(tags_arg)
                if not success:
                    self.append_system_message(f"Failed to remove tags: {result}")
                    return
                self.append_system_message(
                    f"Removed tags: {result.get('removed', 0)} | Saved total: {len(result.get('saved_tags', []))}"
                )
                return

            if tags_action == "clear":
                success, result = self.api_client.clear_saved_tags()
                if not success:
                    self.append_system_message(f"Failed to clear tags: {result}")
                    return
                self.append_system_message(f"Cleared saved tags. Removed: {result.get('removed', 0)}")
                return

            self.append_system_message("Usage: !bot tags list|add <tags>|remove <tags>|clear")
            return

        if not arg and action in {"search", "searchtags", "image", "blacklist"}:
            self.append_system_message("Invalid bot command. Use !bot help")
            return

        if action in {"search", "searchtags"}:
            success, result = self.api_client.search_tags(arg)
            if not success:
                self.append_system_message(f"Bot search failed: {result}")
                return

            combined = result.get("combined", [])
            if not combined:
                self.append_system_message(f"No tags found for '{result.get('query', arg)}'.")
                return

            query_tag = result.get("query", arg.strip().lower().replace(" ", "_"))

            # Always present exact input tag first when present, then sort remaining by total images.
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

            # Compact list format: trap(11061), trap_on_trap(8009), ...
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
            return

        if action == "image":
            success, result = self.api_client.fetch_bot_images(arg, limit=1)
            if not success:
                self.append_system_message(f"Bot image fetch failed: {result}")
                return

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
            return

        if action == "blacklist":
            bl_parts = arg.split(maxsplit=1)
            bl_action = bl_parts[0].lower()
            bl_tags = bl_parts[1].strip() if len(bl_parts) > 1 else ""

            if bl_action == "show":
                success, result = self.api_client.get_bot_blacklist()
                if not success:
                    self.append_system_message(f"Failed to fetch blacklist: {result}")
                    return
                tags = result.get("blacklist", [])
                self.append_system_message(
                    f"Bot blacklist ({len(tags)}): {', '.join(tags) if tags else 'empty'}"
                )
                return

            if bl_action == "add" and bl_tags:
                success, result = self.api_client.add_bot_blacklist(bl_tags)
                if not success:
                    self.append_system_message(f"Failed to add blacklist tags: {result}")
                    return
                self.append_system_message(
                    f"Added blacklist tags. Total: {len(result.get('blacklist', []))}"
                )
                return

            if bl_action == "remove" and bl_tags:
                success, result = self.api_client.remove_bot_blacklist(bl_tags)
                if not success:
                    self.append_system_message(f"Failed to remove blacklist tags: {result}")
                    return
                self.append_system_message(
                    f"Removed blacklist tags. Total: {len(result.get('blacklist', []))}"
                )
                return

            self.append_system_message("Usage: !bot blacklist show|add <tags>|remove <tags>")
            return

        self.append_system_message("Unknown bot command. Use !bot help")

    def handle_room_command(self, raw_command: str):
        """Handle room creation/deletion commands from chat input."""
        cmd = raw_command.strip()

        if cmd.startswith("!makeprivate"):
            if not self.current_room:
                self.append_system_message("Join a room first, then run !makeprivate")
                return

            success, result = self.api_client.make_room_private(self.current_room)
            if not success:
                self.append_system_message(f"Make private failed: {result}")
                return

            self.append_system_message(result.get("message", "Room is now private"))
            self.refresh_rooms()
            return

        if cmd.startswith("!invite"):
            rest = cmd[len("!invite"):].strip()
            if not rest:
                self.append_system_message("Usage: !invite <username>")
                return
            if not self.current_room:
                self.append_system_message("Join a room first, then run !invite <username>")
                return
            success, result = self.api_client.invite_user(self.current_room, rest)
            if not success:
                self.append_system_message(f"Invite failed: {result}")
                return
            self.append_system_message(result.get("message", f"Invited {rest}"))
            return

        if cmd.startswith("!rooms"):
            success, rooms = self.api_client.list_rooms()
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

            success, result = self.api_client.create_room(rest, is_private=is_private)
            if not success:
                self.append_system_message(f"Create room failed: {result}")
                return

            self.append_system_message(
                f"Room created: {result.get('name', rest)}"
                f" ({'private' if is_private else 'public'})"
            )
            self.refresh_rooms()
            return

        if cmd.startswith("!removeroom"):
            rest = cmd[len("!removeroom"):].strip()
            if not rest:
                self.append_system_message("Usage: !removeroom <room name or room id>")
                return

            target_room_id = None
            if rest.isdigit():
                target_room_id = int(rest)
            else:
                ok, rooms = self.api_client.list_rooms()
                if ok:
                    for room in rooms:
                        if room.get("name", "").strip().lower() == rest.lower():
                            target_room_id = room.get("id")
                            break

            if not target_room_id:
                self.append_system_message(f"Room not found: {rest}")
                return

            success, result = self.api_client.delete_room(target_room_id)
            if not success:
                self.append_system_message(f"Remove room failed: {result}")
                return

            self.append_system_message(f"Room removed (id={target_room_id}).")

            if self.current_room == target_room_id:
                self.current_room = None
                self.room_name_label.setText("Select a room")
                self.message_display.clear()
                self.members_list.clear()
                if self.websocket_thread:
                    self.websocket_thread.stop()
                    self.websocket_thread.wait()
                    self.websocket_thread = None

            self.refresh_rooms()
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
    
    def upload_image(self):
        """Upload an image to the current room."""
        if not self.current_room:
            QMessageBox.warning(self, "Error", "Please select a room first")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp)"
        )
        if file_path:
            success, result = self.api_client.upload_file(self.current_room, file_path)
            if success:
                QMessageBox.information(self, "Success", "Image uploaded")
                self.load_messages()
            else:
                QMessageBox.critical(self, "Error", f"Upload failed: {result}")
    
    def connect_websocket(self):
        """Connect to WebSocket for real-time messaging."""
        if not self.current_room:
            return
        
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
        username = data.get("username", "Unknown")
        content = data.get("content", "")
        msg_type = data.get("message_type", "text")

        if msg_type == "image":
            content = f"[Image] {data.get('file_url', '')}"

        self.append_chat_message(username, content, msg_type)
        
        # Only notify (sound) for messages from other users
        if username != self.api_client.username:
            self.notification_handler.notify_message_received(username, content[:50])
    
    def on_user_joined(self, data: dict):
        """Handle user joined — suppress the notice for the user who joined."""
        username = data.get("username", "Unknown")
        # The user who triggered the join already knows they joined; only show to others.
        if username == self.api_client.username:
            self.refresh_members()
            return
        message = f"{username} is online"
        self.append_chat_message("SYSTEM", message, "system")
        self.notification_handler.notify_user_joined(username)
        self.refresh_members()
    
    def on_user_left(self, data: dict):
        """Handle user left."""
        username = data.get("username", "Unknown")
        message = f"{username} is offline"

        self.append_chat_message("SYSTEM", message, "system")
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
            success, result = self.api_client.create_room(room_name)
            if success:
                QMessageBox.information(self, "Success", "Room created")
                self.refresh_rooms()
            else:
                QMessageBox.critical(self, "Error", str(result))
    
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

        # ── Tab 2: Appearance ─────────────────────────────────────────────────
        app_scroll = QScrollArea()
        app_scroll.setWidgetResizable(True)
        app_inner = QWidget()
        app_layout = QVBoxLayout()
        app_layout.setSpacing(6)

        # Preset row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Theme preset:"))
        preset_combo = QComboBox()
        preset_combo.addItems(["Custom", "Dark (Default)", "PowerShell", "Light", "Midnight Blue", "Forest Green"])
        preset_row.addWidget(preset_combo)
        apply_preset_btn = QPushButton("Apply Preset")
        preset_row.addWidget(apply_preset_btn)
        app_layout.addLayout(preset_row)

        # Color pickers
        color_settings = [
            ("window_bg",      "Window background"),
            ("panel_bg",       "Panel / widget background"),
            ("border_color",   "Border / separator"),
            ("text_color",     "Main text"),
            ("button_bg",      "Button background"),
            ("button_border",  "Button border"),
            ("button_text",    "Button text"),
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
        font_combo.addItems(["(default)", "Consolas", "Courier New", "Segoe UI", "Arial",
                             "Verdana", "Calibri", "Tahoma", "Lucida Console", "Cascadia Code"])
        current_ff = self._theme.get("font_family", "")
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

        # Apply / Reset buttons
        btn_row = QHBoxLayout()
        apply_theme_btn = QPushButton("Apply && Save")
        reset_theme_btn = QPushButton("Reset to Default")
        btn_row.addWidget(apply_theme_btn)
        btn_row.addWidget(reset_theme_btn)
        app_layout.addLayout(btn_row)
        app_layout.addStretch()

        app_inner.setLayout(app_layout)
        app_scroll.setWidget(app_inner)
        tabs.addTab(app_scroll, "Appearance")

        # ── Wire preset selector ──────────────────────────────────────────────
        def _apply_preset():
            name = preset_combo.currentText()
            if name == "Custom":
                return
            preset_data = _THEME_PRESETS.get(name, {})
            for k, v in preset_data.items():
                self._theme[k] = v
            ff2 = self._theme.get("font_family", "")
            font_combo.setCurrentText(ff2 if ff2 else "(default)")
            size_spin.setValue(int(self._theme.get("font_size", 13)))
            for k2, (sw2, cl2) in color_buttons.items():
                cv = self._theme.get(k2, "#ffffff")
                sw2.setStyleSheet(
                    f"background-color:{cv};"
                    f"border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                )
                cl2.setText(cv)

        apply_preset_btn.clicked.connect(_apply_preset)

        # ── Wire apply & save ─────────────────────────────────────────────────
        def _apply_and_save():
            ff3 = font_combo.currentText()
            self._theme["font_family"] = "" if ff3 == "(default)" else ff3
            self._theme["font_size"] = size_spin.value()
            self._apply_theme()
            self._save_user_settings()
            self.load_messages()

        apply_theme_btn.clicked.connect(_apply_and_save)

        # ── Wire reset ────────────────────────────────────────────────────────
        def _reset_defaults():
            self._theme = copy.deepcopy(_THEME_DEFAULTS)
            font_combo.setCurrentText("(default)")
            size_spin.setValue(13)
            for k3, (sw3, cl3) in color_buttons.items():
                cv2 = self._theme.get(k3, "#ffffff")
                sw3.setStyleSheet(
                    f"background-color:{cv2};"
                    f"border:1px solid #888;border-radius:4px;min-width:0;padding:0;"
                )
                cl3.setText(cv2)

        reset_theme_btn.clicked.connect(_reset_defaults)

        outer.addWidget(tabs)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        outer.addWidget(close_btn)
        dialog.setLayout(outer)
        dialog.exec()

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
            if isinstance(saved_theme, dict):
                for k, v in saved_theme.items():
                    if k in _THEME_DEFAULTS:
                        self._theme[k] = v
        except Exception:
            pass

    def _save_user_settings(self):
        """Persist client-side settings."""
        try:
            payload = {
                "sound_enabled": self.notification_handler.sound_enabled,
                "custom_sound_path": self.notification_handler.custom_sound_path,
                "theme": self._theme,
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
        if self.current_room:
            # Best effort to announce offline state when app closes.
            self.api_client.leave_room(self.current_room)
        if self.websocket_thread:
            self.websocket_thread.stop()
        self.room_refresh_thread.stop()
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
    
    # Get server URL from user (or use default)
    server_url, ok = QInputDialog.getText(
        None,
        "Server Configuration",
        "Server URL (default: http://localhost:8000):",
        text="http://localhost:8000"
    )
    
    if not ok:
        sys.exit(1)
    
    app = ChatApp(sys.argv, server_url)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
