"""
WebSocket client for real-time messaging.
"""

import asyncio
import websockets
import json
from typing import Callable, Optional
from datetime import datetime


class WebSocketClient:
    """Manages WebSocket connection to the server."""
    
    def __init__(self, server_url: str, token: str, room_id: int):
        self.server_url = server_url
        self.token = token
        self.room_id = room_id
        self.websocket = None
        self.is_connected = False
        self.on_message_callback: Optional[Callable] = None
        self.on_user_joined_callback: Optional[Callable] = None
        self.on_user_left_callback: Optional[Callable] = None
        self.on_typing_callback: Optional[Callable] = None
        self.loop = None
        self.receive_task = None
    
    def set_on_message(self, callback: Callable):
        """Set callback for when a message is received."""
        self.on_message_callback = callback
    
    def set_on_user_joined(self, callback: Callable):
        """Set callback for when a user joins."""
        self.on_user_joined_callback = callback
    
    def set_on_user_left(self, callback: Callable):
        """Set callback for when a user leaves."""
        self.on_user_left_callback = callback
    
    def set_on_typing(self, callback: Callable):
        """Set callback for typing indicators."""
        self.on_typing_callback = callback
    
    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            ws_url = f"{self.server_url}/ws/rooms/{self.room_id}/{self.token}"
            # Convert https to wss, http to ws
            ws_url = ws_url.replace("https://", "wss://").replace("http://", "ws://")
            
            self.websocket = await websockets.connect(ws_url)
            self.is_connected = True
            print(f"Connected to room {self.room_id}")
            
            # Start receiving messages
            self.receive_task = asyncio.create_task(self._receive_loop())
        
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            self.is_connected = False
            raise
    
    async def _receive_loop(self):
        """Receive messages from the server."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            self.is_connected = False
        
        except Exception as e:
            print(f"WebSocket receive error: {e}")
            self.is_connected = False
    
    async def _handle_message(self, data: dict):
        """Handle incoming message based on type."""
        msg_type = data.get("type")
        
        if msg_type == "message_new":
            if self.on_message_callback:
                self.on_message_callback(data)
        
        elif msg_type == "user_joined":
            if self.on_user_joined_callback:
                self.on_user_joined_callback(data)
        
        elif msg_type == "user_left":
            if self.on_user_left_callback:
                self.on_user_left_callback(data)
        
        elif msg_type == "typing":
            if self.on_typing_callback:
                self.on_typing_callback(data)
        
        elif msg_type == "message_deleted":
            print(f"Message {data.get('message_id')} was deleted")
    
    async def send_message(self, content: str):
        """Send a text message."""
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        message = {
            "type": "message",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.websocket.send(json.dumps(message))
    
    async def send_typing(self):
        """Send typing indicator."""
        if not self.is_connected or not self.websocket:
            return
        
        message = {
            "type": "typing",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.websocket.send(json.dumps(message))
    
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket:
            if self.receive_task:
                self.receive_task.cancel()
            await self.websocket.close()
            self.is_connected = False
            print(f"Disconnected from room {self.room_id}")
