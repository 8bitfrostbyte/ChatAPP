"""
Main GUI application for encrypted chat client.
PyQt6-based user interface for Windows.
"""

import sys
import asyncio
import json
import requests
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QPushButton,
    QTextEdit, QTextBrowser, QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QFileDialog, QScrollArea, QInputDialog, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QFont
from PyQt6.QtGui import QDesktopServices

import requests
from websocket_client import WebSocketClient
from notification_handler import NotificationHandler


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
                timeout=10
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {}
        except Exception as e:
            return False, {}

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
                timeout=10
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
        
        self.setWindowTitle("Encrypted Chat")
        self.setGeometry(100, 100, 1000, 600)
        
        self.apply_dark_theme()

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()

        # Header row
        header_layout = QHBoxLayout()
        self.user_label = QLabel("User: not logged in")
        self.user_label.setObjectName("HeaderUserLabel")
        self.server_label = QLabel(f"Server: {self.server_url}")
        self.server_label.setObjectName("HeaderServerLabel")
        header_layout.addWidget(self.user_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.server_label)
        main_layout.addLayout(header_layout)

        # Content layout with resizable splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
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
        
        # Right side - Chat
        chat_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Room name
        self.room_name_label = QLabel("Select a room")
        self.room_name_label.setObjectName("RoomTitleLabel")
        right_layout.addWidget(self.room_name_label)
        
        # Messages
        self.message_display = QTextBrowser()
        self.message_display.setReadOnly(True)
        self.message_display.setOpenExternalLinks(False)
        self.message_display.anchorClicked.connect(self.open_message_link)
        right_layout.addWidget(self.message_display)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        right_layout.addWidget(self.message_input)
        
        # Button layout
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
        
        right_layout.addLayout(button_layout)

        chat_widget.setLayout(right_layout)

        self.main_splitter.addWidget(self.sidebar_widget)
        self.main_splitter.addWidget(chat_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([280, 720])

        main_layout.addWidget(self.main_splitter)
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

    def apply_dark_theme(self):
        """Apply a custom dark theme for the app."""
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #141a24;
                color: #e8edf5;
            }
            QLabel#HeaderUserLabel, QLabel#HeaderServerLabel {
                color: #8fa7c7;
                font-size: 11px;
            }
            QLabel#SectionLabel {
                color: #d6e1f2;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#RoomTitleLabel {
                color: #f2f6ff;
                font-size: 16px;
                font-weight: 700;
                padding: 4px 2px;
            }
            QListWidget, QTextEdit, QLineEdit {
                background-color: #1d2533;
                border: 1px solid #2f3d54;
                border-radius: 8px;
                padding: 6px;
                color: #e8edf5;
                selection-background-color: #2f4f7a;
            }
            QPushButton {
                background-color: #244063;
                border: 1px solid #33547c;
                border-radius: 8px;
                padding: 7px 10px;
                color: #edf3ff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2d4f78;
            }
            QPushButton:pressed {
                background-color: #1f3b5b;
            }
            QPushButton#SidebarToggleBtn {
                min-width: 88px;
            }
            QSplitter::handle {
                background-color: #2f3d54;
                width: 3px;
            }
            QScrollBar:vertical {
                background: #18202d;
                width: 10px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #2f4f7a;
                border-radius: 5px;
            }
            """
        )

    def toggle_sidebar(self):
        """Collapse/expand the left sidebar."""
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.sidebar_widget.setVisible(not self.sidebar_collapsed)
        self.toggle_sidebar_btn.setText("Expand" if self.sidebar_collapsed else "Collapse")

    def format_message_html(self, username: str, content: str, msg_type: str = "text") -> str:
        """Render a styled chat line with timestamp and role-specific colors."""
        timestamp = datetime.now().strftime("%H:%M")
        safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if "http://" in safe_content or "https://" in safe_content:
            for token in safe_content.split():
                if token.startswith("http://") or token.startswith("https://"):
                    safe_content = safe_content.replace(
                        token,
                        f'<a href="{token}" style="color:#7fb4ff;text-decoration:none;">{token}</a>'
                    )

        if msg_type == "system":
            return (
                f'<div style="margin:2px 0;color:#9aa8ba;font-style:italic;">'
                f'[{timestamp}] [SYSTEM] {safe_content}</div>'
            )

        is_self = username == self.api_client.username
        align = "right" if is_self else "left"
        bubble = "#2d5f57" if is_self else "#273349"
        name_color = "#8df2d4" if is_self else "#9bc3ff"

        return (
            f'<div style="text-align:{align};margin:4px 0;">'
            f'<span style="color:#8da0b9;font-size:11px;">[{timestamp}] </span>'
            f'<span style="color:{name_color};font-weight:700;">{username}</span><br>'
            f'<span style="display:inline-block;background:{bubble};padding:6px 10px;border-radius:10px;">'
            f'{safe_content}</span>'
            f'</div>'
        )

    def append_chat_message(self, username: str, content: str, msg_type: str = "text"):
        """Append one formatted message to the chat display."""
        self.message_display.append(self.format_message_html(username, content, msg_type))

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
        for room in rooms:
            item = QListWidgetItem(room["name"])
            item.setData(Qt.ItemDataRole.UserRole, room["id"])
            self.room_list.addItem(item)
    
    def on_room_selected(self, item):
        """Handle room selection — all network calls run in background."""
        room_id = item.data(Qt.ItemDataRole.UserRole)
        room_name = item.text()

        self.current_room = room_id
        self.room_name_label.setText(f"Room: {room_name}")
        self.message_display.clear()
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
            for msg in result["messages"]:
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
            for msg in messages:
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

        if content.startswith("!commands") or content.startswith("!commands"):
            self.show_room_commands()
            self.message_input.clear()
            return

        if content.startswith("!botcommand") or content.startswith("!botcommand"):
            self.show_bot_commands()
            self.message_input.clear()
            return

        if content.startswith("!room") or content.startswith("!createroom") or content.startswith("!removeroom") or content.startswith("!rooms") or content.startswith("!makeprivate"):
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
            "!clear <count> - Clear recent messages (creator clears room, others clear own)",
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
            "!bot search <tags> - Search for images",
            "!bot image <tags> - Fetch single image",
            "!bot blacklist show|add|remove - Manage blacklist"
        ]
        self.append_system_message(" | ".join(commands))

    def handle_bot_command(self, raw_command: str):
        """Handle !bot and Discord-like ! commands typed in chat input."""
        cmd = raw_command.strip()

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
                    "!addtags <tag1,tag2> | !removetags <tag1,tag2> | !taglist | !cleartags"
                )
                return

            shorthand_map = {
                "start":      lambda: self.handle_bot_command(f"!bot start {bang_rest}".strip()),
                "stop":       lambda: self.handle_bot_command("!bot stop"),
                "pause":      lambda: self.handle_bot_command("!bot pause"),
                "resume":     lambda: self.handle_bot_command("!bot resume"),
                "status":     lambda: self.handle_bot_command("!bot status"),
                "commands":   lambda: self.handle_bot_command("!bot commands"),
                "addtags":    lambda: self.handle_bot_command(f"!bot tags add {bang_rest}".strip()),
                "removetags": lambda: self.handle_bot_command(f"!bot tags remove {bang_rest}".strip()),
                "taglist":    lambda: self.handle_bot_command("!bot tags list"),
                "cleartags":  lambda: self.handle_bot_command("!bot tags clear"),
                "search":     lambda: self.handle_bot_command(f"!bot search {bang_rest}".strip()),
                "image":      lambda: self.handle_bot_command(f"!bot image {bang_rest}".strip()),
                "blacklist":  lambda: self.handle_bot_command(f"!bot blacklist {bang_rest}".strip()),
                "tags":       lambda: self.handle_bot_command(f"!bot tags {bang_rest}".strip()),
            }

            if bang_action in shorthand_map:
                shorthand_map[bang_action]()
                return

            self.append_system_message(
                "Unknown command. Available: !start !stop !pause !resume !status "
                "!search !image !addtags !removetags !taglist !cleartags !blacklist"
            )
            return

        parts = cmd.split(maxsplit=2)
        if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() in {"help", "commands"}):
            self.append_system_message(
                "Bot commands: !bot start <seconds> [tags] | !bot pause | !bot resume | !bot stop | !bot status | !bot commands | "
                "!bot search <query> | !bot image <tags> | "
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

        if not arg and action in {"search", "image", "blacklist"}:
            self.append_system_message("Invalid bot command. Use !bot help")
            return

        if action == "search":
            success, result = self.api_client.search_tags(arg)
            if not success:
                self.append_system_message(f"Bot search failed: {result}")
                return

            combined = result.get("combined", [])[:8]
            if not combined:
                self.append_system_message(f"No bot tag results for '{arg}'.")
                return

            summary = ", ".join(f"{item.get('name')}({item.get('count', 0)})" for item in combined)
            self.append_system_message(f"Bot search '{arg}': {summary}")
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
                self.append_system_message("Room commands: !room list | !room create <name> [private] | !room delete <name|id> | !room makeprivate")
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

            if action in {"delete", "remove"}:
                if len(parts) < 3:
                    self.append_system_message("Usage: !room delete <name|id>")
                    return
                room_part = " ".join(parts[2:]).strip()
                self.handle_room_command(f"!removeroom {room_part}")
                return

            self.append_system_message("Room commands: /room list | /room create <name> [private] | /room delete <name|id> | /room makeprivate")
            return

        self.append_system_message("Unknown room command. Use !createroom or !removeroom")
    
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
        """Handle user joined."""
        username = data.get("username", "Unknown")
        message = data.get("message", f"{username} joined")

        self.append_chat_message("SYSTEM", message, "system")
        self.notification_handler.notify_user_joined(username)
        self.refresh_members()
    
    def on_user_left(self, data: dict):
        """Handle user left — update members list only; offline message comes from server."""
        self.refresh_members()
    
    def on_typing(self, data: dict):
        """Handle typing indicator."""
        pass  # Could show "User is typing..."
    
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
        """Show settings dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout()
        
        # Sound toggle
        layout.addWidget(QLabel("Notifications:"))
        sound_checkbox = QPushButton("Toggle Sound")
        sound_checkbox.clicked.connect(
            lambda: self.notification_handler.set_sound_enabled(
                not self.notification_handler.sound_enabled
            )
        )
        layout.addWidget(sound_checkbox)
        
        dialog.setLayout(layout)
        dialog.exec()
    
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
