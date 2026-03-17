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
    QTextEdit, QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QFileDialog, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont

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
        
        self.setWindowTitle("Encrypted Chat")
        self.setGeometry(100, 100, 1000, 600)
        
        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left sidebar - Rooms
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Rooms:"))
        
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
        left_layout.addWidget(QLabel("In Room:"))
        self.members_list = QListWidget()
        self.members_list.setMaximumWidth(260)
        left_layout.addWidget(self.members_list)
        
        main_layout.addLayout(left_layout, 1)
        
        # Right side - Chat
        right_layout = QVBoxLayout()
        
        # Room name
        self.room_name_label = QLabel("Select a room")
        right_layout.addWidget(self.room_name_label)
        
        # Messages
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
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
        
        main_layout.addLayout(right_layout, 2)
        central_widget.setLayout(main_layout)
        
        # Refresh rooms timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_rooms)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def show_login(self):
        """Show login dialog."""
        dialog = LoginDialog(self.api_client, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_rooms()
            self.auto_join_default_room()

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
    
    def refresh_rooms(self):
        """Refresh list of available rooms."""
        success, rooms = self.api_client.list_rooms()
        if success:
            self.room_list.clear()
            for room in rooms:
                item = QListWidgetItem(room["name"])
                item.setData(Qt.ItemDataRole.UserRole, room["id"])
                self.room_list.addItem(item)
    
    def on_room_selected(self, item):
        """Handle room selection."""
        room_id = item.data(Qt.ItemDataRole.UserRole)
        room_name = item.text()
        
        self.current_room = room_id
        self.room_name_label.setText(f"Room: {room_name}")
        
        # Join room
        success, _ = self.api_client.join_room(room_id)
        if success:
            # Disconnect from previous WebSocket if any
            if self.websocket_thread:
                self.websocket_thread.stop()
                self.websocket_thread.wait()
            
            # Load message history
            self.load_messages()
            
            # Connect WebSocket
            self.connect_websocket()
            
            # Load members
            self.refresh_members()
        else:
            QMessageBox.warning(self, "Error", "Failed to join room")
    
    def load_messages(self):
        """Load message history for current room."""
        if not self.current_room:
            return
        
        self.message_display.clear()
        success, messages = self.api_client.get_messages(self.current_room, limit=50)
        if success:
            for msg in messages:
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")
                timestamp = msg.get("created_at", "")
                msg_type = msg.get("message_type", "text")
                
                if msg_type == "system":
                    display = f"[SYSTEM] {content}"
                else:
                    display = f"[{username}] {content}"
                
                self.message_display.append(display)
    
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
        self.message_display.append(f"[SYSTEM] {text}")

    def show_room_commands(self):
        """Display all room commands."""
        commands = [
            "Room Commands:",
            "!rooms - List all available rooms",
            "!createroom <name> [private] - Create a new room",
            "!removeroom <name|id> - Delete a room (creator-only)",
            "!makeprivate - Make current room private (creator-only)",
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

        if cmd.startswith("!"):
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

            if bang_action == "start":
                self.handle_bot_command(f"!bot start {bang_rest}".strip())
                return
            if bang_action == "stop":
                self.handle_bot_command("!bot stop")
                return
            if bang_action == "pause":
                self.handle_bot_command("!bot pause")
                return
            if bang_action == "resume":
                self.handle_bot_command("!bot resume")
                return
            if bang_action == "status":
                self.handle_bot_command("!bot status")
                return
            if bang_action == "commands":
                self.handle_bot_command("!bot commands")
                return
            if bang_action == "addtags":
                self.handle_bot_command(f"!bot tags add {bang_rest}".strip())
                return
            if bang_action == "removetags":
                self.handle_bot_command(f"!bot tags remove {bang_rest}".strip())
                return
            if bang_action == "taglist":
                self.handle_bot_command("!bot tags list")
                return
            if bang_action == "cleartags":
                self.handle_bot_command("!bot tags clear")
                return

            self.append_system_message("Unknown bot command. Use !help")
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
            if not image_url:
                self.append_system_message("Bot returned an image without URL.")
                return

            if self.websocket_thread and self.websocket_thread.client:
                self.websocket_thread.send_message(f"[BOT IMAGE] {image_url}")
                self.append_system_message("Bot image sent to room.")
            else:
                self.append_system_message(f"Bot image URL: {image_url}")
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
            display = f"[{username}] [Image] {data.get('file_url', '')}"
        else:
            display = f"[{username}] {content}"
        
        self.message_display.append(display)
        
        # Notification
        self.notification_handler.notify_message_received(username, content[:50])
    
    def on_user_joined(self, data: dict):
        """Handle user joined."""
        username = data.get("username", "Unknown")
        message = data.get("message", f"{username} joined")
        
        self.message_display.append(f"[SYSTEM] {message}")
        self.notification_handler.notify_user_joined(username)
        self.refresh_members()
    
    def on_user_left(self, data: dict):
        """Handle user left."""
        username = data.get("username", "Unknown")
        message = data.get("message", f"{username} left")
        
        self.message_display.append(f"[SYSTEM] {message}")
        self.notification_handler.notify_user_left(username)
        self.refresh_members()
    
    def on_typing(self, data: dict):
        """Handle typing indicator."""
        pass  # Could show "User is typing..."
    
    def refresh_members(self):
        """Refresh room members list."""
        if not self.current_room:
            return
        
        self.members_list.clear()
        success, members = self.api_client.get_room_members(self.current_room)
        if success:
            for member in members:
                item = QListWidgetItem(member["username"])
                self.members_list.addItem(item)
    
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
        self.refresh_timer.stop()
        super().closeEvent(event)


class ChatApp(QApplication):
    """Main application class."""
    
    def __init__(self, argv, server_url: str = "http://localhost:8000"):
        super().__init__(argv)
        
        self.window = ChatWindow(server_url)
        self.window.show_login()
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
